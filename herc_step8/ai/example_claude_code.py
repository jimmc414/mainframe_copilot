#!/usr/bin/env python3
"""
Example script for Claude Code to control the mainframe

This script demonstrates how Claude Code can interact with the
mainframe emulator through the AI agent command queue system.
"""

import json
import time
from pathlib import Path


def send_mainframe_command(action: str, params: dict = None):
    """Send command to mainframe agent via file queue"""

    # Command directory for agent monitoring
    cmd_dir = Path("~/herc/ai/commands").expanduser()
    cmd_dir.mkdir(parents=True, exist_ok=True)

    # Create command
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    command = {
        "action": action,
        "params": params or {},
        "source": "claude_code",
        "timestamp": timestamp
    }

    # Write to queue
    cmd_file = cmd_dir / f"cmd_claude_{timestamp}.json"
    with open(cmd_file, 'w') as f:
        json.dump(command, f, indent=2)

    print(f"Sent: {action}")
    return cmd_file


def get_agent_status():
    """Get current agent status"""
    status_file = Path("~/herc/ai/commands/status.json").expanduser()

    if status_file.exists():
        with open(status_file) as f:
            status = json.load(f)
        return status
    return {"state": "unknown"}


def example_workflow():
    """Example workflow for mainframe interaction"""

    print("=== Claude Code Mainframe Control Example ===\n")

    # 1. Check agent status
    print("1. Checking agent status...")
    status = get_agent_status()
    print(f"   Agent state: {status.get('state')}")

    # 2. Connect to mainframe
    print("\n2. Connecting to mainframe...")
    send_mainframe_command("connect", {"host": "127.0.0.1:3270"})
    time.sleep(2)

    # 3. Get screen
    print("\n3. Getting current screen...")
    send_mainframe_command("screen")
    time.sleep(1)

    # 4. Login to TSO
    print("\n4. Running TSO login flow...")
    send_mainframe_command("flow", {"flow_name": "login.yaml"})
    time.sleep(5)

    # 5. Check status again
    print("\n5. Final status check...")
    status = get_agent_status()
    print(f"   State: {status.get('state')}")
    if status.get('last_screen'):
        print("   Screen preview:")
        lines = status['last_screen'].split('\n')[:3]
        for line in lines:
            print(f"     {line}")

    print("\n=== Example Complete ===")
    print("\nThe agent will continue monitoring for commands.")
    print("You can send more commands or use the controller:")
    print("  python ~/herc/ai/claude_code_control.py --interactive")


def interactive_example():
    """Interactive example for Claude Code"""

    print("=== Interactive Mainframe Control ===")
    print("Commands: connect, screen, fill, press, flow, status, quit\n")

    while True:
        cmd = input("Command> ").strip().lower()

        if cmd == "quit":
            break
        elif cmd == "status":
            status = get_agent_status()
            print(json.dumps(status, indent=2))
        elif cmd == "connect":
            send_mainframe_command("connect")
        elif cmd == "screen":
            send_mainframe_command("screen")
        elif cmd.startswith("fill "):
            parts = cmd.split()
            if len(parts) >= 4:
                row = int(parts[1])
                col = int(parts[2])
                text = ' '.join(parts[3:])
                send_mainframe_command("fill", {
                    "row": row, "col": col, "text": text
                })
        elif cmd.startswith("press "):
            key = cmd.split()[1].upper()
            send_mainframe_command("press", {"key": key})
        elif cmd.startswith("flow "):
            flow = cmd.split()[1]
            send_mainframe_command("flow", {"flow_name": f"{flow}.yaml"})
        else:
            print(f"Unknown command: {cmd}")

        time.sleep(0.5)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_example()
    else:
        example_workflow()
        print("\nFor interactive mode: python example_claude_code.py --interactive")