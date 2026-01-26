# 🔍 Debug Service Errors

## Kiểm tra logs chi tiết

```bash
# Xem logs chi tiết
sudo journalctl -xeu crawl_sections.service -n 100

# Hoặc
sudo journalctl -u crawl_sections.service -n 100 --no-pager

# Xem status
sudo systemctl status crawl_sections.service
```

## Các lỗi thường gặp

### 1. Lỗi Python/Import
```bash
# Test chạy script trực tiếp
cd /var/www/flask/nococo
/var/www/flask/nococo/venv/bin/python scripts/crawl_sections_multi_language.py --section all
```

### 2. Lỗi Permission
```bash
# Kiểm tra quyền
ls -la /var/www/flask/nococo/scripts/crawl_sections_multi_language.py
ls -la /var/www/flask/nococo/venv/bin/python

# Đảm bảo www-data có quyền
sudo chown -R www-data:www-data /var/www/flask/nococo
```

### 3. Lỗi Database Connection
```bash
# Kiểm tra .env file
cat /var/www/flask/nococo/.env | grep DATABASE_URL

# Test database connection
cd /var/www/flask/nococo
/var/www/flask/nococo/venv/bin/python -c "from app import app; from database import db; app.app_context().push(); print('DB OK')"
```

### 4. Lỗi Chrome/Chromium
```bash
# Kiểm tra Chrome
which chromium-browser || which chromium || which google-chrome

# Cài Chrome nếu chưa có
cd /var/www/flask/nococo/deploy
sudo bash install_chrome.sh
```

## Test từng bước

```bash
# 1. Test Python
/var/www/flask/nococo/venv/bin/python --version

# 2. Test import
cd /var/www/flask/nococo
/var/www/flask/nococo/venv/bin/python -c "import sys; sys.path.insert(0, '.'); from app import app; print('Import OK')"

# 3. Test script với dry-run
cd /var/www/flask/nococo
/var/www/flask/nococo/venv/bin/python scripts/crawl_sections_multi_language.py --section erhverv --max-articles 1
```

