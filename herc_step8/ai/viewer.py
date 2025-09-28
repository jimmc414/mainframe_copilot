#!/usr/bin/env python3
"""Terminal UI viewer for mainframe agent"""

import curses
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class MainframeViewer:
    """Terminal UI for monitoring mainframe agent"""

    def __init__(self, command_dir: Optional[Path] = None):
        self.command_dir = Path(command_dir or "~/herc/ai/commands").expanduser()
        self.running = False
        self.status = {}
        self.screen_content = []
        self.log_lines = []
        self.max_log_lines = 10

    def load_status(self) -> Dict[str, Any]:
        """Load current status"""
        status_file = self.command_dir / "status.json"
        if status_file.exists():
            try:
                with open(status_file) as f:
                    return json.load(f)
            except:
                pass
        return {"state": "unknown"}

    def load_logs(self):
        """Load recent log entries"""
        log_dir = Path("~/herc/ai/logs").expanduser()
        if not log_dir.exists():
            return []

        # Find most recent log file
        log_files = sorted(log_dir.glob("agent_*.log"), reverse=True)
        if not log_files:
            return []

        lines = []
        with open(log_files[0]) as f:
            # Get last N lines
            all_lines = f.readlines()
            lines = all_lines[-self.max_log_lines:] if all_lines else []

        return [line.strip() for line in lines]

    def draw_box(self, win, title: str):
        """Draw box with title"""
        h, w = win.getmaxyx()
        win.border()

        if title:
            title = f" {title} "
            x = (w - len(title)) // 2
            if x > 0:
                win.addstr(0, x, title)

    def update_display(self, stdscr):
        """Update display panels"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.clear()

        h, w = stdscr.getmaxyx()

        # Create windows
        # Top: Status (5 lines)
        status_h = 5
        status_win = curses.newwin(status_h, w, 0, 0)

        # Middle: Screen (15 lines)
        screen_h = min(15, h - status_h - 12)
        screen_y = status_h
        screen_win = curses.newwin(screen_h, w, screen_y, 0)

        # Bottom: Logs (remaining)
        log_h = h - status_h - screen_h - 1
        log_y = screen_y + screen_h
        log_win = curses.newwin(log_h, w, log_y, 0)

        while self.running:
            try:
                # Load current data
                self.status = self.load_status()
                self.log_lines = self.load_logs()

                # Draw status window
                status_win.clear()
                self.draw_box(status_win, "Agent Status")

                state = self.status.get("state", "unknown")
                timestamp = self.status.get("timestamp", "")
                last_action = self.status.get("last_action", "none")
                error = self.status.get("error")

                status_win.addstr(1, 2, f"State: {state}")
                status_win.addstr(2, 2, f"Last Action: {last_action}")
                status_win.addstr(3, 2, f"Updated: {timestamp[:19] if timestamp else 'never'}")

                if error:
                    status_win.addstr(3, 40, f"Error: {error[:30]}", curses.A_BOLD)

                status_win.refresh()

                # Draw screen window
                screen_win.clear()
                self.draw_box(screen_win, "Mainframe Screen")

                if self.status.get("last_screen"):
                    lines = self.status["last_screen"].split('\n')
                    for i, line in enumerate(lines[:screen_h - 2]):
                        if i < screen_h - 2:
                            # Truncate long lines
                            display_line = line[:w - 4] if len(line) > w - 4 else line
                            screen_win.addstr(i + 1, 2, display_line)

                screen_win.refresh()

                # Draw log window
                log_win.clear()
                self.draw_box(log_win, "Recent Activity")

                for i, line in enumerate(self.log_lines):
                    if i < log_h - 2:
                        # Format log line
                        if " - ERROR - " in line:
                            attr = curses.A_BOLD
                        elif " - WARNING - " in line:
                            attr = curses.A_DIM
                        else:
                            attr = curses.A_NORMAL

                        # Truncate and display
                        display_line = line[:w - 4] if len(line) > w - 4 else line
                        try:
                            log_win.addstr(i + 1, 2, display_line, attr)
                        except:
                            pass  # Ignore errors from long lines

                log_win.refresh()

                # Status line
                help_text = " [Q]uit  [R]efresh  [C]lear "
                stdscr.addstr(h - 1, 2, help_text, curses.A_REVERSE)
                stdscr.refresh()

                # Handle input
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    self.running = False
                elif key == ord('r') or key == ord('R'):
                    continue  # Force refresh
                elif key == ord('c') or key == ord('C'):
                    self.log_lines = []

                time.sleep(1)  # Update rate

            except curses.error:
                pass  # Ignore curses errors
            except Exception as e:
                # Show error in status
                self.status["error"] = str(e)

    def run(self):
        """Run viewer"""
        self.running = True

        try:
            curses.wrapper(self.update_display)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\nViewer stopped")


class SimpleViewer:
    """Simple non-curses viewer for basic terminals"""

    def __init__(self, command_dir: Optional[Path] = None):
        self.command_dir = Path(command_dir or "~/herc/ai/commands").expanduser()

    def run(self):
        """Run simple viewer loop"""
        print("=== Mainframe Agent Monitor ===")
        print("Press Ctrl+C to exit\n")

        try:
            while True:
                status_file = self.command_dir / "status.json"

                if status_file.exists():
                    with open(status_file) as f:
                        status = json.load(f)

                    # Clear screen (portable)
                    print("\033[2J\033[H", end="")

                    print("=== Agent Status ===")
                    print(f"State: {status.get('state', 'unknown')}")
                    print(f"Last Action: {status.get('last_action', 'none')}")
                    print(f"Updated: {status.get('timestamp', 'never')}")

                    if status.get('error'):
                        print(f"ERROR: {status['error']}")

                    print("\n=== Last Screen ===")
                    if status.get('last_screen'):
                        lines = status['last_screen'].split('\n')[:10]
                        for line in lines:
                            print(line[:78])  # Limit width

                    print("\n[Refreshing every 2 seconds...]")

                time.sleep(2)

        except KeyboardInterrupt:
            print("\n\nMonitor stopped")


def test_viewer():
    """Test viewer with mock data"""
    print("=== Testing Viewer ===")

    # Create mock status
    command_dir = Path("~/herc/ai/commands").expanduser()
    command_dir.mkdir(parents=True, exist_ok=True)

    status = {
        "state": "processing",
        "last_action": "fill",
        "timestamp": datetime.now().isoformat(),
        "last_screen": """Terminal   CUU0C0                                                 Date  28.09.25
                                                                   Time  04:23:11

ISPF Primary Option Menu

  0  Settings      Terminal and user parameters
  1  Browse        Display source data or output listings
  2  Edit          Create or change source data
  3  Utilities     Perform utility functions

Option ===> _"""
    }

    status_file = command_dir / "status.json"
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

    print("Mock status created. You can now run:")
    print("  python ~/herc/ai/viewer.py")
    print("  python ~/herc/ai/viewer.py --simple")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mainframe agent viewer")
    parser.add_argument("--simple", action="store_true",
                        help="Use simple mode (no curses)")
    parser.add_argument("--test", action="store_true",
                        help="Create test data")

    args = parser.parse_args()

    if args.test:
        test_viewer()
    elif args.simple:
        viewer = SimpleViewer()
        viewer.run()
    else:
        viewer = MainframeViewer()
        viewer.run()