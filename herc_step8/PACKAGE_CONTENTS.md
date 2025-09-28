# Mainframe Automation System - Step 8 Package

## Package Contents

This directory contains the complete Step 8 hardened mainframe automation system.

### Core Components

#### `/ai/` - AI Agent System
- `agent_controller.py` - Main agent with command queue monitoring
- `claude_code_control.py` - Claude Code interface controller
- `llm_cli.py` - Claude CLI wrapper
- `observability.py` - JSONL logging and metrics
- `run_agent.py` - CLI entry point
- `tn3270_client.py` - TN3270 bridge client
- `viewer.py` - Terminal UI for monitoring
- `test_integration.py` - Integration tests
- `example_claude_code.py` - Usage examples
- `/prompts/` - System and developer prompts
- `/commands/` - Command queue directory

#### `/bridge/` - TN3270 Bridge API
- `/tn3270_bridge/`
  - `api.py` - Original API
  - `api_enhanced.py` - Enhanced API with health/reset
  - `session.py` - S3270 session manager
  - `parser.py` - Screen parser
  - `cli_stdio.py` - CLI interface
- `start_api.sh` - API startup script
- `requirements.txt` - Python dependencies

#### `/tools/` - Utilities
- `watchdog.py` - Service health monitor
- `replay_harness.py` - Regression testing
- `flow_runner.py` - YAML flow executor
- `screen_fingerprint.py` - Golden screen manager

#### `/flows/` - Automation Workflows
- `login.yaml` - TSO login flow
- `logout.yaml` - TSO logout flow
- `kicks_start.yaml` - Start KICKS system
- `kicks_demo.yaml` - KICKS demo transaction
- `end_to_end.yaml` - Complete cycle
- `test_recovery.yaml` - Error recovery test

#### `/docs/` - Documentation
- `RUNBOOK.md` - Complete operational guide
- `POLICY_ADDENDUM.md` - Security policies
- `POLICY_MAP.md` - Policy enforcement mapping

#### `/config/` - Configuration
- `tn3270-bridge.service` - Systemd service for bridge
- `herc-watchdog.service` - Systemd service for watchdog

#### `/logs/` - Sample Data
- `sample_transcript.jsonl` - Example session
- `eval_summary.json` - Evaluation metrics

#### `/goldens/` - Reference Screens
- `logon_screen.json` - Login screen golden
- `ready_prompt.json` - Ready prompt golden

### Main Files
- `README.md` - System overview and quick start
- `config.yaml` - Central configuration
- `demo.sh` - One-command startup script
- `stop.sh` - Graceful shutdown script
- `demo.tmux` - tmux layout configuration

## Installation Instructions

### Prerequisites
```bash
# Ubuntu 20.04+ in WSL2
sudo apt update && sudo apt install -y \
    build-essential cmake libsdl2-dev \
    python3 python3-pip python3-venv \
    x3270 s3270 c3270 \
    netcat tmux jq curl git
```

### Setup
1. Copy this directory to `~/herc` in WSL:
   ```bash
   cp -r /mnt/c/python/mainframe_copilot/herc_step8 ~/herc
   ```

2. Set permissions:
   ```bash
   cd ~/herc
   chmod +x *.sh tools/*.py ai/*.py
   ```

3. Create Python environment:
   ```bash
   cd ~/herc/bridge
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Start the system:
   ```bash
   cd ~/herc
   ./demo.sh
   ```

## Usage

### Quick Start
```bash
# Start in batch mode
./demo.sh batch "Login to TSO"

# Start in interactive mode (for Claude Code)
./demo.sh interactive

# Start with UI viewer
./demo.sh ui
```

### Claude Code Integration
From Claude Code or Python:
```python
import sys
sys.path.insert(0, '/home/jim/herc/ai')
from claude_code_control import ClaudeCodeController

ctrl = ClaudeCodeController()
ctrl.connect()
ctrl.tso_login("HERC02", "CUL8TR")
```

### API Access
```bash
# Check health
curl http://127.0.0.1:8080/healthz | jq

# Get screen
curl http://127.0.0.1:8080/screen | jq
```

## Key Features
- ✅ Localhost-only security
- ✅ Automatic credential redaction
- ✅ Action allowlist enforcement
- ✅ JSONL structured logging
- ✅ Health monitoring and auto-recovery
- ✅ Regression testing with replay
- ✅ Claude Code real-time control

## Support
See `docs/RUNBOOK.md` for complete operational guide.

---
**Version**: 1.0.0 (Step 8 Complete)
**Date**: 2024-01-01
**Security**: Localhost-only, no external network access