# 🚀 Quick Start - Deploy Flask App lên VPS

Hướng dẫn nhanh để deploy Flask app lên VPS sau khi clone từ GitHub.

## ✅ Yêu cầu

- VPS đã có Nginx và SSL certificate (hoặc script sẽ tự cài)
- Quyền root/sudo
- Domain: `nococo.shop` (hoặc cập nhật config)

---

## 📋 Các bước thực hiện

### **Bước 1: Clone code từ GitHub**

```bash
# SSH vào VPS
ssh root@your-vps-ip

# Tạo thư mục và clone
mkdir -p /var/www/flask/nococo
cd /var/www/flask/nococo
git clone https://github.com/heneken1989/Flask_news.git .
```

### **Bước 2: Chạy script setup**

```bash
# Chạy script với quyền root
cd /var/www/flask/nococo
sudo chmod +x deploy/setup_flask_nococo.sh
sudo ./deploy/setup_flask_nococo.sh
```

**Vậy là xong!** 🎉

Script sẽ tự động:
- ✅ Tạo thư mục và cấp quyền
- ✅ Setup Python virtual environment
- ✅ Cài đặt dependencies
- ✅ Cấu hình Nginx
- ✅ Enable Nginx site
- ✅ Tạo systemd service
- ✅ Khởi động Flask app

---

## 🔍 Kiểm tra sau khi setup

### **1. Kiểm tra Flask app đang chạy**
```bash
systemctl status flask-nococo
```

### **2. Kiểm tra logs**
```bash
# Xem logs real-time
journalctl -u flask-nococo -f

# Hoặc xem logs file
tail -f /var/www/flask/nococo/logs/error.log
```

### **3. Test website**
```bash
# Test local
curl http://localhost:5000

# Test qua Nginx
curl https://nococo.shop:8443

# Test static files
curl https://nococo.shop:8443/static/css/grid.css
```

### **4. Kiểm tra Nginx**
```bash
# Test config
nginx -t

# Xem status
systemctl status nginx

# Xem logs
tail -f /var/log/nginx/nococo_error.log
```

---

## 🛠️ Quản lý Service

### **Start/Stop/Restart**
```bash
# Start
sudo systemctl start flask-nococo

# Stop
sudo systemctl stop flask-nococo

# Restart
sudo systemctl restart flask-nococo

# Reload (không downtime)
sudo systemctl reload flask-nococo
```

### **Xem logs**
```bash
# Systemd logs
journalctl -u flask-nococo -f

# Application logs
tail -f /var/www/flask/nococo/logs/error.log
tail -f /var/www/flask/nococo/logs/access.log
```

---

## 🔄 Update code mới

Khi có code mới từ GitHub:

```bash
cd /var/www/flask/nococo

# Pull code mới
git pull

# Restart service
sudo systemctl restart flask-nococo
```

**Nếu có thay đổi dependencies:**
```bash
cd /var/www/flask/nococo
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart flask-nococo
```

---

## ❌ Troubleshooting

### **Lỗi: Flask project not found**
```bash
# Kiểm tra code đã clone chưa
ls -la /var/www/flask/nococo/app.py

# Nếu chưa có, clone lại
cd /var/www/flask/nococo
git clone https://github.com/heneken1989/Flask_news.git .
```

### **Lỗi: Service failed to start**
```bash
# Xem logs chi tiết
journalctl -u flask-nococo -n 50

# Kiểm tra Python environment
cd /var/www/flask/nococo
source venv/bin/activate
python app.py  # Test chạy trực tiếp
```

### **Lỗi: Nginx config test failed**
```bash
# Test config
nginx -t

# Xem lỗi chi tiết
cat /var/log/nginx/error.log
```

### **Lỗi: Permission denied**
```bash
# Fix permissions
sudo chown -R www-data:www-data /var/www/flask/nococo
sudo chmod -R 755 /var/www/flask/nococo
```

### **Lỗi: Port 5000 already in use**
```bash
# Kiểm tra process đang dùng port 5000
sudo lsof -i :5000

# Kill process nếu cần
sudo kill -9 <PID>
```

---

## 📊 Tóm tắt đường dẫn

| Component | Path |
|-----------|------|
| **Source Code** | `/var/www/flask/nococo/` |
| **Static Files** | `/var/www/flask/nococo/static/` |
| **Logs** | `/var/www/flask/nococo/logs/` |
| **Nginx Config** | `/etc/nginx/sites-available/nococo` |
| **Systemd Service** | `/etc/systemd/system/flask-nococo.service` |

---

## 🎯 Checklist hoàn thành

Sau khi chạy script, kiểm tra:

- [ ] Flask service đang chạy: `systemctl status flask-nococo`
- [ ] Nginx đang chạy: `systemctl status nginx`
- [ ] Website accessible: `curl https://nococo.shop:8443`
- [ ] Static files load được: `curl https://nococo.shop:8443/static/css/grid.css`
- [ ] Logs không có lỗi: `journalctl -u flask-nococo -n 20`

---

## 📚 Tài liệu thêm

- Chi tiết đường dẫn: [`PATHS_VPS.md`](PATHS_VPS.md)
- Hướng dẫn deploy đầy đủ: [`DEPLOY_REPLACE_REACT.md`](DEPLOY_REPLACE_REACT.md)

