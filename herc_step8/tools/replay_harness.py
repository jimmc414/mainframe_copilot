#!/usr/bin/env python3
"""Replay harness for regression testing with golden screens"""

import json
import sys
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib
import argparse


class MockBridge:
    """Mock TN3270 bridge for offline replay"""

    def __init__(self, transcript_file: Path = None, golden_dir: Path = None):
        self.transcript = []
        self.golden_screens = {}
        self.current_step = 0
        self.current_screen = None

        # Load transcript if provided
        if transcript_file and transcript_file.exists():
            self.load_transcript(transcript_file)

        # Load golden screens if provided
        if golden_dir and golden_dir.exists():
            self.load_goldens(golden_dir)

    def load_transcript(self, transcript_file: Path):
        """Load JSONL transcript"""
        self.transcript = []
        with open(transcript_file) as f:
            for line in f:
                if line.strip():
                    self.transcript.append(json.loads(line))
        print(f"Loaded {len(self.transcript)} steps from transcript")

    def load_goldens(self, golden_dir: Path):
        """Load golden screens"""
        self.golden_screens = {}
        for golden_file in golden_dir.glob("*.json"):
            with open(golden_file) as f:
                data = json.load(f)
                name = golden_file.stem
                self.golden_screens[name] = data
        print(f"Loaded {len(self.golden_screens)} golden screens")

    def connect(self, host: str = "127.0.0.1:3270") -> Dict[str, Any]:
        """Mock connect"""
        if self.golden_screens.get("initial"):
            self.current_screen = self.golden_screens["initial"]["ascii"]
        else:
            self.current_screen = "MOCK: Connected to " + host
        return {"status": "connected", "mock": True}

    def get_screen(self) -> Dict[str, Any]:
        """Return current mock screen"""
        if self.current_step < len(self.transcript):
            step = self.transcript[self.current_step]
            # Try to get screen from digest
            digest = step.get("digest_after")
            if digest:
                for name, golden in self.golden_screens.items():
                    if golden.get("digest", "").startswith(digest):
                        self.current_screen = golden["ascii"]
                        break

        return {
            "ascii": self.current_screen or "MOCK SCREEN",
            "cursor": [1, 1],
            "mock": True
        }

    def execute_action(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mock action"""
        self.current_step += 1

        # Update screen based on action
        if tool == "press" and params.get("key") == "Enter":
            if "LOGON" in self.current_screen and self.golden_screens.get("ready"):
                self.current_screen = self.golden_screens["ready"]["ascii"]
            elif self.golden_screens.get("next"):
                self.current_screen = self.golden_screens["next"]["ascii"]

        return {"status": "success", "mock": True}


class ReplayHarness:
    """Main replay harness for regression testing"""

    def __init__(self, mode: str = "replay"):
        self.mode = mode  # "replay", "record", "compare"
        self.results = []
        self.differences = []

    def replay_transcript(self, transcript_file: Path, golden_dir: Path = None) -> bool:
        """Replay a transcript and compare with goldens"""
        print(f"\n=== Replaying Transcript: {transcript_file.name} ===")

        # Create mock bridge
        bridge = MockBridge(transcript_file, golden_dir)

        # Replay each step
        with open(transcript_file) as f:
            steps = [json.loads(line) for line in f if line.strip()]

        success_count = 0
        error_count = 0

        for i, step in enumerate(steps):
            print(f"\nStep {i+1}/{len(steps)}: {step['tool']}")

            # Get expected outcome
            expected_outcome = step.get("outcome", "success")
            expected_digest = step.get("digest_after")

            # Execute action
            if step["tool"] == "connect":
                result = bridge.connect()
            elif step["tool"] == "screen":
                result = bridge.get_screen()
            else:
                result = bridge.execute_action(
                    step["tool"],
                    step.get("params_redacted", {})
                )

            # Compare outcome
            actual_outcome = "success" if result else "error"
            if actual_outcome == expected_outcome:
                print(f"  ✓ Outcome matches: {expected_outcome}")
                success_count += 1
            else:
                print(f"  ✗ Outcome mismatch: expected {expected_outcome}, got {actual_outcome}")
                error_count += 1
                self.differences.append({
                    "step": i+1,
                    "tool": step["tool"],
                    "expected": expected_outcome,
                    "actual": actual_outcome
                })

            # Check screen digest if available
            if expected_digest and result.get("ascii"):
                actual_digest = hashlib.sha256(result["ascii"].encode()).hexdigest()[:16]
                if actual_digest == expected_digest:
                    print(f"  ✓ Screen digest matches")
                else:
                    print(f"  ✗ Screen digest mismatch")
                    self.differences.append({
                        "step": i+1,
                        "type": "digest",
                        "expected": expected_digest,
                        "actual": actual_digest
                    })

        # Summary
        total = success_count + error_count
        success_rate = (success_count / total * 100) if total > 0 else 0

        print(f"\n=== Replay Summary ===")
        print(f"Total Steps: {total}")
        print(f"Successful: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Success Rate: {success_rate:.1f}%")

        return error_count == 0

    def compare_screens(self, screen1: str, screen2: str, name: str = "screen") -> bool:
        """Compare two screens and show differences"""
        if screen1 == screen2:
            print(f"  ✓ {name} matches exactly")
            return True

        # Show diff
        lines1 = screen1.split('\n')
        lines2 = screen2.split('\n')

        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=f"{name}_expected",
            tofile=f"{name}_actual",
            lineterm=''
        )

        diff_lines = list(diff)
        if diff_lines:
            print(f"  ✗ {name} differs:")
            for line in diff_lines[:20]:  # Show first 20 lines of diff
                print(f"    {line}")

        return False

    def validate_golden(self, golden_dir: Path, test_screens: Dict[str, str]) -> bool:
        """Validate screens against golden snapshots"""
        print(f"\n=== Validating Against Golden Screens ===")

        golden_dir = Path(golden_dir)
        if not golden_dir.exists():
            print(f"  ✗ Golden directory not found: {golden_dir}")
            return False

        all_match = True

        for name, test_screen in test_screens.items():
            golden_file = golden_dir / f"{name}.json"

            if not golden_file.exists():
                print(f"  ⚠ No golden for: {name}")
                continue

            with open(golden_file) as f:
                golden_data = json.load(f)

            golden_screen = golden_data.get("ascii", "")

            if not self.compare_screens(golden_screen, test_screen, name):
                all_match = False

        return all_match

    def record_golden(self, screen: str, name: str, golden_dir: Path):
        """Record a golden screen snapshot"""
        golden_dir = Path(golden_dir)
        golden_dir.mkdir(parents=True, exist_ok=True)

        golden_file = golden_dir / f"{name}.json"

        golden_data = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "digest": hashlib.sha256(screen.encode()).hexdigest(),
            "ascii": screen,
            "metadata": {
                "rows": len(screen.split('\n')),
                "cols": max(len(line) for line in screen.split('\n')) if screen else 0
            }
        }

        with open(golden_file, 'w') as f:
            json.dump(golden_data, f, indent=2)

        print(f"  ✓ Recorded golden: {golden_file}")

    def generate_report(self, output_file: Path = None):
        """Generate regression test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
            "differences": self.differences,
            "summary": {
                "total_differences": len(self.differences),
                "types": {}
            }
        }

        # Count difference types
        for diff in self.differences:
            diff_type = diff.get("type", "outcome")
            report["summary"]["types"][diff_type] = \
                report["summary"]["types"].get(diff_type, 0) + 1

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {output_file}")
        else:
            print(f"\n=== Regression Report ===")
            print(json.dumps(report, indent=2))

        return report


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Replay harness for regression testing")

    parser.add_argument("--mode", choices=["replay", "record", "validate"],
                        default="replay", help="Operating mode")
    parser.add_argument("--transcript", type=Path,
                        help="Transcript file to replay (JSONL)")
    parser.add_argument("--golden-dir", type=Path, default=Path("~/herc/goldens").expanduser(),
                        help="Directory with golden screens")
    parser.add_argument("--test-screen", type=Path,
                        help="Test screen file to validate")
    parser.add_argument("--record-name", type=str,
                        help="Name for recording golden screen")
    parser.add_argument("--report", type=Path,
                        help="Output file for regression report")

    args = parser.parse_args()

    harness = ReplayHarness(mode=args.mode)

    if args.mode == "replay":
        if not args.transcript:
            print("Error: --transcript required for replay mode")
            sys.exit(1)

        success = harness.replay_transcript(args.transcript, args.golden_dir)

        if args.report:
            harness.generate_report(args.report)

        sys.exit(0 if success else 1)

    elif args.mode == "record":
        if not args.test_screen or not args.record_name:
            print("Error: --test-screen and --record-name required for record mode")
            sys.exit(1)

        with open(args.test_screen) as f:
            screen = f.read()

        harness.record_golden(screen, args.record_name, args.golden_dir)

    elif args.mode == "validate":
        if not args.test_screen:
            print("Error: --test-screen required for validate mode")
            sys.exit(1)

        # Load test screens
        with open(args.test_screen) as f:
            test_data = json.load(f) if args.test_screen.suffix == '.json' else {"test": f.read()}

        success = harness.validate_golden(args.golden_dir, test_data)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()