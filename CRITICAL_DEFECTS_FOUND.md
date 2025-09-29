# Critical Defects Found in Mainframe Copilot Demo

## Executive Summary
The demo.sh script cannot run successfully due to multiple blocking issues in the startup sequence. While individual components work when started manually, the automated startup fails at multiple points.

## Critical Issues & Fixes

### 1. Hercules Startup Failure (BLOCKER)
**Problem**: Hercules terminates immediately when started with daemon flag
```bash
# Current (BROKEN):
nohup hercules -d -f conf/tk5.cnf > "$HERC_HOME/logs/hercules.log" 2>&1 &
```

**Fix Required**:
```bash
# Use tmux session instead:
tmux new-session -d -s hercules "cd $HERC_HOME/mvs38j/mvs-tk5 && hercules -f conf/tk5.cnf"
```

### 2. Wrong IPL Address (BLOCKER)
**Problem**: IPL attempts use non-existent devices (00c, 148)
```bash
# Current (BROKEN):
send "ipl 00c\r"  # Device not found
send "ipl 148\r"  # Device not found
```

**Fix Required**:
```bash
# Correct IPL address for TK5:
send "ipl 0390\r"  # This is the actual boot device
```

### 3. Missing Response to Second IPL Prompt (BLOCKER)
**Problem**: Script only responds to first IEA101A prompt, missing second
```bash
# Current (INCOMPLETE):
send "r 0,clpa\r"
# Missing second response
```

**Fix Required**:
```bash
send "/r 0,clpa\r"
sleep 5
send "/r 0,cont\r"  # Add response to second prompt
```

### 4. Missing Dependencies (BLOCKER)
**Problem**: FastAPI not installed in bridge virtual environment
```
ModuleNotFoundError: No module named 'fastapi'
```

**Fix Required** - Add to setup script:
```bash
cd ~/herc/bridge
source venv/bin/activate
pip install fastapi uvicorn[standard]
```

### 5. API Version Confusion
**Problem**: Two API versions with different bugs
- `api.py` - Works but limited features
- `api_enhanced.py` - Has healthz endpoint but AttributeError bug

**Fix Required**: Fix api_enhanced.py line causing error or use api.py consistently

## Working Configuration Found

After manual intervention, the following sequence works:

1. Start Hercules in tmux:
```bash
tmux new-session -d -s hercules "cd ~/herc/mvs38j/mvs-tk5 && hercules -f conf/tk5.cnf"
```

2. Perform IPL with correct address:
```bash
tmux send-keys -t hercules "ipl 0390" Enter
sleep 10
tmux send-keys -t hercules "/r 0,clpa" Enter
sleep 5
tmux send-keys -t hercules "/r 0,cont" Enter
```

3. Start bridge with dependencies installed:
```bash
cd ~/herc/bridge
source venv/bin/activate
pip install fastapi uvicorn[standard]
./start_api.sh
```

## Immediate Action Items

1. **Update demo.sh** to use tmux instead of daemon mode
2. **Fix IPL address** in auto_ipl.expect to use 0390
3. **Add dependency installation** to setup process
4. **Fix or remove** api_enhanced.py
5. **Add proper error handling** and status checking between steps

## Testing Status

| Component | Status | Issue |
|-----------|--------|-------|
| Hercules Start | ❌ FAIL | Daemon mode causes immediate exit |
| MVS Boot | ❌ FAIL | Wrong IPL address (00c/148 vs 0390) |
| TN3270 Bridge | ❌ FAIL | Missing dependencies |
| API Connection | ❌ FAIL | Connection logic issues |
| AI Agent | ⚠️ NOT TESTED | Blocked by earlier failures |
| TSO/KICKS | ⚠️ NOT TESTED | Blocked by connection issues |

## Regression Impact

These issues completely prevent the demo from running, affecting:
- Quick Start experience
- CI/CD automation
- New user onboarding
- All automated workflows

## Recommended Priority

1. **P0**: Fix Hercules startup (blocks everything)
2. **P0**: Fix IPL address (blocks MVS boot)
3. **P0**: Install dependencies (blocks API)
4. **P1**: Fix bridge connection logic
5. **P1**: Consolidate API versions

## Manual Workaround

Users can manually start the system component by component using the commands in "Working Configuration Found" section above, but this defeats the purpose of the one-command demo startup.