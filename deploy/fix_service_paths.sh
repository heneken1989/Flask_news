#!/bin/bash
# Script để tự động sửa paths trong crawl_sections.service
# Chạy trên VPS: sudo bash fix_service_paths.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔧 Fixing crawl_sections.service paths...${NC}"

# Detect paths
FLASK_DIR="/var/www/flask/nococo"
VENV_PATH="$FLASK_DIR/venv"
SERVICE_FILE="/etc/systemd/system/crawl_sections.service"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}❌ Service file not found: $SERVICE_FILE${NC}"
    echo -e "${YELLOW}Please copy crawl_sections.service to /etc/systemd/system/ first${NC}"
    exit 1
fi

# Check if directories exist
if [ ! -d "$FLASK_DIR" ]; then
    echo -e "${RED}❌ Flask directory not found: $FLASK_DIR${NC}"
    read -p "Enter correct Flask directory path: " FLASK_DIR
    VENV_PATH="$FLASK_DIR/venv"
fi

if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Venv directory not found: $VENV_PATH${NC}"
    read -p "Enter correct venv path: " VENV_PATH
fi

echo -e "${YELLOW}Using paths:${NC}"
echo -e "   Flask dir: $FLASK_DIR"
echo -e "   Venv path: $VENV_PATH"
echo -e "   Service file: $SERVICE_FILE"

# Backup service file
cp "$SERVICE_FILE" "$SERVICE_FILE.backup"
echo -e "${GREEN}✅ Backup created: $SERVICE_FILE.backup${NC}"

# Fix paths
echo -e "${YELLOW}Updating paths...${NC}"
sed -i "s|/path/to/GC_HRAI/flask|$FLASK_DIR|g" "$SERVICE_FILE"
sed -i "s|/path/to/venv|$VENV_PATH|g" "$SERVICE_FILE"

# Verify changes
echo -e "${GREEN}✅ Paths updated!${NC}"
echo -e "${YELLOW}Verifying changes:${NC}"
echo ""
grep -E "(WorkingDirectory|ExecStart|PYTHONPATH)" "$SERVICE_FILE" || true
echo ""

# Reload systemd
echo -e "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload

# Test service file syntax
echo -e "${YELLOW}Testing service file...${NC}"
systemctl cat crawl_sections.service > /dev/null && echo -e "${GREEN}✅ Service file syntax OK${NC}" || echo -e "${RED}❌ Service file syntax error${NC}"

echo ""
echo -e "${GREEN}✅ Done!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Test: ${GREEN}sudo systemctl start crawl_sections.service${NC}"
echo -e "  2. Check logs: ${GREEN}journalctl -u crawl_sections.service -n 50${NC}"
echo -e "  3. Check timer: ${GREEN}systemctl status crawl_sections.timer${NC}"

