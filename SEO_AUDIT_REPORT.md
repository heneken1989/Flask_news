# 🔍 SEO Audit Report - Base HTML Header

## ⚠️ Vấn đề hiện tại

### 1. **Meta tags bị hardcoded trong `head.html`**
- File `flask/templates/partials/head.html` có dữ liệu mẫu hardcoded
- Tất cả các trang đều hiển thị cùng một title, description, og:image
- Không có logic động để set meta tags theo từng trang/article

### 2. **Thiếu meta tags động**
- ❌ Title không động (chỉ có trong `article_detail.html`)
- ❌ Description không động
- ❌ og:image không động
- ❌ og:url không động
- ❌ Canonical URL không động
- ❌ Thiếu hreflang tags cho đa ngôn ngữ (da, kl, en)
- ❌ Thiếu meta robots
- ❌ Thiếu structured data (JSON-LD) động

### 3. **Vấn đề đa ngôn ngữ**
- ❌ Không có `hreflang` tags để chỉ định language versions
- ❌ `lang` attribute trong `<html>` luôn là `da-DK` (không động)

## ✅ Cần cải thiện

### 1. **Meta tags cơ bản**
- ✅ `<title>` - Động theo từng trang
- ✅ `<meta name="description">` - Động theo từng trang
- ✅ `<meta name="keywords">` - Từ tags của article
- ✅ `<link rel="canonical">` - URL chính xác của trang

### 2. **Open Graph (Facebook, LinkedIn)**
- ✅ `og:title` - Động
- ✅ `og:description` - Động
- ✅ `og:image` - Động từ `article.image_data`
- ✅ `og:url` - Động
- ✅ `og:type` - `article` cho article pages, `website` cho home
- ✅ `og:locale` - Động theo language (da_DK, kl_GL, en_US)

### 3. **Twitter Cards**
- ✅ `twitter:card` - `summary_large_image`
- ✅ `twitter:title` - Động
- ✅ `twitter:description` - Động
- ✅ `twitter:image` - Động

### 4. **Đa ngôn ngữ (hreflang)**
- ✅ `<link rel="alternate" hreflang="da" href="...">`
- ✅ `<link rel="alternate" hreflang="kl" href="...">`
- ✅ `<link rel="alternate" hreflang="en" href="...">`
- ✅ `<link rel="alternate" hreflang="x-default" href="...">`

### 5. **Structured Data (JSON-LD)**
- ✅ NewsArticle schema cho article pages
- ✅ WebSite schema cho home page
- ✅ BreadcrumbList schema
- ✅ Organization schema

### 6. **Meta tags khác**
- ✅ `<meta name="robots">` - `index, follow` hoặc `noindex, nofollow`
- ✅ `<meta name="author">` - Từ article author
- ✅ `<meta property="article:published_time">` - Động
- ✅ `<meta property="article:modified_time">` - Động
- ✅ `<meta property="article:author">` - Động
- ✅ `<meta property="article:tag">` - Từ article tags

## 📋 Đề xuất giải pháp

### Option 1: Tạo template variables trong views
- Set `seo_meta` dict trong mỗi view
- Pass vào template và render động

### Option 2: Tạo helper function
- Function `get_seo_meta(article, language, request)` 
- Trả về dict với tất cả meta tags
- Sử dụng trong template

### Option 3: Tạo Jinja2 macro
- Macro `render_seo_meta()` trong template
- Nhận parameters và render tất cả meta tags

## 🎯 Ưu tiên

1. **HIGH**: Title, Description, og:image, og:url, canonical
2. **MEDIUM**: hreflang, og:locale, structured data
3. **LOW**: Meta robots, author, keywords

