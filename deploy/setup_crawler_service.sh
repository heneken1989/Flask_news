#!/bin/bash
# Setup script for crawl_sections_multi_language.py systemd service
# Run this script as root or with sudo

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Sermitsiaq Crawler Service...${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FLASK_DIR="$PROJECT_ROOT/flask"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Get user and group (default to www-data, or current user)
if [ -z "$SERVICE_USER" ]; then
    SERVICE_USER="www-data"
fi

if [ -z "$SERVICE_GROUP" ]; then
    SERVICE_GROUP="www-data"
fi

# Find Python virtual environment
if [ -z "$VENV_PATH" ]; then
    # Try common locations
    if [ -d "$PROJECT_ROOT/venv" ]; then
        VENV_PATH="$PROJECT_ROOT/venv"
    elif [ -d "$PROJECT_ROOT/.venv" ]; then
        VENV_PATH="$PROJECT_ROOT/.venv"
    else
        echo -e "${YELLOW}Warning: Virtual environment not found. Please set VENV_PATH manually.${NC}"
        read -p "Enter path to virtual environment: " VENV_PATH
    fi
fi

# Update service file with actual paths
sed -i "s|/path/to/GC_HRAI/flask|$FLASK_DIR|g" "$SCRIPT_DIR/crawl_sections.service"
sed -i "s|/path/to/venv|$VENV_PATH|g" "$SCRIPT_DIR/crawl_sections.service"
sed -i "s|User=www-data|User=$SERVICE_USER|g" "$SCRIPT_DIR/crawl_sections.service"
sed -i "s|Group=www-data|Group=$SERVICE_GROUP|g" "$SCRIPT_DIR/crawl_sections.service"

# Copy service and timer files
echo -e "${GREEN}Copying service files...${NC}"
cp "$SCRIPT_DIR/crawl_sections.service" /etc/systemd/system/
cp "$SCRIPT_DIR/crawl_sections.timer" /etc/systemd/system/

# Reload systemd
echo -e "${GREEN}Reloading systemd...${NC}"
systemctl daemon-reload

# Enable and start timer
echo -e "${GREEN}Enabling and starting timer...${NC}"
systemctl enable crawl_sections.timer
systemctl start crawl_sections.timer

# Show status
echo -e "${GREEN}Service status:${NC}"
systemctl status crawl_sections.timer --no-pager

echo -e "${GREEN}Timer status:${NC}"
systemctl list-timers crawl_sections.timer --no-pager

echo -e "${GREEN}✅ Setup completed!${NC}"
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  Check timer status: ${GREEN}systemctl status crawl_sections.timer${NC}"
echo -e "  Check service logs: ${GREEN}journalctl -u crawl_sections.service -f${NC}"
echo -e "  Manually run service: ${GREEN}systemctl start crawl_sections.service${NC}"
echo -e "  Stop timer: ${GREEN}systemctl stop crawl_sections.timer${NC}"
echo -e "  Disable timer: ${GREEN}systemctl disable crawl_sections.timer${NC}"

