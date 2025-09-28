#!/usr/bin/env python3
"""Claude Code control interface for real-time mainframe interaction"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class ClaudeCodeController:
    """Interface for Claude Code to control mainframe agent"""

    def __init__(self, command_dir: Optional[Path] = None):
        self.command_dir = Path(command_dir or "~/herc/ai/commands").expanduser()
        self.command_dir.mkdir(parents=True, exist_ok=True)
        self.sequence = 0

    def _send_command(self, action: str, params: Dict[str, Any] = None) -> str:
        """Send command to agent"""
        self.sequence += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cmd_{timestamp}_{self.sequence:04d}.json"

        command = {
            "action": action,
            "params": params or {},
            "timestamp": timestamp,
            "sequence": self.sequence,
            "source": "claude_code"
        }

        filepath = self.command_dir / filename
        with open(filepath, 'w') as f:
            json.dump(command, f, indent=2)

        print(f"Sent command: {action} (sequence {self.sequence})")
        return filename

    def _wait_for_result(self, sequence: int, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Wait for command result"""
        result_file = self.command_dir / f"result_{sequence:04d}.json"
        start = time.time()

        while time.time() - start < timeout:
            if result_file.exists():
                with open(result_file) as f:
                    result = json.load(f)
                result_file.unlink()  # Clean up
                return result
            time.sleep(0.5)

        print(f"Timeout waiting for result {sequence}")
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        status_file = self.command_dir / "status.json"
        if status_file.exists():
            with open(status_file) as f:
                return json.load(f)
        return {"state": "unknown"}

    def connect(self, host: str = "127.0.0.1:3270") -> bool:
        """Connect to mainframe"""
        self._send_command("connect", {"host": host})
        result = self._wait_for_result(self.sequence)
        return result and result.get("status") == "connected"

    def get_screen(self) -> Optional[str]:
        """Get current screen text"""
        self._send_command("screen")
        result = self._wait_for_result(self.sequence)
        if result and "ascii" in result:
            return result["ascii"]
        return None

    def fill_field(self, row: int, col: int, text: str) -> bool:
        """Fill field at position"""
        self._send_command("fill", {"row": row, "col": col, "text": text})
        result = self._wait_for_result(self.sequence)
        return result and result.get("status") == "success"

    def press(self, key: str) -> bool:
        """Press function key (Enter, PF3, Clear, etc)"""
        self._send_command("press", {"key": key})
        result = self._wait_for_result(self.sequence)
        return result and result.get("status") == "success"

    def run_flow(self, flow_name: str) -> bool:
        """Execute predefined flow"""
        self._send_command("flow", {"flow_name": flow_name})
        result = self._wait_for_result(self.sequence, timeout=60)
        return result and result.get("status") == "success"

    def ask_llm(self, prompt: str) -> Dict[str, Any]:
        """Ask LLM for next action"""
        self._send_command("llm_action", {"prompt": prompt})
        return self._wait_for_result(self.sequence, timeout=45)

    def tso_login(self, userid: str = "HERC02", password: str = "CUL8TR") -> bool:
        """Automated TSO login"""
        print(f"Logging in as {userid}...")

        # Get current screen
        screen = self.get_screen()
        if not screen:
            print("Failed to get screen")
            return False

        # Check if at logon screen
        if "Logon ==>" in screen or "TSO/E LOGON" in screen:
            # Run login flow
            return self.run_flow("login.yaml")

        print("Not at logon screen")
        return False

    def navigate_to_ispf(self) -> bool:
        """Navigate to ISPF main menu"""
        screen = self.get_screen()

        if "ISPF Primary Option Menu" in screen:
            print("Already at ISPF")
            return True

        # Try to get to ISPF
        if "READY" in screen:
            # At TSO READY prompt
            self.fill_field(1, 1, "ISPF")
            self.press("Enter")
            time.sleep(2)
            return "ISPF" in self.get_screen()

        return False

    def submit_jcl(self, jcl_text: str) -> Optional[str]:
        """Submit JCL job"""
        # Navigate to ISPF edit
        if not self.navigate_to_ispf():
            return None

        # Go to edit (option 2)
        self.fill_field(20, 14, "2")
        self.press("Enter")
        time.sleep(1)

        # Create new member
        member_name = f"J{int(time.time()) % 100000:05d}"
        self.fill_field(2, 14, f"'HERC02.JCL({member_name})'")
        self.press("Enter")
        time.sleep(1)

        # Enter JCL
        lines = jcl_text.strip().split('\n')
        for i, line in enumerate(lines):
            self.fill_field(i + 1, 1, line)

        # Submit
        self.fill_field(1, 1, "SUB")
        self.press("Enter")
        time.sleep(2)

        # Check for job ID
        screen = self.get_screen()
        if "JOB" in screen:
            # Extract job ID from message
            for line in screen.split('\n'):
                if "JOB" in line and "SUBMITTED" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "JOB":
                            return parts[i + 1] if i + 1 < len(parts) else None

        return None

    def exit_to_ready(self) -> bool:
        """Exit to TSO READY prompt"""
        max_attempts = 5
        for _ in range(max_attempts):
            screen = self.get_screen()

            if "READY" in screen:
                return True

            # Try PF3 to exit
            self.press("PF3")
            time.sleep(1)

            # If prompted, confirm
            screen = self.get_screen()
            if "EXIT" in screen or "CANCEL" in screen:
                self.press("Enter")
                time.sleep(1)

        return False

    def stop(self):
        """Send stop command to agent"""
        self._send_command("stop")
        print("Stop command sent")

    def show_screen(self):
        """Display current screen"""
        screen = self.get_screen()
        if screen:
            print("\n" + "=" * 80)
            print(screen)
            print("=" * 80 + "\n")
        else:
            print("No screen available")

    def interactive_mode(self):
        """Interactive command mode"""
        print("=== Claude Code Mainframe Controller ===")
        print("Commands: screen, fill, press, flow, login, ispf, exit, stop, help")
        print("Type 'help' for details\n")

        while True:
            try:
                cmd = input("> ").strip().lower()

                if cmd == "help":
                    self._show_help()
                elif cmd == "screen":
                    self.show_screen()
                elif cmd == "status":
                    print(json.dumps(self.get_status(), indent=2))
                elif cmd == "login":
                    self.tso_login()
                elif cmd == "ispf":
                    self.navigate_to_ispf()
                elif cmd == "exit":
                    self.exit_to_ready()
                elif cmd == "stop":
                    self.stop()
                    break
                elif cmd.startswith("fill "):
                    parts = cmd.split()
                    if len(parts) >= 4:
                        row = int(parts[1])
                        col = int(parts[2])
                        text = ' '.join(parts[3:])
                        self.fill_field(row, col, text)
                elif cmd.startswith("press "):
                    key = cmd.split()[1].upper()
                    self.press(key)
                elif cmd.startswith("flow "):
                    flow = cmd.split()[1]
                    self.run_flow(f"{flow}.yaml")
                elif cmd.startswith("ask "):
                    prompt = cmd[4:]
                    result = self.ask_llm(prompt)
                    print(f"LLM says: {result}")
                elif cmd:
                    print(f"Unknown command: {cmd}")

            except KeyboardInterrupt:
                print("\nUse 'stop' to exit")
            except Exception as e:
                print(f"Error: {e}")

    def _show_help(self):
        """Show help message"""
        print("""
Available commands:
  screen          - Show current screen
  status          - Show agent status
  login           - Automated TSO login
  ispf            - Navigate to ISPF
  exit            - Exit to TSO READY
  fill R C TEXT   - Fill text at row R, column C
  press KEY       - Press key (Enter, PF3, Clear, etc)
  flow NAME       - Run flow (e.g., 'flow login')
  ask PROMPT      - Ask LLM for assistance
  stop            - Stop agent and exit
  help            - Show this help
""")


