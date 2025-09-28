# Mainframe Automation System - Operational Runbook

## 1. Overview

### Purpose
This runbook provides comprehensive operational guidance for the Mainframe Automation System, a production-ready demonstration environment for AI-driven TN3270 interaction with MVS 3.8J running on Hercules.

### Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude Code /     │────▶│   Command Queue  │────▶│   AI Agent      │
│   Human Operator    │     │  (File-based IPC)│     │  Controller     │
└─────────────────────┘     └──────────────────┘     └────────┬────────┘
                                                               │
                            ┌──────────────────┐              │
                            │    Watchdog      │              │
                            │    Monitor       │──────────────┤
                            └──────────────────┘              │
                                                               ▼
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   TN3270 Bridge     │◀────│   JSON API       │────▶│   Observability │
│   (s3270 process)   │     │  (FastAPI/HTTP)  │     │   (JSONL logs)  │
└──────────┬──────────┘     └──────────────────┘     └─────────────────┘
           │
           │ TN3270 Protocol
           ▼
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Hercules          │────▶│   MVS 3.8J       │────▶│   KICKS/TSO     │
│   Emulator          │     │   Operating Sys  │     │   Applications  │
└─────────────────────┘     └──────────────────┘     └─────────────────┘
```

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Hercules | IBM mainframe emulator | `~/herc/mvs38j/mvs-tk5/` |
| MVS 3.8J | IBM operating system (1981) | Running in Hercules |
| KICKS | CICS-compatible transaction processor | Installed in MVS |
| TN3270 Bridge | JSON API over s3270 | `~/herc/bridge/` |
| AI Agent | LLM-driven automation | `~/herc/ai/` |
| Flows | YAML automation sequences | `~/herc/flows/` |
| Watchdog | Service health monitor | `~/herc/tools/` |

## 2. Prerequisites

### System Requirements

**WSL2 Ubuntu:**
```bash
# Check version
lsb_release -a
# Required: Ubuntu 20.04+ in WSL2

# Check resources
free -h    # Minimum 4GB RAM
df -h      # Minimum 10GB disk
nproc      # Minimum 2 CPUs
```

**Required Packages:**
```bash
sudo apt update
sudo apt install -y \
    build-essential cmake libsdl2-dev \
    python3 python3-pip python3-venv \
    x3270 s3270 c3270 pr3287 \
    netcat expect tmux jq \
    curl wget git
```

**Claude CLI (Optional):**
```bash
# Install Claude CLI if available
pip install claude-cli
claude login  # Authenticate

# Or use mock mode (no CLI required)
```

**Ports (localhost only):**
- 3270: Hercules console/TN3270
- 8080: TN3270 Bridge API

### Directory Structure

```
~/herc/
├── config.yaml              # Central configuration
├── demo.sh                  # Start script
├── stop.sh                  # Stop script
├── demo.tmux               # tmux layout
│
├── mvs38j/mvs-tk5/         # Hercules & MVS
│   └── conf/tk5.cnf        # Hercules config
│
├── bridge/                 # TN3270 Bridge
│   ├── tn3270_bridge/      # API modules
│   └── venv/               # Python virtualenv
│
├── ai/                     # AI Agent
│   ├── agent_controller.py # Main agent
│   ├── observability.py    # Logging
│   ├── commands/           # Command queue
│   └── prompts/            # LLM prompts
│
├── flows/                  # Automation flows
│   ├── login.yaml
│   ├── kicks_start.yaml
│   └── end_to_end.yaml
│
├── tools/                  # Utilities
│   ├── watchdog.py         # Health monitor
│   └── replay_harness.py   # Regression testing
│
├── logs/                   # All logs
│   ├── ai/                 # Agent logs (JSONL)
│   ├── archive/            # Archived logs
│   └── trace/              # Screen traces
│
├── goldens/                # Golden screens
└── docs/                   # Documentation
    ├── RUNBOOK.md          # This file
    ├── POLICY_ADDENDUM.md  # Security policies
    └── POLICY_MAP.md       # Policy enforcement
