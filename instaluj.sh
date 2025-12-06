#!/bin/bash

# Installation script for Pisak application
# This script clones the repository, installs dependencies, and creates a desktop icon

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/Julia-M-B/pisak2.0.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/pisak}"
APP_NAME="Pisak Speller"
DESKTOP_FILE_NAME="pisak-speller.desktop"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Pisak Installation Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Error: This script is designed for Linux systems.${NC}"
    exit 1
fi

# Check for required commands
echo -e "${YELLOW}Checking prerequisites...${NC}"
for cmd in git python3 pip3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed. Please install it first.${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ Prerequisites found${NC}"
echo ""

# Install system dependencies for PySide6 on Linux
echo -e "${YELLOW}Installing system dependencies for PySide6...${NC}"
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y \
        python3-dev \
        python3-pip \
        python3-venv \
        libxcb-xinerama0 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-sync1 \
        libxcb-xfixes0 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libxkbcommon-dev \
        libxcb1-dev \
        libx11-xcb-dev \
        libxcb-glx0 \
        libxcb-util1 \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libfontconfig1 \
        libfreetype6 \
        libxrender1 \
        libxext6
elif command -v dnf &> /dev/null; then
    # Fedora/RHEL/CentOS
    sudo dnf install -y \
        python3-devel \
        python3-pip \
        libxcb \
        libxkbcommon \
        libxkbcommon-x11 \
        libxkbcommon-devel \
        libxcb-devel \
        libX11-xcb \
        mesa-libGL \
        glib2 \
        fontconfig \
        freetype \
        libXrender \
        libXext
else
    echo -e "${YELLOW}Warning: Could not detect package manager. Skipping system dependencies.${NC}"
    echo -e "${YELLOW}You may need to install PySide6 system dependencies manually.${NC}"
fi
echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory $INSTALL_DIR already exists. Updating...${NC}"
    cd "$INSTALL_DIR"
    if [ -d ".git" ]; then
        git pull
    else
        echo -e "${RED}Error: $INSTALL_DIR exists but is not a git repository.${NC}"
        echo -e "${YELLOW}Please remove it or specify a different INSTALL_DIR.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Cloning repository from $GITHUB_REPO_URL...${NC}"
    git clone "$GITHUB_REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Navigate to pisak2.0 directory
if [ -d "pisak2.0" ]; then
    cd pisak2.0
else
    echo -e "${YELLOW}Warning: pisak2.0 directory not found. Using current directory.${NC}"
fi

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
else
    python3 -m venv venv
fi
echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

# Activate virtual environment and install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    echo -e "${RED}Error: requirements.txt not found!${NC}"
    exit 1
fi
echo ""

# Get absolute path to run.py
SCRIPT_DIR=$(pwd)
RUN_PATH="$SCRIPT_DIR/run.py"

# Verify test_speller.py exists
if [ ! -f "$RUN_PATH" ]; then
    echo -e "${RED}Error: run.py not found at $RUN_PATH${NC}"
    exit 1
fi

# Create desktop icon
echo -e "${YELLOW}Creating desktop icon...${NC}"

# Create applications directory if it doesn't exist
mkdir -p "$HOME/.local/share/applications"

# Create .desktop file
DESKTOP_FILE="$HOME/.local/share/applications/$DESKTOP_FILE_NAME"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Launch Pisak Speller Application
Exec=$SCRIPT_DIR/venv/bin/python "$RUN__PATH"
Icon="$INSTALL_DIR/pisak2.0/pisak/config_files/icons/pisak_logo.png"
Terminal=false
Categories=Utility;Application;
StartupNotify=true
EOF

# Make desktop file executable
chmod +x "$DESKTOP_FILE"

echo -e "${GREEN}✓ Desktop icon created at $DESKTOP_FILE${NC}"
echo ""

# Update desktop database (for some desktop environments)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Installation directory: ${GREEN}$INSTALL_DIR${NC}"
echo -e "Desktop icon: ${GREEN}$DESKTOP_FILE${NC}"
echo ""
echo -e "${YELLOW}To run the application:${NC}"
echo -e "  1. Look for '$APP_NAME' in your application menu"
echo -e "  2. Or run: $SCRIPT_DIR/venv/bin/python \"$RUN__PATH\""
echo ""
