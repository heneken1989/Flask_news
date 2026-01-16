# 🔧 Fix Git Ownership Error trên VPS

Khi gặp lỗi `fatal: detected dubious ownership in repository`, đây là cách xử lý.

## ❌ Lỗi

```bash
fatal: detected dubious ownership in repository at '/var/www/flask/nococo'
To add an exception for this directory, call:
    git config --global --add safe.directory /var/www/flask/nococo
```

## ✅ Giải pháp

### **Cách 1: Thêm exception (Nhanh)**

```bash
# Chạy lệnh này với quyền root
git config --global --add safe.directory /var/www/flask/nococo

# Sau đó pull lại
git pull origin main
```

### **Cách 2: Fix ownership (Khuyến nghị)**

Fix ownership để www-data sở hữu repository:

```bash
# Fix ownership của toàn bộ thư mục
chown -R www-data:www-data /var/www/flask/nococo

# Sau đó pull với user www-data hoặc dùng sudo -u
sudo -u www-data git pull origin main
```

**Hoặc nếu muốn root sở hữu:**

```bash
chown -R root:root /var/www/flask/nococo
git pull origin main
```

### **Cách 3: Clone lại với ownership đúng**

Nếu vẫn gặp vấn đề, clone lại:

```bash
# Backup (nếu cần)
cp -r /var/www/flask/nococo /var/www/flask/nococo.backup

# Xóa và clone lại
rm -rf /var/www/flask/nococo
cd /var/www/flask
git clone https://github.com/heneken1989/Flask_news.git nococo

# Fix ownership
chown -R www-data:www-data /var/www/flask/nococo
```

## 🎯 Khuyến nghị

**Sử dụng Cách 2** vì:
- ✅ Đảm bảo ownership đúng (www-data)
- ✅ Không cần thêm exception
- ✅ An toàn hơn
- ✅ Phù hợp với cấu hình systemd service (chạy với www-data)

## 📝 Script tự động

Tạo script để fix ownership và pull:

```bash
#!/bin/bash
# fix_git_and_pull.sh

cd /var/www/flask/nococo

# Fix ownership
chown -R www-data:www-data /var/www/flask/nococo

# Pull với www-data
sudo -u www-data git pull origin main

# Nếu có thay đổi dependencies
sudo -u www-data bash -c "cd /var/www/flask/nococo && source venv/bin/activate && pip install -r requirements.txt"

# Restart service
systemctl restart flask-nococo
```

## ⚠️ Lưu ý

1. **Nếu dùng www-data**, phải dùng `sudo -u www-data` khi chạy git commands
2. **Nếu dùng root**, có thể chạy trực tiếp nhưng cần fix ownership sau
3. **Trên production**, nên dùng www-data để đảm bảo security

## 🔄 Workflow đề xuất

```bash
# 1. Pull code (với user phù hợp)
cd /var/www/flask/nococo
sudo -u www-data git pull origin main

# 2. Update dependencies nếu cần
sudo -u www-data bash -c "cd /var/www/flask/nococo && source venv/bin/activate && pip install -r requirements.txt"

# 3. Restart service
sudo systemctl restart flask-nococo

# 4. Check logs
sudo journalctl -u flask-nococo -f
```

