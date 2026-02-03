# 🚀 Deployment Guide - VPS Updates

Hướng dẫn deploy và update code trên VPS an toàn, giữ nguyên các files auto-generated.

---

## 📋 Files Cần Bảo Vệ

Các files này được tự động generate và **KHÔNG NÊN** bị ghi đè khi pull code:

1. **Home Layouts** (207-242KB mỗi file)
   - `scripts/home_layouts/home_layout_da.json`
   - `scripts/home_layouts/home_layout_kl.json`
   - `scripts/home_layouts/*.backup*`

2. **Sitemap Files** (124-136KB mỗi file)
   - `sitemap.xml`
   - `sitemap-DK.xml`
   - `sitemap-KL.xml`
   - `scripts/sitemap*.xml`

---

## ✅ OPTION 1: Safe Git Pull (RECOMMENDED)

**Khi nào dùng:** Update code thường xuyên, giữ nguyên auto-generated files.

### Sử dụng Script Tự Động:

```bash
cd /var/www/flask
./safe_git_pull.sh
```

**Script này sẽ:**
- ✅ Check trạng thái hiện tại
- ✅ Show preview những thay đổi
- ✅ Pull code mới
- ✅ Verify files auto-generated vẫn còn
- ✅ Hướng dẫn restart service

### Hoặc Manual:

```bash
cd /var/www/flask

# Fetch updates
git fetch origin

# Check what will change
git log HEAD..origin/main --oneline

# Pull (auto-generated files sẽ KHÔNG bị động vào vì đã gitignore)
git pull origin main

# Restart service
sudo systemctl restart sermitsiaq-flask.service
```

---

## ✅ OPTION 2: Safe Git Reset (Khi có conflict)

**Khi nào dùng:** Có conflict hoặc cần reset về trạng thái clean.

### Sử dụng Script Tự Động:

```bash
cd /var/www/flask
./safe_git_reset.sh
```

**Script này sẽ:**
- ✅ Backup auto-generated files vào `/tmp/`
- ✅ Reset về `origin/main`
- ✅ Restore lại các files đã backup
- ✅ Verify và report status

### Hoặc Manual:

```bash
cd /var/www/flask

# Backup layouts
cp -r scripts/home_layouts /tmp/home_layouts_backup

# Backup sitemaps
cp sitemap*.xml /tmp/

# Reset
git fetch origin
git reset --hard origin/main

# Restore
cp -r /tmp/home_layouts_backup/* scripts/home_layouts/
cp /tmp/sitemap*.xml .
```

---

## ✅ OPTION 3: Skip Worktree (Advanced)

**Khi nào dùng:** Muốn Git hoàn toàn bỏ qua một số files cụ thể.

```bash
cd /var/www/flask

# Đánh dấu files để Git skip
git update-index --skip-worktree scripts/home_layouts/home_layout_da.json
git update-index --skip-worktree scripts/home_layouts/home_layout_kl.json
git update-index --skip-worktree sitemap.xml
git update-index --skip-worktree sitemap-DK.xml
git update-index --skip-worktree sitemap-KL.xml

# Giờ pull bình thường
git pull origin main

# Check skip-worktree status
git ls-files -v | grep "^S"
```

**Undo skip-worktree:**
```bash
git update-index --no-skip-worktree <file>
```

---

## 🔄 Standard Deployment Workflow

### 1. **Development → Staging**

```bash
# Trên local
cd /Users/hien/Desktop/Projects/GC_HRAI/flask
git add .
git commit -m "Your commit message"
git push origin main
```

### 2. **Staging → Production VPS**

```bash
# SSH vào VPS
ssh user@your-vps-ip

# Navigate to project
cd /var/www/flask

# Option A: Safe pull (recommended)
./safe_git_pull.sh

# Option B: Manual pull
git pull origin main

# Restart service
sudo systemctl restart sermitsiaq-flask.service

# Check status
sudo systemctl status sermitsiaq-flask.service

# Check logs (nếu có lỗi)
sudo journalctl -u sermitsiaq-flask.service -f
```

---

## 🛡️ Verify Files After Deployment

```bash
# Check home layouts
ls -lh scripts/home_layouts/
# Expected: home_layout_da.json, home_layout_kl.json

# Check sitemaps
ls -lh sitemap*.xml
# Expected: sitemap.xml, sitemap-DK.xml, sitemap-KL.xml

# Check gitignore
cat .gitignore | grep -A 5 "Home layout"
# Should show: scripts/home_layouts/ and sitemap*.xml
```

---

## 🚨 Troubleshooting

### Problem: Files bị xóa sau git pull

**Nguyên nhân:** Files vẫn đang được tracked trong git (từ commit cũ)

**Giải pháp:**
```bash
# Check if files are tracked
git ls-files | grep -E "(home_layout|sitemap)"

# If tracked, untrack them
git rm --cached scripts/home_layouts/*.json
git rm --cached sitemap*.xml

# Verify .gitignore
grep -E "(home_layouts|sitemap)" .gitignore
```

### Problem: "Your local changes would be overwritten"

**Giải pháp 1:** Stash changes
```bash
git stash
git pull origin main
git stash pop
```

**Giải pháp 2:** Use safe_git_reset.sh
```bash
./safe_git_reset.sh
```

### Problem: Service không restart sau deploy

```bash
# Check service status
sudo systemctl status sermitsiaq-flask.service

# Check logs
sudo journalctl -u sermitsiaq-flask.service -n 50

# Manual restart
sudo systemctl restart sermitsiaq-flask.service

# Check if port is in use
sudo lsof -i :5000
```

---

## 📝 Regenerate Auto-Generated Files

Nếu files bị mất, regenerate chúng:

### Regenerate Home Layouts:
```bash
cd /var/www/flask
source venv/bin/activate
python scripts/link_home_articles.py
```

### Regenerate Sitemaps:
```bash
cd /var/www/flask
source venv/bin/activate
python scripts/generate_sitemaps.py
```

---

## 🎯 Best Practices

1. ✅ **Always use `safe_git_pull.sh`** cho production deployments
2. ✅ **Test trên local** trước khi push
3. ✅ **Check logs** sau mỗi deployment
4. ✅ **Backup database** trước major updates
5. ✅ **Monitor service status** sau restart
6. ❌ **NEVER** commit auto-generated files (đã có trong .gitignore)
7. ❌ **NEVER** use `git reset --hard` without backup

---

## 📞 Quick Reference

```bash
# Safe pull
./safe_git_pull.sh

# Safe reset
./safe_git_reset.sh

# Restart service
sudo systemctl restart sermitsiaq-flask.service

# Check logs
sudo journalctl -u sermitsiaq-flask.service -f

# Check process
ps aux | grep gunicorn
```

---

## 📚 Related Files

- `safe_git_pull.sh` - Safe pull script
- `safe_git_reset.sh` - Safe reset script
- `.gitignore` - Ignore rules
- `gunicorn_config.py` - Gunicorn config
- `DEPLOY_VPS.md` - Initial VPS setup guide
