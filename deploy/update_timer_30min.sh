#!/bin/bash
# Script để update crawler timer từ 1 giờ sang 30 phút

set -e

echo "============================================================"
echo "⏰ Update Crawler Timer: 1 hour → 30 minutes"
echo "============================================================"

# 1. Copy timer file đã update
echo ""
echo "Step 1: Copying updated timer file..."
sudo cp /var/www/flask/nococo/deploy/crawl_sections.timer /etc/systemd/system/
echo "✅ Timer file updated"

# 2. Reload systemd daemon
echo ""
echo "Step 2: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# 3. Restart timer để áp dụng thay đổi
echo ""
echo "Step 3: Restarting timer..."
sudo systemctl restart crawl_sections.timer
echo "✅ Timer restarted with new schedule"

# 4. Check timer status
echo ""
echo "============================================================"
echo "📊 Timer Status"
echo "============================================================"
systemctl status crawl_sections.timer --no-pager

# 5. Show next run times
echo ""
echo "============================================================"
echo "⏰ Next Run Schedule (Every 30 minutes)"
echo "============================================================"
systemctl list-timers crawl_sections.timer --no-pager

echo ""
echo "============================================================"
echo "✅ Timer updated successfully!"
echo "============================================================"
echo "Crawler will now run every 30 minutes (:00 and :30 of each hour)"
echo "with a random delay of 0-180 seconds."
echo ""
echo "Useful commands:"
echo "  - Check timer status: systemctl status crawl_sections.timer"
echo "  - Check next runs: systemctl list-timers | grep crawl"
echo "  - View logs: journalctl -u crawl_sections.service -f"
echo ""

