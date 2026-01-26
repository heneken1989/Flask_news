#!/bin/bash
# Script để fix permissions cho crawler service
# Chạy: sudo bash fix_permissions.sh

set -e

FLASK_DIR="/var/www/flask/nococo"
SERVICE_USER="www-data"

echo "🔧 Fixing permissions for crawler service..."

# Tạo các thư mục cần thiết
mkdir -p "$FLASK_DIR/downloaded_files"
mkdir -p "$FLASK_DIR/archived_files"
mkdir -p "$FLASK_DIR/user_data"
mkdir -p "$FLASK_DIR/static/uploads/images"
mkdir -p "$FLASK_DIR/logs"

# Set ownership
chown -R $SERVICE_USER:$SERVICE_USER "$FLASK_DIR/downloaded_files"
chown -R $SERVICE_USER:$SERVICE_USER "$FLASK_DIR/archived_files"
chown -R $SERVICE_USER:$SERVICE_USER "$FLASK_DIR/user_data"
chown -R $SERVICE_USER:$SERVICE_USER "$FLASK_DIR/static/uploads"
chown -R $SERVICE_USER:$SERVICE_USER "$FLASK_DIR/logs"

# Set permissions
chmod -R 755 "$FLASK_DIR/downloaded_files"
chmod -R 755 "$FLASK_DIR/archived_files"
chmod -R 755 "$FLASK_DIR/user_data"
chmod -R 755 "$FLASK_DIR/static/uploads"
chmod -R 755 "$FLASK_DIR/logs"

echo "✅ Permissions fixed!"
echo ""
echo "Created directories:"
echo "  - $FLASK_DIR/downloaded_files"
echo "  - $FLASK_DIR/archived_files"
echo "  - $FLASK_DIR/user_data"
echo "  - $FLASK_DIR/static/uploads/images"
echo "  - $FLASK_DIR/logs"
echo ""
echo "All directories are owned by $SERVICE_USER:$SERVICE_USER"

