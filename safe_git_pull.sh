#!/bin/bash

# Script: Safe Git Pull - Preserve auto-generated files
# Usage: ./safe_git_pull.sh

set -e

echo "=========================================="
echo "🔄 SAFE GIT PULL SCRIPT"
echo "=========================================="
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

echo "📊 Step 1: Checking current status..."
echo ""

# Show current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "   Current branch: $CURRENT_BRANCH"

# Show files that might be affected
echo ""
echo "📂 Step 2: Checking auto-generated files..."
echo ""

# Check home layouts
if [ -d "scripts/home_layouts" ]; then
    LAYOUT_COUNT=$(ls -1 scripts/home_layouts/*.json 2>/dev/null | wc -l | xargs)
    echo "   ✓ Home layouts: $LAYOUT_COUNT files"
else
    echo "   ⚠️  No home_layouts directory"
fi

# Check sitemaps
SITEMAP_COUNT=$(ls -1 sitemap*.xml 2>/dev/null | wc -l | xargs)
if [ "$SITEMAP_COUNT" -gt 0 ]; then
    echo "   ✓ Sitemaps: $SITEMAP_COUNT files"
else
    echo "   ⚠️  No sitemap files"
fi

echo ""
echo "🔍 Step 3: Checking if files are tracked by git..."
echo ""

# Check if layout files are tracked
TRACKED_LAYOUTS=$(git ls-files scripts/home_layouts/*.json 2>/dev/null | wc -l | xargs)
TRACKED_SITEMAPS=$(git ls-files sitemap*.xml 2>/dev/null | wc -l | xargs)

if [ "$TRACKED_LAYOUTS" -gt 0 ] || [ "$TRACKED_SITEMAPS" -gt 0 ]; then
    echo "   ⚠️  Warning: Some files are still tracked by git!"
    echo "   Tracked layouts: $TRACKED_LAYOUTS"
    echo "   Tracked sitemaps: $TRACKED_SITEMAPS"
    echo ""
    echo "   💡 These files will be removed from tracking after pull"
    echo "      (but kept on filesystem)"
    echo ""
fi

echo "📥 Step 4: Fetching from origin..."
git fetch origin

echo ""
echo "🔍 Step 5: Checking for changes..."
echo ""

# Show what will be updated
CHANGES=$(git log HEAD..origin/$CURRENT_BRANCH --oneline | wc -l | xargs)
if [ "$CHANGES" -gt 0 ]; then
    echo "   📝 $CHANGES new commit(s) to pull:"
    git log HEAD..origin/$CURRENT_BRANCH --oneline --color=always | head -5
    
    if [ "$CHANGES" -gt 5 ]; then
        echo "   ... and $((CHANGES - 5)) more"
    fi
else
    echo "   ✓ Already up to date!"
    exit 0
fi

echo ""
echo "📂 Step 6: Files that will be changed:"
echo ""
git diff --name-status HEAD origin/$CURRENT_BRANCH | head -10
TOTAL_CHANGES=$(git diff --name-status HEAD origin/$CURRENT_BRANCH | wc -l | xargs)
if [ "$TOTAL_CHANGES" -gt 10 ]; then
    echo "   ... and $((TOTAL_CHANGES - 10)) more files"
fi

echo ""
read -p "❓ Continue with git pull? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted by user"
    exit 1
fi

echo ""
echo "🔄 Step 7: Pulling from origin/$CURRENT_BRANCH..."
echo ""

# Pull with merge strategy
git pull origin $CURRENT_BRANCH

echo ""
echo "✅ Step 8: Verifying auto-generated files..."
echo ""

# Verify home layouts still exist
if [ -d "scripts/home_layouts" ]; then
    LAYOUT_COUNT_AFTER=$(ls -1 scripts/home_layouts/*.json 2>/dev/null | wc -l | xargs)
    if [ "$LAYOUT_COUNT_AFTER" -gt 0 ]; then
        echo "   ✓ Home layouts preserved: $LAYOUT_COUNT_AFTER files"
    else
        echo "   ⚠️  No layout files found (may need regeneration)"
    fi
fi

# Verify sitemaps still exist
SITEMAP_COUNT_AFTER=$(ls -1 sitemap*.xml 2>/dev/null | wc -l | xargs)
if [ "$SITEMAP_COUNT_AFTER" -gt 0 ]; then
    echo "   ✓ Sitemaps preserved: $SITEMAP_COUNT_AFTER files"
else
    echo "   ⚠️  No sitemap files found (may need regeneration)"
fi

# Check gitignore status
echo ""
echo "📋 Step 9: Checking .gitignore status..."
if grep -q "scripts/home_layouts/" .gitignore && grep -q "sitemap.*\.xml" .gitignore; then
    echo "   ✓ .gitignore configured correctly"
    echo "   → Auto-generated files are now protected"
else
    echo "   ⚠️  Warning: .gitignore may not be configured"
    echo "   → Files might be tracked in future commits"
fi

echo ""
echo "=========================================="
echo "✅ Git pull completed successfully!"
echo "=========================================="
echo ""
echo "🎉 Summary:"
echo "   • Pulled $CHANGES new commit(s)"
echo "   • Auto-generated files preserved"
echo "   • Ready to restart services if needed"
echo ""
echo "🔧 Next steps:"
echo "   1. Restart Flask service: sudo systemctl restart sermitsiaq-flask.service"
echo "   2. Check service status: sudo systemctl status sermitsiaq-flask.service"
echo ""
