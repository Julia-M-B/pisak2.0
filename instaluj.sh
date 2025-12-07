#!/bin/bash

# Installation script for Pisak application
# This script clones the repository (or updates existing one),
# installs dependencies, and creates a desktop icon

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


GITHUB_REPO_URL="https://github.com/Julia-M-B/pisak2.0.git"
INSTALL_DIR="$HOME/pisak2.0"
APP_NAME="Pisak 2.0"
DESKTOP_FILE_NAME="pisak2.desktop"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Skrypt instalacyjny PISAKa${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Błąd: Ten skrypt stworzony jest dla systemów typu Linux.${NC}"
    exit 1
fi

# Check for required commands
echo -e "${YELLOW}Sprawdzenie, czy są zainstalowane wymagane paczki ...${NC}"
for cmd in git python3 pip3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Błąd: $cmd nie jest zainstalowany. Zainstaluj odpowiednią paczkę przed ponownym uruchomieniem skryptu.${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Wymagane paczki są zainstalowane${NC}"
echo ""

# todo: add python version checking with the possibility of installation newer version of python

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Folder $INSTALL_DIR już istnieje. Ściągam najnowszą wersję ...${NC}"
    cd "$INSTALL_DIR"
    if [ -d ".git" ]; then
        git pull
    else
        echo -e "${RED}Błąd: $INSTALL_DIR już istnieje, ale nie jest połączony z repozytorium git.${NC}"
        echo -e "${YELLOW}Usuń istniejący folder przed ponownym uruchomieniem skryptu.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Klonuję repozytorium $GITHUB_REPO_URL ...${NC}"
    git clone "$GITHUB_REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Navigate to pisak2.0 directory
cd
if [ -d "pisak2.0" ]; then
    cd pisak2.0
else
    echo -e "${YELLOW}Ostrzeżenie: folder 'pisak2.0' nie został znaleziony.${NC}"
fi

# Create virtual environment
echo -e "${YELLOW}Tworzę wirtualne środowisko ...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}Wirtualne środowisko już istnieje.${NC}"
else
    python3 -m venv venv
fi
echo -e "${GREEN}✓ Wirtualne środowisko zostało pomyślnie stworzone.${NC}"
echo ""

# Activate virtual environment and install Python dependencies
echo -e "${YELLOW}Instaluję potrzebne biblioteki ...${NC}"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Wszystkie biblioteki zostały poprawnie zainstalowane.${NC}"
else
    echo -e "${RED}Błąd: nie znaleziono pliku z wymaganymi bibliotekami!${NC}"
    exit 1
fi
echo ""

# Get absolute path to run.py
SCRIPT_DIR=$(pwd)
RUN_PATH="$SCRIPT_DIR/run.py"

# Verify test_speller.py exists
if [ ! -f "$RUN_PATH" ]; then
    echo -e "${RED}Błąd: skrypt 'run.py' nie został znaleziony.${NC}"
    exit 1
fi

# Create desktop icon
echo -e "${YELLOW}Tworzę ikonkę na pulpicie ...${NC}"

# Create applications directory if it doesn't exist
mkdir -p "$HOME/.local/share/applications"

# Create .desktop file
LAUNCH_FILE="$HOME/.local/share/applications/$DESKTOP_FILE_NAME"

cat > "$LAUNCH_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Launch Pisak 2.0 Application
Exec=$SCRIPT_DIR/venv/bin/python "$RUN_PATH"
Icon=$INSTALL_DIR/pisak/config_files/icons/pisak_logo.png
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

echo -e "${GREEN}✓ Ikona została poprawnie stworzona.${NC}"
echo ""

# Update desktop database (for some desktop environments)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Instalacja zakończyła się sukcesem!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Aby uruchomić aplikację:${NC}"
echo -e "  1. Wyszukaj '$APP_NAME' w dostępnych aplikacjach"
echo -e "  2. Kliknij na ikonkę aplikacji znajdującą się na pulpicie."
echo ""
