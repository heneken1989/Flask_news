# 🔧 Sửa Lỗi: Service Paths

## ❌ Lỗi
```
crawl_sections.service: Changing to the requested working directory failed: No such file or directory
```

## ✅ Giải Pháp

### Cách 1: Sửa trực tiếp service file (Nhanh nhất)

```bash
# 1. Kiểm tra path thực tế trên VPS
cd /var/www/flask/nococo
pwd  # Sẽ hiển thị: /var/www/flask/nococo

# 2. Kiểm tra venv path
ls -la venv/bin/python  # Sẽ hiển thị: /var/www/flask/nococo/venv/bin/python

# 3. Sửa service file
sudo nano /etc/systemd/system/crawl_sections.service
```

Cập nhật các dòng sau:

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

**Lưu ý:** Thay `/var/www/flask/nococo` bằng path thực tế trên VPS của bạn nếu khác.

### Cách 2: Chạy lại setup script (Tự động)

```bash
cd /var/www/flask/nococo/deploy
sudo bash setup_crawler_service.sh
```

Script sẽ tự động detect và cập nhật paths.

### Cách 3: Sử dụng sed để thay thế tự động

```bash
# Thay thế paths trong service file
sudo sed -i 's|/path/to/GC_HRAI/flask|/var/www/flask/nococo|g' /etc/systemd/system/crawl_sections.service
sudo sed -i 's|/path/to/venv|/var/www/flask/nococo/venv|g' /etc/systemd/system/crawl_sections.service

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart crawl_sections.timer
```

## ✅ Kiểm Tra Sau Khi Sửa

```bash
# 1. Kiểm tra service file đã đúng chưa
sudo systemctl cat crawl_sections.service

# 2. Test chạy thủ công
sudo systemctl start crawl_sections.service

# 3. Xem logs
journalctl -u crawl_sections.service -n 50

# 4. Kiểm tra timer
systemctl status crawl_sections.timer
```

## 🔍 Tìm Path Thực Tế

Nếu không chắc path, chạy các lệnh sau:

```bash
# Tìm thư mục flask
find /var/www -name "crawl_sections_multi_language.py" 2>/dev/null

# Hoặc
find /home -name "crawl_sections_multi_language.py" 2>/dev/null

# Hoặc
find /opt -name "crawl_sections_multi_language.py" 2>/dev/null

# Tìm venv
find /var/www -name "python" -path "*/venv/bin/python" 2>/dev/null
```

## 📝 Ví Dụ Service File Đúng

```ini
[Unit]
Description=Sermitsiaq Multi-Language Crawler Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/var/www/flask/nococo
Environment="PATH=/var/www/flask/nococo/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/var/www/flask/nococo"
ExecStart=/var/www/flask/nococo/venv/bin/python /var/www/flask/nococo/scripts/crawl_sections_multi_language.py --section all
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crawl_sections

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Restart policy (only on failure)
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

## ⚠️ Lưu Ý

- Đảm bảo user `www-data` có quyền truy cập thư mục `/var/www/flask/nococo`
- Đảm bảo venv path đúng và Python có thể chạy
- Sau khi sửa, luôn chạy `sudo systemctl daemon-reload`

