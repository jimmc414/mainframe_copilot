#!/usr/bin/env python3
"""Mainframe AI Agent Controller with Claude Code integration"""

import json
import time
import threading
import queue
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
import logging
from datetime import datetime
import sys
import yaml
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.llm_cli import ClaudeCLI, ClaudeStreamWrapper
from ai.tn3270_client import TN3270Bridge, FlowRunner


class CommandQueue:
    """File-based command queue for Claude Code interaction"""

    def __init__(self, queue_dir: Path):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir = self.queue_dir / "processed"
        self.processed_dir.mkdir(exist_ok=True)

        # Command files pattern: cmd_<timestamp>_<sequence>.json
        self.sequence = 0
        self.logger = logging.getLogger("command_queue")

    def push(self, command: Dict[str, Any]) -> Path:
        """Add command to queue"""
        self.sequence += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cmd_{timestamp}_{self.sequence:04d}.json"
        filepath = self.queue_dir / filename

        command["timestamp"] = timestamp
        command["sequence"] = self.sequence

        with open(filepath, 'w') as f:
            json.dump(command, f, indent=2)

        self.logger.debug(f"Queued command: {filename}")
        return filepath

    def pop(self) -> Optional[Dict[str, Any]]:
        """Get next command from queue"""
        # Find oldest unprocessed command
        commands = sorted([
            f for f in self.queue_dir.iterdir()
            if f.name.startswith("cmd_") and f.suffix == ".json"
        ])

        if not commands:
            return None

        cmd_file = commands[0]

        try:
            with open(cmd_file) as f:
                command = json.load(f)

            # Move to processed
            processed_file = self.processed_dir / cmd_file.name
            cmd_file.rename(processed_file)

            self.logger.debug(f"Processing command: {cmd_file.name}")
            return command

        except Exception as e:
            self.logger.error(f"Failed to process command {cmd_file}: {e}")
            # Move to processed with error suffix
            error_file = self.processed_dir / f"{cmd_file.stem}_error.json"
            cmd_file.rename(error_file)
            return None

    def clear(self):
        """Clear all pending commands"""
        for f in self.queue_dir.glob("cmd_*.json"):
            f.unlink()
        self.logger.info("Command queue cleared")


class StatusReporter:
    """Reports agent status for Claude Code monitoring"""

    def __init__(self, status_file: Path):
        self.status_file = Path(status_file)
        self.status = {
            "state": "initializing",
            "last_action": None,
            "last_screen": None,
            "error": None,
            "timestamp": None
        }
        self.update("initializing")

    def update(self, state: str, **kwargs):
        """Update status file"""
        self.status["state"] = state
        self.status["timestamp"] = datetime.now().isoformat()
        self.status.update(kwargs)

        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)

    def set_screen(self, screen_text: str):
        """Update last screen content"""
        # Store first 10 lines of screen
        lines = screen_text.split('\n')[:10]
        self.status["last_screen"] = '\n'.join(lines)
        self.update(self.status["state"])

    def set_error(self, error: str):
        """Set error status"""
        self.update("error", error=error)


