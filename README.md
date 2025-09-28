# Mainframe Automation System with AI Control

A production-ready IBM mainframe emulation environment with AI-driven automation, designed for demonstrating TN3270 interaction with MVS 3.8J through natural language commands.

## 🎯 Project Overview

**Demo Version (What This Is):**
This project creates a fully automated IBM mainframe environment (MVS 3.8J) running locally on your computer that can be controlled through natural language commands via AI Copilot (Claude Code or Codex), allowing you to demonstrate mainframe operations, run CICS-like transactions, and interact with legacy systems without any mainframe knowledge or hardware.

**Production Capability (What It Enables):**
The same AI Copilot and TN3270 automation demonstrated here can connect directly to live production IBM mainframes, providing identical natural language control and automation capabilities for real enterprise mainframe operations.

## What It Does

This system creates a complete IBM mainframe environment on your local machine and allows you to control it through:
- **Natural language commands** ("Login to TSO and check the dataset list")
- **Claude Code integration** (direct control from AI assistant)
- **Automated workflows** (predefined YAML sequences)
- **API calls** (JSON over HTTP)

### Key Capabilities
- ✅ Run a full IBM MVS 3.8J operating system (circa 1981)
- ✅ Execute TSO commands and ISPF navigation
- ✅ Run KICKS (CICS-compatible) transactions
- ✅ AI-powered screen reading and decision making
- ✅ Automatic error recovery and keyboard lock handling
- ✅ Session recording and replay for regression testing
- ✅ Real-time monitoring and health checks

## Quick Start

### Prerequisites
```bash
# Ubuntu 20.04+ in WSL2 or native Linux
# Install required packages
sudo apt update && sudo apt install -y \
    build-essential cmake libsdl2-dev \
    python3 python3-pip python3-venv \
    x3270 s3270 c3270 \
    netcat tmux jq curl git
```

### Installation
```bash
# 1. Clone/extract the project
cd ~
git clone [repository] herc  # or extract archive

# 2. Run one-command setup
cd ~/herc
./demo.sh
```

That's it! The system will:
1. Start the Hercules mainframe emulator
2. Boot MVS 3.8J operating system
3. Start the TN3270 Bridge API
4. Launch the AI agent
5. Wait for your commands

## How It Works

### Architecture Overview
```
Your Commands → AI Agent → TN3270 Bridge → Mainframe Emulator → MVS 3.8J
```

### Components

#### 1. **Hercules Emulator** (`~/herc/mvs38j/`)
- Emulates IBM System/370 mainframe hardware
- Runs the actual MVS 3.8J operating system from 1981
- Provides TN3270 terminal access on port 3270

#### 2. **TN3270 Bridge** (`~/herc/bridge/`)
- Converts between JSON API calls and TN3270 protocol
- Manages s3270 subprocess for screen scraping
- Provides REST endpoints for automation
- Health monitoring and session management

#### 3. **AI Agent** (`~/herc/ai/`)
- Interprets natural language commands
- Reads and understands mainframe screens
- Makes decisions on next actions
- Handles error recovery automatically

#### 4. **Command Queue** (`~/herc/ai/commands/`)
- File-based IPC for Claude Code integration
- Allows real-time control from external processes
- Status reporting for monitoring

#### 5. **Flow System** (`~/herc/flows/`)
- YAML-based automation sequences
- Predefined workflows (login, KICKS, etc.)
- Recovery strategies for common errors

## Usage Examples

### 1. Basic Operation
```bash
# Start in batch mode (run and exit)
./demo.sh batch "Login to TSO and check status"

# Start in interactive mode (continuous monitoring)
./demo.sh interactive

# Start with UI viewer
./demo.sh ui
```

### 2. Claude Code Integration
From Claude Code or any Python environment:

```python
# Method 1: Direct command queue
import json
from pathlib import Path

def send_command(action, params={}):
    cmd_dir = Path("~/herc/ai/commands").expanduser()
    command = {"action": action, "params": params}
    cmd_file = cmd_dir / f"cmd_{time.time()}.json"
    with open(cmd_file, 'w') as f:
        json.dump(command, f)

# Control the mainframe
send_command("connect")
send_command("screen")
send_command("flow", {"flow_name": "login.yaml"})
```

```python
# Method 2: High-level controller
from claude_code_control import ClaudeCodeController

ctrl = ClaudeCodeController()
ctrl.connect()
ctrl.tso_login("HERC02", "CUL8TR")
screen = ctrl.get_screen()
print(screen)
ctrl.navigate_to_ispf()
```

### 3. API Access
```bash
# Check health
curl http://127.0.0.1:8080/healthz | jq

# Get screen
curl http://127.0.0.1:8080/screen | jq

# Send keypress
curl -X POST http://127.0.0.1:8080/press \
  -H "Content-Type: application/json" \
  -d '{"key": "Enter"}'
```

