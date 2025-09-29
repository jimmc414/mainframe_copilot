#!/bin/bash
# Mainframe Automation Demo Script
# One-command startup for demo environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect base directory - support both repo structure and runtime structure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the repository structure
if [ -d "${SCRIPT_DIR}/herc_step8" ]; then
    echo "Detected repository structure, using herc_step8 as base"
    HERC_HOME="${SCRIPT_DIR}/herc_step8"
elif [ -d "${HOME}/herc" ]; then
    echo "Using existing runtime directory: ~/herc"
    HERC_HOME="${HOME}/herc"
else
    echo "Creating runtime directory: ~/herc"
    # Setup runtime directory from repository
    if [ -d "${SCRIPT_DIR}/herc_step8" ]; then
        cp -r "${SCRIPT_DIR}/herc_step8" "${HOME}/herc"
    elif [ -d "${SCRIPT_DIR}/ai" ] && [ -d "${SCRIPT_DIR}/bridge" ]; then
        # We're already in a proper structure
        HERC_HOME="${SCRIPT_DIR}"
    else
        echo -e "${RED}Error: Cannot find required directories (ai, bridge, etc.)${NC}"
        echo "Please ensure you're running from the cloned repository."
        exit 1
    fi
    HERC_HOME="${HOME}/herc"
fi

cd "$HERC_HOME"

# Cleanup function for graceful shutdown
cleanup() {
    echo -e "${YELLOW}Cleaning up processes...${NC}"
    pkill -f "tn3270_bridge" 2>/dev/null || true
    pkill -f "run_agent.py" 2>/dev/null || true
    pkill s3270 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Set trap for cleanup on exit or error
trap cleanup EXIT ERR

# Parse arguments
MODE="${1:-batch}"  # Default to batch mode
GOAL="${2:-login_logout}"  # Default scenario

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}   Mainframe Automation Demo System${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

check_service() {
    local service=$1
    local port=$2
    if nc -z 127.0.0.1 "$port" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        return 0
    else
        echo -e "${YELLOW}○${NC} $service not running on port $port"
        return 1
    fi
}

check_mvs_files() {
    echo -e "${YELLOW}Checking for MVS files...${NC}"

    if [ ! -d "$HERC_HOME/mvs38j/mvs-tk5" ]; then
        echo -e "${RED}✗${NC} MVS TK5 not found at $HERC_HOME/mvs38j/mvs-tk5"
        echo
        echo "MVS 3.8J system files are required but not included in the repository."
        echo "The files are 1.1GB and must be downloaded separately."
        echo
        echo "To download MVS TK5, run:"
        echo "  /mnt/c/python/mainframe_copilot/scripts/download_mvs.sh"
        echo
        echo "Or download manually from:"
        echo "  http://wotho.ethz.ch/tk4-/tk4-_v1.00_current.zip"
        echo "And extract to: $HERC_HOME/mvs38j/"
        echo
        exit 1
    fi

    # Check for required files
    if [ ! -f "$HERC_HOME/mvs38j/mvs-tk5/conf/tk5.cnf" ]; then
        echo -e "${RED}✗${NC} MVS configuration file not found"
        echo "MVS TK5 installation appears incomplete."
        echo "Please run: /mnt/c/python/mainframe_copilot/scripts/download_mvs.sh"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} MVS files found"
}

