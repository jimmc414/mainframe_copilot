"""S3270 Session Manager - Manages persistent s3270 subprocess"""

import subprocess
import threading
import queue
import time
import hashlib
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class StatusLine:
    """Parsed s3270 status line"""
    keyboard_state: str  # L=locked, U=unlocked, E=error
    screen_formatting: str  # F=formatted, U=unformatted
    field_protection: str  # P=protected, U=unprotected
    connection_state: str  # C=connected, N=not connected
    emulator_mode: str  # I=3270 mode, N=NVT mode, P=processing
    model_number: str  # 2,3,4,5
    rows: int
    cols: int
    cursor_row: int
    cursor_col: int
    window_id: str
    exec_time: float

    @classmethod
    def parse(cls, line: str) -> 'StatusLine':
        """Parse s3270 status line format"""
        parts = line.strip().split()
        # Status lines should have at least 11 parts
        if len(parts) < 11:
            raise ValueError(f"Invalid status line: {line}")

        # Parse dimensions and cursor position
        try:
            dims = parts[6].split(',') if len(parts) > 6 else ['24', '80']
            rows = int(dims[0]) if dims[0] else 24
            cols = int(dims[1]) if len(dims) > 1 and dims[1] else 80

            cursor = parts[8].split(',') if len(parts) > 8 else ['0', '0']
            cursor_row = int(cursor[0]) if cursor[0] else 0
            cursor_col = int(cursor[1]) if len(cursor) > 1 and cursor[1] else 0
        except (ValueError, IndexError):
            rows, cols = 24, 80
            cursor_row, cursor_col = 0, 0

        return cls(
            keyboard_state=parts[0] if parts else 'U',
            screen_formatting=parts[1] if len(parts) > 1 else 'F',
            field_protection=parts[2] if len(parts) > 2 else 'U',
            connection_state=parts[3][0] if len(parts) > 3 and '(' in parts[3] else parts[3] if len(parts) > 3 else 'N',
            emulator_mode=parts[4] if len(parts) > 4 else 'N',
            model_number=parts[5] if len(parts) > 5 else '2',
            rows=rows,
            cols=cols,
            cursor_row=cursor_row,
            cursor_col=cursor_col,
            window_id=parts[9] if len(parts) > 9 else '0x0',
            exec_time=float(parts[10]) if len(parts) > 10 else 0.0
        )

