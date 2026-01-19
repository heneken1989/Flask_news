# Hướng dẫn thiết lập Cloudflare CDN cho Flask App

## Tổng quan

Cloudflare CDN sẽ tự động cache và phân phối static files (CSS, JS, images) từ các edge servers gần người dùng, giúp tăng tốc độ tải trang đáng kể.

## ✅ Những gì KHÔNG cần config trong dự án

**Tin tốt:** Hầu hết chỉ cần config ở Cloudflare dashboard, **KHÔNG cần thay đổi code Flask**.

Flask app hiện tại đã đúng:
- ✅ Dùng `url_for('static', filename='...')` - tự động tạo URL đúng
- ✅ Static files nằm trong `/static/` folder
- ✅ Nginx đã config serve static files trực tiếp

## 🔧 Config cần thiết ở Cloudflare Dashboard

### 1. Thêm Domain vào Cloudflare

1. Đăng ký/đăng nhập Cloudflare
2. Add Site → Nhập domain của bạn
3. Cloudflare sẽ scan DNS records
4. Update nameservers theo hướng dẫn của Cloudflare

### 2. Cấu hình Caching Rules

**Vào Cloudflare Dashboard → Caching → Configuration:**

#### A. Caching Level
- **Setting:** Standard hoặc Aggressive
- **Mục đích:** Cache static files lâu hơn

#### B. Browser Cache TTL
- **Setting:** Respect Existing Headers (khuyến nghị)
- **Hoặc:** 4 hours, 1 day, 1 week (tùy nhu cầu)

#### C. Purge Cache
- Có thể purge cache khi cần update static files

### 3. Cấu hình Page Rules (Quan trọng!)

**Vào Cloudflare Dashboard → Rules → Page Rules:**

Tạo các rules sau:

#### Rule 1: Cache Static Files Aggressively
```
URL Pattern: *your-domain.com/static/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 1 month
```

#### Rule 2: Bypass Cache cho Dynamic Content
```
URL Pattern: *your-domain.com/api/*
Settings:
  - Cache Level: Bypass
```

#### Rule 3: Bypass Cache cho HTML Pages (nếu cần)
```
URL Pattern: *your-domain.com/article/*
Settings:
  - Cache Level: Standard
  - Edge Cache TTL: 2 hours
```

### 4. Cấu hình Auto Minify (Tùy chọn)

**Vào Cloudflare Dashboard → Speed → Optimization:**

- ✅ Auto Minify: JavaScript, CSS, HTML
- **Lưu ý:** Chỉ bật nếu static files chưa được minify

### 5. Cấu hình Compression

**Vào Cloudflare Dashboard → Speed → Optimization:**

- ✅ Brotli: ON (tự động nén tốt hơn gzip)
- ✅ Gzip: ON (fallback cho browsers cũ)

## 🔧 Config tùy chọn trong dự án (Không bắt buộc)

### Option 1: Thêm Cache Headers trong Nginx (Khuyến nghị)

Cập nhật `nginx.conf` để thêm cache headers cho static files:

```nginx
location /static {
    alias /path/to/your/flask/static;
    
    # Cache headers cho Cloudflare
    expires 30d;
    add_header Cache-Control "public, max-age=2592000, immutable";
    add_header Vary "Accept-Encoding";
    
    # Gzip compression (Cloudflare sẽ tự động nén, nhưng có thể giúp)
    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
    
    # CORS nếu cần
    add_header Access-Control-Allow-Origin *;
}
```

### Option 2: Thêm Cache Headers trong Flask (Không khuyến nghị)

Nếu không dùng Nginx, có thể thêm trong Flask:

```python
@app.after_request
def add_cache_headers(response):
    """Add cache headers for static files"""
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 2592000  # 30 days
        response.cache_control.public = True
        response.cache_control.immutable = True
    return response
```

**Lưu ý:** Không khuyến nghị vì Nginx đã xử lý tốt hơn.

### Option 3: Versioning Static Files (Nâng cao)

Để force browser reload khi update static files, có thể thêm version:

```python
# Trong app.py hoặc config
STATIC_VERSION = '1.0.0'  # Tăng version khi update

# Trong template
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}?v={{ STATIC_VERSION }}">
```

