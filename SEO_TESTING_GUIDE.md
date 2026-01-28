# 🧪 Hướng Dẫn Kiểm Tra SEO Meta Tags

## 🔍 Cách 1: Kiểm tra trực tiếp trong Browser

### **View Page Source**
1. Mở trang web trong browser
2. Right-click → "View Page Source" (hoặc `Cmd+Option+U` trên Mac, `Ctrl+U` trên Windows)
3. Tìm các meta tags trong `<head>`:
   - `<title>`
   - `<meta name="description">`
   - `<meta property="og:title">`
   - `<meta property="og:image">`
   - `<link rel="canonical">`

### **Browser DevTools**
1. Mở DevTools (`F12` hoặc `Cmd+Option+I`)
2. Tab **Elements** → Tìm `<head>` section
3. Kiểm tra các meta tags có đúng không

### **Console Commands**
Mở Console trong DevTools và chạy:
```javascript
// Kiểm tra title
document.title

// Kiểm tra meta description
document.querySelector('meta[name="description"]')?.content

// Kiểm tra og:title
document.querySelector('meta[property="og:title"]')?.content

// Kiểm tra og:image
document.querySelector('meta[property="og:image"]')?.content

// Kiểm tra canonical
document.querySelector('link[rel="canonical"]')?.href

// Kiểm tra hreflang tags
Array.from(document.querySelectorAll('link[rel="alternate"][hreflang]')).map(link => ({
    lang: link.getAttribute('hreflang'),
    url: link.href
}))

// Kiểm tra structured data
JSON.parse(document.querySelector('script[type="application/ld+json"]')?.textContent || '[]')
```

## 🌐 Cách 2: Sử dụng Online Tools

### **1. Google Rich Results Test**
- URL: https://search.google.com/test/rich-results
- Kiểm tra: Structured Data (JSON-LD)
- Nhập URL của trang → Test → Xem kết quả

### **2. Facebook Sharing Debugger**
- URL: https://developers.facebook.com/tools/debug/
- Kiểm tra: Open Graph tags
- Nhập URL → Debug → Xem preview và meta tags

### **3. Twitter Card Validator**
- URL: https://cards-dev.twitter.com/validator
- Kiểm tra: Twitter Card tags
- Nhập URL → Preview Card

### **4. LinkedIn Post Inspector**
- URL: https://www.linkedin.com/post-inspector/
- Kiểm tra: Open Graph tags cho LinkedIn

### **5. Schema.org Validator**
- URL: https://validator.schema.org/
- Kiểm tra: JSON-LD structured data
- Paste JSON-LD code hoặc URL

### **6. SEO Checker Tools**
- **Screaming Frog SEO Spider**: Crawl website và check meta tags
- **SEMrush Site Audit**: Kiểm tra SEO issues
- **Ahrefs Site Audit**: Kiểm tra technical SEO

## 🐍 Cách 3: Tạo Script Test (Python)

Tạo script để tự động test:

