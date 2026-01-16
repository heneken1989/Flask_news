# 🕷️ Crawl Service

Service để crawl articles từ sermitsiaq.ag sử dụng SeleniumBase.

## 📋 Cấu trúc

```
services/
├── __init__.py
├── crawl_service.py      # Main crawl service với SeleniumBase
├── article_parser.py     # Parser để extract data từ HTML
└── README.md
```

## 🚀 Sử dụng

### 1. Crawl một section

```bash
# Crawl section erhverv (mặc định)
python3 scripts/crawl_articles.py erhverv

# Crawl với số lượng articles tùy chỉnh
python3 scripts/crawl_articles.py erhverv --max-articles 100

# Crawl với browser visible (để debug)
python3 scripts/crawl_articles.py erhverv --no-headless

# Crawl section khác
python3 scripts/crawl_articles.py samfund
python3 scripts/crawl_articles.py kultur
python3 scripts/crawl_articles.py sport
python3 scripts/crawl_articles.py job

# Crawl custom URL
python3 scripts/crawl_articles.py erhverv --url "https://www.sermitsiaq.ag/tag/erhverv"
```

### 2. Sử dụng trong code

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

## 📊 Dữ liệu được crawl

Mỗi article sẽ được lưu với các thông tin:

- **element_guid**: GUID duy nhất từ website gốc
- **title**: Tiêu đề bài viết
- **slug**: URL slug
- **url**: URL đầy đủ
- **k5a_url**: URL cho K5A
- **section**: Section (erhverv, samfund, kultur, sport, job)
- **published_date**: Ngày publish
- **is_paywall**: Có phải paywall không
- **image_data**: Thông tin hình ảnh (JSON)
  - `desktop_webp`, `desktop_jpeg`
  - `mobile_webp`, `mobile_jpeg`
  - `fallback`
  - `width`, `height`, `alt`, `title`
- **display_order**: Thứ tự hiển thị (0, 1, 2, ...)

## 🖼️ Hình ảnh

**Không download hình ảnh** - chỉ lưu link từ website gốc:
- Tiết kiệm storage
- Đơn giản hơn
- Luôn có hình ảnh mới nhất từ CDN của họ

## 🔄 Logic crawl

1. Mở browser với SeleniumBase
2. Navigate đến section URL
3. Scroll để load thêm articles (lazy loading)
4. Parse HTML để extract article data
5. Lưu vào database:
   - Nếu article đã tồn tại (theo `element_guid`) → Update
   - Nếu chưa tồn tại → Create mới
6. Set `display_order` để match pattern 2-3-2-3-2-3...

## 📝 Lưu ý

1. **Cần database connection**: Đảm bảo `.env` có `DATABASE_URL` đúng
2. **SeleniumBase**: Cần cài đặt Chrome/Chromium
3. **Rate limiting**: Tránh crawl quá nhanh để không bị block
4. **Headless mode**: Mặc định chạy headless (không hiển thị browser)

## 🐛 Troubleshooting

### Browser không khởi động
```bash
# Cài đặt Chrome/Chromium
# Ubuntu/Debian:
sudo apt-get install chromium-browser

# macOS:
brew install --cask google-chrome
```

### Lỗi import
```bash
# Cài đặt dependencies
pip install -r requirements.txt
```

### Database connection error
```bash
# Kiểm tra .env file
cat .env | grep DATABASE_URL
```

