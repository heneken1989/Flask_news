# 📁 view-resources Directory

Thư mục này chứa các static files (images, icons, JavaScript) được serve trực tiếp bởi Nginx với đường dẫn `/view-resources/`.

## 🎯 Mục đích

Giữ nguyên đường dẫn trong HTML gốc mà không cần thay đổi. Nginx sẽ map `/view-resources/` đến thư mục này.

## 📂 Cấu trúc folder

```
view-resources/
├── dachser2/
│   └── public/
│       └── sermitsiaq/
│           ├── logo.svg                    # Logo chính
│           ├── 1-favicon.ico               # Favicon
│           ├── 1-favicon-16x16.png
│           ├── 1-favicon-32x32.png
│           ├── 1-android-chrome-192x192.png
│           ├── 1-android-chrome-512x512.png
│           └── 1-apple-touch-icon.png
│
├── baseview/
│   └── public/
│       └── common/
│           ├── ClientAPI/
│           │   └── index.js
│           ├── baseview/
│           │   └── moduleHandlers.js
│           └── build/
│               └── baseview_dependencies_dom.js
│
└── public/
    └── common/
        ├── JWTCookie.js
        └── Paywall.js
```

## 📝 Danh sách files cần có

### **1. Images & Icons (dachser2/public/sermitsiaq/)**
- `logo.svg` - Logo chính (dùng ở 2 chỗ trong HTML)
- `1-favicon.ico` - Favicon
- `1-favicon-16x16.png` - Favicon 16x16
- `1-favicon-32x32.png` - Favicon 32x32
- `1-android-chrome-192x192.png` - Android icon 192x192
- `1-android-chrome-512x512.png` - Android icon 512x512
- `1-apple-touch-icon.png` - Apple touch icon

### **2. JavaScript Files (baseview/public/common/)**
- `ClientAPI/index.js` - Client API module
- `baseview/moduleHandlers.js` - Module handlers
- `build/baseview_dependencies_dom.js` - Dependencies DOM

### **3. Common JavaScript (public/common/)**
- `JWTCookie.js` - JWT Cookie handler
- `Paywall.js` - Paywall handler

## 🚀 Cách sử dụng

### **1. Copy files vào đây**

Copy các files từ source cũ vào các thư mục tương ứng:

```bash
# Ví dụ: Copy logo
cp /path/to/old/logo.svg view-resources/dachser2/public/sermitsiaq/

# Copy favicons
cp /path/to/old/*.ico view-resources/dachser2/public/sermitsiaq/
cp /path/to/old/*.png view-resources/dachser2/public/sermitsiaq/
```

### **2. Nginx sẽ tự động serve**

Nginx đã được cấu hình trong `deploy/nginx_flask_nococo.conf`:

```nginx
location /view-resources {
    alias /var/www/flask/nococo/view-resources;
    expires 30d;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

### **3. Test trên local (development)**

Khi chạy Flask local, bạn có thể:

**Option 1: Dùng Flask static folder**
- Copy `view-resources` vào `static/view-resources`
- Hoặc tạo symlink: `ln -s ../view-resources static/view-resources`

**Option 2: Dùng Nginx local**
- Cấu hình Nginx local để serve từ `view-resources/`

## ⚠️ Lưu ý

1. **Files này sẽ được commit vào Git** (trừ khi thêm vào `.gitignore`)
2. **Trên VPS**, files sẽ được copy vào `/var/www/flask/nococo/view-resources/`
3. **Nginx serve trực tiếp** nên rất nhanh, không qua Flask

## 📋 Checklist

- [ ] Tạo cấu trúc folder (đã có)
- [ ] Copy logo.svg vào `dachser2/public/sermitsiaq/`
- [ ] Copy favicons vào `dachser2/public/sermitsiaq/`
- [ ] Copy JavaScript files vào các thư mục tương ứng
- [ ] Test trên local
- [ ] Deploy lên VPS và copy files vào `/var/www/flask/nococo/view-resources/`