class S3270Session:
    """Manages a persistent s3270 subprocess"""

    def __init__(self, trace_file: Optional[str] = None):
        """Initialize S3270 session"""
        self.process: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.output_queue: queue.Queue = queue.Queue()
        self.trace_file = trace_file
        self.connected = False
        self.last_status: Optional[StatusLine] = None
        self.model = "3278-2"

    def start(self):
        """Start s3270 subprocess"""
        if self.process and self.process.poll() is None:
            return  # Already running

        cmd = ["s3270", "-script", "-model", self.model]
        if self.trace_file:
            cmd.extend(["-trace", "-tracefile", self.trace_file])

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Start reader thread
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

        # Wait for initial prompt
        time.sleep(0.1)

    def stop(self):
        """Stop s3270 subprocess"""
        if self.process:
            if self.connected:
                self.disconnect()
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def _read_output(self):
        """Read output from s3270 in background thread"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_queue.put(line.strip())
            except Exception as e:
                logger.error(f"Reader thread error: {e}")
                break

    def _send_command(self, command: str, timeout: float = 5.0) -> List[str]:
        """Send command and collect response"""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("s3270 process not running")

        # Clear queue
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

        # Send command
        self.process.stdin.write(f"{command}\n")
        self.process.stdin.flush()

        # Collect response
        response = []
        start_time = time.time()
        status_seen = False

        while time.time() - start_time < timeout:
            try:
                line = self.output_queue.get(timeout=0.1)
                response.append(line)

                # Check if this looks like a status line
                if line and line[0] in "LUEFN" and len(line.split()) >= 12:
                    try:
                        self.last_status = StatusLine.parse(line)
                        status_seen = True
                    except ValueError:
                        pass

                # "ok" or "error" indicates command completion
                if line in ["ok", "error"]:
                    break

            except queue.Empty:
                if status_seen:
                    break
                continue

        return response

    def connect(self, host: str = "127.0.0.1:3270") -> bool:
        """Connect to TN3270 host"""
        if not host.startswith(("127.0.0.1:", "localhost:")):
            raise ValueError("Only localhost connections allowed")

        if not self.process:
            self.start()

        response = self._send_command(f"Connect({host})")

        # Check for successful connection
        if self.last_status and self.last_status.connection_state == "C":
            self.connected = True
            # Wait for input field
            self._send_command("Wait(InputField)")
            return True

        return False

    def disconnect(self):
        """Disconnect from host"""
        if self.connected:
            self._send_command("Disconnect")
            self.connected = False

    def wait_ready(self, timeout: float = 5.0) -> bool:
        """Wait for input field to be ready"""
        response = self._send_command("Wait(InputField)", timeout)
        return "ok" in response

    def send_text(self, text: str):
        """Send text string"""
        # Escape special characters
        text = text.replace('"', '\\"').replace('\\', '\\\\')
        self._send_command(f'String("{text}")')

    def press(self, aid: str):
        """Press AID key (Enter, PF1-PF24, PA1-PA3, Clear)"""
        if aid.upper() == "ENTER":
            self._send_command("Enter")
        elif aid.upper().startswith("PF"):
            num = aid[2:]
            self._send_command(f"PF({num})")
        elif aid.upper().startswith("PA"):
            num = aid[2:]
            self._send_command(f"PA({num})")
        elif aid.upper() == "CLEAR":
            self._send_command("Clear")
        else:
            raise ValueError(f"Unknown AID key: {aid}")

    def move_cursor(self, row: int, col: int):
        """Move cursor to position (1-based)"""
        self._send_command(f"MoveCursor({row},{col})")

    def fill_at(self, row: int, col: int, text: str, enter: bool = False) -> Dict[str, Any]:
        """Fill field at position"""
        self.move_cursor(row, col)
        self.send_text(text)
        if enter:
            self.press("Enter")
        return {"status": "ok", "row": row, "col": col, "text_length": len(text)}

    def fill_by_label(self, label: str, offset: int, text: str) -> bool:
        """Find label and fill field at offset"""
        # Get screen to find label
        ascii_lines = self._send_command("Ascii")

        # Search for label
        for i, line in enumerate(ascii_lines):
            if label in line:
                # Found label, calculate position
                col_pos = line.index(label) + len(label) + offset
                row_pos = i + 1  # 1-based

                if col_pos > 80:  # Wrap to next line
                    row_pos += col_pos // 80
                    col_pos = col_pos % 80

                self.fill_at(row_pos, col_pos, text)
                return True

        return False

    def snapshot(self) -> Dict[str, Any]:
        """Capture complete screen state"""
        # Save current state
        self._send_command("Snap(Save)")

        # Get ASCII representation
        ascii_response = self._send_command("Snap(Ascii)")

        # Filter out status lines and "ok"
        ascii_lines = []
        for line in ascii_response:
            if line and not line.startswith("data:"):
                continue
            if line.startswith("data:"):
                ascii_lines.append(line[5:])

        ascii_text = "\n".join(ascii_lines)

        # Get cursor position
        cursor_response = self._send_command("Query(Cursor)")
        cursor_row, cursor_col = 0, 0
        for line in cursor_response:
            if "," in line and not line.startswith("U"):
                parts = line.split(",")
                if len(parts) == 2:
                    try:
                        cursor_row = int(parts[0])
                        cursor_col = int(parts[1])
                    except ValueError:
                        pass

        # Get screen size
        size_response = self._send_command("Query(ScreenCurSize)")
        rows, cols = 24, 80
        for line in size_response:
            if "x" in line:
                parts = line.split("x")
                if len(parts) == 2:
                    try:
                        rows = int(parts[0])
                        cols = int(parts[1])
                    except ValueError:
                        pass

        # Get field data via ReadBuffer
        from .parser import parse_readbuffer_ascii
        readbuf_response = self._send_command("ReadBuffer(Ascii)")
        fields = parse_readbuffer_ascii(readbuf_response, rows, cols)

        # Calculate digest
        normalized = re.sub(r'\s+', ' ', ascii_text.strip())
        digest = hashlib.sha256(normalized.encode()).hexdigest()

        return {
            "rows": rows,
            "cols": cols,
            "cursor": [cursor_row, cursor_col],
            "ascii": ascii_text,
            "fields": fields,
            "digest": digest
        }

    def execute_actions(self, actions: List[str]) -> List[str]:
        """Execute raw s3270 actions"""
        results = []
        for action in actions:
            response = self._send_command(action)
            results.extend(response)
        return results