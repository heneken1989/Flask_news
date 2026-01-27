#!/bin/bash
# Script để check timer status trên VPS

echo "============================================================"
echo "1. Checking if crawl_sections.timer exists..."
echo "============================================================"
if [ -f /etc/systemd/system/crawl_sections.timer ]; then
    echo "✅ Timer file exists: /etc/systemd/system/crawl_sections.timer"
    ls -lh /etc/systemd/system/crawl_sections.timer
else
    echo "❌ Timer file NOT found: /etc/systemd/system/crawl_sections.timer"
fi

echo ""
echo "============================================================"
echo "2. Checking timer status..."
echo "============================================================"
systemctl status crawl_sections.timer --no-pager

echo ""
echo "============================================================"
echo "3. Checking if timer is enabled..."
echo "============================================================"
systemctl is-enabled crawl_sections.timer 2>&1

echo ""
echo "============================================================"
echo "4. Checking all timers (including inactive)..."
echo "============================================================"
systemctl list-timers --all | grep -i crawl || echo "❌ No crawl timers found"

echo ""
echo "============================================================"
echo "5. Checking service file..."
echo "============================================================"
if [ -f /etc/systemd/system/crawl_sections.service ]; then
    echo "✅ Service file exists: /etc/systemd/system/crawl_sections.service"
    ls -lh /etc/systemd/system/crawl_sections.service
else
    echo "❌ Service file NOT found: /etc/systemd/system/crawl_sections.service"
fi

echo ""
echo "============================================================"
echo "6. Checking service status..."
echo "============================================================"
systemctl status crawl_sections.service --no-pager

echo ""
echo "============================================================"
echo "7. Recent service logs (last 10 lines)..."
echo "============================================================"
journalctl -u crawl_sections.service -n 10 --no-pager

echo ""
echo "============================================================"
echo "RECOMMENDATIONS"
echo "============================================================"
if [ ! -f /etc/systemd/system/crawl_sections.timer ]; then
    echo "❌ Timer file missing. Copy it to /etc/systemd/system/"
    echo "   sudo cp flask/deploy/crawl_sections.timer /etc/systemd/system/"
elif ! systemctl is-enabled crawl_sections.timer &>/dev/null; then
    echo "❌ Timer not enabled. Enable and start it:"
    echo "   sudo systemctl daemon-reload"
    echo "   sudo systemctl enable crawl_sections.timer"
    echo "   sudo systemctl start crawl_sections.timer"
    echo "   sudo systemctl list-timers | grep crawl"
else
    echo "✅ Timer should be running"
fi