start_hercules() {
    echo -e "${YELLOW}Starting Hercules mainframe emulator...${NC}"

    # Check MVS files first
    check_mvs_files

    # Check if already running
    if pgrep hercules > /dev/null; then
        echo -e "${GREEN}✓${NC} Hercules already running"
    else
        # Start Hercules in tmux session
        cd "$HERC_HOME/mvs38j/mvs-tk5"

        # Check if tmux is available
        if ! command -v tmux > /dev/null; then
            echo -e "${RED}✗${NC} tmux not found. Please install tmux: sudo apt install tmux"
            exit 1
        fi

        # Start Hercules in detached tmux session
        tmux new-session -d -s hercules "cd $HERC_HOME/mvs38j/mvs-tk5 && hercules -f conf/tk5.cnf"

        echo "Waiting for Hercules to initialize..."
        sleep 10

        # Automated IPL using tmux
        if [ -f "$HERC_HOME/scripts/auto_ipl.expect" ]; then
            # Send IPL commands directly to tmux session
            tmux send-keys -t hercules "ipl 0390" Enter
            sleep 10
            # Wait for first prompt and reply
            tmux send-keys -t hercules "/r 0,clpa" Enter
            sleep 5
            # Wait for second prompt and reply
            tmux send-keys -t hercules "/r 0,cont" Enter
        fi

        echo -e "${GREEN}✓${NC} Hercules started"

        # Wait for MVS to fully boot
        echo "Waiting for MVS to become ready..."
        local attempts=0
        while [ $attempts -lt 30 ]; do
            if nc -z 127.0.0.1 3270 2>/dev/null; then
                echo -e "${GREEN}✓${NC} MVS is responsive on port 3270"
                break
            fi
            sleep 2
            attempts=$((attempts + 1))
            echo -n "."
        done
        echo
    fi

    cd "$HERC_HOME"
}

start_bridge() {
    echo -e "${YELLOW}Starting TN3270 Bridge API...${NC}"

    # Check if already running
    if check_service "TN3270 Bridge" 8080; then
        return 0
    fi

    # Start bridge
    cd "$HERC_HOME/bridge"

    # Check for virtual environment and create if needed
    if [ ! -f "venv/bin/activate" ]; then
        echo "Creating virtual environment for bridge..."
        python3 -m venv venv
        source venv/bin/activate
        echo "Installing bridge dependencies..."
        pip install --quiet fastapi uvicorn[standard] pyyaml psutil requests
    else
        source venv/bin/activate
        # Ensure all dependencies are installed
        pip install --quiet --upgrade fastapi uvicorn[standard] pyyaml psutil requests
    fi

    # Always use enhanced API for health endpoints
    nohup python -m tn3270_bridge.api_enhanced > "$HERC_HOME/logs/bridge.log" 2>&1 &

    echo "Waiting for API to start..."
    sleep 5

    # Verify API is responding
    if curl -s http://127.0.0.1:8080/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} TN3270 Bridge API started"
    else
        echo -e "${RED}✗${NC} Bridge API failed to start"
        echo "Check logs at: $HERC_HOME/logs/bridge.log"
        exit 1
    fi

    cd "$HERC_HOME"
}

start_watchdog() {
    if [ "$MODE" = "production" ]; then
        echo -e "${YELLOW}Starting watchdog monitor...${NC}"
        nohup python "$HERC_HOME/tools/watchdog.py" > "$HERC_HOME/logs/watchdog.log" 2>&1 &
        echo -e "${GREEN}✓${NC} Watchdog started"
    fi
}

start_viewer() {
    if [ "$MODE" = "ui" ]; then
        echo -e "${YELLOW}Starting status viewer...${NC}"

        # Start viewer in new terminal if possible
        if command -v gnome-terminal > /dev/null; then
            gnome-terminal -- python "$HERC_HOME/ai/viewer.py"
        elif command -v xterm > /dev/null; then
            xterm -e python "$HERC_HOME/ai/viewer.py" &
        else
            # Run in background if no terminal available
            nohup python "$HERC_HOME/ai/viewer.py" --simple > "$HERC_HOME/logs/viewer.log" 2>&1 &
        fi

        echo -e "${GREEN}✓${NC} Viewer started"
    fi
}

