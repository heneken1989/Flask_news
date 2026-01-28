# ✅ SEO Checklist cho Google

## 🎯 Đã hoàn thành

### 1. **Meta Tags**
- ✅ Dynamic `<title>` từ database
- ✅ Dynamic `<meta name="description">` từ database
- ✅ Canonical URLs với domain `.com`
- ✅ Open Graph tags (og:title, og:description, og:image, og:url, og:locale)
- ✅ Twitter Card tags
- ✅ Article meta tags (published_time, modified_time, author, tags, section)

### 2. **Hreflang Tags**
- ✅ Hreflang cho đa ngôn ngữ (da, kl, en)
- ✅ x-default hreflang

### 3. **Structured Data (JSON-LD)**
- ✅ NewsArticle schema cho article pages
- ✅ WebSite schema cho tất cả pages
- ✅ Organization schema trong NewsArticle (publisher)

### 4. **Sitemaps**
- ✅ `/sitemap.xml` - English
- ✅ `/sitemap-DK.xml` - Danish
- ✅ `/sitemap-KL.xml` - Greenlandic
- ✅ `/sitemap_news.xml` - Google News sitemap

### 5. **Technical SEO**
- ✅ Language attributes trong `<html>` tag
- ✅ Image URLs với domain `.com`
- ✅ Mobile-responsive (CSS đã có)

## 🔧 Cần bổ sung

### 1. **Robots.txt** ✅
- ✅ Đã có route `/robots.txt` trong Flask app
- ✅ Include tất cả sitemaps
- ✅ Disallow admin và login pages

### 2. **Google Search Console**
- ⚠️ Cần verify domain trong Google Search Console
- ⚠️ Submit sitemaps vào Google Search Console:
  - `https://www.sermitsiaq.com/sitemap.xml`
  - `https://www.sermitsiaq.com/sitemap-DK.xml`
  - `https://www.sermitsiaq.com/sitemap-KL.xml`
  - `https://www.sermitsiaq.com/sitemap_news.xml`

### 3. **Structured Data (Optional - nâng cao)**
- ⚠️ BreadcrumbList schema (cho navigation)
- ⚠️ Organization schema riêng (ngoài NewsArticle)
- ⚠️ Article schema với full content (nếu cần)

### 4. **Performance & Core Web Vitals**
- ⚠️ Kiểm tra PageSpeed Insights
- ⚠️ Optimize images (đã có WebP, có thể cần lazy loading)
- ⚠️ Minify CSS/JS (có thể đã có)

### 5. **Security & HTTPS**
- ✅ Domain `.com` (HTTPS sẽ được setup)
- ⚠️ SSL certificate (cần setup trên server)

## 📋 Hành động tiếp theo

### Ngay lập tức:
1. ✅ **Tạo robots.txt** - Đã implement (xem `flask/app.py`)
2. ⚠️ **Submit sitemaps** vào Google Search Console
3. ⚠️ **Verify domain** trong Google Search Console

### Sau khi deploy:
1. ⚠️ Test tất cả sitemaps: `/sitemap.xml`, `/sitemap-DK.xml`, `/sitemap-KL.xml`, `/sitemap_news.xml`
2. ⚠️ Test robots.txt: `/robots.txt`
3. ⚠️ Verify structured data bằng Google Rich Results Test
4. ⚠️ Check mobile-friendly bằng Google Mobile-Friendly Test

## 🔗 Links hữu ích

- **Google Search Console:** https://search.google.com/search-console
- **Rich Results Test:** https://search.google.com/test/rich-results
- **Mobile-Friendly Test:** https://search.google.com/test/mobile-friendly
- **PageSpeed Insights:** https://pagespeed.web.dev/

