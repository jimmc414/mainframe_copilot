#!/bin/bash
# Graceful shutdown script for mainframe automation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect base directory - support both repo structure and runtime structure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the repository structure
if [ -d "${SCRIPT_DIR}/herc_step8" ]; then
    HERC_HOME="${SCRIPT_DIR}/herc_step8"
elif [ -d "${HOME}/herc" ]; then
    HERC_HOME="${HOME}/herc"
elif [ -d "${SCRIPT_DIR}/ai" ] && [ -d "${SCRIPT_DIR}/bridge" ]; then
    # We're already in a proper structure
    HERC_HOME="${SCRIPT_DIR}"
else
    # Default to ~/herc
    HERC_HOME="${HOME}/herc"
fi

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}   Stopping Mainframe Automation System${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

archive_logs() {
    echo -e "${YELLOW}Archiving logs...${NC}"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_DIR="$HERC_HOME/logs/archive/$TIMESTAMP"

    mkdir -p "$ARCHIVE_DIR"

    # Copy current logs
    if [ -d "$HERC_HOME/logs/ai" ]; then
        cp -r "$HERC_HOME/logs/ai" "$ARCHIVE_DIR/" 2>/dev/null || true
    fi

    if [ -f "$HERC_HOME/logs/bridge.log" ]; then
        cp "$HERC_HOME/logs/bridge.log" "$ARCHIVE_DIR/" 2>/dev/null || true
    fi

    if [ -f "$HERC_HOME/logs/hercules.log" ]; then
        cp "$HERC_HOME/logs/hercules.log" "$ARCHIVE_DIR/" 2>/dev/null || true
    fi

    # Compress archive
    if command -v tar > /dev/null; then
        cd "$HERC_HOME/logs/archive"
        tar -czf "${TIMESTAMP}.tar.gz" "$TIMESTAMP"
        rm -rf "$TIMESTAMP"
        echo -e "${GREEN}✓${NC} Logs archived to: $HERC_HOME/logs/archive/${TIMESTAMP}.tar.gz"
    else
        echo -e "${GREEN}✓${NC} Logs archived to: $ARCHIVE_DIR"
    fi
}

stop_service() {
    local service=$1
    local pattern=$2

    echo -e "${YELLOW}Stopping $service...${NC}"

    # Get PIDs
    PIDS=$(pgrep -f "$pattern" 2>/dev/null || true)

    if [ -z "$PIDS" ]; then
        echo -e "${GREEN}✓${NC} $service not running"
    else
        # Graceful shutdown first
        for pid in $PIDS; do
            kill -TERM "$pid" 2>/dev/null || true
        done

        sleep 2

        # Force kill if still running
        PIDS=$(pgrep -f "$pattern" 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            for pid in $PIDS; do
                kill -KILL "$pid" 2>/dev/null || true
            done
        fi

        echo -e "${GREEN}✓${NC} $service stopped"
    fi
}

save_metrics() {
    echo -e "${YELLOW}Saving final metrics...${NC}"

    if [ -f "$HERC_HOME/logs/ai/metrics.json" ]; then
        cp "$HERC_HOME/logs/ai/metrics.json" "$HERC_HOME/logs/metrics_final.json"

        # Display summary
        python3 -c "
import json
print('\n${BLUE}=== Final Metrics ===${NC}')
with open('$HERC_HOME/logs/ai/metrics.json') as f:
    m = json.load(f)
    print(f\"Total Runs: {m.get('total_runs', 0)}\")
    print(f\"Success Rate: {m.get('success_rate', 0):.1%}\")
    print(f\"Mean Actions/Run: {m.get('mean_actions_per_run', 0):.1f}\")
    print(f\"Mean Latency: {m.get('mean_latency_ms', 0):.0f}ms\")
    print(f\"Total Errors: {m.get('total_errors', 0)}\")
" 2>/dev/null || true
    fi
}

cleanup_temp() {
    echo -e "${YELLOW}Cleaning up temporary files...${NC}"

    # Clean command queue
    rm -f "$HERC_HOME/ai/commands/cmd_*.json" 2>/dev/null || true

    # Clean old traces (keep last 100)
    if [ -d "$HERC_HOME/logs/ai/trace" ]; then
        cd "$HERC_HOME/logs/ai/trace"
        ls -t *.txt 2>/dev/null | tail -n +101 | xargs rm -f 2>/dev/null || true
    fi

    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Main execution
print_header

# Save metrics first
save_metrics

# Archive logs before stopping
archive_logs

# Stop services in reverse order
stop_service "AI Agent" "run_agent.py"
stop_service "Viewer" "viewer.py"
stop_service "Watchdog" "watchdog.py"
stop_service "TN3270 Bridge" "tn3270_bridge"

# Stop Hercules last
echo -e "${YELLOW}Stopping Hercules...${NC}"

# Try graceful shutdown first
if command -v hercules > /dev/null; then
    # Send quit command to console if possible
    echo "quit" | nc 127.0.0.1 3270 2>/dev/null || true
    sleep 2
fi

# Force stop if needed
stop_service "Hercules" "hercules"

# Cleanup
cleanup_temp

echo
echo -e "${GREEN}=== System Stopped Successfully ===${NC}"
echo "Logs archived to: $HERC_HOME/logs/archive/"
echo "To restart: ./demo.sh"