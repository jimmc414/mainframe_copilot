# Mainframe AI Agent with Claude Code Integration

## Overview

AI-powered mainframe automation using Claude for intelligent TN3270 interaction with MVS 3.8J. Features real-time Claude Code control for interactive mainframe operations.

## Architecture

```
Claude Code <-> Command Queue <-> Agent Controller <-> TN3270 Bridge <-> Mainframe
     |                                    |
     v                                    v
File-based IPC                      Claude CLI (LLM)
```

## Components

### 1. LLM CLI Wrapper (`llm_cli.py`)
- Interfaces with Claude CLI tool
- Handles prompt formatting and tool manifests
- Falls back to mock mode if Claude CLI not available

### 2. Agent Controller (`agent_controller.py`)
- Core automation agent with mainframe operations
- Monitors command queue for Claude Code instructions
- Executes LLM-decided actions based on screen state
- Maintains status file for monitoring

### 3. Claude Code Control (`claude_code_control.py`)
- Direct interface for Claude Code to control agent
- Sends commands via file-based queue
- Provides high-level mainframe operations
- Interactive command mode for testing

### 4. Viewer (`viewer.py`)
- Terminal UI for monitoring agent status
- Shows current screen, activity logs, and state
- Simple mode available for basic terminals

### 5. Run Agent (`run_agent.py`)
- Main CLI entry point
- Multiple modes: interactive, batch, flow, controller, viewer
- Setup testing and validation

## Installation

### Prerequisites
- Hercules mainframe emulator running MVS 3.8J
- TN3270 Bridge API at http://127.0.0.1:8080
- Python 3.8+ with required packages
- Claude CLI (optional, will use mock mode if absent)

### Setup
```bash
# Ensure TN3270 Bridge is running
cd ~/herc/bridge && ./start_api.sh

# Test the setup
python ~/herc/ai/test_integration.py

# Check specific component
python ~/herc/ai/run_agent.py --test
```

## Usage

### 1. Interactive Mode (Claude Code Control)

Start the agent with command queue monitoring:
```bash
python ~/herc/ai/run_agent.py --interactive
```

In another terminal or from Claude Code, control the agent:
```bash
python ~/herc/ai/claude_code_control.py --interactive
```

Commands:
- `screen` - Show current mainframe screen
- `login` - Automated TSO login
- `ispf` - Navigate to ISPF menu
- `fill R C TEXT` - Fill text at row R, column C
- `press KEY` - Press key (Enter, PF3, Clear, etc)
- `flow NAME` - Run YAML flow
- `ask PROMPT` - Ask LLM for help

### 2. Batch Mode

Execute single task:
```bash
python ~/herc/ai/run_agent.py --batch --task "Login and navigate to ISPF"
```

### 3. Flow Mode

Run predefined YAML flow:
```bash
python ~/herc/ai/run_agent.py --flow login.yaml
```

### 4. Viewer Mode

Monitor agent status:
```bash
# Full UI
python ~/herc/ai/viewer.py

# Simple mode
python ~/herc/ai/viewer.py --simple
```

## Claude Code Integration

### Direct Command Sending

From Claude Code, create command files:
```python
import json
from pathlib import Path

# Send command to agent
command = {
    "action": "screen",
    "params": {},
    "source": "claude_code"
}

cmd_dir = Path("~/herc/ai/commands").expanduser()
cmd_file = cmd_dir / "cmd_manual_001.json"
with open(cmd_file, 'w') as f:
    json.dump(command, f)
```

### Using Controller Class

```python
from claude_code_control import ClaudeCodeController

ctrl = ClaudeCodeController()

# Connect to mainframe
ctrl.connect()

# Login to TSO
ctrl.tso_login("HERC02", "CUL8TR")

# Get current screen
screen = ctrl.get_screen()
print(screen)

# Navigate to ISPF
ctrl.navigate_to_ispf()

# Fill and submit
ctrl.fill_field(10, 15, "DATA")
ctrl.press("Enter")
```

## Command Queue Protocol

Commands are JSON files in `~/herc/ai/commands/`:
```json
{
  "action": "fill",
  "params": {
    "row": 10,
    "col": 15,
    "text": "HERC02"
  },
  "source": "claude_code",
  "timestamp": "20250928_143022",
  "sequence": 1
}
```

Results are written to `result_<sequence>.json`:
```json
{
  "status": "success",
  "screen": "...",
  "cursor": [10, 20]
}
```

## Available Actions

### Basic Operations
- `connect` - Connect to mainframe
- `screen` - Get current screen
- `fill` - Fill text at position
- `press` - Press function key
- `wait` - Wait for ready/change

### High-Level Operations
- `flow` - Run YAML flow
- `llm_action` - Let LLM decide action
- `assert` - Assert screen content
- `tso_command` - Execute TSO command

### Navigation
- `login` - TSO login
- `ispf` - Navigate to ISPF
- `exit` - Return to READY

## Status Monitoring

Status file at `~/herc/ai/commands/status.json`:
```json
{
  "state": "processing",
  "last_action": "fill",
  "last_screen": "first 10 lines...",
  "error": null,
  "timestamp": "2025-09-28T14:30:22"
}
```

States:
- `initializing` - Starting up
- `idle` - Waiting for commands
- `processing_command` - Executing command
- `error` - Error occurred

## Troubleshooting

### API Not Running
```bash
cd ~/herc/bridge && ./start_api.sh
```

### Mainframe Not Connected
```bash
cd ~/herc && ./start_hercules.sh
```

### Test Individual Components
```bash
python ~/herc/ai/test_integration.py --component bridge
python ~/herc/ai/test_integration.py --component controller
```

### Check Logs
```bash
# Agent logs
tail -f ~/herc/ai/logs/agent_*.log

# Claude CLI logs
tail -f ~/herc/ai/logs/claude_cli.log

# Flow execution logs
tail -f ~/herc/logs/flows/*.log
```

## Examples

### Example 1: Automated TSO Login
```python
from claude_code_control import ClaudeCodeController

ctrl = ClaudeCodeController()
ctrl.connect()
ctrl.tso_login("HERC02", "CUL8TR")
```

### Example 2: Submit JCL Job
```python
jcl = """//HERC02A JOB (ACCT),'TEST JOB'
//STEP1 EXEC PGM=IEFBR14
//"""

job_id = ctrl.submit_jcl(jcl)
print(f"Submitted job: {job_id}")
```

### Example 3: LLM-Assisted Navigation
```python
result = ctrl.ask_llm("Navigate to dataset list for HERC02")
print(result)
```

## Security Notes

- All operations are localhost only
- Credentials use environment variables
- No cloud services required
- Command files are local filesystem only

## Architecture Benefits

1. **Decoupled Design**: Components communicate via files, not network
2. **Claude Code Integration**: Real-time control from Claude Code window
3. **LLM Intelligence**: Claude decides actions based on screen context
4. **Idempotent Operations**: Safe to retry commands
5. **Observable State**: All actions logged and monitorable

## Next Steps

1. Extend tools manifest for more operations
2. Add more recovery strategies
3. Create domain-specific flows
4. Implement batch job monitoring
5. Add dataset operations

## Support

Check logs in:
- `~/herc/ai/logs/` - Agent logs
- `~/herc/logs/flows/` - Flow execution
- `~/herc/ai/commands/` - Command queue

Run tests:
```bash
python ~/herc/ai/test_integration.py
python ~/herc/ai/run_agent.py --test
```