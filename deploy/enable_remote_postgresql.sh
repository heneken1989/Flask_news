#!/bin/bash

# Script để enable remote connections cho PostgreSQL
# Cho phép kết nối từ local machine đến VPS database
# Usage: sudo ./enable_remote_postgresql.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Kiểm tra quyền root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}🌐 Enabling remote PostgreSQL connections${NC}"
echo ""

# Find PostgreSQL version and config directory
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
PG_CONF_DIR="/etc/postgresql/${PG_VERSION}/main"
PG_HBA_FILE="${PG_CONF_DIR}/pg_hba.conf"
PG_CONF_FILE="${PG_CONF_DIR}/postgresql.conf"

if [ ! -d "$PG_CONF_DIR" ]; then
    # Try alternative path
    PG_CONF_DIR=$(find /etc/postgresql -name "main" -type d | head -1)
    PG_HBA_FILE="${PG_CONF_DIR}/pg_hba.conf"
    PG_CONF_FILE="${PG_CONF_DIR}/postgresql.conf"
fi

if [ ! -f "$PG_HBA_FILE" ] || [ ! -f "$PG_CONF_FILE" ]; then
    echo -e "${RED}❌ Could not find PostgreSQL config files${NC}"
    exit 1
fi

# Backup config files
if [ ! -f "${PG_HBA_FILE}.bak" ]; then
    cp "$PG_HBA_FILE" "${PG_HBA_FILE}.bak"
    echo -e "${GREEN}✅ Backed up pg_hba.conf${NC}"
fi

if [ ! -f "${PG_CONF_FILE}.bak" ]; then
    cp "$PG_CONF_FILE" "${PG_CONF_FILE}.bak"
    echo -e "${GREEN}✅ Backed up postgresql.conf${NC}"
fi

# Step 1: Configure postgresql.conf to listen on all interfaces
echo -e "${YELLOW}[1/3] Configuring PostgreSQL to listen on all interfaces...${NC}"
if grep -q "^#listen_addresses = 'localhost'" "$PG_CONF_FILE" || grep -q "^listen_addresses = 'localhost'" "$PG_CONF_FILE"; then
    sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF_FILE"
    sed -i "s/^listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF_FILE"
    echo -e "${GREEN}✅ Updated listen_addresses${NC}"
else
    if ! grep -q "^listen_addresses" "$PG_CONF_FILE"; then
        echo "listen_addresses = '*'" >> "$PG_CONF_FILE"
        echo -e "${GREEN}✅ Added listen_addresses${NC}"
    else
        echo -e "${YELLOW}⚠️  listen_addresses already configured${NC}"
    fi
fi

# Step 2: Configure pg_hba.conf to allow remote connections
echo -e "${YELLOW}[2/3] Configuring pg_hba.conf for remote connections...${NC}"
if ! grep -q "^# Remote connections for Flask app" "$PG_HBA_FILE"; then
    cat >> "$PG_HBA_FILE" <<EOF

# Remote connections for Flask app
# Allow connections from any IP (use specific IP for better security)
host    all             all             0.0.0.0/0               md5
host    all             all             ::/0                   md5
EOF
    echo -e "${GREEN}✅ Added remote connection rules${NC}"
else
    echo -e "${YELLOW}⚠️  Remote connection rules already exist${NC}"
fi

# Step 3: Restart PostgreSQL
echo -e "${YELLOW}[3/3] Restarting PostgreSQL...${NC}"
systemctl restart postgresql
echo -e "${GREEN}✅ PostgreSQL restarted${NC}"
echo ""

# Step 4: Check firewall
echo -e "${YELLOW}Checking firewall...${NC}"
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        echo -e "${YELLOW}⚠️  UFW firewall is active${NC}"
        echo -e "${YELLOW}   You may need to allow PostgreSQL port:${NC}"
        echo -e "${YELLOW}   sudo ufw allow 5432/tcp${NC}"
        read -p "Allow PostgreSQL port 5432 now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ufw allow 5432/tcp
            echo -e "${GREEN}✅ Port 5432 allowed${NC}"
        fi
    fi
fi

# Get VPS IP
VPS_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✅ Remote connections enabled!${NC}"
echo ""
echo -e "${YELLOW}📝 Connection Information:${NC}"
echo -e "   VPS IP: ${VPS_IP}"
echo -e "   Port: 5432"
echo -e "   Database: flask_news"
echo -e "   User: flask_user"
echo ""
echo -e "${YELLOW}📋 For local .env file, use:${NC}"
echo -e "   DATABASE_URL=postgresql://flask_user:PASSWORD@${VPS_IP}:5432/flask_news"
echo ""
echo -e "${RED}⚠️  SECURITY WARNING:${NC}"
echo -e "   - Remote connections are now enabled"
echo -e "   - Use strong password for flask_user"
echo -e "   - Consider restricting IPs in pg_hba.conf for better security"
echo ""

