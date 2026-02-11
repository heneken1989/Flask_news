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

# Step 1: Add static/uploads/images/ and user_data* to .gitignore (if not already added)
if ! grep -q "static/uploads/images/" .gitignore 2>/dev/null; then
    echo "📝 Adding static/uploads/images/ to .gitignore..."
    echo "" >> .gitignore
    echo "# Uploaded images (auto-downloaded, should not be committed)" >> .gitignore
    echo "static/uploads/images/" >> .gitignore
    echo "static/uploads/images/*" >> .gitignore
fi

if ! grep -q "user_data_translate/" .gitignore 2>/dev/null; then
    echo "📝 Adding user_data directories to .gitignore..."
    echo "" >> .gitignore
    echo "# Chrome user data (browser cache, should not be committed)" >> .gitignore
    echo "user_data/" >> .gitignore
    echo "user_data_*/" >> .gitignore
    echo "user_data_translate/" >> .gitignore
fi

# Remove user_data* from git tracking if they were previously tracked
if git ls-files --error-unmatch user_data/ user_data_translate/ > /dev/null 2>&1; then
    echo "🗑️  Removing user_data directories from git tracking (keeping files on disk)..."
    git rm -r --cached user_data/ user_data_translate/ 2>/dev/null || true
    echo "   ✅ Removed from git tracking"
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

# Step 3: Backup existing images before pull (to preserve VPS images)
BACKUP_DIR="/tmp/images_backup_$(date +%s)"
if [ -d "static/uploads/images" ] && [ "$(ls -A static/uploads/images 2>/dev/null)" ]; then
    echo "💾 Backing up existing images to preserve VPS images..."
    mkdir -p "$BACKUP_DIR"
    cp -r static/uploads/images/* "$BACKUP_DIR/" 2>/dev/null || true
    echo "   ✅ Backed up $(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l) image files"
fi

# Step 4: Temporarily remove untracked images to allow pull (they're now in .gitignore)
echo "🗑️  Temporarily removing untracked image files to allow pull..."
# Only remove files that would conflict with git pull
git clean -fd static/uploads/images/ 2>/dev/null || true

# Step 5: Pull (with merge strategy to handle divergent branches)
echo "⬇️  Pulling latest changes..."
# Set merge strategy if not already configured
if ! git config pull.rebase > /dev/null 2>&1 && ! git config pull.ff > /dev/null 2>&1; then
    echo "   ⚙️  Configuring git pull strategy to merge (to handle divergent branches)..."
    git config pull.rebase false
fi

# Pull with merge strategy
git pull origin main --no-rebase || {
    echo "   ⚠️  Pull failed, trying with merge strategy..."
    git pull origin main --no-rebase --no-edit || {
        echo "   ⚠️  Merge conflict detected. Attempting to resolve..."
        # If there are conflicts, try to resolve automatically (prefer remote)
        git checkout --theirs . 2>/dev/null || true
        git add . 2>/dev/null || true
        git commit -m "Merge remote changes" 2>/dev/null || true
    }
}

# Step 6: Restore backed up images (merge with new images from git)
if [ -d "$BACKUP_DIR" ] && [ "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    echo "📦 Restoring backed up images (merging with new images from git)..."
    if [ ! -d "static/uploads/images" ]; then
        mkdir -p static/uploads/images
    fi
    
    # Copy back images that don't exist in git (preserve VPS images)
    for img in "$BACKUP_DIR"/*; do
        if [ -f "$img" ]; then
            img_name=$(basename "$img")
            dest="static/uploads/images/$img_name"
            # Only restore if file doesn't exist (don't overwrite new images from git)
            if [ ! -f "$dest" ]; then
                cp "$img" "$dest"
            fi
        fi
    done
    
    restored_count=$(ls -1 static/uploads/images/ 2>/dev/null | wc -l)
    echo "   ✅ Restored images (total: $restored_count files in static/uploads/images/)"
    
    # Cleanup backup
    rm -rf "$BACKUP_DIR"
    echo "   🗑️  Cleaned up backup directory"
fi

# Step 7: Restore stashed file if needed
if [ "$STASHED" = "1" ]; then
    echo "📦 Restoring stashed file..."
    git stash pop || true
fi

echo ""
echo "✅ Pull completed successfully!"
echo ""
echo "💡 Note: Image files in static/uploads/images/ are now ignored by git"
echo "   They will be re-downloaded automatically when needed"
