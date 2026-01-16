# 📂 Đường dẫn Source Code trên VPS

Tài liệu này mô tả chi tiết cấu trúc đường dẫn của Flask project trên VPS.

## 🎯 Đường dẫn chính

### **Source Code Flask App**
```
/var/www/flask/nococo/
```

Đây là thư mục gốc chứa toàn bộ source code của Flask application.

---

## 📁 Cấu trúc chi tiết

```
/var/www/flask/nococo/
├── app.py                      # Flask application chính
├── requirements.txt            # Python dependencies
├── gunicorn_config.py          # Gunicorn configuration
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
│
├── venv/                       # Python virtual environment
│   ├── bin/
│   ├── lib/
│   └── ...
│
├── api/                        # API blueprints
│   ├── __init__.py
│   └── article_api.py
│
├── views/                      # View functions
│   ├── __init__.py
│   └── article_views.py
│
├── templates/                  # Jinja2 templates
│   └── 1.html
│
├── static/                     # Static files (CSS, JS, images)
│   ├── css/
│   │   ├── grid.css
│   │   ├── main.css
│   │   ├── colors.css
│   │   ├── sermitsiaq.css
│   │   └── ...
│   ├── js/
│   └── images/
│
├── logs/                       # Application logs
│   ├── access.log             # Gunicorn access log
│   └── error.log              # Gunicorn error log
│
└── deploy/                     # Deployment scripts & configs
    ├── nginx_flask_nococo.conf
    ├── setup_flask_nococo.sh
    └── DEPLOY_REPLACE_REACT.md
```

---

## 🔧 Các đường dẫn quan trọng khác

### **Nginx Configuration**
```
/etc/nginx/sites-available/nococo
```
File cấu hình Nginx cho domain `nococo.shop`

### **Nginx Logs**
```
/var/log/nginx/nococo_access.log
/var/log/nginx/nococo_error.log
```

### **Systemd Service**
```
/etc/systemd/system/flask-nococo.service
```
File service để quản lý Flask app với systemd

### **SSL Certificates**
```
/etc/letsencrypt/live/nococo.shop/
├── fullchain.pem
└── privkey.pem
```

---

## 📝 Chi tiết từng đường dẫn

### 1. **Source Code Root**
```bash
/var/www/flask/nococo/
```
- **Mục đích:** Chứa toàn bộ source code Flask
- **Owner:** `www-data:www-data`
- **Permissions:** `755`
- **Sử dụng trong:**
  - `setup_flask_nococo.sh`: `FLASK_DIR="/var/www/flask/nococo"`
  - `nginx_flask_nococo.conf`: Static files alias
  - `flask-nococo.service`: WorkingDirectory

### 2. **Static Files**
```bash
/var/www/flask/nococo/static/
```
- **Mục đích:** CSS, JS, images được serve trực tiếp bởi Nginx
- **Nginx config:** `location /static { alias /var/www/flask/nococo/static; }`
- **Subdirectories:**
  - `/var/www/flask/nococo/static/css/` - CSS files
  - `/var/www/flask/nococo/static/js/` - JavaScript files
  - `/var/www/flask/nococo/static/images/` - Image files

### 3. **Templates**
```bash
/var/www/flask/nococo/templates/
```
- **Mục đích:** Jinja2 HTML templates
- **File chính:** `1.html`

### 4. **Logs**
```bash
/var/www/flask/nococo/logs/
```
- **Mục đích:** Gunicorn application logs
- **Files:**
  - `access.log` - Access logs
  - `error.log` - Error logs
- **Config trong:** `gunicorn_config.py`

### 5. **Virtual Environment**
```bash
/var/www/flask/nococo/venv/
```
- **Mục đích:** Python virtual environment
- **Python executable:** `/var/www/flask/nococo/venv/bin/python`
- **Gunicorn:** `/var/www/flask/nococo/venv/bin/gunicorn`

---

## 🚀 Cách clone/upload code lên VPS

