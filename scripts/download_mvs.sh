#!/bin/bash
# MVS 3.8J TK5 Download Script
# Downloads and sets up MVS TK5 for the mainframe automation system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MVS_DIR="${HOME}/herc/mvs38j"
TK5_URL="http://wotho.ethz.ch/tk4-/tk4-_v1.00_current.zip"
TK5_BACKUP_URL="https://github.com/MVS38J/tk4/releases/download/v1.0/tk4-_v1.00_current.zip"
TK5_SIZE_MB=500  # Approximate size in MB

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}   MVS 3.8J TK5 Download and Setup${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

check_space() {
    echo -e "${YELLOW}Checking disk space...${NC}"

    # Get available space in MB
    AVAILABLE_MB=$(df -BM "$HOME" | awk 'NR==2 {print $4}' | sed 's/M//')
    REQUIRED_MB=$((TK5_SIZE_MB * 3))  # Need space for download + extraction

    if [ "$AVAILABLE_MB" -lt "$REQUIRED_MB" ]; then
        echo -e "${RED}✗${NC} Insufficient disk space"
        echo "Required: ${REQUIRED_MB}MB"
        echo "Available: ${AVAILABLE_MB}MB"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Sufficient disk space available (${AVAILABLE_MB}MB)"
}

check_existing() {
    if [ -d "$MVS_DIR/mvs-tk5" ] && [ -f "$MVS_DIR/mvs-tk5/conf/tk5.cnf" ]; then
        echo -e "${YELLOW}MVS TK5 already exists at $MVS_DIR${NC}"
        read -p "Do you want to reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Keeping existing installation"
            exit 0
        fi

        echo -e "${YELLOW}Backing up existing installation...${NC}"
        mv "$MVS_DIR" "${MVS_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
}

download_tk5() {
    echo -e "${YELLOW}Downloading MVS TK5 (approximately ${TK5_SIZE_MB}MB)...${NC}"
    echo "This may take several minutes depending on your connection speed."

    mkdir -p "$MVS_DIR"
    cd "$MVS_DIR"

    # Try primary URL first
    if wget --progress=bar:force "$TK5_URL" -O mvs-tk5.zip 2>&1; then
        echo -e "${GREEN}✓${NC} Download successful from primary source"
    elif wget --progress=bar:force "$TK5_BACKUP_URL" -O mvs-tk5.zip 2>&1; then
        echo -e "${GREEN}✓${NC} Download successful from backup source"
    else
        echo -e "${RED}✗${NC} Failed to download MVS TK5"
        echo "Please download manually from:"
        echo "  $TK5_URL"
        echo "And place it as: $MVS_DIR/mvs-tk5.zip"
        exit 1
    fi
}

extract_tk5() {
    echo -e "${YELLOW}Extracting MVS TK5...${NC}"

    cd "$MVS_DIR"

    if [ ! -f "mvs-tk5.zip" ]; then
        echo -e "${RED}✗${NC} mvs-tk5.zip not found"
        exit 1
    fi

    # Check file size
    FILE_SIZE=$(stat -c%s "mvs-tk5.zip" 2>/dev/null || stat -f%z "mvs-tk5.zip" 2>/dev/null)
    FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))

    if [ "$FILE_SIZE_MB" -lt 100 ]; then
        echo -e "${RED}✗${NC} Downloaded file seems too small (${FILE_SIZE_MB}MB)"
        echo "Expected approximately ${TK5_SIZE_MB}MB"
        exit 1
    fi

    echo "Extracting ${FILE_SIZE_MB}MB archive..."
    unzip -q mvs-tk5.zip || {
        echo -e "${RED}✗${NC} Extraction failed"
        echo "The archive may be corrupted. Please try downloading again."
        exit 1
    }

    # Find the extracted directory (might be tk4- or similar)
    TK5_EXTRACTED=$(find . -maxdepth 1 -type d -name "tk*" | head -1)

    if [ -n "$TK5_EXTRACTED" ] && [ "$TK5_EXTRACTED" != "./mvs-tk5" ]; then
        echo "Renaming $TK5_EXTRACTED to mvs-tk5"
        mv "$TK5_EXTRACTED" "mvs-tk5"
    fi

    if [ ! -d "mvs-tk5" ]; then
        echo -e "${RED}✗${NC} mvs-tk5 directory not found after extraction"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Extraction complete"
}

setup_permissions() {
    echo -e "${YELLOW}Setting up permissions...${NC}"

    cd "$MVS_DIR/mvs-tk5"

    # Make scripts executable
    chmod +x mvs start_herc *.sh 2>/dev/null || true

    # Ensure DASD files are writable
    chmod 644 dasd/*.* 2>/dev/null || true

    echo -e "${GREEN}✓${NC} Permissions configured"
}

create_symlinks() {
    echo -e "${YELLOW}Creating convenience symlinks...${NC}"

    # Create symlink in home directory for easy access
    if [ ! -L "$HOME/mvs38j" ]; then
        ln -s "$MVS_DIR" "$HOME/mvs38j" 2>/dev/null || true
    fi

    echo -e "${GREEN}✓${NC} Symlinks created"
}

verify_installation() {
    echo -e "${YELLOW}Verifying installation...${NC}"

    REQUIRED_FILES=(
        "$MVS_DIR/mvs-tk5/conf/tk5.cnf"
        "$MVS_DIR/mvs-tk5/dasd/mvsres.3350"
        "$MVS_DIR/mvs-tk5/dasd/mvs000.3350"
    )

    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}✗${NC} Missing required file: $file"
            exit 1
        fi
    done

    # Check total size
    TOTAL_SIZE=$(du -sh "$MVS_DIR/mvs-tk5" | cut -f1)
    echo -e "${GREEN}✓${NC} Installation verified (${TOTAL_SIZE})"
}

print_next_steps() {
    echo
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}   MVS TK5 Installation Complete!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo
    echo "MVS 3.8J TK5 has been installed to:"
    echo "  $MVS_DIR/mvs-tk5"
    echo
    echo "Next steps:"
    echo "1. Return to the mainframe_copilot directory:"
    echo "   cd /mnt/c/python/mainframe_copilot"
    echo
    echo "2. Run the setup script:"
    echo "   ./scripts/setup.sh"
    echo
    echo "3. Start the system:"
    echo "   cd ~/herc"
    echo "   ./demo.sh"
    echo
}

# Main execution
print_header
check_space
check_existing
download_tk5
extract_tk5
setup_permissions
create_symlinks
verify_installation
print_next_steps