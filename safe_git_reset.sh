#!/bin/bash

# Script: Safe Git Reset - Preserve auto-generated files
# Usage: ./safe_git_reset.sh

set -e

echo "=========================================="
echo "🛡️  SAFE GIT RESET SCRIPT"
echo "=========================================="
echo ""

# Define backup directory
BACKUP_DIR="/tmp/flask_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Step 1: Backing up important files..."
echo "   Backup location: $BACKUP_DIR"
echo ""

# Backup home layouts
if [ -d "scripts/home_layouts" ]; then
    echo "   ✓ Backing up home_layouts..."
    cp -r scripts/home_layouts "$BACKUP_DIR/"
else
    echo "   ⚠️  No home_layouts directory found"
fi

# Backup sitemaps
if ls sitemap*.xml 1> /dev/null 2>&1; then
    echo "   ✓ Backing up sitemap files..."
    cp sitemap*.xml "$BACKUP_DIR/" 2>/dev/null || true
else
    echo "   ⚠️  No sitemap files found"
fi

# Backup scripts/sitemap files if they exist
if ls scripts/sitemap*.xml 1> /dev/null 2>&1; then
    echo "   ✓ Backing up scripts/sitemap files..."
    cp scripts/sitemap*.xml "$BACKUP_DIR/" 2>/dev/null || true
fi

echo ""
echo "📥 Step 2: Fetching from origin..."
git fetch origin

echo ""
echo "🔍 Step 3: Checking what will be deleted..."
echo ""
git diff --name-status HEAD origin/main | grep "^D" || echo "   No files will be deleted"

echo ""
read -p "❓ Continue with git reset? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted by user"
    exit 1
fi

echo ""
echo "🔄 Step 4: Resetting to origin/main..."
git reset --hard origin/main

echo ""
echo "📂 Step 5: Restoring auto-generated files..."

# Restore home layouts
if [ -d "$BACKUP_DIR/home_layouts" ]; then
    echo "   ✓ Restoring home_layouts..."
    mkdir -p scripts/home_layouts
    cp -r "$BACKUP_DIR/home_layouts/"* scripts/home_layouts/
else
    echo "   ⚠️  No home_layouts to restore"
fi

# Restore sitemaps
if ls "$BACKUP_DIR"/sitemap*.xml 1> /dev/null 2>&1; then
    echo "   ✓ Restoring sitemap files..."
    cp "$BACKUP_DIR"/sitemap*.xml . 2>/dev/null || true
else
    echo "   ⚠️  No sitemap files to restore"
fi

echo ""
echo "✅ Step 6: Verifying restored files..."
echo ""

# Check home layouts
if [ -d "scripts/home_layouts" ]; then
    echo "   Home layouts: ✓"
    ls -lh scripts/home_layouts/*.json 2>/dev/null | awk '{print "      -", $9, "("$5")"}'
else
    echo "   Home layouts: ✗ (will need to regenerate)"
fi

# Check sitemaps
if ls sitemap*.xml 1> /dev/null 2>&1; then
    echo "   Sitemaps: ✓"
    ls -lh sitemap*.xml 2>/dev/null | awk '{print "      -", $9, "("$5")"}'
else
    echo "   Sitemaps: ✗ (will need to regenerate)"
fi

echo ""
echo "=========================================="
echo "✅ Git reset completed successfully!"
echo "=========================================="
echo ""
echo "📌 Backup preserved at: $BACKUP_DIR"
echo "   (You can delete it after verifying everything works)"
echo ""
echo "🔧 If any files are missing, you can:"
echo "   1. Restore from backup: cp -r $BACKUP_DIR/* ."
echo "   2. Or regenerate them using scripts"
echo ""