def example_usage():
    """Example of using controller from Claude Code"""
    print("=== Example Claude Code Usage ===\n")

    # Create controller
    ctrl = ClaudeCodeController()

    print("1. Checking agent status...")
    status = ctrl.get_status()
    print(f"   State: {status.get('state')}")

    print("\n2. Connecting to mainframe...")
    if ctrl.connect():
        print("   Connected!")

        print("\n3. Getting screen...")
        screen = ctrl.get_screen()
        if screen:
            lines = screen.split('\n')[:5]
            for line in lines:
                print(f"   {line}")

        print("\n4. Attempting TSO login...")
        if ctrl.tso_login():
            print("   Login successful!")

            print("\n5. Navigating to ISPF...")
            if ctrl.navigate_to_ispf():
                print("   At ISPF menu")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude Code controller for mainframe agent"
    )
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run interactive command mode")
    parser.add_argument("--example", action="store_true",
                        help="Run example usage")
    parser.add_argument("--command", "-c", type=str,
                        help="Execute single command")

    args = parser.parse_args()

    if args.interactive:
        ctrl = ClaudeCodeController()
        ctrl.interactive_mode()
    elif args.example:
        example_usage()
    elif args.command:
        ctrl = ClaudeCodeController()
        # Parse and execute command
        if args.command == "screen":
            ctrl.show_screen()
        elif args.command == "status":
            print(json.dumps(ctrl.get_status(), indent=2))
        elif args.command == "login":
            ctrl.tso_login()
        else:
            print(f"Unknown command: {args.command}")
    else:
        print("Use --interactive for command mode or --example for demo")
        print("Use --command to execute single command")