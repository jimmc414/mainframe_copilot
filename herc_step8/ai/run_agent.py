#!/usr/bin/env python3
"""Main entry point for mainframe AI agent"""

import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.agent_controller import MainframeAgent
from ai.claude_code_control import ClaudeCodeController
from ai.viewer import MainframeViewer, SimpleViewer


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_interactive_mode(args):
    """Run agent in interactive mode with Claude Code control"""
    print("=== Mainframe Agent - Interactive Mode ===")
    print("Starting agent with Claude Code command queue monitoring...")
    print(f"Command directory: ~/herc/ai/commands/")
    print("The agent is now waiting for commands from Claude Code\n")

    # Start agent in interactive mode
    agent = MainframeAgent(interactive=True)

    # Show how to control it
    print("To control from Claude Code, use:")
    print("  python ~/herc/ai/claude_code_control.py --interactive")
    print("\nOr send commands directly:")
    print("  echo '{\"action\": \"connect\"}' > ~/herc/ai/commands/cmd_manual_001.json")
    print("\nPress Ctrl+C to stop the agent\n")

    # Run interactive session
    agent.interactive_session()


def run_batch_mode(args):
    """Run agent in batch mode for single task"""
    if not args.task:
        print("Error: --task required for batch mode")
        sys.exit(1)

    print(f"=== Mainframe Agent - Batch Mode ===")
    print(f"Task: {args.task}\n")

    agent = MainframeAgent(interactive=False)
    result = agent.batch_mode(args.task)

    # Save result if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResult saved to: {output_path}")


def run_flow_mode(args):
    """Run a predefined flow"""
    if not args.flow:
        print("Error: --flow required")
        sys.exit(1)

    print(f"=== Mainframe Agent - Flow Mode ===")
    print(f"Running flow: {args.flow}\n")

    agent = MainframeAgent(interactive=False)

    # Connect first
    print("Connecting to mainframe...")
    agent.connect()

    # Run flow
    result = agent.run_flow(args.flow)
    print(f"Flow result: {result}")


def run_controller_mode(args):
    """Run Claude Code controller"""
    print("=== Claude Code Mainframe Controller ===")

    controller = ClaudeCodeController()

    if args.command:
        # Execute single command
        print(f"Executing: {args.command}")

        if args.command == "status":
            status = controller.get_status()
            print(json.dumps(status, indent=2))
        elif args.command == "screen":
            screen = controller.get_screen()
            if screen:
                print(screen)
            else:
                print("No screen available")
        elif args.command == "login":
            success = controller.tso_login()
            print("Login successful" if success else "Login failed")
        elif args.command.startswith("press "):
            key = args.command.split()[1]
            controller.press(key)
        else:
            print(f"Unknown command: {args.command}")
    else:
        # Interactive controller mode
        controller.interactive_mode()


def run_viewer_mode(args):
    """Run status viewer"""
    print("Starting mainframe agent viewer...")

    if args.simple:
        viewer = SimpleViewer()
    else:
        viewer = MainframeViewer()

    viewer.run()


