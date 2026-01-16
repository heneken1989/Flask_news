# Hướng dẫn Thay thế React bằng Flask trên VPS

Hướng dẫn chi tiết để thay thế React app bằng Flask app trên VPS, **giữ nguyên Nginx và SSL** đã cấu hình.

## 📋 Thông tin cấu hình

**Domain:** `nococo.shop`  
**Ports:** 
- HTTP: `8080` → Redirect to HTTPS
- HTTPS: `8443` (SSL)
**SSL Certificate:** `/etc/letsencrypt/live/nococo.shop/`  
**Nginx Config:** `/etc/nginx/sites-available/nococo` (hoặc tên file bạn đang dùng)

## 🔄 So sánh: React vs Flask

### React (Cũ)
- Nginx serve static files từ `/var/www/html/hrai`
- Không cần backend process
- Build output là HTML/CSS/JS files

### Flask (Mới)
- Flask app chạy trên port 5000 (Gunicorn)
- Nginx proxy requests đến Flask trên port 8443
- Static files vẫn serve từ Nginx (nhanh hơn)

## 📝 Các bước thực hiện

### Bước 1: Chuẩn bị trên máy local

#### 1.1. Copy Flask project lên VPS

```bash
# Từ máy local
cd /Users/hien/Desktop/Projects/GC_HRAI/flask

# Tạo archive
tar -czf flask-app.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='logs' \
    .

# Upload lên VPS
scp flask-app.tar.gz root@your-vps-ip:/tmp/
```

---

### Bước 2: Setup trên VPS

#### 2.1. SSH vào VPS

```bash
ssh root@your-vps-ip
```

#### 2.2. Tạo thư mục cho Flask app

```bash
# Tạo thư mục
mkdir -p /var/www/flask/nococo
mkdir -p /var/www/flask/nococo/logs

# Cấp quyền
chown -R www-data:www-data /var/www/flask/nococo
chmod -R 755 /var/www/flask/nococo
```

#### 2.3. Extract Flask project

```bash
# Extract từ archive
cd /var/www/flask/nococo
tar -xzf /tmp/flask-app.tar.gz

# Hoặc clone từ Git (nếu có)
# git clone your-repo-url .
```

#### 2.4. Setup Python virtual environment

```bash
cd /var/www/flask/nococo

# Cài Python 3 và pip nếu chưa có
apt update
apt install -y python3 python3-pip python3-venv

# Tạo virtual environment
python3 -m venv venv

# Activate và install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2.5. Kiểm tra static files

```bash
# Đảm bảo static files có trong thư mục
ls -la /var/www/flask/nococo/static/css/
# Phải thấy: grid.css, main.css, colors.css, etc.
```

---

### Bước 3: Cập nhật Nginx config

#### 3.1. Backup config cũ (React)

```bash
# Tìm file config hiện tại (có thể là nococo hoặc tên khác)
ls -la /etc/nginx/sites-available/ | grep nococo

# Backup config cũ
cp /etc/nginx/sites-available/nococo /etc/nginx/sites-available/nococo.react.backup
# Hoặc nếu tên file khác:
# cp /etc/nginx/sites-available/your-config-file /etc/nginx/sites-available/your-config-file.react.backup
```

#### 3.2. Copy config mới (Flask)

**Cách 1: Upload file config**

```bash
# Upload file nginx_flask_nococo.conf lên VPS
scp deploy/nginx_flask_nococo.conf root@your-vps-ip:/tmp/