### **Cách 1: Clone từ GitHub**
```bash
# SSH vào VPS
ssh root@your-vps-ip

# Tạo thư mục
mkdir -p /var/www/flask/nococo
cd /var/www/flask/nococo

# Clone repository
git clone https://github.com/heneken1989/Flask_news.git .

# Hoặc clone vào thư mục tạm rồi copy
git clone https://github.com/heneken1989/Flask_news.git /tmp/flask-temp
cp -r /tmp/flask-temp/* /var/www/flask/nococo/
```

### **Cách 2: Upload từ local**
```bash
# Từ máy local
cd /Users/hien/Desktop/Projects/GC_HRAI/flask

# Tạo archive (loại bỏ venv, __pycache__)
tar -czf flask-app.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*.log' \
    .

# Upload lên VPS
scp flask-app.tar.gz root@your-vps-ip:/tmp/

# Trên VPS
ssh root@your-vps-ip
mkdir -p /var/www/flask/nococo
cd /var/www/flask/nococo
tar -xzf /tmp/flask-app.tar.gz
```

### **Cách 3: Sử dụng rsync (recommended)**
```bash
# Từ máy local
cd /Users/hien/Desktop/Projects/GC_HRAI/flask

rsync -avz --exclude 'venv' \
           --exclude '__pycache__' \
           --exclude '*.pyc' \
           --exclude '.git' \
           --exclude 'logs/*.log' \
           ./ root@your-vps-ip:/var/www/flask/nococo/
```

---

## ✅ Sau khi upload code

### **1. Cấp quyền**
```bash
chown -R www-data:www-data /var/www/flask/nococo
chmod -R 755 /var/www/flask/nococo
```

### **2. Tạo virtual environment**
```bash
cd /var/www/flask/nococo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **3. Chạy setup script**
```bash
cd /var/www/flask/nococo
sudo ./deploy/setup_flask_nococo.sh
```

---

## 🔍 Kiểm tra đường dẫn

### **Kiểm tra source code có tồn tại**
```bash
ls -la /var/www/flask/nococo/
```

### **Kiểm tra static files**
```bash
ls -la /var/www/flask/nococo/static/css/
```

### **Kiểm tra templates**
```bash
ls -la /var/www/flask/nococo/templates/
```

### **Kiểm tra logs**
```bash
ls -la /var/www/flask/nococo/logs/
```

### **Kiểm tra Nginx config**
```bash
grep "alias" /etc/nginx/sites-available/nococo
# Phải thấy: alias /var/www/flask/nococo/static;
```

### **Kiểm tra systemd service**
```bash
grep "WorkingDirectory" /etc/systemd/system/flask-nococo.service
# Phải thấy: WorkingDirectory=/var/www/flask/nococo
```

---

## 📊 So sánh với React (cũ)

| Component | React (Cũ) | Flask (Mới) |
|-----------|------------|-------------|
| **Source Code** | `/var/www/html/hrai/` | `/var/www/flask/nococo/` |
| **Static Files** | `/var/www/html/hrai/` | `/var/www/flask/nococo/static/` |
| **Nginx Config** | `/etc/nginx/sites-available/nococo` | `/etc/nginx/sites-available/nococo` (GIỮ NGUYÊN) |
| **SSL Cert** | `/etc/letsencrypt/live/nococo.shop/` | `/etc/letsencrypt/live/nococo.shop/` (GIỮ NGUYÊN) |
| **Service** | Không có (static files) | `/etc/systemd/system/flask-nococo.service` |

---

## 🎯 Tóm tắt

**Đường dẫn chính trên VPS:**
```
/var/www/flask/nococo/
```

**Các thư mục con quan trọng:**
- `static/` - Static files (CSS, JS, images)
- `templates/` - HTML templates
- `logs/` - Application logs
- `venv/` - Python virtual environment
- `api/` - API blueprints
- `views/` - View functions

**Các file config:**
- Nginx: `/etc/nginx/sites-available/nococo`
- Systemd: `/etc/systemd/system/flask-nococo.service`
- Gunicorn: `/var/www/flask/nococo/gunicorn_config.py`

