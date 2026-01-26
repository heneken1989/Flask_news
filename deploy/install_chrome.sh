#!/bin/bash
# Script to install Chrome/Chromium on Linux VPS for SeleniumBase
# Supports: Ubuntu/Debian, CentOS/RHEL, Alpine

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing Chrome/Chromium for SeleniumBase...${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    echo -e "${RED}Cannot detect OS. Please install Chrome/Chromium manually.${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS $OS_VERSION${NC}"

# Install based on OS
case $OS in
    ubuntu|debian)
        echo -e "${GREEN}Installing Chromium for Ubuntu/Debian...${NC}"
        sudo apt-get update
        sudo apt-get install -y chromium-browser chromium-chromedriver
        
        # Verify installation
        if command -v chromium-browser &> /dev/null; then
            CHROME_PATH=$(which chromium-browser)
            echo -e "${GREEN}✅ Chromium installed at: $CHROME_PATH${NC}"
        else
            echo -e "${RED}❌ Chromium installation failed${NC}"
            exit 1
        fi
        ;;
    
    centos|rhel|fedora)
        echo -e "${GREEN}Installing Chromium for CentOS/RHEL/Fedora...${NC}"
        if [ "$OS" = "fedora" ]; then
            sudo dnf install -y chromium chromium-headless
        else
            # For CentOS/RHEL, need to enable EPEL
            sudo yum install -y epel-release
            sudo yum install -y chromium chromium-headless
        fi
        
        # Verify installation
        if command -v chromium &> /dev/null; then
            CHROME_PATH=$(which chromium)
            echo -e "${GREEN}✅ Chromium installed at: $CHROME_PATH${NC}"
        else
            echo -e "${RED}❌ Chromium installation failed${NC}"
            exit 1
        fi
        ;;
    
    alpine)
        echo -e "${GREEN}Installing Chromium for Alpine...${NC}"
        sudo apk add --no-cache chromium chromium-chromedriver
        
        # Verify installation
        if command -v chromium-browser &> /dev/null; then
            CHROME_PATH=$(which chromium-browser)
            echo -e "${GREEN}✅ Chromium installed at: $CHROME_PATH${NC}"
        else
            echo -e "${RED}❌ Chromium installation failed${NC}"
            exit 1
        fi
        ;;
    
    *)
        echo -e "${YELLOW}OS $OS not directly supported. Attempting generic Chrome installation...${NC}"
        echo -e "${YELLOW}Please install Chrome/Chromium manually:${NC}"
        echo -e "  Ubuntu/Debian: sudo apt-get install chromium-browser"
        echo -e "  CentOS/RHEL: sudo yum install chromium"
        echo -e "  Or download from: https://www.google.com/chrome/"
        exit 1
        ;;
esac

# Set Chrome binary path for SeleniumBase (optional)
# SeleniumBase should auto-detect, but we can set it explicitly
if [ -n "$CHROME_PATH" ]; then
    echo -e "${GREEN}Chrome/Chromium is ready!${NC}"
    echo -e "${YELLOW}Note: SeleniumBase should auto-detect Chrome.${NC}"
    echo -e "${YELLOW}If you encounter issues, you can set CHROME_BIN environment variable:${NC}"
    echo -e "  export CHROME_BIN=$CHROME_PATH"
fi

echo -e "${GREEN}✅ Chrome/Chromium installation completed!${NC}"

