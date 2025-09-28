#!/usr/bin/env python3
"""Test AI integration with mainframe"""

import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.llm_cli import ClaudeCLI
from ai.claude_code_control import ClaudeCodeController
from ai.tn3270_client import TN3270Bridge


def test_llm_cli():
    """Test Claude CLI wrapper"""
    print("=== Testing LLM CLI ===")

    cli = ClaudeCLI()

    # Test basic invocation
    print("1. Testing mock response...")
    response = cli.invoke("Navigate to ISPF main menu")
    print(f"   Response: {json.dumps(response, indent=2)}")

    # Test tools loading
    print("\n2. Testing tools manifest...")
    tools_file = Path("~/herc/ai/tools/mainframe_tools.json").expanduser()
    if tools_file.exists():
        with open(tools_file) as f:
            tools = json.load(f)
        print(f"   Loaded {len(tools)} tools")
        for tool in tools[:3]:
            print(f"   - {tool['name']}: {tool['description']}")
    else:
        print("   Tools manifest not found")

    return True


def test_bridge_connection():
    """Test TN3270 bridge"""
    print("\n=== Testing TN3270 Bridge ===")

    bridge = TN3270Bridge("http://127.0.0.1:8080")

    # Test API status
    print("1. Checking API status...")
    try:
        import requests
        response = requests.get("http://127.0.0.1:8080/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   API running: {data}")
        else:
            print(f"   API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   API not reachable: {e}")
        print("   Start with: cd ~/herc/bridge && ./start_api.sh")
        return False

    # Test connection
    print("\n2. Testing mainframe connection...")
    result = bridge.connect()
    if result.get("status") == "connected":
        print("   Connected to mainframe")

        # Get screen
        screen = bridge.get_screen()
        if screen and "ascii" in screen:
            print("\n3. Current screen:")
            lines = screen["ascii"].split('\n')[:5]
            for line in lines:
                print(f"   {line}")
        return True
    else:
        print("   Failed to connect")
        return False


def test_command_queue():
    """Test command queue mechanism"""
    print("\n=== Testing Command Queue ===")

    command_dir = Path("~/herc/ai/commands").expanduser()
    command_dir.mkdir(parents=True, exist_ok=True)

    # Create test command
    print("1. Creating test command...")
    test_cmd = {
        "action": "screen",
        "params": {},
        "source": "test",
        "timestamp": time.strftime("%Y%m%d_%H%M%S")
    }

    cmd_file = command_dir / "cmd_test_001.json"
    with open(cmd_file, 'w') as f:
        json.dump(test_cmd, f, indent=2)
    print(f"   Created: {cmd_file}")

    # Check if command exists
    print("\n2. Verifying command file...")
    if cmd_file.exists():
        print("   Command file exists")
        cmd_file.unlink()  # Clean up
        return True
    else:
        print("   Failed to create command")
        return False


def test_claude_code_control():
    """Test Claude Code controller"""
    print("\n=== Testing Claude Code Controller ===")

    controller = ClaudeCodeController()

    print("1. Getting agent status...")
    status = controller.get_status()
    print(f"   Status: {status.get('state', 'unknown')}")

    print("\n2. Testing command creation...")
    # Don't actually send, just test the mechanism
    cmd_file = controller._send_command("test", {"param": "value"})
    print(f"   Command created: {cmd_file}")

    # Clean up test command
    cmd_path = controller.command_dir / cmd_file
    if cmd_path.exists():
        cmd_path.unlink()
        print("   Test command cleaned up")

    return True


def test_flow_runner():
    """Test flow runner integration"""
    print("\n=== Testing Flow Runner ===")

    flows_dir = Path("~/herc/flows").expanduser()
    if not flows_dir.exists():
        print("   Flows directory not found")
        return False

    print("1. Available flows:")
    yaml_files = list(flows_dir.glob("*.yaml"))
    for flow in yaml_files[:5]:
        print(f"   - {flow.name}")

    print("\n2. Checking flow structure...")
    test_flow = flows_dir / "test_recovery.yaml"
    if test_flow.exists():
        with open(test_flow) as f:
            content = f.read()
        if "steps:" in content and "recovery:" in content:
            print("   Flow structure valid")
            return True
        else:
            print("   Invalid flow structure")
            return False
    else:
        print("   Test flow not found")
        return False


def run_integration_test():
    """Run full integration test"""
    print("=" * 60)
    print("MAINFRAME AI INTEGRATION TEST")
    print("=" * 60)

    results = []

    # Test each component
    tests = [
        ("LLM CLI", test_llm_cli),
        ("Bridge Connection", test_bridge_connection),
        ("Command Queue", test_command_queue),
        ("Claude Code Control", test_claude_code_control),
        ("Flow Runner", test_flow_runner),
    ]

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\nError in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{name:20} {status}")
        if not success:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed! The AI integration is ready to use.")
        print("\nNext steps:")
        print("1. Start the agent:")
        print("   python ~/herc/ai/run_agent.py --interactive")
        print("\n2. Control from Claude Code:")
        print("   python ~/herc/ai/claude_code_control.py --interactive")
        print("\n3. Monitor status:")
        print("   python ~/herc/ai/viewer.py")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("- Ensure TN3270 Bridge API is running:")
        print("  cd ~/herc/bridge && ./start_api.sh")
        print("- Ensure Hercules is running:")
        print("  cd ~/herc && ./start_hercules.sh")

    return all_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test AI integration")
    parser.add_argument("--component", "-c", type=str,
                        choices=["llm", "bridge", "queue", "controller", "flows"],
                        help="Test specific component")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    if args.component:
        # Test specific component
        if args.component == "llm":
            test_llm_cli()
        elif args.component == "bridge":
            test_bridge_connection()
        elif args.component == "queue":
            test_command_queue()
        elif args.component == "controller":
            test_claude_code_control()
        elif args.component == "flows":
            test_flow_runner()
    else:
        # Run full integration test
        success = run_integration_test()
        sys.exit(0 if success else 1)