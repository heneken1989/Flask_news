#!/bin/bash
# Script để cài đặt Chrome dependencies trên VPS

echo "============================================================"
echo "Installing Chrome/Chromium dependencies..."
echo "============================================================"

# Update package list
echo "📦 Updating package list..."
apt-get update -qq

# Install dependencies
echo "📦 Installing Chrome dependencies..."
apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

echo ""
echo "============================================================"
echo "✅ Dependencies installation completed!"
echo "============================================================"
echo ""
echo "💡 To verify, run:"
echo "   python check_chrome_status.py"

