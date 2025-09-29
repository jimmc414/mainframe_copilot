# Mainframe Copilot - Complete Project File Map

## Directory Structure Overview

```
/mnt/c/python/mainframe_copilot/     # Windows-accessible repository root
│
├── 📁 herc_step8/                   # Main project directory (all automation code)
│   │
│   ├── 📁 ai/                       # AI Agent Components
│   │   ├── agent_controller.py      # Main agent with command queue monitoring
│   │   ├── claude_code_control.py   # Claude Code interface controller
│   │   ├── llm_cli.py              # Claude CLI wrapper with mock mode
│   │   ├── observability.py        # JSONL logging and metrics
│   │   ├── run_agent.py            # CLI entry point for agent
│   │   ├── tn3270_client.py        # TN3270 bridge client wrapper
│   │   ├── viewer.py               # Terminal UI for monitoring
│   │   ├── test_integration.py     # Integration tests
│   │   ├── example_claude_code.py  # Usage examples
│   │   ├── 📁 commands/            # Command queue directory (runtime)
│   │   ├── 📁 prompts/             # System and developer prompts
│   │   │   ├── system_prompt.txt   # Main system prompt
│   │   │   └── developer_prompt.txt # Developer instructions
│   │   └── 📁 tools/               # Tool definitions
│   │       └── mainframe_tools.json # Tool manifest
│   │
│   ├── 📁 bridge/                  # TN3270 Bridge API
│   │   ├── requirements.txt        # Python dependencies (fastapi, uvicorn, psutil)
│   │   ├── start_api.sh           # API startup script
│   │   └── 📁 tn3270_bridge/      # Bridge module
│   │       ├── __init__.py        # Module init
│   │       ├── api.py             # Original API (legacy)
│   │       ├── api_enhanced.py    # Enhanced API with health/reset
│   │       ├── session.py         # S3270 session manager
│   │       ├── parser.py          # Screen parser
│   │       └── cli_stdio.py       # CLI interface
│   │
│   ├── 📁 flows/                   # YAML Automation Workflows
│   │   ├── login.yaml             # TSO login flow
│   │   ├── logout.yaml            # TSO logout flow
│   │   ├── kicks_start.yaml       # Start KICKS system
│   │   ├── kicks_demo.yaml        # KICKS demo transaction
│   │   ├── end_to_end.yaml        # Complete cycle test
│   │   ├── test_recovery.yaml     # Error recovery test
│   │   └── README.md              # Flow documentation
│   │
│   ├── 📁 tools/                   # Utilities and Helpers
│   │   ├── flow_runner.py         # YAML flow executor
│   │   ├── screen_fingerprint.py  # Golden screen manager
│   │   ├── watchdog.py           # Service health monitor
│   │   ├── replay_harness.py     # Regression testing
│   │   └── evaluate.py           # Evaluation suite
│   │
│   ├── 📁 scripts/                 # Setup and Automation Scripts
│   │   ├── auto_ipl.expect        # MVS IPL automation
│   │   └── README.md              # Scripts documentation
│   │
│   ├── 📁 docs/                    # Documentation
│   │   ├── RUNBOOK.md            # Complete operational guide
│   │   ├── POLICY_ADDENDUM.md    # Security policies
│   │   └── POLICY_MAP.md         # Policy enforcement mapping
│   │
│   ├── 📁 config/                  # Configuration Files
│   │   ├── tn3270-bridge.service  # Systemd service for bridge
│   │   └── herc-watchdog.service  # Systemd service for watchdog
│   │
│   ├── 📁 logs/                    # Sample Logs and Data
│   │   ├── sample_transcript.jsonl # Example session
│   │   └── eval_summary.json      # Evaluation metrics
│   │
│   ├── 📁 goldens/                 # Reference Screens
│   │   ├── logon_screen.json      # Login screen golden
│   │   └── ready_prompt.json      # Ready prompt golden
│   │
│   ├── 📄 Core Files
│   │   ├── demo.sh                # One-command startup script
│   │   ├── stop.sh                # Graceful shutdown script
│   │   ├── config.yaml            # Central configuration
│   │   ├── demo.tmux              # tmux layout configuration
│   │   ├── README.md              # Project README
│   │   ├── PACKAGE_CONTENTS.md    # Package inventory
│   │   ├── CRITICAL_FIXES.md      # First round of fixes
│   │   └── FIXES_APPLIED.md       # Fix tracking document
│   │
│   └── 📁 mvs38j/ (NOT IN GIT)    # MVS System Files (1.1GB)
│       └── mvs-tk5/               # Downloaded separately
│           ├── conf/              # Hercules configuration
│           ├── dasd/              # Disk images
│           └── hercules/          # Emulator binaries
│
├── 📁 scripts/                     # Repository-level Scripts
│   ├── download_mvs.sh           # MVS TK5 downloader
│   └── setup.sh                   # Setup automation
│
├── 📁 ai/                          # Legacy AI directory
│   └── (old files - deprecated)
│
├── 📁 config/                      # Legacy config directory
│   └── (old files - deprecated)
│
├── 📄 Root Files
│   ├── README.md                  # Main project README
│   ├── setup.py                   # Python package installer
│   ├── requirements.txt           # Python requirements
│   ├── MVS_SETUP.md              # MVS installation guide
│   ├── CODE_REVIEW_FIXES.md      # Code review response
│   ├── CRITICAL_FIXES_ROUND2.md  # Second round fixes
│   └── PROJECT_FILEMAP.md        # This file
│
└── 📁 Archives
    ├── herc_step8_complete.tar.gz # Complete package
    └── herc_step8_fixed.tar.gz    # Fixed version

```