class MainframeAgent:
    """AI agent for mainframe automation"""

    def __init__(self,
                 bridge_url: str = "http://127.0.0.1:8080",
                 command_dir: Optional[Path] = None,
                 interactive: bool = False):

        self.bridge = TN3270Bridge(bridge_url)
        self.cli = ClaudeCLI()
        self.flow_runner = FlowRunner(self.bridge)

        # Setup directories
        self.base_dir = Path("~/herc/ai").expanduser()
        self.command_dir = command_dir or self.base_dir / "commands"
        self.log_dir = self.base_dir / "logs"

        # Setup logging
        self.logger = self._setup_logging()

        # Interactive mode with Claude Code
        self.interactive = interactive
        if self.interactive:
            self.command_queue = CommandQueue(self.command_dir)
            self.status = StatusReporter(self.command_dir / "status.json")
            self.monitor_thread = None
            self._start_monitor()

        # Load prompts and tools
        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.tools_manifest = self._load_tools()

        # Load configuration and TSO credentials
        self.config = self._load_config()
        self.tso_credentials = self._get_tso_credentials()

    def _setup_logging(self) -> logging.Logger:
        """Configure logging"""
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("mainframe_agent")
        logger.setLevel(logging.DEBUG)

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handler = logging.FileHandler(
            self.log_dir / f"agent_{timestamp}.log"
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)

        # Console handler for important messages
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logger.addHandler(console)

        return logger

    def _load_prompt(self, filename: str) -> str:
        """Load system prompt"""
        prompt_file = self.base_dir / "prompts" / filename
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are a mainframe automation assistant."

    def _load_tools(self) -> List[Dict[str, Any]]:
        """Load tools manifest"""
        tools_file = self.base_dir / "tools/mainframe_tools.json"
        if tools_file.exists():
            with open(tools_file) as f:
                return json.load(f)
        return []

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        config_file = Path("~/herc/config.yaml").expanduser()
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f)
        return {}

    def _get_tso_credentials(self) -> Dict[str, str]:
        """Get TSO credentials from config or environment"""
        credentials = {}

        # First try environment variables
        credentials['TSO_USER'] = os.environ.get('TSO_USER', '')
        credentials['TSO_PASS'] = os.environ.get('TSO_PASS', '')

        # If not in environment, get from config
        if not credentials['TSO_USER'] and self.config:
            tso_config = self.config.get('tso', {})
            credentials['TSO_USER'] = tso_config.get('default_user', 'HERC02')
            credentials['TSO_PASS'] = tso_config.get('default_password', 'CUL8TR')

        # If still not found, use defaults
        if not credentials['TSO_USER']:
            credentials['TSO_USER'] = 'HERC02'
            credentials['TSO_PASS'] = 'CUL8TR'

        self.logger.info(f"Using TSO user: {credentials['TSO_USER']}")
        return credentials

    def _start_monitor(self):
        """Start command queue monitor for interactive mode"""
        self.monitor_thread = threading.Thread(
            target=self._monitor_commands,
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("Started command queue monitor")

    def _monitor_commands(self):
        """Monitor command queue for Claude Code instructions"""
        self.logger.info("Monitoring command queue...")

        while True:
            try:
                # Check for new command
                command = self.command_queue.pop()

                if command:
                    self.logger.info(f"Received command: {command.get('action')}")
                    self.status.update("processing_command", last_action=command.get('action'))

                    # Process command
                    result = self._process_command(command)

                    # Write result
                    if result:
                        result_file = self.command_dir / f"result_{command['sequence']:04d}.json"
                        with open(result_file, 'w') as f:
                            json.dump(result, f, indent=2)

                    self.status.update("idle")

                # Small delay to prevent spinning
                time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                self.status.set_error(str(e))
                time.sleep(5)  # Back off on error

    def _process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process command from Claude Code"""
        action = command.get("action")
        params = command.get("params", {})

        try:
            if action == "connect":
                return self.connect(params.get("host"))

            elif action == "screen":
                return self.get_screen()

            elif action == "fill":
                return self.fill(
                    params.get("row"),
                    params.get("col"),
                    params.get("text")
                )

            elif action == "press":
                return self.press_key(params.get("key"))

            elif action == "flow":
                return self.run_flow(params.get("flow_name"))

            elif action == "llm_action":
                # Let LLM decide next action
                prompt = params.get("prompt", "What should I do next?")
                return self.llm_action(prompt)

            elif action == "assert":
                return self.assert_screen(params.get("contains"))

            elif action == "stop":
                self.logger.info("Stop command received")
                return {"status": "stopped"}

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            self.logger.error(f"Command processing error: {e}")
            return {"error": str(e)}

    def connect(self, host: str = "127.0.0.1:3270") -> Dict[str, Any]:
        """Connect to mainframe"""
        self.logger.info(f"Connecting to {host}")
        result = self.bridge.connect(host)

        if self.interactive:
            screen = self.bridge.get_screen()
            if screen and "ascii" in screen:
                self.status.set_screen(screen["ascii"])

        return result

    def get_screen(self) -> Dict[str, Any]:
        """Get current screen snapshot"""
        screen = self.bridge.get_screen()

        if self.interactive and screen and "ascii" in screen:
            self.status.set_screen(screen["ascii"])

        return screen

    def fill(self, row: int, col: int, text: str) -> Dict[str, Any]:
        """Fill text at position"""
        self.logger.info(f"Filling at {row},{col}: {text[:20]}...")
        return self.bridge.fill_at(row, col, text)

    def press_key(self, key: str) -> Dict[str, Any]:
        """Press function key"""
        self.logger.info(f"Pressing {key}")
        result = self.bridge.press_key(key)

        # Update screen after key press
        if self.interactive:
            time.sleep(0.5)  # Brief delay for screen update
            screen = self.bridge.get_screen()
            if screen and "ascii" in screen:
                self.status.set_screen(screen["ascii"])

        return result

    def run_flow(self, flow_name: str) -> Dict[str, Any]:
        """Run YAML flow"""
        self.logger.info(f"Running flow: {flow_name}")

        flow_path = Path(f"~/herc/flows/{flow_name}").expanduser()
        if not flow_path.exists():
            return {"error": f"Flow not found: {flow_name}"}

        try:
            # Pass TSO credentials to flow runner
            result = self.flow_runner.run(str(flow_path), env=self.tso_credentials)
            return {"status": "success" if result else "failed"}
        except Exception as e:
            return {"error": str(e)}

    def assert_screen(self, contains: str) -> Dict[str, Any]:
        """Assert screen contains text"""
        screen = self.get_screen()
        if not screen or "ascii" not in screen:
            return {"status": False, "error": "No screen data"}

        found = contains in screen["ascii"]
        return {"status": found, "found": found}

    def llm_action(self, prompt: str) -> Dict[str, Any]:
        """Let LLM decide next action based on screen"""
        # Get current screen
        screen = self.get_screen()
        if not screen:
            return {"error": "No screen available"}

        # Format prompt with screen context
        full_prompt = f"""Current mainframe screen:
```
{screen.get('ascii', 'No screen data')}
```

Cursor position: {screen.get('cursor', [1,1])}
Fields: {len(screen.get('fields', []))} fields

User request: {prompt}

Respond with appropriate tool call."""

        # Get LLM response
        response = self.cli.invoke(full_prompt, system=self.system_prompt)

        # Parse LLM response to extract action
        if "action" in response:
            # Direct action in response (structured)
            return self._process_command(response)
        elif "content" in response:
            # Parse content for action keywords
            content = response.get("content", "").lower()

            # Try to extract action from natural language
            if "login" in content or "logon" in content:
                return self.run_flow("login.yaml")
            elif "logout" in content or "logoff" in content:
                return self.run_flow("logout.yaml")
            elif "enter" in content or "press enter" in content:
                return self.press_key("Enter")
            elif "clear" in content:
                return self.press_key("Clear")
            elif "fill" in content and "field" in content:
                # Extract field details from content if possible
                import re
                match = re.search(r'fill.*?(\d+).*?(\d+).*?"([^"]+)"', content)
                if match:
                    row, col, text = match.groups()
                    return self.fill(int(row), int(col), text)
            elif "connect" in content:
                return self.connect()
            elif "disconnect" in content:
                return self.bridge.disconnect()

            # If no action detected, return the LLM response as-is
            return {"message": response.get("content", "No action determined")}

        return response

    def interactive_session(self):
        """Run interactive session with Claude Code monitoring"""
        print("=== Mainframe Agent Interactive Mode ===")
        print(f"Command queue: {self.command_dir}")
        print("Waiting for commands from Claude Code...")
        print("Send 'stop' command to exit\n")

        # Connect to mainframe
        self.connect()

        # Wait for commands
        try:
            while True:
                status = self.status.status
                if status.get("state") == "error":
                    print(f"Error: {status.get('error')}")
                    time.sleep(5)
                elif status.get("last_action") == "stop":
                    print("Stop command received. Exiting.")
                    break
                else:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")

    def batch_mode(self, task: str):
        """Run single task in batch mode"""
        self.logger.info(f"Batch mode task: {task}")

        # Connect to mainframe
        self.connect()

        # Execute task
        result = self.llm_action(task)

        print(f"Result: {json.dumps(result, indent=2)}")
        return result


def test_agent():
    """Test agent functionality"""
    print("=== Testing Mainframe Agent ===\n")

    # Create agent
    agent = MainframeAgent(interactive=False)

    # Test connection
    print("1. Testing connection...")
    result = agent.connect()
    print(f"   Connected: {result.get('status')}\n")

    # Test screen read
    print("2. Testing screen read...")
    screen = agent.get_screen()
    if screen and "ascii" in screen:
        lines = screen["ascii"].split('\n')[:5]
        for line in lines:
            print(f"   {line}")
    print()

    # Test LLM action
    print("3. Testing LLM decision...")
    result = agent.llm_action("Check if we're at the TSO login screen")
    print(f"   Result: {result}\n")

    print("=== Test Complete ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mainframe AI Agent")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run in interactive mode with Claude Code monitoring")
    parser.add_argument("--task", "-t", type=str,
                        help="Execute single task in batch mode")
    parser.add_argument("--test", action="store_true",
                        help="Run tests")

    args = parser.parse_args()

    if args.test:
        test_agent()
    elif args.interactive:
        agent = MainframeAgent(interactive=True)
        agent.interactive_session()
    elif args.task:
        agent = MainframeAgent(interactive=False)
        agent.batch_mode(args.task)
    else:
        print("Use --interactive for Claude Code control or --task for batch mode")
        print("Use --test to run tests")