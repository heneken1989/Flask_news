#!/bin/bash

# Script tự động setup Flask app thay thế React trên VPS
# Domain: nococo.shop
# Ports: 8080 (HTTP) → 8443 (HTTPS)
# Usage: sudo ./setup_flask_nococo.sh

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

# Thông tin cấu hình
FLASK_DIR="/var/www/flask/nococo"
NGINX_CONFIG="/etc/nginx/sites-available/nococo"
SERVICE_NAME="flask-nococo"

echo -e "${GREEN}🚀 Setting up Flask app to replace React${NC}"
echo ""

# Bước 1: Tạo thư mục
echo -e "${YELLOW}[1/6] Creating directories...${NC}"
mkdir -p "$FLASK_DIR"
mkdir -p "$FLASK_DIR/logs"
chown -R www-data:www-data "$FLASK_DIR"
chmod -R 755 "$FLASK_DIR"
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Bước 2: Kiểm tra Flask project
echo -e "${YELLOW}[2/6] Checking Flask project...${NC}"
if [ ! -f "$FLASK_DIR/app.py" ]; then
    echo -e "${RED}❌ Flask project not found in $FLASK_DIR${NC}"
    echo -e "${YELLOW}Please upload Flask project first:${NC}"
    echo "  scp -r flask-project/* root@your-vps:$FLASK_DIR/"
    exit 1
fi
echo -e "${GREEN}✅ Flask project found${NC}"
echo ""

# Bước 3: Setup Python environment
echo -e "${YELLOW}[3/6] Setting up Python environment...${NC}"
cd "$FLASK_DIR"

# Cài Python nếu chưa có
if ! command -v python3 &> /dev/null; then
    apt update
    apt install -y python3 python3-pip python3-venv
fi

# Tạo venv nếu chưa có
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Install dependencies
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, installing Flask and Gunicorn...${NC}"
    pip install Flask gunicorn
fi
echo -e "${GREEN}✅ Python environment ready${NC}"
echo ""

# Bước 4: Kiểm tra static files
echo -e "${YELLOW}[4/6] Checking static files...${NC}"
if [ ! -d "static/css" ]; then
    echo -e "${YELLOW}⚠️  Static files not found. Creating directory...${NC}"
    mkdir -p static/css static/js static/images
    echo -e "${YELLOW}Please copy CSS files to $FLASK_DIR/static/css/${NC}"
else
    echo -e "${GREEN}✅ Static files found${NC}"
fi
echo ""

# Bước 5: Cập nhật Nginx config
echo -e "${YELLOW}[5/6] Updating Nginx configuration...${NC}"

# Kiểm tra Nginx đã cài chưa
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nginx not found. Installing...${NC}"
    apt update
    apt install -y nginx
fi

# Backup config cũ
if [ -f "$NGINX_CONFIG" ]; then
    cp "$NGINX_CONFIG" "${NGINX_CONFIG}.react.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✅ Old config backed up${NC}"
fi

# Kiểm tra nếu có file config mới
if [ -f "$FLASK_DIR/deploy/nginx_flask_nococo.conf" ]; then
    cp "$FLASK_DIR/deploy/nginx_flask_nococo.conf" "$NGINX_CONFIG"
    echo -e "${GREEN}✅ New config copied${NC}"
else
    echo -e "${YELLOW}⚠️  nginx_flask_nococo.conf not found${NC}"
    echo -e "${YELLOW}Please manually update $NGINX_CONFIG${NC}"
    echo "See: deploy/DEPLOY_REPLACE_REACT.md"
fi

# Enable site (tạo symlink nếu chưa có)
NGINX_ENABLED="/etc/nginx/sites-enabled/nococo"
if [ ! -L "$NGINX_ENABLED" ]; then
    ln -s "$NGINX_CONFIG" "$NGINX_ENABLED"
    echo -e "${GREEN}✅ Nginx site enabled${NC}"
else
    echo -e "${GREEN}✅ Nginx site already enabled${NC}"
fi

# Test và reload Nginx
if nginx -t; then
    # Start Nginx nếu chưa chạy
    if ! systemctl is-active --quiet nginx; then
        systemctl start nginx
        echo -e "${GREEN}✅ Nginx started${NC}"
    else
        systemctl reload nginx
        echo -e "${GREEN}✅ Nginx reloaded${NC}"
    fi
else
    echo -e "${RED}❌ Nginx config test failed${NC}"
    echo "Check config: nginx -t"
    exit 1
fi
echo ""

# Bước 6: Tạo systemd service
echo -e "${YELLOW}[6/6] Creating systemd service...${NC}"

cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Flask Nococo App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$FLASK_DIR
Environment="PATH=$FLASK_DIR/venv/bin"
ExecStart=$FLASK_DIR/venv/bin/gunicorn -c $FLASK_DIR/gunicorn_config.py app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd và start service
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

# Kiểm tra status
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}✅ Service started successfully${NC}"
else
    echo -e "${RED}❌ Service failed to start${NC}"
    echo "Check logs: journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi
echo ""

# Tổng kết
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Flask app setup completed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo "📝 Service information:"
echo "   Status: systemctl status ${SERVICE_NAME}"
echo "   Logs:   journalctl -u ${SERVICE_NAME} -f"
echo "   Stop:   systemctl stop ${SERVICE_NAME}"
echo "   Start:  systemctl start ${SERVICE_NAME}"
echo ""
echo "🌐 Test your site:"
echo "   https://nococo.shop:8443"
echo ""
echo "📂 Directories:"
echo "   Flask app:  $FLASK_DIR"
echo "   Static:     $FLASK_DIR/static"
echo "   Logs:       $FLASK_DIR/logs"
echo ""
echo "🔍 Verify:"
echo "   curl http://localhost:5000"
echo "   curl https://nococo.shop:8443/static/css/grid.css"
echo ""