```

## 3. Security & Scope

### Localhost-Only Design
- **ALL services bind to 127.0.0.1 only** - no external network exposure
- Enforced in: `api_enhanced.py`, `config.yaml`, `watchdog.py`
- Verification: `netstat -tlnp | grep -E "3270|8080"`

### Credential Handling
- Default demo credentials: HERC02/CUL8TR
- Environment variables for overrides
- Automatic redaction in logs: password, secret, key, token
- Never commit credentials to version control

### Action Allowlist
Only these s3270 actions are permitted:
```
Wait(3270), Wait(InputField), Ascii(), ReadBuffer(Ascii)
Query(...), MoveCursor(r,c), String("text")
Enter, PF(1-12), PA(1-3), Clear
Connect(127.0.0.1:3270), Disconnect()
```

### Policy Documents
- **POLICY_ADDENDUM.md**: Complete security and operational policies
- **POLICY_MAP.md**: Maps policies to code enforcement points

## 4. Installation & Setup

### First-Time Setup

```bash
# 1. Clone or extract the system
cd ~
tar -xzf herc_automation.tar.gz  # If from archive

# 2. Build Hercules (if needed)
cd ~/herc
./build_hercules.sh

# 3. Setup Python environment
cd ~/herc/bridge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Verify configuration
cd ~/herc
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 5. Create required directories
mkdir -p logs/ai/trace logs/archive goldens

