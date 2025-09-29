#!/bin/bash
# Setup dependencies for Mainframe Copilot components
# This script ensures all required Python packages are installed

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up dependencies for Mainframe Copilot...${NC}"

# Base directory
HERC_HOME="${HOME}/herc"

# Function to setup Python dependencies for a component
setup_python_deps() {
    local component=$1
    local path=$2
    shift 2
    local packages=("$@")

    echo -e "${YELLOW}Setting up $component dependencies...${NC}"

    # Navigate to component directory
    cd "$path"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment for $component..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip --quiet

    # Install packages
    for package in "${packages[@]}"; do
        echo "  Installing $package..."
        pip install "$package" --quiet
    done

    deactivate
    echo -e "${GREEN}✓${NC} $component dependencies installed"
}

# 1. Setup TN3270 Bridge dependencies
if [ -d "$HERC_HOME/bridge" ]; then
    setup_python_deps "TN3270 Bridge" "$HERC_HOME/bridge" \
        "fastapi" \
        "uvicorn[standard]" \
        "pyyaml" \
        "psutil"
else
    echo -e "${YELLOW}Warning: Bridge directory not found at $HERC_HOME/bridge${NC}"
fi

# 2. Setup AI Agent dependencies
if [ -d "$HERC_HOME/ai" ]; then
    setup_python_deps "AI Agent" "$HERC_HOME/ai" \
        "requests" \
        "pyyaml" \
        "python-dotenv" \
        "anthropic" \
        "openai"
else
    echo -e "${YELLOW}Warning: AI directory not found at $HERC_HOME/ai${NC}"
fi

# 3. Check for system dependencies
echo -e "${YELLOW}Checking system dependencies...${NC}"

missing_deps=()

# Check for tmux
if ! command -v tmux > /dev/null; then
    missing_deps+=("tmux")
fi

# Check for expect
if ! command -v expect > /dev/null; then
    missing_deps+=("expect")
fi

# Check for s3270
if ! command -v s3270 > /dev/null; then
    missing_deps+=("s3270")
fi

# Check for netcat
if ! command -v nc > /dev/null; then
    missing_deps+=("netcat")
fi

# Check for jq
if ! command -v jq > /dev/null; then
    missing_deps+=("jq")
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${RED}Missing system dependencies:${NC}"
    for dep in "${missing_deps[@]}"; do
        echo "  - $dep"
    done
    echo
    echo "Install with:"
    echo "  sudo apt update && sudo apt install -y ${missing_deps[*]}"
    echo
else
    echo -e "${GREEN}✓${NC} All system dependencies installed"
fi

echo
echo -e "${GREEN}Dependency setup complete!${NC}"
echo
echo "Note: If this is a fresh installation, you may also need to:"
echo "  1. Download MVS TK5 files (if not present)"
echo "  2. Configure TSO credentials in environment"
echo "  3. Review config.yaml settings"
echo
echo "To start the system, run: ./demo.sh"