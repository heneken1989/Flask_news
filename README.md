# Flask Article Project

Dự án Flask để hiển thị articles sử dụng template HTML từ `1.html`, thay thế React frontend.

## 📁 Cấu trúc dự án

```
flask/
├── app.py                      # Flask application chính
├── requirements.txt            # Python dependencies
├── gunicorn_config.py          # Gunicorn configuration
├── api/
│   ├── __init__.py
│   └── article_api.py          # API endpoints cho articles
├── views/
│   ├── __init__.py
│   └── article_views.py        # View functions và blueprints
├── templates/
│   └── 1.html                  # Main HTML template
├── static/
│   ├── css/                    # CSS files
│   ├── js/                     # JavaScript files
│   └── images/                 # Image files
└── deploy/
    ├── nginx_flask_nococo.conf # Nginx config cho nococo.shop
    ├── setup_flask_nococo.sh   # Auto setup script
    └── DEPLOY_REPLACE_REACT.md # Hướng dẫn deploy
```

## 🚀 Setup Local

1. **Clone repository:**
```bash
git clone https://github.com/heneken1989/Flask_news.git
cd Flask_news
```

2. **Tạo virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows
```

3. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

4. **Chạy ứng dụng:**
```bash
python app.py
```

5. **Truy cập:** http://localhost:5000

## 🌐 Deploy lên VPS

Xem chi tiết trong: [`deploy/DEPLOY_REPLACE_REACT.md`](deploy/DEPLOY_REPLACE_REACT.md)

**Quick setup:**
```bash
# Upload project lên VPS
scp -r flask/* root@your-vps:/var/www/flask/nococo/

# Chạy setup script
ssh root@your-vps
cd /var/www/flask/nococo
sudo ./deploy/setup_flask_nococo.sh
```

## 📝 Notes

- **Domain:** nococo.shop (Port 8080/8443)
- **SSL:** Let's Encrypt certificate
- **Server:** Gunicorn + Nginx reverse proxy
- **Static files:** Served directly by Nginx for better performance

## 🔧 Configuration

- **Nginx:** `deploy/nginx_flask_nococo.conf`
- **Gunicorn:** `gunicorn_config.py`
- **Flask routes:** `app.py` và `views/article_views.py`

## 📚 API Endpoints

API endpoints sẽ được implement trong `api/article_api.py` (coming soon).