```python
# flask/scripts/test_seo_meta.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def test_seo_meta(url, expected_title=None, expected_description=None):
    """
    Test SEO meta tags của một URL
    """
    print(f"\n{'='*60}")
    print(f"🔍 Testing SEO for: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Test title
        title = soup.find('title')
        if title:
            print(f"✅ Title: {title.text[:80]}...")
            if expected_title and expected_title.lower() not in title.text.lower():
                print(f"⚠️  WARNING: Title không khớp với expected: {expected_title}")
        else:
            print("❌ ERROR: Không tìm thấy <title> tag")
        
        # Test meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')
            print(f"✅ Meta Description: {desc[:80]}...")
            if len(desc) > 160:
                print(f"⚠️  WARNING: Description quá dài ({len(desc)} chars, nên < 160)")
            if expected_description and expected_description.lower() not in desc.lower():
                print(f"⚠️  WARNING: Description không khớp")
        else:
            print("❌ ERROR: Không tìm thấy meta description")
        
        # Test og:title
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if og_title:
            print(f"✅ OG Title: {og_title.get('content', '')[:80]}...")
        else:
            print("❌ ERROR: Không tìm thấy og:title")
        
        # Test og:image
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image:
            img_url = og_image.get('content', '')
            print(f"✅ OG Image: {img_url[:80]}...")
            # Check if image URL is accessible
            if img_url.startswith('http'):
                img_response = requests.head(img_url, timeout=5)
                if img_response.status_code == 200:
                    print(f"   ✅ Image accessible")
                else:
                    print(f"   ⚠️  WARNING: Image không accessible (status: {img_response.status_code})")
        else:
            print("❌ ERROR: Không tìm thấy og:image")
        
        # Test canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            print(f"✅ Canonical: {canonical.get('href', '')}")
        else:
            print("❌ ERROR: Không tìm thấy canonical URL")
        
        # Test hreflang
        hreflangs = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
        if hreflangs:
            print(f"✅ Hreflang tags ({len(hreflangs)}):")
            for hreflang in hreflangs:
                print(f"   - {hreflang.get('hreflang')}: {hreflang.get('href')}")
        else:
            print("⚠️  WARNING: Không tìm thấy hreflang tags")
        
        # Test structured data
        json_ld = soup.find('script', attrs={'type': 'application/ld+json'})
        if json_ld:
            import json
            try:
                data = json.loads(json_ld.string)
                print(f"✅ Structured Data: {len(data) if isinstance(data, list) else 1} schema(s)")
                if isinstance(data, list):
                    for schema in data:
                        print(f"   - {schema.get('@type', 'Unknown')}")
                else:
                    print(f"   - {data.get('@type', 'Unknown')}")
            except:
                print("⚠️  WARNING: Structured data không parse được")
        else:
            print("❌ ERROR: Không tìm thấy structured data (JSON-LD)")
        
        print(f"\n{'='*60}")
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == '__main__':
    # Test home page
    test_seo_meta('http://localhost:5000/', 
                  expected_title='Sermitsiaq',
                  expected_description='Grønlands største nyhedssite')
    
    # Test article page (thay bằng article URL thực tế)
    # test_seo_meta('http://localhost:5000/samfund/article-slug/12345')
```

## 📋 Checklist Kiểm Tra

### **Home Page** (`/`)
- [ ] Title = "Sermitsiaq - Grønlands største nyhedssite"
- [ ] Description có chứa "Sermitsiaq"
- [ ] og:type = "website"
- [ ] og:image có default image
- [ ] Canonical URL đúng
- [ ] Có hreflang tags (da, kl, en)
- [ ] Có WebSite schema trong JSON-LD

### **Article Page** (`/<section>/<slug>/<id>`)
- [ ] Title = article.title (từ database)
- [ ] Description = article.excerpt (từ database)
- [ ] og:type = "article"
- [ ] og:image = article.image_data (từ database)
- [ ] og:url = article.published_url
- [ ] Canonical URL = article.published_url
- [ ] article:published_time có đúng không
- [ ] article:author có đúng không
- [ ] article:section có đúng không
- [ ] article:tag có đúng tags không
- [ ] Có hreflang tags với translations
- [ ] Có NewsArticle schema trong JSON-LD

### **Section Page** (`/tag/<section>`)
- [ ] Title có section name
- [ ] Description có section description
- [ ] og:type = "website"
- [ ] Canonical URL đúng

## 🔧 Quick Test Script

Tạo script đơn giản để test nhanh:

```bash
# Test một URL
curl -s "http://localhost:5000/" | grep -o '<title>.*</title>'
curl -s "http://localhost:5000/" | grep -o 'meta name="description" content="[^"]*"'
curl -s "http://localhost:5000/" | grep -o 'property="og:title" content="[^"]*"'
```

## 🎯 Các Lỗi Thường Gặp

### **1. Meta tags không hiển thị**
- ✅ Check xem view có pass `seo_meta` vào template không
- ✅ Check xem `base.html` có sử dụng macro đúng không
- ✅ Check xem có fallback về `head.html` cũ không

### **2. Title/Description không đúng**
- ✅ Check xem `article.title` và `article.excerpt` có data trong DB không
- ✅ Check xem `get_seo_meta()` có lấy đúng data không

### **3. Image không hiển thị**
- ✅ Check xem `article.image_data` có format đúng không
- ✅ Check xem image URL có accessible không

### **4. Hreflang không có**
- ✅ Check xem article có translations không (canonical_id)
- ✅ Check xem translations có `published_url` không

### **5. Structured data lỗi**
- ✅ Check xem JSON-LD có valid JSON không
- ✅ Test bằng Schema.org Validator

## 📊 Monitoring

Sau khi deploy, monitor bằng:
1. **Google Search Console** - Xem indexing và errors
2. **Google Analytics** - Track organic traffic
3. **Facebook Insights** - Xem sharing performance
4. **Twitter Analytics** - Xem card performance

