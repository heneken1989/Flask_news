#!/bin/bash
# Script để pull code an toàn khi có untracked files

set -e

echo "🔄 Safe git pull script"
echo "========================"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not a git repository"
    exit 1
fi

# Step 1: Add static/uploads/images/ to .gitignore (if not already added)
if ! grep -q "static/uploads/images/" .gitignore 2>/dev/null; then
    echo "📝 Adding static/uploads/images/ to .gitignore..."
    echo "" >> .gitignore
    echo "# Uploaded images (auto-downloaded, should not be committed)" >> .gitignore
    echo "static/uploads/images/" >> .gitignore
    echo "static/uploads/images/*" >> .gitignore
fi

# Step 2: Check if redownload_missing_images.py needs to be committed
if [ -f "scripts/redownload_missing_images.py" ]; then
    if ! git ls-files --error-unmatch scripts/redownload_missing_images.py > /dev/null 2>&1; then
        echo "📝 File scripts/redownload_missing_images.py is untracked"
        echo "   Options:"
        echo "   1. Commit it (recommended if it's a new feature)"
        echo "   2. Stash it temporarily"
        read -p "   Choose (1=commit, 2=stash, 3=skip): " choice
        
        case $choice in
            1)
                echo "   ✅ Committing redownload_missing_images.py..."
                git add scripts/redownload_missing_images.py
                git commit -m "Add redownload_missing_images.py script"
                ;;
            2)
                echo "   📦 Stashing redownload_missing_images.py..."
                git stash push -u scripts/redownload_missing_images.py -m "Temporary stash: redownload_missing_images.py"
                STASHED=1
                ;;
            3)
                echo "   ⏭️  Skipping redownload_missing_images.py (will be overwritten)"
                rm -f scripts/redownload_missing_images.py
                ;;
            *)
                echo "   ⚠️  Invalid choice, skipping..."
                rm -f scripts/redownload_missing_images.py
                ;;
        esac
    fi
fi

# Step 3: Remove untracked images (they're now in .gitignore)
echo "🗑️  Removing untracked image files (they're in .gitignore now)..."
git clean -fd static/uploads/images/ 2>/dev/null || true

# Step 4: Pull
echo "⬇️  Pulling latest changes..."
git pull origin main

# Step 5: Restore stashed file if needed
if [ "$STASHED" = "1" ]; then
    echo "📦 Restoring stashed file..."
    git stash pop || true
fi

echo ""
echo "✅ Pull completed successfully!"
echo ""
echo "💡 Note: Image files in static/uploads/images/ are now ignored by git"
echo "   They will be re-downloaded automatically when needed"