# 6. Set permissions
chmod +x demo.sh stop.sh demo.tmux
chmod +x tools/*.py ai/*.py
```

### Configuration File

Edit `~/herc/config.yaml` to customize:
- Service ports (keep 127.0.0.1!)
- Logging levels
- Operational limits
- Execution modes
- LLM settings

### Systemd Services (Optional)

```bash
# Create user service directory
mkdir -p ~/.config/systemd/user

# Copy service files (if provided)
cp systemd/*.service ~/.config/systemd/user/

# Enable services
systemctl --user daemon-reload
systemctl --user enable tn3270-bridge.service
systemctl --user enable herc-watchdog.service

# Start services
systemctl --user start tn3270-bridge.service
```

## 5. Starting the System

### Quick Start

```bash
cd ~/herc

# Default: Batch mode with login/logout scenario
./demo.sh

# Interactive mode (Claude Code control)
./demo.sh interactive

# Dry-run mode (planning only)
./demo.sh dry-run

# UI mode with viewer
./demo.sh ui

# Monitor mode (logs only)
./demo.sh monitor
```

### Execution Modes

| Mode | Description | Usage |
|------|-------------|-------|
| **batch** | Run single goal and exit | `./demo.sh batch login_logout` |
| **interactive** | Command queue monitoring | `./demo.sh interactive` |
| **dry-run** | Plan without execution | `./demo.sh dry-run` |
| **confirm** | Require user approval | Set in config.yaml |
| **ui** | With status viewer | `./demo.sh ui` |

### Example Goals

```bash
# Login and logout
./demo.sh batch login_logout

# Navigate to KICKS
./demo.sh batch kicks_menu

# Run KICKS demo transaction
./demo.sh batch kicks_demo

# Custom goal
./demo.sh batch "Login and check dataset list"
```

### Using tmux Layout

```bash
# Start with tmux layout (4 panes)
tmux source-file demo.tmux

# Or manually:
tmux new -s mainframe
# Then run demo.sh in one pane
```

## 6. Stopping & Cleanup

### Graceful Shutdown

```bash
# Stop all services and archive logs
./stop.sh

# This will:
# 1. Save final metrics
# 2. Archive logs to ~/herc/logs/archive/<timestamp>/
# 3. Stop services in reverse order
# 4. Clean temporary files
```

### Manual Cleanup

```bash
# Stop individual services
pkill -f run_agent.py
pkill -f tn3270_bridge
pkill hercules

# Clean command queue
rm -f ~/herc/ai/commands/cmd_*.json

# Clean old traces
find ~/herc/logs/ai/trace -name "*.txt" -mtime +7 -delete
```

### Session Reset

```bash
# Reset TN3270 session without restart
curl -X POST http://127.0.0.1:8080/reset_session
```

## 7. Operations

### Health Checks

```bash
# Check system health
curl http://127.0.0.1:8080/healthz | jq

# Response:
{
  "status": "healthy",
  "connected": true,
  "hercules_pid": 12345,
  "s3270_pid": 12346,
  "uptime_seconds": 3600,
  "last_action": "screen",
  "action_count": 150
}
```

### Watchdog Monitoring

```bash
# Test watchdog (no restarts)
python ~/herc/tools/watchdog.py --test

# Run watchdog
python ~/herc/tools/watchdog.py

# With custom config
python ~/herc/tools/watchdog.py --config watchdog.json
```

### Log Locations

| Log Type | Location | Format |
|----------|----------|--------|
| Actions | `~/herc/logs/ai/actions_YYYYMMDD.jsonl` | JSONL |
| Metrics | `~/herc/logs/ai/metrics.json` | JSON |
| Traces | `~/herc/logs/ai/trace/screen_*.txt` | Text |
| Bridge | `~/herc/logs/bridge.log` | Text |
| Hercules | `~/herc/logs/hercules.log` | Text |
| Watchdog | `~/herc/logs/watchdog/*.log` | Text |

### Viewing Logs

```bash
# Tail action logs (pretty printed)
tail -f ~/herc/logs/ai/actions_$(date +%Y%m%d).jsonl | jq

# View metrics
cat ~/herc/logs/ai/metrics.json | jq

# Search logs
grep -i error ~/herc/logs/ai/*.jsonl | jq

# View traces
ls -lt ~/herc/logs/ai/trace/ | head
```

## 8. Flows & Screen Fingerprints

### Flow DSL Reference

```yaml
name: example_flow
description: Example automation flow
steps:
  - action: connect
    host: "127.0.0.1:3270"

  - action: wait
    condition: ready
    timeout: 5000

  - action: fill
    row: 10
    col: 15
    text: "HERC02"

  - action: press
    key: Enter

  - action: assert
    contains: "READY"

recovery:
  - action: press
    key: PF3
  - action: press
    key: Clear
```

### Available Flows

| Flow | Purpose | Location |
|------|---------|----------|
| login.yaml | TSO login | `~/herc/flows/` |
| logout.yaml | TSO logout | `~/herc/flows/` |
| kicks_start.yaml | Start KICKS | `~/herc/flows/` |
| kicks_demo.yaml | KICKS demo | `~/herc/flows/` |
| end_to_end.yaml | Complete cycle | `~/herc/flows/` |

### Golden Screens

```bash
# Save golden screen
python ~/herc/tools/screen_fingerprint.py save --name logon

# Compare with golden
python ~/herc/tools/screen_fingerprint.py compare --name logon

# List goldens
ls ~/herc/goldens/*.json
```

## 9. LLM Integration (No API Keys)

### Claude CLI Mode

```bash
# Check if Claude CLI available
which claude

# If available, agent will use it
# If not, uses mock mode
```

### Mock Mode

When Claude CLI is not available:
- Uses pattern matching for common scenarios
- Falls back to predefined flows
- Still fully functional for demos

### Prompt Management

```bash
# System prompt
cat ~/herc/ai/prompts/system_prompt.txt

# Developer prompt
cat ~/herc/ai/prompts/developer_prompt.txt

# Modify prompts
vim ~/herc/ai/prompts/system_prompt.txt
```

### Model Configuration

```yaml
# In config.yaml
llm:
  provider: "claude"  # or "mock"
  model: "default"
  temperature: 0.3
  max_tokens: 4000
```

## 10. Replay & Regression

### Recording Sessions

```bash
# Sessions automatically recorded to:
~/herc/logs/ai/actions_YYYYMMDD.jsonl

# Convert to replay format
python ~/herc/tools/replay_harness.py \
  --mode record \
  --transcript logs/ai/actions_20240101.jsonl
```

### Replay Testing

```bash
# Replay transcript
python ~/herc/tools/replay_harness.py \
  --mode replay \
  --transcript logs/ai/sample_transcript.jsonl \
  --golden-dir goldens/

# Validate against goldens
python ~/herc/tools/replay_harness.py \
  --mode validate \
  --test-screen current_screen.txt \
  --golden-dir goldens/
```

### Regression Reports

```bash
# Generate report
python ~/herc/tools/replay_harness.py \
  --mode replay \
  --transcript logs/ai/sample_transcript.jsonl \
  --report regression_report.json

# View report
cat regression_report.json | jq
```

## 11. Troubleshooting

### Common Issues

#### Connection Failed
```bash
# Check Hercules
ps aux | grep hercules
ss -ltn | grep 3270

# Restart if needed
pkill hercules
cd ~/herc && ./demo.sh
```

#### Keyboard Lock
```bash
# Send recovery keys
curl -X POST http://127.0.0.1:8080/press -d '{"key": "Clear"}'

# Or reset session
curl -X POST http://127.0.0.1:8080/reset_session
```

#### Bridge Not Responding
```bash
# Check process
ps aux | grep tn3270_bridge

# Check logs
tail -f ~/herc/logs/bridge.log

# Restart
pkill -f tn3270_bridge
cd ~/herc/bridge && ./start_api.sh
```

#### Agent Stuck
```bash
# Check command queue
ls ~/herc/ai/commands/

# Clear queue
rm -f ~/herc/ai/commands/cmd_*.json

# Check status
cat ~/herc/ai/commands/status.json | jq
```

### Diagnostic Commands

```bash
# Full system check
curl http://127.0.0.1:8080/healthz | jq
python ~/herc/tools/watchdog.py --test
python ~/herc/ai/test_integration.py

# Network check (must show 127.0.0.1 only!)
netstat -tlnp | grep -E "3270|8080"

# Process check
ps aux | grep -E "hercules|s3270|python"

# Log analysis
grep ERROR ~/herc/logs/ai/*.jsonl | jq '.notes'
```

## 12. Evaluation & KPIs

### Running Evaluation

```bash
# Run standard evaluation suite
python ~/herc/tools/evaluate.py

# Custom evaluation
python ~/herc/tools/evaluate.py \
  --scenarios "login_logout,kicks_menu" \
  --runs 3
```

### Success Criteria

| Metric | Target | Threshold |
|--------|--------|-----------|
| Success Rate | ≥95% | Required |
| Actions per Run | ≤40 | Required |
| Fallbacks per Run | ≤2 | Required |
| No-Progress Loops | ≤3 | Required |
| Mean Latency | <500ms | Desired |

### Viewing Results

```bash
# View evaluation summary
cat ~/herc/logs/ai/eval_summary.json | jq

# Key metrics
jq '.overall_metrics' ~/herc/logs/ai/eval_summary.json

# Recommendations
jq '.recommendations[]' ~/herc/logs/ai/eval_summary.json
```

## 13. Customization

### Adding New Flows

```bash
# Create new flow
cat > ~/herc/flows/custom_flow.yaml << EOF
name: custom_flow
description: My custom automation
steps:
  - action: connect
    host: "127.0.0.1:3270"
  # Add steps...
EOF

# Test flow
python ~/herc/tools/flow_runner.py --flow custom_flow.yaml
```

### Extending Tool Allowlist

Edit `~/herc/ai/safety.py`:
```python
ALLOWED_ACTIONS = [
    # ... existing actions ...
    "NewAction",  # Add your action
]
```

Update `config.yaml`:
```yaml
security:
  action_allowlist:
    - "NewAction"
```

### Policy Updates

1. Edit `~/herc/docs/POLICY_ADDENDUM.md`
2. Update enforcement in code
3. Document in `~/herc/docs/POLICY_MAP.md`
4. Test with `python ~/herc/tools/validate_policies.py`

## 14. Appendices

### A. Environment Variables

```bash
# Optional overrides
export HERC_HOME=~/herc
export HERC_USER=HERC02
export HERC_PASS=CUL8TR
export HERC_DEBUG=1
export HERC_TRACE=1
```

### B. Port Summary

| Port | Service | Binding |
|------|---------|---------|
| 3270 | Hercules Console | 127.0.0.1 |
| 8080 | TN3270 Bridge API | 127.0.0.1 |

### C. Command Cheat Sheet

```bash
# Start/Stop
./demo.sh [mode]          # Start system
./stop.sh                 # Stop system

# Health
curl http://127.0.0.1:8080/healthz | jq
python tools/watchdog.py --test

# Logs
tail -f logs/ai/actions_$(date +%Y%m%d).jsonl | jq
cat logs/ai/metrics.json | jq

# Control
python ai/claude_code_control.py --interactive
python ai/run_agent.py --batch --task "goal"

# Testing
python tools/replay_harness.py --mode replay --transcript file.jsonl
python ai/test_integration.py

# Reset
curl -X POST http://127.0.0.1:8080/reset_session
rm -f ai/commands/cmd_*.json
```

### D. Glossary

| Term | Definition |
|------|------------|
| **TN3270** | Terminal protocol for IBM mainframes |
| **TSO** | Time Sharing Option - MVS interactive interface |
| **ISPF** | Interactive System Productivity Facility |
| **KICKS** | Open-source CICS-compatible transaction processor |
| **JCL** | Job Control Language |
| **PF Keys** | Program Function keys (PF1-PF12) |
| **AID Keys** | Attention Identifier keys (Enter, Clear, PA, PF) |
| **READY** | TSO prompt indicating ready for input |
| **Golden** | Reference screen for regression testing |
| **JSONL** | JSON Lines format (one JSON per line) |

## Support

For issues or questions:
1. Check logs in `~/herc/logs/`
2. Run diagnostics: `python ~/herc/ai/test_integration.py`
3. Review policies: `~/herc/docs/POLICY_ADDENDUM.md`
4. Consult this runbook

---

**Version**: 1.0.0
**Last Updated**: 2024-01-01
**Next Review**: Quarterly