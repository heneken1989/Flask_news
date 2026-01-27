#!/bin/bash
# Script để enable và start crawl_sections timer

set -e

echo "============================================================"
echo "🔧 Enable Crawler Timer"
echo "============================================================"

# 1. Copy timer file to systemd directory
echo ""
echo "Step 1: Copying timer file..."
if [ ! -f /etc/systemd/system/crawl_sections.timer ]; then
    sudo cp /var/www/flask/nococo/deploy/crawl_sections.timer /etc/systemd/system/
    echo "✅ Copied timer file to /etc/systemd/system/"
else
    echo "✅ Timer file already exists"
    # Update it anyway in case it changed
    sudo cp /var/www/flask/nococo/deploy/crawl_sections.timer /etc/systemd/system/
    echo "✅ Updated timer file"
fi

# 2. Copy service file (if not already there)
echo ""
echo "Step 2: Checking service file..."
if [ ! -f /etc/systemd/system/crawl_sections.service ]; then
    sudo cp /var/www/flask/nococo/deploy/crawl_sections.service /etc/systemd/system/
    echo "✅ Copied service file to /etc/systemd/system/"
else
    echo "✅ Service file already exists"
    # Update it anyway
    sudo cp /var/www/flask/nococo/deploy/crawl_sections.service /etc/systemd/system/
    echo "✅ Updated service file"
fi

# 3. Reload systemd daemon
echo ""
echo "Step 3: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# 4. Enable timer (will start on boot)
echo ""
echo "Step 4: Enabling timer..."
sudo systemctl enable crawl_sections.timer
echo "✅ Timer enabled (will start on boot)"

# 5. Start timer now
echo ""
echo "Step 5: Starting timer..."
sudo systemctl start crawl_sections.timer
echo "✅ Timer started"

# 6. Check timer status
echo ""
echo "============================================================"
echo "📊 Timer Status"
echo "============================================================"
systemctl status crawl_sections.timer --no-pager

# 7. Show next run time
echo ""
echo "============================================================"
echo "⏰ Next Run Schedule"
echo "============================================================"
systemctl list-timers crawl_sections.timer --no-pager

echo ""
echo "============================================================"
echo "✅ Timer setup completed!"
echo "============================================================"
echo "Timer will run every hour with a random delay of 0-300 seconds."
echo ""
echo "Useful commands:"
echo "  - Check timer status: systemctl status crawl_sections.timer"
echo "  - Check next run: systemctl list-timers | grep crawl"
echo "  - View logs: journalctl -u crawl_sections.service -f"
echo "  - Stop timer: sudo systemctl stop crawl_sections.timer"
echo "  - Disable timer: sudo systemctl disable crawl_sections.timer"
echo "  - Trigger manually: sudo systemctl start crawl_sections.service"

