# 📁 Setup view-resources Directory

Hướng dẫn setup thư mục `view-resources` để giữ nguyên đường dẫn trong HTML.

## 🎯 Vấn đề

File HTML có các đường dẫn như:
- `/view-resources/dachser2/public/sermitsiaq/logo.svg`
- `/view-resources/baseview/public/common/ClientAPI/index.js`
- `/view-resources/public/common/JWTCookie.js`
- v.v...

Tổng cộng có **13 đường dẫn** sử dụng `/view-resources/`.

## ✅ Giải pháp: Dùng Nginx Alias

Không cần thay đổi HTML, chỉ cần:
1. Tạo cấu trúc folder trên VPS
2. Copy files vào đó
3. Nginx đã được cấu hình để serve từ đó

---

## 📋 Các bước thực hiện

### **Bước 1: Tạo cấu trúc folder trên VPS**

```bash
# SSH vào VPS
ssh root@your-vps-ip

# Tạo cấu trúc folder
mkdir -p /var/www/flask/nococo/view-resources/dachser2/public/sermitsiaq
mkdir -p /var/www/flask/nococo/view-resources/baseview/public/common
mkdir -p /var/www/flask/nococo/view-resources/public/common

# Cấp quyền
chown -R www-data:www-data /var/www/flask/nococo/view-resources
chmod -R 755 /var/www/flask/nococo/view-resources
```

### **Bước 2: Copy files vào**

Bạn cần copy các files từ source cũ vào các thư mục tương ứng:

```bash
# Ví dụ: Copy logo.svg
# Từ source cũ (nếu có):
# scp /path/to/old/view-resources/dachser2/public/sermitsiaq/logo.svg \
#     root@your-vps:/var/www/flask/nococo/view-resources/dachser2/public/sermitsiaq/

# Hoặc tạo file trực tiếp trên VPS
cd /var/www/flask/nococo/view-resources
# Copy files vào đây
```

### **Bước 3: Kiểm tra Nginx config**

Nginx đã được cấu hình trong `nginx_flask_nococo.conf`:

```nginx
location /view-resources {
    alias /var/www/flask/nococo/view-resources;
    expires 30d;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

Nếu chưa có, thêm vào và reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### **Bước 4: Test**

```bash
# Test từ VPS
curl https://nococo.shop:8443/view-resources/dachser2/public/sermitsiaq/logo.svg

# Phải trả về nội dung file (hoặc 404 nếu file chưa có)
```

---

## 📂 Cấu trúc folder cần tạo

Dựa trên các đường dẫn trong HTML, bạn cần tạo:

```
/var/www/flask/nococo/view-resources/
├── dachser2/
│   └── public/
│       └── sermitsiaq/
│           ├── logo.svg
│           ├── 1-favicon.ico
│           ├── 1-favicon-16x16.png
│           ├── 1-favicon-32x32.png
│           ├── 1-android-chrome-192x192.png
│           ├── 1-android-chrome-512x512.png
│           └── 1-apple-touch-icon.png
├── baseview/
│   └── public/
│       └── common/
│           ├── ClientAPI/
│           │   └── index.js
│           ├── baseview/
│           │   └── moduleHandlers.js
│           └── build/
│               └── baseview_dependencies_dom.js
└── public/
    └── common/
        ├── JWTCookie.js
        └── Paywall.js
```

---

## 🔍 Danh sách files cần có

Dựa trên HTML, các files cần thiết:

1. **Favicons & Icons:**
   - `/view-resources/dachser2/public/sermitsiaq/1-favicon.ico`
   - `/view-resources/dachser2/public/sermitsiaq/1-favicon-16x16.png`
   - `/view-resources/dachser2/public/sermitsiaq/1-favicon-32x32.png`
   - `/view-resources/dachser2/public/sermitsiaq/1-android-chrome-192x192.png`
   - `/view-resources/dachser2/public/sermitsiaq/1-android-chrome-512x512.png`
   - `/view-resources/dachser2/public/sermitsiaq/1-apple-touch-icon.png`

2. **Logo:**
   - `/view-resources/dachser2/public/sermitsiaq/logo.svg` (2 chỗ dùng)

3. **JavaScript files:**
   - `/view-resources/baseview/public/common/ClientAPI/index.js`
   - `/view-resources/baseview/public/common/baseview/moduleHandlers.js`
   - `/view-resources/baseview/public/common/build/baseview_dependencies_dom.js`
   - `/view-resources/public/common/JWTCookie.js`
   - `/view-resources/public/common/Paywall.js`

---

## 🚀 Script tự động tạo cấu trúc

Tạo script để tự động tạo cấu trúc folder:

```bash
#!/bin/bash
# create_view_resources_structure.sh

BASE_DIR="/var/www/flask/nococo/view-resources"

# Tạo các thư mục
mkdir -p "$BASE_DIR/dachser2/public/sermitsiaq"
mkdir -p "$BASE_DIR/baseview/public/common/ClientAPI"
mkdir -p "$BASE_DIR/baseview/public/common/baseview"
mkdir -p "$BASE_DIR/baseview/public/common/build"
mkdir -p "$BASE_DIR/public/common"

# Cấp quyền
chown -R www-data:www-data "$BASE_DIR"
chmod -R 755 "$BASE_DIR"

echo "✅ Cấu trúc folder đã được tạo!"
echo "📂 Bây giờ copy files vào các thư mục tương ứng"
```

---

## ⚠️ Lưu ý

1. **Nếu không có files gốc:**
   - Có thể tạo placeholder files
   - Hoặc comment out các đường dẫn trong HTML
   - Hoặc thay đổi đường dẫn trong HTML để dùng Flask static

2. **Nếu muốn đơn giản hơn:**
   - Có thể thay đổi tất cả `/view-resources/` thành `/static/view-resources/` trong HTML
   - Sau đó copy files vào `/var/www/flask/nococo/static/view-resources/`

3. **Performance:**
   - Nginx serve trực tiếp nên rất nhanh
   - Files được cache 30 ngày

---

## 🔄 Alternative: Thay đổi HTML (nếu không có files gốc)

Nếu bạn không có các files gốc và muốn đơn giản hơn, có thể:

1. **Thay đổi đường dẫn trong HTML:**
   ```bash
   # Tìm và thay thế
   sed -i 's|/view-resources/|/static/view-resources/|g' templates/1.html
   ```

2. **Copy files vào Flask static:**
   ```bash
   mkdir -p /var/www/flask/nococo/static/view-resources
   # Copy files vào đây
   ```

3. **Flask sẽ tự động serve từ `/static/`**

---

## ✅ Checklist

- [ ] Tạo cấu trúc folder `/var/www/flask/nococo/view-resources/`
- [ ] Copy tất cả files cần thiết vào
- [ ] Cấp quyền `www-data:www-data`
- [ ] Kiểm tra Nginx config có `location /view-resources`
- [ ] Reload Nginx: `sudo systemctl reload nginx`
- [ ] Test: `curl https://nococo.shop:8443/view-resources/...`