start_agent() {
    echo -e "${YELLOW}Starting AI Agent...${NC}"

    cd "$HERC_HOME/ai"

    # Ensure Python dependencies are installed for AI agent
    echo "Checking AI agent dependencies..."
    python3 -c "import yaml, requests" 2>/dev/null || {
        echo "Installing AI agent Python dependencies..."
        pip install --quiet pyyaml requests psutil
    }

    case "$MODE" in
        "interactive")
            echo "Starting in INTERACTIVE mode (command queue monitoring)"
            echo -e "${BLUE}Control from another terminal with:${NC}"
            echo "  python ~/herc/ai/claude_code_control.py --interactive"
            echo
            python run_agent.py --interactive
            ;;

        "batch")
            echo "Starting in BATCH mode with goal: $GOAL"
            python run_agent.py --batch --task "$GOAL"
            ;;

        "dry-run")
            echo "Starting in DRY-RUN mode (planning only)"
            python run_agent.py --batch --task "$GOAL" --dry-run
            ;;

        "ui")
            echo "Starting in UI mode with viewer"
            python run_agent.py --interactive &
            ;;

        *)
            echo -e "${RED}Unknown mode: $MODE${NC}"
            echo "Available modes: interactive, batch, dry-run, ui"
            exit 1
            ;;
    esac
}

show_status() {
    echo
    echo -e "${BLUE}=== System Status ===${NC}"
    check_service "Hercules" 3270
    check_service "TN3270 Bridge API" 8080

    # Check health endpoint
    if curl -s http://127.0.0.1:8080/healthz > /dev/null 2>&1; then
        HEALTH=$(curl -s http://127.0.0.1:8080/healthz | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Connected: {data.get('connected')}, Uptime: {data.get('uptime_seconds', 0):.0f}s\")")
        echo "  Bridge health: $HEALTH"
    fi

    echo
}

tail_logs() {
    echo -e "${BLUE}=== Tailing Logs ===${NC}"
    echo "Logs are in: $HERC_HOME/logs/"
    echo "Press Ctrl+C to stop"
    echo

    # Tail the most relevant log
    if [ -f "$HERC_HOME/logs/ai/actions_$(date +%Y%m%d).jsonl" ]; then
        tail -f "$HERC_HOME/logs/ai/actions_$(date +%Y%m%d).jsonl" | while read line; do
            # Pretty print JSONL
            echo "$line" | python3 -m json.tool 2>/dev/null || echo "$line"
        done
    else
        tail -f "$HERC_HOME/logs/bridge.log"
    fi
}

# Main execution
print_header

echo "Mode: $MODE"
echo "Goal: $GOAL"
echo "Config: $HERC_HOME/config.yaml"
echo

# Export TSO credentials (can be overridden by environment)
if [ -z "$TSO_USER" ]; then
    export TSO_USER="HERC02"
    export TSO_PASS="CUL8TR"
    echo "Using default TSO credentials: TSO_USER=$TSO_USER"
fi

# Create log directories
mkdir -p "$HERC_HOME/logs/ai/trace"
mkdir -p "$HERC_HOME/logs/archive"

# Start services
start_hercules
start_bridge
start_watchdog
start_viewer

# Show status
show_status

# Start agent or tail logs
if [ "$MODE" = "monitor" ]; then
    tail_logs
else
    start_agent

    # Show metrics if batch mode
    if [ "$MODE" = "batch" ]; then
        echo
        echo -e "${BLUE}=== Execution Complete ===${NC}"
        if [ -f "$HERC_HOME/logs/ai/metrics.json" ]; then
            python3 -c "
import json
with open('$HERC_HOME/logs/ai/metrics.json') as f:
    m = json.load(f)
    print(f\"Success Rate: {m.get('success_rate', 0):.1%}\")
    print(f\"Mean Actions: {m.get('mean_actions_per_run', 0):.1f}\")
    print(f\"Mean Latency: {m.get('mean_latency_ms', 0):.0f}ms\")
"
        fi
    fi
fi

echo
echo -e "${GREEN}Demo system ready!${NC}"
echo "To stop: ./stop.sh"