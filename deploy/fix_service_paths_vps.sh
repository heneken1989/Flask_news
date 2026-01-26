#!/bin/bash
# Script để sửa paths trong crawl_sections.service trên VPS
# Chạy: sudo bash fix_service_paths_vps.sh

set -e

SERVICE_FILE="/etc/systemd/system/crawl_sections.service"

echo "🔧 Fixing crawl_sections.service paths..."

# Backup
cp "$SERVICE_FILE" "$SERVICE_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup created"

# Sửa paths - bỏ /flask thừa
sed -i 's|/var/www/flask/nococo/flask|/var/www/flask/nococo|g' "$SERVICE_FILE"

echo "✅ Paths fixed!"
echo ""
echo "Verifying changes:"
grep -E "(WorkingDirectory|ExecStart|PYTHONPATH)" "$SERVICE_FILE"
echo ""

# Reload
systemctl daemon-reload
echo "✅ Systemd reloaded"

echo ""
echo "Next steps:"
echo "  1. Test: sudo systemctl start crawl_sections.service"
echo "  2. Check logs: journalctl -u crawl_sections.service -n 50"

