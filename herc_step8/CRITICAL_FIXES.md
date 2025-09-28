# Critical Fixes Required for Mainframe Automation System

## Priority 1 - Blocking Issues (Must Fix)

### 1. Fix Bridge API Module Name
**File**: `/home/jim/herc/demo.sh`
**Line**: 84
**Current**:
```bash
nohup python -m tn3270_bridge.api > "$HERC_HOME/logs/bridge.log" 2>&1 &
```
**Fixed**:
```bash
nohup python -m tn3270_bridge.api_enhanced > "$HERC_HOME/logs/bridge.log" 2>&1 &
```

### 2. Create Missing IPL Script
**File**: `/home/jim/herc/scripts/auto_ipl.expect`
**Content**:
```expect
#!/usr/bin/expect
set timeout 30
spawn nc 127.0.0.1 3270
expect -re ".*"
send "\x00\x00\x00\x00"
expect -re ".*"
close
spawn hercules -d -f /home/jim/herc/mvs38j/mvs-tk5/conf/tk5.cnf
expect "HHCCP002I"
send "ipl 00c\r"
expect "IEA101A"
send "r 0,clpa\r"
expect "IEA101A"
send "r 0,cont\r"
expect "IEA517I"
send "detach"
exit 0
```

### 3. Add MVS Boot Wait
**File**: `/home/jim/herc/demo.sh`
**After line 63, add**:
```bash
# Wait for MVS to be ready
wait_for_mvs() {
    echo "Waiting for MVS to boot completely..."
    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if nc -z 127.0.0.1 3270 2>/dev/null; then
            # Try to get a response
            if echo -e '\xff\xfd\x18' | nc -w 1 127.0.0.1 3270 2>/dev/null | xxd | grep -q "00"; then
                echo -e "${GREEN}✓${NC} MVS is responsive"
                return 0
            fi
        fi
        sleep 2
        attempt=$((attempt + 1))
        echo -n "."
    done

    echo -e "${RED}✗${NC} MVS failed to become ready"
    return 1
}

# Call after starting Hercules
wait_for_mvs || exit 1
```

### 4. Fix Import Paths
**File**: `/home/jim/herc/ai/agent_controller.py`
**Lines**: 14-19
**Current**:
```python
sys.path.insert(0, str(Path(__file__).parent.parent))
from ai.llm_cli import ClaudeCLI, ClaudeStreamWrapper
from ai.tn3270_client import TN3270Bridge, FlowRunner
```
**Fixed**:
```python
# Remove sys.path manipulation
from .llm_cli import ClaudeCLI, ClaudeStreamWrapper
from .tn3270_client import TN3270Bridge, FlowRunner
```

### 5. Implement LLM Mock Mode
**File**: `/home/jim/herc/ai/llm_cli.py`
**After line 48, add**:
```python
def _mock_invoke(self, prompt: str) -> str:
    """Mock LLM responses for testing"""
    responses = {
        "connect": "Connecting to mainframe...",
        "login": "Logging in with TSO credentials",
        "screen": "Reading screen content",
        "logout": "Logging out from TSO"
    }

    for keyword, response in responses.items():
        if keyword in prompt.lower():
            return response

    return "Mock response: Command acknowledged"
```

## Priority 2 - Reliability Issues

### 6. Add Process Cleanup
**File**: `/home/jim/herc/demo.sh`
**Add cleanup function**:
```bash
cleanup() {
    echo -e "${YELLOW}Cleaning up processes...${NC}"

    # Kill bridge
    pkill -f "tn3270_bridge" 2>/dev/null || true

    # Kill agent
    pkill -f "run_agent.py" 2>/dev/null || true

    # Kill Hercules (give it time to shutdown)
    if pgrep hercules > /dev/null; then
        pkill hercules
        sleep 5
        pkill -9 hercules 2>/dev/null || true
    fi

    # Kill any orphaned s3270
    pkill s3270 2>/dev/null || true

    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Set trap for cleanup
trap cleanup EXIT ERR
```

### 7. Add Command Queue Locking
**File**: `/home/jim/herc/ai/agent_controller.py`
**In CommandQueue.push method, add**:
```python
import fcntl

def push(self, command: Dict[str, Any]) -> Path:
    """Add command to queue with file locking"""
    self.sequence += 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cmd_{timestamp}_{self.sequence:04d}.json"
    filepath = self.queue_dir / filename

    command["timestamp"] = timestamp
    command["sequence"] = self.sequence

    # Write with exclusive lock
    with open(filepath, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(command, f, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    self.logger.debug(f"Queued command: {filename}")
    return filepath
```

## Priority 3 - Enhancement Issues

### 8. Add Health Check Retry
**File**: `/home/jim/herc/demo.sh`
**Line 93, enhance health check**:
```bash
# Verify API is responding with retries
for i in {1..10}; do
    if curl -s http://127.0.0.1:8080/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} TN3270 Bridge API started"
        break
    elif [ $i -eq 10 ]; then
        echo -e "${RED}✗${NC} Bridge API failed to start"
        echo "Check logs at: $HERC_HOME/logs/bridge.log"
        tail -20 "$HERC_HOME/logs/bridge.log"
        exit 1
    else
        echo "Waiting for API... attempt $i/10"
        sleep 2
    fi
done
```

### 9. Fix Virtual Environment Activation
**File**: `/home/jim/herc/demo.sh`
**Lines 78-80, add error checking**:
```bash
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate || {
        echo -e "${RED}✗${NC} Failed to activate virtual environment"
        echo "Creating new virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    }
else
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi
```

## Testing After Fixes

Run these tests after applying fixes:

```bash
# 1. Test Hercules startup
cd /home/jim/herc
./stop.sh  # Clean state
./demo.sh dry-run

# 2. Test Bridge API
curl http://127.0.0.1:8080/healthz

# 3. Test connection
curl -X POST http://127.0.0.1:8080/connect \
  -H "Content-Type: application/json" \
  -d '{"host": "127.0.0.1:3270"}'

# 4. Test agent
cd /home/jim/herc/ai
python3 run_agent.py --batch --task "test_connection" --dry-run

# 5. Full integration test
cd /home/jim/herc
./demo.sh batch "login_logout"
```

## Verification Checklist

After fixes, verify:
- [ ] Hercules starts and MVS boots automatically
- [ ] Bridge API responds on /healthz endpoint
- [ ] Agent can connect via command queue
- [ ] YAML flows execute without errors
- [ ] Logs show proper JSONL format with redaction
- [ ] Clean shutdown removes all processes
- [ ] No orphaned s3270 processes after shutdown
- [ ] Recovery works after keyboard lock
- [ ] Claude Code controller can send commands
- [ ] Metrics are collected and accessible