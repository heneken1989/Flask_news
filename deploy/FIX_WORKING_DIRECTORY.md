# 🔧 Sửa Lỗi Working Directory

## ❌ Lỗi
```
crawl_sections.service: Changing to the requested working directory failed: No such file or directory
```

## ✅ Giải Pháp

### Bước 1: Kiểm tra thư mục có tồn tại không

```bash
# Kiểm tra thư mục
ls -la /var/www/flask/nococo

# Kiểm tra script có tồn tại không
ls -la /var/www/flask/nococo/scripts/crawl_sections_multi_language.py

# Kiểm tra venv
ls -la /var/www/flask/nococo/venv/bin/python
```

### Bước 2: Kiểm tra service file hiện tại

```bash
# Xem service file
sudo cat /etc/systemd/system/crawl_sections.service

# Kiểm tra WorkingDirectory
sudo systemctl cat crawl_sections.service | grep WorkingDirectory
```

### Bước 3: Sửa service file

```bash
# Mở service file
sudo nano /etc/systemd/system/crawl_sections.service
```

**Đảm bảo các dòng sau đúng:**

```ini
[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/var/www/flask/nococo
Environment="PATH=/var/www/flask/nococo/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/var/www/flask/nococo"
ExecStart=/var/www/flask/nococo/venv/bin/python /var/www/flask/nococo/scripts/crawl_sections_multi_language.py --section all
```

**Lưu ý:** 
- `WorkingDirectory` phải là đường dẫn tuyệt đối và tồn tại
- Không có dấu `/` ở cuối
- User `www-data` phải có quyền truy cập thư mục

### Bước 4: Hoặc dùng sed để sửa tự động

```bash
# Sửa WorkingDirectory
sudo sed -i 's|WorkingDirectory=.*|WorkingDirectory=/var/www/flask/nococo|g' /etc/systemd/system/crawl_sections.service

# Sửa PATH
sudo sed -i 's|Environment="PATH=.*|Environment="PATH=/var/www/flask/nococo/venv/bin:/usr/local/bin:/usr/bin:/bin"|g' /etc/systemd/system/crawl_sections.service

# Sửa PYTHONPATH
sudo sed -i 's|Environment="PYTHONPATH=.*|Environment="PYTHONPATH=/var/www/flask/nococo"|g' /etc/systemd/system/crawl_sections.service

# Sửa ExecStart
sudo sed -i 's|ExecStart=.*|ExecStart=/var/www/flask/nococo/venv/bin/python /var/www/flask/nococo/scripts/crawl_sections_multi_language.py --section all|g' /etc/systemd/system/crawl_sections.service
```

### Bước 5: Reload và test

```bash
# Reload systemd
sudo systemctl daemon-reload

# Kiểm tra lại service file
sudo systemctl cat crawl_sections.service

# Test chạy
sudo systemctl start crawl_sections.service

# Xem logs
journalctl -u crawl_sections.service -n 50
```

### Bước 6: Kiểm tra quyền

```bash
# Đảm bảo www-data có quyền truy cập
sudo chown -R www-data:www-data /var/www/flask/nococo

# Hoặc nếu user khác, thay www-data bằng user của bạn
```

## 🔍 Debug

Nếu vẫn lỗi, kiểm tra:

```bash
# 1. Kiểm tra thư mục có tồn tại
test -d /var/www/flask/nococo && echo "OK" || echo "NOT FOUND"

# 2. Kiểm tra quyền
sudo -u www-data ls /var/www/flask/nococo

# 3. Kiểm tra script có tồn tại
test -f /var/www/flask/nococo/scripts/crawl_sections_multi_language.py && echo "OK" || echo "NOT FOUND"

# 4. Kiểm tra Python
test -f /var/www/flask/nococo/venv/bin/python && echo "OK" || echo "NOT FOUND"
```

## ⚠️ Lưu ý

- Nếu path khác `/var/www/flask/nococo`, thay thế bằng path thực tế của bạn
- Đảm bảo không có trailing slash (`/`) ở cuối WorkingDirectory
- User trong service file phải có quyền truy cập thư mục

