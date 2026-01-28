# 📊 Nguồn Data Cho SEO Meta Tags

## ✅ Hiện tại: Dùng data từ các field hiện có trong database

### **Article Model - Các field dùng cho SEO:**

| SEO Meta Tag | Database Field | Ghi chú |
|-------------|----------------|---------|
| **Title** | `article.title` | ✅ Dùng trực tiếp |
| **Description** | `article.excerpt` | ✅ Dùng trực tiếp (không có field `description`) |
| **Image (og:image)** | `article.image_data` | ✅ Lấy từ JSON: `desktop_jpeg` hoặc `desktop_webp` |
| **URL (canonical)** | `article.published_url` | ✅ Dùng trực tiếp (hoặc `published_url_en` cho EN) |
| **Published Time** | `article.published_date` | ✅ Format: ISO 8601 + 'Z' |
| **Modified Time** | `article.updated_at` | ✅ Format: ISO 8601 + 'Z' |
| **Author** | `article.layout_data['author']` | ✅ Lấy từ JSON field `layout_data` |
| **Tags** | `article.layout_data['tags']` | ✅ Lấy từ JSON field `layout_data` (array) |
| **Section** | `article.section` | ✅ Dùng cho `article:section` |
| **Language** | `article.language` | ✅ Dùng cho hreflang và og:locale |

### **Hreflang URLs:**
- Query từ database: Tìm tất cả translations của article (qua `canonical_id`)
- Lấy `published_url` của mỗi translation để tạo hreflang tags

## ❓ Có cần thêm field riêng cho SEO không?

### **Option 1: KHÔNG cần thêm field (Khuyến nghị)**
- ✅ Dùng `title` và `excerpt` hiện có → Đủ cho SEO
- ✅ Đơn giản, không cần migration
- ✅ Data nhất quán giữa hiển thị và SEO

### **Option 2: Thêm field riêng (Nếu cần customize)**
Nếu muốn SEO title/description khác với title/excerpt hiển thị:

```python
# Thêm vào Article model:
seo_title = db.Column(db.String(500))  # SEO title (có thể khác title)
seo_description = db.Column(db.Text)    # SEO description (có thể khác excerpt)
seo_keywords = db.Column(db.String(500)) # Keywords riêng cho SEO
```

**Khi nào cần:**
- SEO title cần ngắn hơn/khác với title hiển thị
- SEO description cần tối ưu riêng (khác excerpt)
- Cần keywords riêng cho SEO

## 📋 Mapping trong `utils_seo.py`

```python
# Title
seo_title = article.title  # ← Từ DB: article.title

# Description  
seo_description = article.excerpt  # ← Từ DB: article.excerpt

# Image
image_url = article.image_data.get('desktop_jpeg')  # ← Từ DB: article.image_data (JSON)

# URL
seo_url = article.published_url  # ← Từ DB: article.published_url

# Author
author = article.layout_data.get('author')  # ← Từ DB: article.layout_data (JSON)

# Tags
tags = article.layout_data.get('tags', [])  # ← Từ DB: article.layout_data (JSON)

# Dates
published_time = article.published_date.isoformat() + 'Z'  # ← Từ DB: article.published_date
modified_time = article.updated_at.isoformat() + 'Z'  # ← Từ DB: article.updated_at
```

## 🎯 Kết luận

**Hiện tại: KHÔNG cần thêm field riêng cho SEO**

- Tất cả data cần thiết đã có trong database
- `title` và `excerpt` đủ tốt cho SEO
- Chỉ cần implement logic trong `utils_seo.py` để lấy và format data

**Chỉ thêm field riêng nếu:**
- Cần SEO title/description khác với title/excerpt hiển thị
- Cần customize riêng cho từng article