# Trên VPS, copy vào sites-available
cp /tmp/nginx_flask_nococo.conf /etc/nginx/sites-available/nococo
```

**Cách 2: Edit trực tiếp**

```bash
# Edit file config
nano /etc/nginx/sites-available/nococo
```

**Thay đổi phần `location /` từ:**
```nginx
location / {
    try_files $uri $uri/ /index.html;
    # ...
}
```

**Thành:**
```nginx
# Serve static files
location /static {
    alias /var/www/flask/nococo/static;
    expires 30d;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# Proxy to Flask
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
```

**Xóa phần cache static assets cũ:**
```nginx
# XÓA phần này (không cần nữa vì đã có /static location)
# location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
#     expires 1y;
#     ...
# }
```

#### 3.3. Test và reload Nginx

```bash
# Test config
nginx -t

# Nếu OK, reload
systemctl reload nginx
```

---

### Bước 4: Setup Flask app với Gunicorn

#### 4.1. Tạo systemd service

```bash
nano /etc/systemd/system/flask-nococo.service
```

**Paste nội dung:**

```ini
[Unit]
Description=Flask Nococo App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/flask/nococo
Environment="PATH=/var/www/flask/nococo/venv/bin"
ExecStart=/var/www/flask/nococo/venv/bin/gunicorn -c gunicorn_config.py app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4.2. Khởi động service

```bash
# Reload systemd
systemctl daemon-reload

# Start service
systemctl start flask-nococo

# Enable auto-start
systemctl enable flask-nococo

# Kiểm tra status
systemctl status flask-nococo
```

#### 4.3. Kiểm tra logs

```bash
# Xem logs
journalctl -u flask-nococo -f

# Hoặc
tail -f /var/www/flask/nococo/logs/error.log
```

---

### Bước 5: Kiểm tra và test

#### 5.1. Kiểm tra Flask app đang chạy

```bash
# Kiểm tra port 5000
netstat -tlnp | grep 5000
# Hoặc
ss -tlnp | grep 5000

# Test local
curl http://localhost:5000
```

#### 5.2. Test qua Nginx

```bash
# Test từ VPS
curl https://localhost:8443 -k

# Hoặc từ máy local
curl https://nococo.shop:8443
```

#### 5.3. Kiểm tra static files

```bash
# Test CSS file
curl https://nococo.shop:8443/static/css/grid.css

# Phải trả về nội dung CSS
```

---

### Bước 6: (Optional) Dừng React app

Nếu React app đang chạy (PM2, systemd, etc.):

```bash
# Nếu dùng PM2
pm2 stop all
pm2 delete all

# Nếu dùng systemd
systemctl stop react-app  # (nếu có)
systemctl disable react-app
```

**Lưu ý:** Không cần xóa static files cũ ngay, có thể giữ để backup.

---

## 🔍 Troubleshooting

### Lỗi 502 Bad Gateway

**Nguyên nhân:** Flask app chưa chạy hoặc sai port

```bash
# Kiểm tra Flask app
systemctl status flask-nococo

# Kiểm tra port
netstat -tlnp | grep 5000

# Xem logs
journalctl -u flask-nococo -n 50
```

### Lỗi 404 cho static files

**Nguyên nhân:** Đường dẫn static files sai

```bash
# Kiểm tra đường dẫn trong Nginx config
grep "alias" /etc/nginx/sites-available/nococo

# Phải là: alias /var/www/flask/nococo/static;

# Kiểm tra files có tồn tại
ls -la /var/www/flask/nococo/static/css/
```

### SSL Certificate không load

**Nguyên nhân:** Đường dẫn SSL sai

```bash
# Kiểm tra SSL cert
ls -la /etc/letsencrypt/live/nococo.shop/

# Phải có: fullchain.pem và privkey.pem

# Test SSL
openssl s_client -connect nococo.shop:8443
```

### Permission denied

**Nguyên nhân:** Quyền truy cập sai

```bash
# Fix permissions
chown -R www-data:www-data /var/www/flask/nococo
chmod -R 755 /var/www/flask/nococo
```

---

## ✅ Checklist hoàn thành

- [ ] Flask project đã upload lên VPS
- [ ] Virtual environment đã setup
- [ ] Dependencies đã install (`pip install -r requirements.txt`)
- [ ] Static files có trong `/var/www/flask/nococo/static/`
- [ ] Nginx config đã cập nhật (`/etc/nginx/sites-available/nococo`)
- [ ] Nginx đã reload (`systemctl reload nginx`)
- [ ] Flask service đã tạo (`/etc/systemd/system/flask-nococo.service`)
- [ ] Flask service đã start (`systemctl start flask-nococo`)
- [ ] Flask service đã enable (`systemctl enable flask-nococo`)
- [ ] Test thành công: `curl https://nococo.shop:8443`
- [ ] Test static files: `curl https://nococo.shop:8443/static/css/grid.css`
- [ ] SSL certificate vẫn hoạt động

---

## 📊 So sánh đường dẫn

### React (Cũ)
```
Static files: /var/www/html/hrai/
Nginx config: /etc/nginx/sites-available/nococo
SSL cert:     /etc/letsencrypt/live/nococo.shop/
Port:         8080 (HTTP) → 8443 (HTTPS)
```

### Flask (Mới)
```
Flask app:    /var/www/flask/nococo/
Static files: /var/www/flask/nococo/static/
Nginx config: /etc/nginx/sites-available/nococo (GIỮ NGUYÊN)
SSL cert:     /etc/letsencrypt/live/nococo.shop/ (GIỮ NGUYÊN)
Port:         8080 (HTTP) → 8443 (HTTPS) (GIỮ NGUYÊN)
```

**Thay đổi duy nhất:** 
- Thư mục Flask app: `/var/www/flask/nococo/`
- Cách Nginx serve: từ static files → proxy đến Flask

---

## 🎯 Tóm tắt

1. **Giữ nguyên:**
   - ✅ Domain: `nococo.shop`
   - ✅ SSL certificate: `/etc/letsencrypt/live/nococo.shop/`
   - ✅ Ports: `8080` (HTTP) và `8443` (HTTPS)
   - ✅ Nginx config path
   - ✅ Backend API proxy (`/api/`, `/leave/`, `/ws/`)

2. **Thay đổi:**
   - ❌ Từ `/var/www/html/hrai` → `/var/www/flask/nococo`
   - ❌ Từ serve static → proxy đến Flask
   - ❌ Thêm Flask service (Gunicorn)

3. **Kết quả:**
   - ✅ Website chạy Flask thay vì React
   - ✅ SSL vẫn hoạt động
   - ✅ Domain không đổi
   - ✅ Ports không đổi
   - ✅ Backend API vẫn hoạt động

