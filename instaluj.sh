#!/bin/bash

# Installation script for the experimental environment simulating AAC applications.
# This script clones the repository (or updates existing one),
# installs dependencies, and creates a desktop icon

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


GITHUB_REPO_URL="https://github.com/Julia-M-B/master_thesis_app.git"
INSTALL_DIR="$HOME/aac_experiment"
APP_NAME="AAC_app"
DESKTOP_FILE_NAME="aac_app.desktop"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation script for the experimental environment simulating AAC application${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Error: This script is meant to be run on Linux.${NC}"
    exit 1
fi

# Check for required commands
echo -e "${YELLOW}Checking whether the required tools are installed ...${NC}"
for cmd in git python3 pip3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed. Install required tools before running the script.${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ All required tools are installed.${NC}"
echo ""

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Dictionary $INSTALL_DIR is already existing. Updating the latest version of the repository ...${NC}"
    cd "$INSTALL_DIR"
    if [ -d ".git" ]; then
        git pull
    else
        echo -e "${RED}Error: $INSTALL_DIR is already existing but it is not connected to any git repository.${NC}"
        echo -e "${YELLOW}Delete existing repository before running the script.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Cloning the repository $GITHUB_REPO_URL ...${NC}"
    git clone "$GITHUB_REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Navigate to aac_experiment directory
cd
if [ -d "aac_experiment" ]; then
    cd aac_experiment
else
    echo -e "${YELLOW}Warning: The 'aac_experiment' dictionary wasn't found.${NC}"
fi

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment ...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}Found existing virtual environment.${NC}"
else
    python3 -m venv venv
fi
echo -e "${GREEN}✓ Virtual environment was successfully created.${NC}"
echo ""

# Activate virtual environment and install Python dependencies
echo -e "${YELLOW}Installing required packages ...${NC}"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ All required packages were successfully installed.${NC}"
else
    echo -e "${RED}error: The 'requirements.txt' file wasn't found!${NC}"
    exit 1
fi
echo ""

# Get absolute path to run.py
SCRIPT_DIR=$(pwd)
RUN_PATH="$SCRIPT_DIR/run.py"

# Verify if run.py exists
if [ ! -f "$RUN_PATH" ]; then
    echo -e "${RED}Error: The 'run.py' file wasn't found.${NC}"
    exit 1
fi

# Create desktop icon
echo -e "${YELLOW}Creating desktop icon ...${NC}"

# Create applications directory if it doesn't exist
mkdir -p "$HOME/.local/share/applications"

# Create .desktop file
LAUNCH_FILE="$HOME/.local/share/applications/$DESKTOP_FILE_NAME"

cat > "$LAUNCH_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Launch experimental AAC environment
Exec=$SCRIPT_DIR/venv/bin/python "$RUN_PATH"
Icon=$INSTALL_DIR/app/config_files/icons/app_logo.png
Terminal=false
Categories=Utility;Application;
StartupNotify=true
EOF

# Make desktop file executable
chmod +x "$LAUNCH_FILE"

cd
if [ -d Desktop ]; then
  cd Desktop
else
  cd Pulpit
fi

cp $LAUNCH_FILE .

echo -e "${GREEN}✓ The icon was successfully created.${NC}"
echo ""

# Update desktop database (for some desktop environments)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation finished!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Fo running the application you need to:${NC}"
echo -e "  1. Search for the  '$APP_NAME' in your available applications."
echo -e "  2. Click on the app's icon on your desktop."
echo ""
