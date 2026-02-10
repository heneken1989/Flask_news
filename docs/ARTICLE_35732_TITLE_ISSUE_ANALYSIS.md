# Phân tích vấn đề: Article ID 35732 - Title trong layout_data không đồng nhất

## Vấn đề
- Article ID 35732 có title trong `layout_data` không đồng nhất (có vẻ dịch sai)
- Nhưng field `title` vẫn đúng

## Phân tích code

### 1. Cấu trúc dữ liệu
- **`title` field**: Field chính trong Article model, lưu title của article
- **`layout_data` field**: JSON field chứa các thông tin bổ sung cho layout:
  - `kicker_floating`
  - `kicker_below`
  - `title_parts` (title được chia thành các parts với highlights)
  - `list_title`
  - `list_items` (có thể chứa titles của các items trong list)
  - `slider_title`
  - `slider_articles` (có thể chứa titles)

### 2. Nơi title có thể xuất hiện trong layout_data

#### a) `title_parts` (dòng 938 trong `article_parser.py`)
- Được extract từ HTML khi crawl home layout
- Chứa title được chia thành các parts với highlight colors
- Được translate trong `translation_service.py` (dòng 185-189)

#### b) `list_items` (dòng 979-1033 trong `article_parser.py`)
- Mỗi item trong list có thể có `title`
- Được translate trong `translation_service.py` (dòng 113-182)
- Logic translate: Tìm EN article tương ứng trước, nếu không có mới translate text

#### c) `slider_articles` (dòng 80-99 trong `translation_service.py`)
- Các articles trong slider có thể có `title`
- Được translate trong `translation_service.py`

### 3. Nguyên nhân có thể

#### Nguyên nhân 1: `title_parts` bị dịch sai
- `title_parts` được translate từng part riêng lẻ (dòng 185-189 trong `translation_service.py`)
- Nếu title có nhiều parts, việc dịch từng part có thể làm mất context
- **Giải pháp**: Kiểm tra xem `title_parts` trong layout_data có khớp với `title` field không

#### Nguyên nhân 2: `list_items` titles bị dịch sai
- Khi translate `list_items`, code tìm EN article tương ứng (dòng 136-149)
- Nếu không tìm thấy, sẽ translate text (dòng 163-172)
- Có thể EN article chưa được tạo hoặc URL không match
- **Giải pháp**: Kiểm tra xem có `list_items` trong layout_data và titles của chúng

#### Nguyên nhân 3: Title từ layout crawl khác với title trong database
- Khi crawl home layout, title được extract từ HTML (dòng 155 trong `article_parser.py`)
- Title này được lưu vào `layout_item['title']` (dòng 253 trong `crawl_home_layout.py`)
- Khi link articles, title này có thể được update vào article (dòng 251-262 trong `link_home_articles.py`)
- **Giải pháp**: Kiểm tra xem có sự khác biệt giữa title từ layout crawl và title trong DB

#### Nguyên nhân 4: EN article được tạo trước khi DA article được update
- Nếu EN article được translate từ DA article cũ
- Sau đó DA article được update với title mới từ layout crawl
- EN article vẫn giữ title cũ
- **Giải pháp**: Kiểm tra `canonical_id` và so sánh titles giữa DA và EN versions

### 4. Cách kiểm tra

Chạy script sau để kiểm tra article 35732:

```python
from app import app
from database import db, Article
import json

with app.app_context():
    article = Article.query.get(35732)
    if article:
        print(f'Title field: {article.title}')
        print(f'Language: {article.language}')
        if article.layout_data:
            print(f'\nLayout Data:')
            print(json.dumps(article.layout_data, indent=2, ensure_ascii=False))
            
            # Check title_parts
            if 'title_parts' in article.layout_data:
                title_parts = article.layout_data['title_parts']
                print(f'\nTitle parts: {title_parts}')
                # Reconstruct title from parts
                reconstructed = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in title_parts])
                print(f'Reconstructed from parts: {reconstructed}')
                if reconstructed.strip() != article.title.strip():
                    print(f'⚠️ MISMATCH: title_parts does not match title field!')
            
            # Check list_items
            if 'list_items' in article.layout_data:
                list_items = article.layout_data['list_items']
                print(f'\nList items ({len(list_items)}):')
                for i, item in enumerate(list_items):
                    if isinstance(item, dict) and 'title' in item:
                        print(f'  Item {i}: {item["title"]}')
        
        # Check EN version if exists
        if article.language == 'da':
            en_article = Article.query.filter_by(
                canonical_id=article.id,
                language='en'
            ).first()
            if en_article:
                print(f'\nEN version (ID: {en_article.id}):')
                print(f'  Title: {en_article.title}')
```

### 5. Giải pháp đề xuất

1. **Kiểm tra database trực tiếp**: Xem chính xác title nào trong layout_data không khớp
2. **Đồng bộ title_parts với title field**: Khi update title, cũng update title_parts
3. **Fix translation logic**: Đảm bảo title_parts được translate đúng cách
4. **Re-translate nếu cần**: Nếu phát hiện mismatch, re-translate article
