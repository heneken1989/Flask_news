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

# Check if Chrome/Chromium is installed
echo -e "${YELLOW}Checking for Chrome/Chromium...${NC}"
if ! command -v chromium-browser &> /dev/null && ! command -v chromium &> /dev/null && ! command -v google-chrome &> /dev/null; then
    echo -e "${YELLOW}Chrome/Chromium not found. Installing...${NC}"
    if [ -f "$SCRIPT_DIR/install_chrome.sh" ]; then
        bash "$SCRIPT_DIR/install_chrome.sh"
    else
        echo -e "${RED}install_chrome.sh not found. Please install Chrome/Chromium manually:${NC}"
        echo -e "  Ubuntu/Debian: sudo apt-get install chromium-browser"
        echo -e "  CentOS/RHEL: sudo yum install chromium"
        read -p "Press Enter to continue anyway, or Ctrl+C to cancel..."
    fi
else
    echo -e "${GREEN}✅ Chrome/Chromium found${NC}"
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Get user and group (default to root for Chrome/Snap compatibility)
if [ -z "$SERVICE_USER" ]; then
    SERVICE_USER="root"
fi

if [ -z "$SERVICE_GROUP" ]; then
    SERVICE_GROUP="root"
fi

echo -e "${YELLOW}Service will run as: ${GREEN}$SERVICE_USER:$SERVICE_GROUP${NC}"

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
echo -e "${YELLOW}Updating service file with paths and user settings...${NC}"
sed -i "s|/path/to/GC_HRAI/flask|$FLASK_DIR|g" "$SCRIPT_DIR/crawl_sections.service"
sed -i "s|/path/to/venv|$VENV_PATH|g" "$SCRIPT_DIR/crawl_sections.service"

# Update User and Group (handle both www-data and root)
sed -i "s|^User=.*|User=$SERVICE_USER|g" "$SCRIPT_DIR/crawl_sections.service"
sed -i "s|^Group=.*|Group=$SERVICE_GROUP|g" "$SCRIPT_DIR/crawl_sections.service"

# Verify User and Group are set correctly
if grep -q "^User=$SERVICE_USER" "$SCRIPT_DIR/crawl_sections.service" && grep -q "^Group=$SERVICE_GROUP" "$SCRIPT_DIR/crawl_sections.service"; then
    echo -e "${GREEN}✅ Service configured to run as: $SERVICE_USER:$SERVICE_GROUP${NC}"
else
    echo -e "${RED}⚠️  Warning: Could not verify User/Group in service file${NC}"
fi

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

# Check service user/group configuration
echo -e "${GREEN}Checking service configuration...${NC}"
SERVICE_USER_CONFIG=$(grep "^User=" /etc/systemd/system/crawl_sections.service | cut -d'=' -f2)
SERVICE_GROUP_CONFIG=$(grep "^Group=" /etc/systemd/system/crawl_sections.service | cut -d'=' -f2)
echo -e "  Service User: ${GREEN}$SERVICE_USER_CONFIG${NC}"
echo -e "  Service Group: ${GREEN}$SERVICE_GROUP_CONFIG${NC}"

# Show status
echo -e "${GREEN}Service status:${NC}"
systemctl status crawl_sections.timer --no-pager

echo -e "${GREEN}Timer status:${NC}"
systemctl list-timers crawl_sections.timer --no-pager

echo -e "${GREEN}✅ Setup completed!${NC}"
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  Check timer status: ${GREEN}systemctl status crawl_sections.timer${NC}"
echo -e "  Check service status: ${GREEN}systemctl status crawl_sections.service${NC}"
echo -e "  Check service user/group: ${GREEN}systemctl show crawl_sections.service | grep -E \"(User|Group|MainPID)\"${NC}"
echo -e "  Check service user (simple): ${GREEN}grep -E \"^(User|Group)=\" /etc/systemd/system/crawl_sections.service${NC}"
echo -e "  Check running process user: ${GREEN}ps aux | grep crawl_sections_multi_language${NC}"
echo -e ""
echo -e "${YELLOW}View logs (live):${NC}"
echo -e "  Live log (follow): ${GREEN}journalctl -u crawl_sections.service -f${NC}"
echo -e "  Last 100 lines: ${GREEN}journalctl -u crawl_sections.service -n 100${NC}"
echo -e "  Last 100 lines + follow: ${GREEN}journalctl -u crawl_sections.service -n 100 -f${NC}"
echo -e "  Since 1 hour ago: ${GREEN}journalctl -u crawl_sections.service --since \"1 hour ago\"${NC}"
echo -e "  Since today: ${GREEN}journalctl -u crawl_sections.service --since today${NC}"
echo -e ""
echo -e "${YELLOW}Control service:${NC}"
echo -e "  Manually run service: ${GREEN}systemctl start crawl_sections.service${NC}"
echo -e "  Stop timer: ${GREEN}systemctl stop crawl_sections.timer${NC}"
echo -e "  Disable timer: ${GREEN}systemctl disable crawl_sections.timer${NC}"