**Lưu ý:** Cloudflare sẽ tự động cache theo URL, nên versioning sẽ tự động invalidate cache.

## 📊 Kiểm tra CDN hoạt động

### 1. Kiểm tra Headers

Sau khi config Cloudflare, kiểm tra headers:

```bash
curl -I https://your-domain.com/static/css/main.css
```

Kết quả mong đợi:
```
HTTP/2 200
cache-control: public, max-age=2592000
cf-cache-status: HIT  # ← Cloudflare đã cache
cf-ray: xxxxx-XXX  # ← Cloudflare edge server
server: cloudflare
```

### 2. Kiểm tra từ Browser

1. Mở DevTools (F12)
2. Tab Network
3. Reload trang
4. Xem static files:
   - **Size:** Sẽ nhỏ hơn (đã nén)
   - **Time:** Sẽ nhanh hơn (từ edge server)
   - **Headers:** Có `cf-cache-status: HIT`

### 3. Test từ nhiều locations

Dùng tools như:
- https://www.webpagetest.org/
- https://tools.keycdn.com/speed

Kiểm tra tốc độ từ nhiều locations khác nhau.

## 🚀 Tối ưu hóa thêm

### 1. Enable HTTP/2 và HTTP/3

**Cloudflare Dashboard → Network:**
- ✅ HTTP/2: ON (mặc định)
- ✅ HTTP/3 (QUIC): ON (nếu muốn)

### 2. Enable Image Optimization

**Cloudflare Dashboard → Speed → Optimization:**
- ✅ Polish: ON (tự động optimize images)
- ✅ Mirage: ON (lazy load images)

### 3. Enable Rocket Loader

**Cloudflare Dashboard → Speed → Optimization:**
- ✅ Rocket Loader: ON (tải JavaScript async)

**Lưu ý:** Test kỹ vì có thể conflict với một số JavaScript.

## ⚠️ Lưu ý quan trọng

### 1. Cache Invalidation

Khi update static files:
- **Option 1:** Purge cache trong Cloudflare Dashboard
- **Option 2:** Dùng versioning (thêm `?v=1.0.1` vào URL)
- **Option 3:** Đổi tên file (không khuyến nghị)

### 2. Dynamic Content

**KHÔNG cache:**
- API endpoints (`/api/*`)
- HTML pages với dynamic content (nếu cần real-time)
- User-specific content

**CÓ THỂ cache:**
- Static files (CSS, JS, images)
- Public HTML pages (với TTL ngắn)

### 3. SSL/TLS

Cloudflare tự động cung cấp SSL certificate:
- **SSL/TLS mode:** Full (strict) - khuyến nghị
- **Automatic HTTPS Rewrites:** ON

### 4. Real IP Address

Nếu cần log real IP của users, config Nginx:

```nginx
# Thêm vào location / block
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 131.0.72.0/22;
real_ip_header CF-Connecting-IP;
```

Hoặc dùng Cloudflare IP ranges từ: https://www.cloudflare.com/ips/

## 📝 Checklist

- [ ] Domain đã được add vào Cloudflare
- [ ] Nameservers đã được update
- [ ] SSL/TLS mode: Full (strict)
- [ ] Page Rules đã config cho `/static/*`
- [ ] Cache Level: Cache Everything cho static files
- [ ] Browser Cache TTL: 1 month
- [ ] Auto Minify: ON (nếu cần)
- [ ] Brotli/Gzip: ON
- [ ] Nginx cache headers đã config (tùy chọn)
- [ ] Test headers với `curl -I`
- [ ] Test từ browser DevTools
- [ ] Purge cache khi cần update files

## 🎯 Kết luận

**TL;DR:**
- ✅ **KHÔNG cần thay đổi code Flask** - app hiện tại đã đúng
- ✅ **Chỉ cần config ở Cloudflare Dashboard** - chủ yếu là Page Rules
- ✅ **Tùy chọn:** Thêm cache headers trong Nginx để tối ưu hơn
- ✅ **Test:** Kiểm tra headers và tốc độ sau khi config

Cloudflare sẽ tự động:
- Cache static files
- Compress content (Brotli/Gzip)
- Serve từ edge servers gần nhất
- Protect DDoS attacks
- Provide SSL certificate

**Không cần thay đổi gì trong Flask app!** 🎉

