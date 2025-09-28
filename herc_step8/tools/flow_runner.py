#!/usr/bin/env python3
"""Flow runner for deterministic mainframe automation"""

import sys
import os
import time
import json
import yaml
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from screen_fingerprint import (
    normalize_screen,
    compute_digest,
    match_screen,
    save_golden,
    assert_golden,
    get_field_at_label
)

class FlowRunner:
    """Executes flows via TN3270 Bridge API"""

    def __init__(self, host: str = "127.0.0.1:8080", trace: bool = False):
        """Initialize flow runner"""
        self.api_url = f"http://{host}"
        self.trace = trace
        self.env_vars = {}
        self.current_digest = None
        self.transcript = []
        self.save_goldens_flag = False
        self.assert_goldens_flag = False
        self.flows_dir = Path.home() / "herc" / "flows"
        self.logs_dir = Path.home() / "herc" / "logs" / "flows"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log_transcript(self, action: str, result: str = "", secret: bool = False):
        """Add entry to transcript"""
        timestamp = datetime.now().isoformat()

        if secret and result:
            result = "***REDACTED***"

        entry = {
            'timestamp': timestamp,
            'action': action,
            'result': result,
            'digest': self.current_digest[:16] if self.current_digest else None
        }

        self.transcript.append(entry)

        if self.trace:
            print(f"[{timestamp}] {action}: {result}")

    def save_transcript(self, flow_name: str, success: bool = True):
        """Save transcript to log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "" if success else "_fail"
        log_file = self.logs_dir / f"{flow_name}_{timestamp}{suffix}.log"

        with open(log_file, 'w') as f:
            for entry in self.transcript:
                f.write(f"[{entry['timestamp']}] {entry['action']}")
                if entry['result']:
                    f.write(f": {entry['result']}")
                if entry['digest']:
                    f.write(f" (digest: {entry['digest']}...)")
                f.write("\n")

        return log_file

    def save_failure_screen(self, flow_name: str, screen_text: str):
        """Save screen dump on failure"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fail_file = self.logs_dir / f"{flow_name}_{timestamp}_fail.txt"

        with open(fail_file, 'w') as f:
            f.write(f"Failed screen dump at {timestamp}\n")
            f.write("=" * 80 + "\n")
            f.write(screen_text)
            f.write("\n" + "=" * 80 + "\n")

        return fail_file

    def get_screen(self) -> Dict[str, Any]:
        """Get current screen via API"""
        response = requests.get(f"{self.api_url}/screen")
        response.raise_for_status()
        snapshot = response.json()
        self.current_digest = snapshot.get('digest')
        return snapshot

    def wait_ready(self, timeout_ms: int = 5000) -> bool:
        """Wait for keyboard to be ready"""
        start = time.time()
        timeout = timeout_ms / 1000.0

        while time.time() - start < timeout:
            try:
                # Check if connected
                status = requests.get(f"{self.api_url}/status").json()
                if status.get('connected'):
                    return True
            except:
                pass
            time.sleep(0.1)

        return False

    def wait_change(self, timeout_ms: int = 5000) -> bool:
        """Wait for screen digest to change"""
        start = time.time()
        timeout = timeout_ms / 1000.0
        initial_digest = self.current_digest

        while time.time() - start < timeout:
            snapshot = self.get_screen()
            if snapshot.get('digest') != initial_digest:
                return True
            time.sleep(0.1)

        return False

    def press(self, aid: str) -> bool:
        """Press AID key"""
        self.log_transcript(f"press: {aid}")

        response = requests.post(
            f"{self.api_url}/press",
            json={"aid": aid}
        )

        return response.status_code == 200

    def fill_at(self, row: int, col: int, value: str, secret: bool = False) -> bool:
        """Fill field at position"""
        display_value = "***REDACTED***" if secret else value
        self.log_transcript(f"fill_at: ({row},{col}) = {display_value}", secret=secret)

        response = requests.post(
            f"{self.api_url}/fill",
            json={"row": row, "col": col, "text": value, "enter": False}
        )

        return response.status_code == 200

    def fill_by_label(self, label: str, offset: int, value: str, secret: bool = False) -> bool:
        """Fill field by label"""
        display_value = "***REDACTED***" if secret else value
        self.log_transcript(f"fill_by_label: {label}+{offset} = {display_value}", secret=secret)

        response = requests.post(
            f"{self.api_url}/fill_by_label",
            json={"label": label, "offset": offset, "text": value}
        )

        return response.status_code == 200

    def execute_step(self, step: Dict[str, Any]) -> bool:
        """Execute a single flow step"""
        # Get step type (first key)
        step_type = list(step.keys())[0]
        params = step[step_type] if isinstance(step[step_type], dict) else {}

        try:
            if step_type == "wait_ready":
                timeout = params.get('timeout_ms', 5000)
                success = self.wait_ready(timeout)
                self.log_transcript(f"wait_ready: {timeout}ms", "ready" if success else "timeout")
                return success

            elif step_type == "wait_change":
                timeout = params.get('timeout_ms', 5000)
                success = self.wait_change(timeout)
                self.log_transcript(f"wait_change: {timeout}ms", "changed" if success else "timeout")
                return success

            elif step_type == "press":
                aid = params.get('aid', 'Enter')
                return self.press(aid)

            elif step_type == "fill_at":
                row = params['row']
                col = params['col']

                # Get value from environment or direct
                if 'value_env' in params:
                    value = self.env_vars.get(params['value_env'], '')
                else:
                    value = params.get('value', '')

                secret = params.get('secret', False)
                return self.fill_at(row, col, value, secret)

            elif step_type == "fill_by_label":
                label = params['label']
                offset = params.get('offset', 1)

                # Get value from environment or direct
                if 'value_env' in params:
                    value = self.env_vars.get(params['value_env'], '')
                else:
                    value = params.get('value', '')

                secret = params.get('secret', False)
                return self.fill_by_label(label, offset, value, secret)

            elif step_type == "assert_screen":
                snapshot = self.get_screen()
                matched, rule = match_screen(snapshot, params)

                if matched:
                    self.log_transcript(f"assert_screen", f"matched: {rule}")
                else:
                    self.log_transcript(f"assert_screen", "FAILED")
                    self.save_failure_screen("assert_fail", snapshot.get('ascii', ''))

                return matched

            elif step_type == "assert_not_screen":
                snapshot = self.get_screen()
                matched, rule = match_screen(snapshot, params)

                if not matched:
                    self.log_transcript(f"assert_not_screen", "passed")
                else:
                    self.log_transcript(f"assert_not_screen", f"FAILED: matched {rule}")
                    self.save_failure_screen("assert_fail", snapshot.get('ascii', ''))

                return not matched

            elif step_type == "snapshot":
                name = params.get('name', 'snapshot')
                snapshot = self.get_screen()
                self.log_transcript(f"snapshot: {name}")

                if self.save_goldens_flag:
                    save_golden(name, snapshot)

                return True

            elif step_type == "golden:save":
                name = params['name']
                snapshot = self.get_screen()
                save_golden(name, snapshot)
                self.log_transcript(f"golden:save: {name}")
                return True

            elif step_type == "golden:assert":
                name = params['name']
                snapshot = self.get_screen()
                matches, diff = assert_golden(name, snapshot)

                if matches:
                    self.log_transcript(f"golden:assert: {name}", "matches")
                else:
                    self.log_transcript(f"golden:assert: {name}", "FAILED")
                    if self.trace:
                        print(f"Diff:\n{diff}")

                return matches

            elif step_type == "sleep_ms":
                ms = params if isinstance(params, int) else params.get('ms', 1000)
                time.sleep(ms / 1000.0)
                self.log_transcript(f"sleep: {ms}ms")
                return True

            else:
                self.log_transcript(f"unknown step: {step_type}", "SKIPPED")
                return True

        except Exception as e:
            self.log_transcript(f"{step_type}", f"ERROR: {str(e)}")
            return False

    def execute_flow(self, flow: Dict[str, Any]) -> bool:
        """Execute a complete flow"""
        flow_name = flow.get('name', 'unnamed')
        self.log_transcript(f"Starting flow: {flow_name}")

        # Handle imports
        if 'imports' in flow:
            for import_file in flow['imports']:
                import_path = self.flows_dir / import_file
                if import_path.exists():
                    with open(import_path, 'r') as f:
                        imported = yaml.safe_load(f)

                    self.log_transcript(f"Importing: {import_file}")
                    if not self.execute_flow(imported):
                        return False

        # Execute steps
        steps = flow.get('steps', [])
        for i, step in enumerate(steps):
            if not self.execute_step(step):
                # Check for recovery actions
                if 'recovery' in flow:
                    if self.handle_recovery(flow['recovery']):
                        continue

                self.log_transcript(f"Flow failed at step {i+1}")
                return False

        self.log_transcript(f"Flow completed: {flow_name}")
        return True

    def handle_recovery(self, recovery: List[Dict[str, Any]]) -> bool:
        """Handle recovery actions"""
        snapshot = self.get_screen()
        ascii_text = snapshot.get('ascii', '')

        for rule in recovery:
            if 'when_ascii_contains' in rule:
                if rule['when_ascii_contains'] in ascii_text:
                    self.log_transcript(f"Recovery triggered: {rule['when_ascii_contains']}")

                    for action in rule.get('do', []):
                        if not self.execute_step(action):
                            return False

                    return True

        return False

    def connect(self) -> bool:
        """Connect to mainframe"""
        response = requests.post(
            f"{self.api_url}/connect",
            json={"host": "127.0.0.1:3270"}
        )

        if response.status_code == 200:
            self.log_transcript("Connected to 127.0.0.1:3270")
            return True

        return False

    def disconnect(self):
        """Disconnect from mainframe"""
        requests.post(f"{self.api_url}/disconnect")
        self.log_transcript("Disconnected")

    def run(self, flow_file: Path, env: Dict[str, str] = None,
            save_goldens: bool = False, assert_goldens: bool = False) -> bool:
        """Run a flow file"""
        self.env_vars = env or {}
        self.save_goldens_flag = save_goldens
        self.assert_goldens_flag = assert_goldens

        # Load flow
        with open(flow_file, 'r') as f:
            flow = yaml.safe_load(f)

        flow_name = flow_file.stem

        try:
            # Connect
            if not self.connect():
                print("Failed to connect")
                return False

            # Execute flow
            success = self.execute_flow(flow)

            # Save transcript
            log_file = self.save_transcript(flow_name, success)
            print(f"Transcript saved to: {log_file}")

            return success

        except Exception as e:
            self.log_transcript(f"Error: {str(e)}")
            log_file = self.save_transcript(flow_name, False)
            print(f"Error transcript saved to: {log_file}")

            # Save failure screen if available
            try:
                snapshot = self.get_screen()
                fail_file = self.save_failure_screen(flow_name, snapshot.get('ascii', ''))
                print(f"Failure screen saved to: {fail_file}")
            except:
                pass

            return False

        finally:
            self.disconnect()

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Run mainframe automation flows')
    parser.add_argument('command', choices=['run'], help='Command to execute')
    parser.add_argument('flow_file', help='YAML flow file to run')
    parser.add_argument('--host', default='127.0.0.1:8080', help='TN3270 Bridge API host')
    parser.add_argument('--env', action='append', help='Environment variable KEY=VALUE')
    parser.add_argument('--save-goldens', action='store_true', help='Save golden snapshots')
    parser.add_argument('--assert-goldens', action='store_true', help='Assert golden snapshots')
    parser.add_argument('--trace', action='store_true', help='Enable trace output')

    args = parser.parse_args()

    # Parse environment variables
    env_vars = {}
    if args.env:
        for env_str in args.env:
            if '=' in env_str:
                key, value = env_str.split('=', 1)
                env_vars[key] = value

    # Also get from environment
    if 'TSO_USER' in os.environ:
        env_vars['TSO_USER'] = os.environ['TSO_USER']
    if 'TSO_PASS' in os.environ:
        env_vars['TSO_PASS'] = os.environ['TSO_PASS']

    # Create runner
    runner = FlowRunner(host=args.host, trace=args.trace)

    # Run flow
    flow_file = Path(args.flow_file)
    if not flow_file.exists():
        # Try flows directory
        flow_file = Path.home() / "herc" / "flows" / args.flow_file
        if not flow_file.exists():
            print(f"Flow file not found: {args.flow_file}")
            sys.exit(1)

    success = runner.run(
        flow_file,
        env=env_vars,
        save_goldens=args.save_goldens,
        assert_goldens=args.assert_goldens
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()