## Directory Structure
```
~/herc/
├── config.yaml           # Central configuration
├── demo.sh              # Start script
├── stop.sh              # Shutdown script
├── README.md            # This file
├── mvs38j/              # Hercules & MVS system
├── bridge/              # TN3270 Bridge API
├── ai/                  # AI Agent & controllers
├── flows/               # Automation workflows
├── tools/               # Utilities (watchdog, replay)
├── logs/                # All system logs
├── goldens/             # Reference screens
└── docs/                # Full documentation
    ├── RUNBOOK.md       # Operational guide
    ├── POLICY_ADDENDUM.md  # Security policies
    └── POLICY_MAP.md    # Policy enforcement
```

## Key Features

### 🔒 Security
- **Localhost only** - No external network exposure
- **Credential redaction** - Automatic in all logs
- **Action allowlist** - Only safe operations permitted
- **Demo credentials** - HERC02/CUL8TR (never production)

### 🔄 Reliability
- **Auto-reconnect** - Handles disconnections gracefully
- **Keyboard recovery** - Automatic unlock on errors
- **Session preservation** - Maintains state across errors
- **Health monitoring** - Watchdog service available

### 📊 Observability
- **JSONL logging** - Structured action logs
- **Metrics collection** - Performance tracking
- **Screen tracing** - Optional full captures
- **Replay system** - Regression testing

### 🎯 Automation
- **Natural language** - "Login and go to ISPF"
- **YAML flows** - Predefined sequences
- **Error recovery** - Built-in strategies
- **Golden screens** - Baseline validation

## Common Operations

### Starting and Stopping
```bash
# Start everything
cd ~/herc
./demo.sh [mode]  # modes: batch, interactive, ui, dry-run

# Stop everything (with log archival)
./stop.sh

# Reset session without restart
curl -X POST http://127.0.0.1:8080/reset_session
```

### Monitoring
```bash
# Check health
curl http://127.0.0.1:8080/healthz | jq

# View logs
tail -f ~/herc/logs/ai/actions_$(date +%Y%m%d).jsonl | jq

# View metrics
cat ~/herc/logs/ai/metrics.json | jq

# Status viewer (separate terminal)
python ~/herc/ai/viewer.py
```

### Testing
```bash
# Run integration tests
python ~/herc/ai/test_integration.py

# Replay session
python ~/herc/tools/replay_harness.py \
  --mode replay \
  --transcript logs/ai/sample_transcript.jsonl

# Run evaluation suite
python ~/herc/tools/evaluate.py
```

## Troubleshooting

### Connection Issues
```bash
# Check services
ps aux | grep -E "hercules|s3270|python"
netstat -tlnp | grep -E "3270|8080"

# Restart Bridge
pkill -f tn3270_bridge
cd ~/herc/bridge && python -m tn3270_bridge.api_enhanced &
```

### Keyboard Lock
```bash
# Send Clear key
curl -X POST http://127.0.0.1:8080/press -d '{"key": "Clear"}'

# Reset session
curl -X POST http://127.0.0.1:8080/reset_session
```

### Agent Not Responding
```bash
# Check command queue
ls ~/herc/ai/commands/

# Clear queue
rm -f ~/herc/ai/commands/cmd_*.json

# Restart agent
pkill -f run_agent.py
cd ~/herc/ai && python run_agent.py --interactive
```

## Advanced Usage

### Custom Flows
Create `~/herc/flows/custom.yaml`:
```yaml
name: custom_flow
description: My automation
steps:
  - action: connect
  - action: wait
    condition: ready
  - action: fill
    row: 10
    col: 15
    text: "HERC02"
  - action: press
    key: Enter
```

### Extending the System
1. Add new flows in `~/herc/flows/`
2. Extend tools in `~/herc/ai/tools/`
3. Modify prompts in `~/herc/ai/prompts/`
4. Update config in `~/herc/config.yaml`

## Documentation

- **[RUNBOOK.md](docs/RUNBOOK.md)** - Complete operational guide
- **[QUICKSTART.md](ai/QUICKSTART.md)** - Quick reference for Claude Code
- **[POLICY_ADDENDUM.md](docs/POLICY_ADDENDUM.md)** - Security and operational policies
- **[API Documentation](bridge/README.md)** - TN3270 Bridge API reference

## Performance Targets

- **Success Rate**: ≥95%
- **Actions per Task**: ≤40
- **Response Time**: <500ms per action
- **Recovery Rate**: ≥90%

## License and Credits

- **Hercules**: Open source System/370 emulator
- **MVS 3.8J**: IBM operating system (public domain)
- **TK5**: Turnkey MVS distribution
- **KICKS**: Open source CICS-compatible system
- **s3270**: Part of x3270 project

## Support

1. Check the [RUNBOOK](docs/RUNBOOK.md) for detailed operations
2. Review logs in `~/herc/logs/`
3. Run diagnostics: `python ~/herc/ai/test_integration.py`
4. Check service health: `curl http://127.0.0.1:8080/healthz`

---

**System Version**: 1.0.0
**Architecture**: Production-ready demonstration system
**Security**: Localhost-only, no external network access
**Requirements**: 4GB RAM, 10GB disk, Ubuntu 20.04+