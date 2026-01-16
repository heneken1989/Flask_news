# Hướng dẫn Deploy Flask App lên VPS

## Đường dẫn Static Files

### Cách 1: Dùng Flask url_for() (Đã cấu hình - Khuyến nghị)

Đường dẫn hiện tại trong `1.html` đã đúng:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/grid.css') }}">
```

**Ưu điểm:**
- Tự động tạo đường dẫn đúng dựa trên cấu hình Flask
- Hoạt động trên cả local và VPS
- Tự động xử lý base URL

**Khi chạy trên VPS:**
- Nếu chạy trực tiếp: `http://your-domain:5000/static/css/grid.css`
- Nếu dùng Nginx reverse proxy: `http://your-domain/static/css/grid.css`

### Cách 2: Dùng đường dẫn tuyệt đối (Không khuyến nghị)

Nếu muốn hardcode (không khuyến nghị):
```html
<link rel="stylesheet" href="/static/css/grid.css">
```

## Cấu hình cho Production trên VPS

### 1. Cấu hình Flask app.py cho Production

```python
from flask import Flask, render_template, jsonify
from api.article_api import article_bp
from views.article_views import article_view_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(article_bp, url_prefix='/api')
app.register_blueprint(article_view_bp)

if __name__ == '__main__':
    # Production: Dùng Gunicorn thay vì app.run()
    # app.run(debug=True, port=5000)  # Chỉ dùng cho development
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### 2. Cấu hình Nginx (Khuyến nghị cho Production)

Tạo file `/etc/nginx/sites-available/flask-app`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Serve static files trực tiếp từ Nginx (nhanh hơn)
    location /static {
        alias /path/to/your/flask/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy requests đến Flask app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Lưu ý:** Thay `/path/to/your/flask/static` bằng đường dẫn thực tế trên VPS.

### 3. Cấu hình Gunicorn (Production WSGI Server)

Tạo file `gunicorn_config.py`:

```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
```

Chạy với Gunicorn:
```bash
gunicorn -c gunicorn_config.py app:app
```

### 4. Systemd Service (Tự động khởi động)

Tạo file `/etc/systemd/system/flask-app.service`:

```ini
[Unit]
Description=Flask Article App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/flask
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/gunicorn -c gunicorn_config.py app:app

[Install]
WantedBy=multi-user.target
```

Khởi động service:
```bash
sudo systemctl daemon-reload
sudo systemctl start flask-app
sudo systemctl enable flask-app
```

## Kết luận

**Đường dẫn hiện tại đã đúng!** `url_for('static', filename='css/grid.css')` sẽ tự động:
- Tạo đường dẫn `/static/css/grid.css` khi chạy trực tiếp
- Hoạt động với Nginx reverse proxy
- Tự động xử lý base URL nếu có subdirectory

**Không cần thay đổi gì trong template**, chỉ cần đảm bảo:
1. Static files nằm trong thư mục `static/`
2. Cấu hình Nginx đúng (nếu dùng)
3. Flask app chạy đúng port