def test_setup():
    """Test if all components are set up correctly"""
    print("=== Testing Mainframe AI Setup ===\n")

    errors = []

    # Check directories
    print("1. Checking directories...")
    dirs = [
        Path("~/herc/ai").expanduser(),
        Path("~/herc/ai/commands").expanduser(),
        Path("~/herc/ai/logs").expanduser(),
        Path("~/herc/ai/prompts").expanduser(),
        Path("~/herc/ai/tools").expanduser(),
    ]

    for dir_path in dirs:
        if dir_path.exists():
            print(f"   ✓ {dir_path}")
        else:
            print(f"   ✗ {dir_path} - Missing")
            errors.append(f"Missing directory: {dir_path}")

    # Check files
    print("\n2. Checking files...")
    files = [
        Path("~/herc/ai/llm_cli.py").expanduser(),
        Path("~/herc/ai/agent_controller.py").expanduser(),
        Path("~/herc/ai/claude_code_control.py").expanduser(),
        Path("~/herc/ai/viewer.py").expanduser(),
        Path("~/herc/ai/tools/mainframe_tools.json").expanduser(),
        Path("~/herc/ai/prompts/system_prompt.txt").expanduser(),
    ]

    for file_path in files:
        if file_path.exists():
            print(f"   ✓ {file_path}")
        else:
            print(f"   ✗ {file_path} - Missing")
            errors.append(f"Missing file: {file_path}")

    # Check API
    print("\n3. Checking TN3270 Bridge API...")
    import requests
    try:
        response = requests.get("http://127.0.0.1:8080/status", timeout=2)
        if response.status_code == 200:
            print("   ✓ API is running")
        else:
            print(f"   ✗ API returned status {response.status_code}")
            errors.append("API not responding correctly")
    except:
        print("   ✗ API not reachable at http://127.0.0.1:8080")
        errors.append("TN3270 Bridge API not running")

    # Check Claude CLI
    print("\n4. Checking Claude CLI...")
    import shutil
    claude_path = shutil.which("claude")
    if claude_path:
        print(f"   ✓ Claude CLI found at {claude_path}")
    else:
        print("   ⚠ Claude CLI not found (will use mock mode)")

    # Summary
    print("\n" + "=" * 50)
    if errors:
        print("Setup incomplete. Issues found:")
        for error in errors:
            print(f"  - {error}")
        print("\nRun setup script to fix issues")
        return False
    else:
        print("✓ All components are set up correctly!")
        print("\nYou can now run:")
        print("  python ~/herc/ai/run_agent.py --interactive")
        print("  python ~/herc/ai/run_agent.py --controller")
        print("  python ~/herc/ai/run_agent.py --viewer")
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mainframe AI Agent - Automated mainframe operations via Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --interactive    Run agent with Claude Code command queue monitoring
  --batch          Run single task and exit
  --flow           Execute predefined YAML flow
  --controller     Run Claude Code controller interface
  --viewer         Run status viewer UI
  --test           Test setup and configuration

Examples:
  # Run agent in interactive mode for Claude Code control
  python ~/herc/ai/run_agent.py --interactive

  # Execute single task
  python ~/herc/ai/run_agent.py --batch --task "Login to TSO and go to ISPF"

  # Run predefined flow
  python ~/herc/ai/run_agent.py --flow login.yaml

  # Control agent from Claude Code
  python ~/herc/ai/run_agent.py --controller

  # Monitor agent status
  python ~/herc/ai/run_agent.py --viewer
"""
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--interactive", "-i", action="store_true",
                            help="Run with Claude Code command queue monitoring")
    mode_group.add_argument("--batch", "-b", action="store_true",
                            help="Run single task in batch mode")
    mode_group.add_argument("--flow", "-f", type=str,
                            help="Run predefined YAML flow")
    mode_group.add_argument("--controller", "-c", action="store_true",
                            help="Run Claude Code controller")
    mode_group.add_argument("--viewer", "-v", action="store_true",
                            help="Run status viewer")
    mode_group.add_argument("--test", "-t", action="store_true",
                            help="Test setup")

    # Options
    parser.add_argument("--task", type=str,
                        help="Task description for batch mode")
    parser.add_argument("--command", type=str,
                        help="Command for controller mode")
    parser.add_argument("--output", "-o", type=str,
                        help="Output file for results")
    parser.add_argument("--simple", action="store_true",
                        help="Use simple viewer (no curses)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Run appropriate mode
    if args.test:
        success = test_setup()
        sys.exit(0 if success else 1)
    elif args.interactive:
        run_interactive_mode(args)
    elif args.batch:
        run_batch_mode(args)
    elif args.flow:
        run_flow_mode(args)
    elif args.controller:
        run_controller_mode(args)
    elif args.viewer:
        run_viewer_mode(args)


if __name__ == "__main__":
    main()