## Runtime Directory (Created During Setup)

```
~/herc/                            # WSL2 runtime location
│
├── 📁 mvs38j/                     # MVS System (downloaded)
│   └── mvs-tk5/                   # TK5 distribution
│       ├── conf/tk5.cnf          # Main config
│       ├── dasd/*.3350           # Disk images
│       └── hercules/             # Emulator
│
├── 📁 ai/ → (symlink)             # Links to herc_step8/ai
├── 📁 bridge/ → (symlink)         # Links to herc_step8/bridge
├── 📁 flows/ → (symlink)          # Links to herc_step8/flows
├── 📁 tools/ → (symlink)          # Links to herc_step8/tools
├── 📁 scripts/ → (symlink)        # Links to herc_step8/scripts
├── 📁 docs/ → (symlink)           # Links to herc_step8/docs
│
├── 📁 logs/                       # Runtime logs (created)
│   ├── hercules.log              # Hercules emulator log
│   ├── bridge.log                # TN3270 bridge log
│   ├── watchdog.log              # Watchdog monitor log
│   ├── 📁 ai/                    # AI agent logs
│   │   ├── actions_YYYYMMDD.jsonl # Daily action log
│   │   ├── metrics.json          # Performance metrics
│   │   └── 📁 trace/             # Detailed traces
│   ├── 📁 flows/                 # Flow execution logs
│   └── 📁 archive/               # Archived logs
│
├── config.yaml → (symlink)       # Links to herc_step8/config.yaml
├── demo.sh → (symlink)           # Links to herc_step8/demo.sh
└── stop.sh → (symlink)           # Links to herc_step8/stop.sh
```

## Key File Purposes

### Core Components
- **agent_controller.py**: Main AI agent orchestrator
- **api_enhanced.py**: TN3270 bridge with health monitoring
- **flow_runner.py**: Executes YAML automation sequences
- **demo.sh**: One-command system startup

### Configuration
- **config.yaml**: Central config (ports, credentials, limits)
- **requirements.txt**: Python dependencies
- **tk5.cnf**: Hercules/MVS configuration (in mvs38j)

### Documentation
- **README.md**: Project overview and quick start
- **RUNBOOK.md**: Complete operational guide
- **MVS_SETUP.md**: MVS download and setup instructions

### Workflows
- **login.yaml**: TSO login automation
- **kicks_start.yaml**: KICKS transaction system
- **end_to_end.yaml**: Full system test

### Utilities
- **watchdog.py**: Service health monitoring
- **replay_harness.py**: Regression testing
- **download_mvs.sh**: MVS TK5 downloader

## File Access Patterns

### From Windows (via WSL2)
```
C:\python\mainframe_copilot\        # Windows path
/mnt/c/python/mainframe_copilot/    # WSL2 path
```

### From WSL2 Runtime
```
~/herc/                              # Runtime location
/home/<user>/herc/                   # Full path
```

### Python Import Paths
```python
from ai.agent_controller import MainframeAgent
from bridge.tn3270_bridge.api_enhanced import app
from tools.flow_runner import FlowRunner
```

## Critical Files for Operation

### Must Have for Startup
1. `demo.sh` - Startup script
2. `config.yaml` - Configuration
3. `bridge/tn3270_bridge/api_enhanced.py` - API server
4. `mvs38j/mvs-tk5/conf/tk5.cnf` - Hercules config
5. `mvs38j/mvs-tk5/dasd/*.3350` - MVS disk images

### Must Have for Automation
1. `ai/agent_controller.py` - Agent logic
2. `flows/*.yaml` - Automation workflows
3. `tools/flow_runner.py` - Flow executor
4. `ai/tn3270_client.py` - Bridge client

### Must Have for Claude Code
1. `ai/claude_code_control.py` - Controller
2. `ai/commands/` - Command queue directory
3. `ai/llm_cli.py` - LLM interface

## Environment Variables

### Required
- `TSO_USER` - TSO username (default: HERC02)
- `TSO_PASS` - TSO password (default: CUL8TR)

### Optional
- `HERC_HOME` - Override runtime location (default: ~/herc)
- `CLAUDE_API_KEY` - For Claude API access
- `DEBUG` - Enable debug logging

## Port Usage

- **3270**: Hercules TN3270 terminal
- **8080**: TN3270 Bridge API
- **3505**: Hercules card reader (optional)
- **8038**: Hercules HTTP server (optional)

## Log Files

### Primary Logs
- `~/herc/logs/hercules.log` - Emulator output
- `~/herc/logs/bridge.log` - API server
- `~/herc/logs/ai/actions_YYYYMMDD.jsonl` - Agent actions

### Debug Logs
- `~/herc/logs/ai/trace/` - Detailed traces
- `~/herc/logs/flows/` - Flow execution details

## Version Control

### In Git
- All code in `/mnt/c/python/mainframe_copilot/`
- Except MVS files (too large)

### Not in Git
- `~/herc/mvs38j/` - MVS system files (1.1GB)
- `~/herc/logs/` - Runtime logs
- Runtime command queue files

---

This file map shows the complete project structure and where every important file lives.