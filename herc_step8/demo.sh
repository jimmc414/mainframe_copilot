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

# Base directory
HERC_HOME="${HOME}/herc"
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

start_hercules() {
    echo -e "${YELLOW}Starting Hercules mainframe emulator...${NC}"

    # Check if already running
    if pgrep hercules > /dev/null; then
        echo -e "${GREEN}✓${NC} Hercules already running"
    else
        # Start Hercules in background
        cd "$HERC_HOME/mvs38j/mvs-tk5"
        nohup hercules -d -f conf/tk5.cnf > "$HERC_HOME/logs/hercules.log" 2>&1 &

        echo "Waiting for Hercules to initialize..."
        sleep 10

        # Automated IPL
        if [ -f "$HERC_HOME/scripts/auto_ipl.expect" ]; then
            expect "$HERC_HOME/scripts/auto_ipl.expect" > /dev/null 2>&1 || true
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

    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
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