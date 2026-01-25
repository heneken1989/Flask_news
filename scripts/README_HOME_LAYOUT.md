# Home Layout Crawl Flow (Mới)

Flow mới để crawl và link home articles, tránh duplicate và crawl lại nội dung đã có.

## 🎯 Mục Tiêu

- **Chỉ crawl layout structure** (published_url, layout_type, display_order)
- **Link với articles đã có** trong DB (từ khi crawl các tag/section)
- **Chỉ update metadata**, không tạo articles mới
- **Nhanh hơn, hiệu quả hơn** so với flow cũ

## 📋 Flow

```
1. Crawl home page → Parse layout structure
   ↓
2. Lưu layout structure (JSON) hoặc dùng trực tiếp
   ↓
3. Link articles đã có trong DB với layout
   ↓
4. Update metadata: display_order, layout_type, is_home, section
```

## 🚀 Cách Sử Dụng

### Bước 1: Crawl Layout Structure

```bash
# Crawl DA home layout và lưu vào file
python scripts/crawl_home_layout.py --language da --save

# Crawl KL home layout
python scripts/crawl_home_layout.py --language kl --url https://kl.sermitsiaq.ag --save

# Crawl với no-headless để debug
python scripts/crawl_home_layout.py --language da --no-headless --save
```

**Output:** File JSON trong `scripts/home_layouts/home_layout_{language}_{timestamp}.json`

### Bước 2: Link Articles với Layout

```bash
# Link từ file layout đã crawl
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_20240101_120000.json --language da

# Hoặc crawl và link trực tiếp (không lưu file)
python scripts/link_home_articles.py --crawl --language da

# Dry run (chỉ log, không update)
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_20240101_120000.json --language da --dry-run
```

## 📊 Layout Structure Format

File JSON có format:

```json
{
  "language": "da",
  "crawled_at": "2024-01-01T12:00:00",
  "total_items": 50,
  "layout_items": [
    {
      "published_url": "https://www.sermitsiaq.ag/samfund/article/1234567",
      "layout_type": "1_full",
      "display_order": 0,
      "row_index": 0,
      "article_index_in_row": 0,
      "total_rows": 10,
      "grid_size": 12,
      "layout_data": {},
      "element_guid": "...",
      "k5a_url": "..."
    },
    {
      "published_url": "",
      "layout_type": "slider",
      "display_order": 1000,
      "row_index": 1,
      "slider_title": "NYHEDER",
      "slider_articles": [
        {
          "published_url": "https://www.sermitsiaq.ag/...",
          "title": "...",
          "image_data": {...}
        }
      ]
    }
  ]
}
```

## 🔍 Logic Link

### Articles thông thường (có published_url):

1. Tìm article trong DB bằng `published_url`
2. Nếu tìm thấy:
   - Update: `display_order`, `layout_type`, `layout_data`, `grid_size`
   - Set: `is_home=True`, `section='home'`
3. Nếu không tìm thấy:
   - Log warning (không tạo mới)

### Slider containers:

1. Tìm slider container bằng `(layout_type, display_order)`
2. Nếu tìm thấy:
   - Update metadata
3. Nếu không tìm thấy:
   - Tạo mới slider container (chỉ container, không có content)
4. Link các articles trong slider với home

## ⚠️ Lưu Ý

1. **Articles phải có sẵn trong DB** (từ khi crawl các tag/section)
2. **Nếu article chưa có**, sẽ log warning nhưng không tạo mới
3. **Slider containers** sẽ được tạo mới nếu chưa có (chỉ container)
4. **Dry run** để test trước khi update thật

## 📈 So Sánh với Flow Cũ

| Flow Cũ | Flow Mới |
|---------|----------|
| Crawl home → Tạo articles DA mới | Crawl home → Chỉ lấy layout structure |
| Translate DA → EN | Link với articles đã có |
| Có thể duplicate | Tránh duplicate |
| Crawl lại nội dung | Chỉ update metadata |
| Chậm hơn | Nhanh hơn |

## 🔧 Troubleshooting

### Articles không được link:

```bash
# Check articles có trong DB chưa
SELECT id, published_url, language, section, is_home
FROM articles
WHERE published_url = 'https://www.sermitsiaq.ag/...';
```

### Layout structure không đúng:

```bash
# Crawl lại với no-headless để debug
python scripts/crawl_home_layout.py --language da --no-headless --save
```

### Dry run trước khi update:

```bash
# Luôn dùng --dry-run trước
python scripts/link_home_articles.py --crawl --language da --dry-run
```

