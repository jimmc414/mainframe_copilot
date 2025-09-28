# Quick Start Guide for Claude Code Mainframe Control

## Overview
Control a mainframe emulator (MVS 3.8J) directly from Claude Code using AI-powered automation.

## Prerequisites Check
```bash
# 1. Check if Hercules is running
ps aux | grep hercules

# 2. Check if TN3270 Bridge API is running
curl http://127.0.0.1:8080/status

# 3. Test the integration
python ~/herc/ai/test_integration.py
```

## Starting Components

### 1. Start Hercules (if not running)
```bash
cd ~/herc && ./start_hercules.sh
```

### 2. Start TN3270 Bridge API
```bash
cd ~/herc/bridge && ./start_api.sh
```

### 3. Start AI Agent
```bash
# Interactive mode (waits for Claude Code commands)
python ~/herc/ai/run_agent.py --interactive
```

## Controlling from Claude Code

### Method 1: Direct Command Queue
```python
import json
from pathlib import Path

# Send command to mainframe
command = {
    "action": "screen",  # Get current screen
    "params": {}
}

cmd_file = Path("~/herc/ai/commands/cmd_001.json").expanduser()
with open(cmd_file, 'w') as f:
    json.dump(command, f)
```

### Method 2: Using Controller
```python
from claude_code_control import ClaudeCodeController

ctrl = ClaudeCodeController()

# Connect and login
ctrl.connect()
ctrl.tso_login("HERC02", "CUL8TR")

# Get screen
screen = ctrl.get_screen()
print(screen)

# Navigate
ctrl.navigate_to_ispf()
```

### Method 3: Interactive Control
```bash
# Run the controller interactively
python ~/herc/ai/claude_code_control.py --interactive
```

## Available Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| connect | Connect to mainframe | host (default: 127.0.0.1:3270) |
| screen | Get current screen | none |
| fill | Fill text at position | row, col, text |
| press | Press function key | key (Enter, PF3, Clear, etc) |
| flow | Run YAML flow | flow_name |
| llm_action | Ask LLM for help | prompt |
| status | Get agent status | none |

## Example Workflows

### 1. TSO Login
```python
ctrl = ClaudeCodeController()
ctrl.connect()
ctrl.tso_login("HERC02", "CUL8TR")
```

### 2. Navigate to ISPF
```python
ctrl.navigate_to_ispf()
```

### 3. Submit JCL Job
```python
jcl = """//HERC02A JOB (ACCT),'TEST'
//STEP1 EXEC PGM=IEFBR14
//"""
job_id = ctrl.submit_jcl(jcl)
```

### 4. Run Predefined Flow
```python
ctrl.run_flow("end_to_end.yaml")
```

## Monitoring

### View Agent Status
```bash
# Terminal UI
python ~/herc/ai/viewer.py

# Simple mode
python ~/herc/ai/viewer.py --simple

# Check status file
cat ~/herc/ai/commands/status.json | python -m json.tool
```

### View Logs
```bash
# Agent logs
tail -f ~/herc/ai/logs/agent_*.log

# Flow execution logs
tail -f ~/herc/logs/flows/*.log
```

## Available Flows

- `login.yaml` - TSO login
- `kicks_start.yaml` - Start KICKS
- `kicks_demo.yaml` - KICKS demo transaction
- `logout.yaml` - Exit and logoff
- `end_to_end.yaml` - Complete sequence

## Troubleshooting

### Connection Failed
1. Check Hercules: `ps aux | grep hercules`
2. Check API: `curl http://127.0.0.1:8080/status`
3. Check port: `ss -ltn | grep 3270`

### Agent Not Responding
1. Check if agent is running: `ps aux | grep agent_controller`
2. Check command queue: `ls ~/herc/ai/commands/`
3. Check status: `cat ~/herc/ai/commands/status.json`

### Screen Not Updating
1. Wait for keyboard unlock: `ctrl.wait("ready")`
2. Check screen digest changed: `ctrl.wait("change")`
3. Add delays: `time.sleep(1)`

## Tips

1. **Always wait for ready** before sending input
2. **Check screen content** before taking actions
3. **Use flows** for complex sequences
4. **Monitor status** to understand agent state
5. **Check logs** when debugging issues

## Full Example

```python
#!/usr/bin/env python3
"""Complete example of mainframe control from Claude Code"""

from claude_code_control import ClaudeCodeController
import time

# Create controller
ctrl = ClaudeCodeController()

# Connect to mainframe
print("Connecting...")
ctrl.connect()
time.sleep(1)

# Login to TSO
print("Logging in...")
ctrl.tso_login("HERC02", "CUL8TR")
time.sleep(3)

# Navigate to ISPF
print("Going to ISPF...")
ctrl.navigate_to_ispf()
time.sleep(2)

# Show current screen
ctrl.show_screen()

# Exit back to READY
print("Exiting...")
ctrl.exit_to_ready()

print("Done!")
```

## Next Steps

1. Explore the [full documentation](README.md)
2. Try the [example script](example_claude_code.py)
3. Create custom flows in YAML
4. Extend the tools manifest
5. Build your own automation scripts

## Support

- Test setup: `python ~/herc/ai/run_agent.py --test`
- Run tests: `python ~/herc/ai/test_integration.py`
- View logs: `~/herc/ai/logs/`
- Command queue: `~/herc/ai/commands/`