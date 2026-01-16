# 🕷️ Hướng Dẫn Crawl Articles

## 📋 Tổng Quan

Service crawl sử dụng **SeleniumBase** để crawl articles từ [sermitsiaq.ag](https://www.sermitsiaq.ag) và lưu vào PostgreSQL database.

## 🖼️ Về Hình Ảnh

**Không download hình ảnh** - chỉ lưu link từ website gốc:
- ✅ Tiết kiệm storage
- ✅ Đơn giản hơn
- ✅ Luôn có hình ảnh mới nhất từ CDN của họ
- ✅ Không cần quản lý file upload

Hình ảnh được lưu trong `image_data` (JSON) với các link:
- `desktop_webp`, `desktop_jpeg`
- `mobile_webp`, `mobile_jpeg`
- `fallback`

## 🚀 Cài Đặt

### 1. Cài đặt dependencies

```bash
cd flask
pip install -r requirements.txt
```

### 2. Cài đặt Chrome/Chromium (cho SeleniumBase)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y chromium-browser
```

**macOS:**
```bash
brew install --cask google-chrome
```

**Hoặc dùng Chromium:**
```bash
brew install --cask chromium
```

## 📝 Sử Dụng

### Crawl section erhverv (mặc định)

```bash
python3 scripts/crawl_articles.py erhverv
```

### Crawl với tùy chọn

```bash
# Crawl 100 articles
python3 scripts/crawl_articles.py erhverv --max-articles 100

# Crawl với browser visible (để debug)
python3 scripts/crawl_articles.py erhverv --no-headless

# Crawl section khác
python3 scripts/crawl_articles.py samfund
python3 scripts/crawl_articles.py kultur
python3 scripts/crawl_articles.py sport
python3 scripts/crawl_articles.py job
```

### Crawl từ Python code

```python
from app import app
from services.crawl_service import SermitsiaqCrawler

with app.app_context():
    crawler = SermitsiaqCrawler()
    
    try:
        crawler.start_browser(headless=True)
        result = crawler.crawl_section(
            section_url='https://www.sermitsiaq.ag/tag/erhverv',
            section_name='erhverv',
            max_articles=50
        )
        print(result)
    finally:
        crawler.close_browser()
```

## 📊 Dữ Liệu Được Crawl

Mỗi article sẽ có:

- ✅ **element_guid**: GUID duy nhất (dùng để check duplicate)
- ✅ **title**: Tiêu đề
- ✅ **slug**: URL slug
- ✅ **url**: URL đầy đủ
- ✅ **k5a_url**: URL cho K5A
- ✅ **section**: Section (erhverv, samfund, kultur, sport, job)
- ✅ **published_date**: Ngày publish
- ✅ **is_paywall**: Có phải paywall không
- ✅ **image_data**: Thông tin hình ảnh (JSON) - **chỉ link, không download**
- ✅ **display_order**: Thứ tự hiển thị (0, 1, 2, ...) - **quan trọng cho pattern 2-3-2-3-2-3...**

## 🔄 Logic Crawl

1. **Mở browser** với SeleniumBase (headless mode)
2. **Navigate** đến section URL (ví dụ: `https://www.sermitsiaq.ag/tag/erhverv`)
3. **Scroll** để load thêm articles (lazy loading)
4. **Parse HTML** để extract article data:
   - Tìm tất cả `<article>` elements
   - Extract: title, URL, image, paywall, date, etc.
5. **Lưu vào database**:
   - Nếu article đã tồn tại (theo `element_guid`) → **Update**
   - Nếu chưa tồn tại → **Create mới**
6. **Set `display_order`** để match pattern 2-3-2-3-2-3...

## 📁 Cấu Trúc Files

```
flask/
├── services/
│   ├── __init__.py
│   ├── crawl_service.py      # Main crawl service
│   ├── article_parser.py     # Parser HTML
│   └── README.md
├── scripts/
│   └── crawl_articles.py     # Script chạy crawl
└── CRAWL_GUIDE.md            # File này
```

## ⚙️ Cấu Hình

### Database Connection

Đảm bảo `.env` có `DATABASE_URL`:

```env
DATABASE_URL=postgresql://flask_user:password@localhost/flask_news
```

### Crawl Settings

Trong `crawl_service.py`, có thể tùy chỉnh:
- `max_scrolls`: Số lần scroll tối đa (default: 10)
- `scroll_pause`: Thời gian chờ giữa các lần scroll (default: 2 giây)

## 🐛 Troubleshooting

### Browser không khởi động

```bash
# Kiểm tra Chrome/Chromium
which google-chrome
which chromium-browser

# Cài đặt nếu chưa có
sudo apt-get install chromium-browser  # Ubuntu/Debian
brew install --cask google-chrome      # macOS
```

### Lỗi import

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Kiểm tra Python path
python3 -c "import sys; print(sys.path)"
```

### Database connection error

```bash
# Kiểm tra .env
cat .env | grep DATABASE_URL

# Test connection
python3 -c "from app import app, db; app.app_context().push(); print('✅ Connected!')"
```

### Không crawl được articles

1. **Kiểm tra network**: Đảm bảo có thể truy cập `https://www.sermitsiaq.ag`
2. **Chạy với `--no-headless`**: Để xem browser có load được không
3. **Kiểm tra HTML structure**: Website có thể đã thay đổi cấu trúc

## 📝 Lưu Ý

1. **Rate limiting**: Tránh crawl quá nhanh để không bị block
2. **Respect robots.txt**: Nên check robots.txt trước khi crawl
3. **Update logic**: Nếu website thay đổi cấu trúc HTML, cần update parser
4. **Display order**: Quan trọng để match pattern 2-3-2-3-2-3... trong UI

## ✅ Sau Khi Crawl

Sau khi crawl xong, articles sẽ tự động hiển thị trên trang chủ (`/`) với pattern 2-3-2-3-2-3...

Xem articles:
```bash
# Query từ database
python3 -c "from app import app, db; from database import Article; app.app_context().push(); print(f'Total articles: {Article.query.count()}')"
```

