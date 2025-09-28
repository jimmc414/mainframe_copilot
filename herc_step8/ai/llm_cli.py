#!/usr/bin/env python3
"""Claude CLI wrapper for mainframe automation"""

import json
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import tempfile

class ClaudeCLI:
    """Wrapper for Claude CLI tool"""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("~/herc/ai/logs").expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger("claude_cli")
        handler = logging.FileHandler(self.log_dir / "claude_cli.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

        # Check for Claude CLI
        self.claude_path = self._find_claude()

    def _find_claude(self) -> Optional[str]:
        """Find Claude CLI executable"""
        # Check common locations
        paths = [
            shutil.which("claude"),
            Path.home() / ".local/bin/claude",
            Path("/usr/local/bin/claude"),
            Path("/opt/homebrew/bin/claude"),
        ]

        for path in paths:
            if path and Path(path).exists():
                self.logger.info(f"Found Claude CLI at: {path}")
                return str(path)

        self.logger.warning("Claude CLI not found. Using mock mode.")
        return None

    def _mock_invoke(self, prompt: str, max_tokens: int = 2000) -> str:
        """Mock LLM responses for testing"""
        import random
        import time

        # Simulate processing delay
        time.sleep(random.uniform(0.5, 1.5))

        # Pattern-based mock responses
        prompt_lower = prompt.lower()

        if "connect" in prompt_lower:
            return "I'll connect to the mainframe at 127.0.0.1:3270"
        elif "login" in prompt_lower or "tso" in prompt_lower:
            return "I'll login to TSO using the provided credentials HERC02"
        elif "screen" in prompt_lower or "read" in prompt_lower:
            return "The screen shows the TSO logon prompt. I can see 'Logon ==>' field."
        elif "logout" in prompt_lower or "logoff" in prompt_lower:
            return "I'll logout from the TSO session using the LOGOFF command"
        elif "error" in prompt_lower or "keyboard" in prompt_lower:
            return "I'll clear the keyboard lock by pressing the Clear key"
        elif "ispf" in prompt_lower:
            return "I'll navigate to ISPF by entering the ISPF command"
        elif "dataset" in prompt_lower:
            return "I'll list the datasets using option 3.4 in ISPF"
        else:
            # Generic response
            actions = [
                "I'll execute the requested command",
                "Processing your request",
                "I'll perform that action now",
                "Executing the specified operation"
            ]
            return random.choice(actions)

    def invoke(self,
               prompt: str,
               system: Optional[str] = None,
               tools: Optional[List[Dict[str, Any]]] = None,
               temperature: float = 0.3) -> Dict[str, Any]:
        """Invoke Claude with prompt and optional tools"""

        if not self.claude_path:
            # Mock response for testing
            mock_text = self._mock_invoke(prompt)
            return {
                "status": "success",
                "content": mock_text,
                "usage": {"tokens": len(mock_text.split())}
            }

        try:
            # Build command
            cmd = [self.claude_path]

            # Add system prompt if provided
            if system:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(system)
                    system_file = f.name
                cmd.extend(['--system', system_file])

            # Note: temperature flag may not be supported by all Claude CLI versions

            # Add JSON output flag for parsing
            cmd.append('--json')

            # Add prompt (use stdin for long prompts)
            if len(prompt) > 1000:
                # Use stdin for long prompts
                process = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=30
                )
            else:
                # Use command line for short prompts
                cmd.append(prompt)
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

            # Clean up temp file
            if system and 'system_file' in locals():
                Path(system_file).unlink(missing_ok=True)

            if process.returncode == 0:
                # Parse JSON response
                response = json.loads(process.stdout)
                self.logger.debug(f"Claude response: {response}")
                return response
            else:
                self.logger.error(f"Claude CLI error: {process.stderr}")
                return {"error": process.stderr}

        except subprocess.TimeoutExpired:
            self.logger.error("Claude CLI timed out")
            return {"error": "Timeout"}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude response: {e}")
            # Return raw text if JSON parsing fails
            return {"text": process.stdout if 'process' in locals() else ""}
        except Exception as e:
            self.logger.error(f"Claude invocation failed: {e}")
            return {"error": str(e)}


    def invoke_with_tools(self,
                          prompt: str,
                          tools_manifest: Path,
                          system_prompt: Optional[Path] = None) -> Dict[str, Any]:
        """Invoke Claude with tools from manifest file"""

        # Load tools manifest
        with open(tools_manifest) as f:
            tools = json.load(f)

        # Load system prompt if provided
        system = None
        if system_prompt and system_prompt.exists():
            system = system_prompt.read_text()

        # Format prompt with tools context
        full_prompt = self._format_prompt_with_tools(prompt, tools)

        return self.invoke(full_prompt, system=system)

    def _format_prompt_with_tools(self, prompt: str, tools: List[Dict]) -> str:
        """Format prompt with available tools"""
        tools_desc = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in tools
        ])

        return f"""Available tools:
{tools_desc}

User request: {prompt}

Please respond with the appropriate tool call in JSON format."""


class ClaudeStreamWrapper:
    """Wrapper for streaming Claude responses"""

    def __init__(self, cli: ClaudeCLI):
        self.cli = cli
        self.logger = cli.logger

    def stream_invoke(self, prompt: str, callback=None) -> str:
        """Invoke Claude with streaming output"""
        if not self.cli.claude_path:
            response = self.cli._mock_invoke(prompt)
            if callback:
                callback(response)
            return response

        try:
            # Use --print flag for streaming
            cmd = [self.cli.claude_path, '--print', prompt]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            full_response = []
            for line in process.stdout:
                full_response.append(line)
                if callback:
                    callback(line.rstrip())

            process.wait()

            return ''.join(full_response)

        except Exception as e:
            self.logger.error(f"Stream invocation failed: {e}")
            return f"Error: {str(e)}"


def test_cli():
    """Test Claude CLI wrapper"""
    print("=== Testing Claude CLI Wrapper ===\n")

    cli = ClaudeCLI()

    # Test basic invocation
    print("1. Testing basic invocation...")
    response = cli.invoke("What is 2+2?")
    print(f"   Response: {response}\n")

    # Test with system prompt
    print("2. Testing with system prompt...")
    response = cli.invoke(
        "Analyze this mainframe screen",
        system="You are a mainframe automation expert."
    )
    print(f"   Response: {response}\n")

    # Test streaming
    print("3. Testing streaming...")
    wrapper = ClaudeStreamWrapper(cli)

    def print_callback(text):
        print(f"   > {text}")

    result = wrapper.stream_invoke(
        "List three mainframe commands",
        callback=print_callback
    )

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_cli()