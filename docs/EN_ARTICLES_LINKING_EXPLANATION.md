# Giải thích: Quá trình Link EN Articles vào Layout

## 1. Layout Structure (DA Layout)

### Layout được crawl từ đâu?
- **Layout được crawl từ DA URL**: `https://www.sermitsiaq.ag`
- **Lưu vào file JSON**: `home_layout_da_YYYYMMDD_HHMMSS.json`
- **Mỗi layout item có**:
  ```json
  {
    "published_url": "/samfund/article-title/123456",  // DA URL
    "layout_type": "1_full",
    "display_order": 0,
    "row_index": 0,
    "title": "Article Title (DA)",
    ...
  }
  ```

### ⚠️ QUAN TRỌNG:
- **Layout LUÔN chứa DA URLs** (vì crawl từ DA site)
- **View LUÔN dùng DA layout** cho tất cả languages (DA, EN, KL)
- **Sau đó thay thế articles** bằng version tương ứng

---

## 2. Cấu trúc Articles trong DB

### DA Articles:
```python
Article(
    id=100,
    language='da',
    published_url='/samfund/article-title/123456',  # DA URL
    published_url_en=None,  # Chưa có EN URL
    canonical_id=None,  # DA article là original
    ...
)
```

### EN Articles (sau khi được tạo):
```python
Article(
    id=200,
    language='en',
    published_url='/samfund/article-title/123456',  # ⚠️ VẪN LÀ DA URL!
    published_url_en='/samfund/article-title-en/123456',  # EN URL (đã translate)
    canonical_id=100,  # ⚠️ Link với DA article (id=100)
    ...
)
```

### ⚠️ QUAN TRỌNG:
- **EN articles có `published_url` = DA URL** (giống với layout)
- **EN articles có `published_url_en` = EN URL** (đã translate)
- **EN articles có `canonical_id` = DA article.id** (link với DA version)

---

## 3. Quá trình Link EN Articles trong View

### Step 1: Load DA Layout
```python
# Luôn tìm DA layout
json_files = list(layouts_dir.glob('home_layout_da_*.json'))
latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
layout_items = load_from_json(latest_json)
# layout_items chứa DA URLs
```

### Step 2: Tạo Articles Map
```python
# Pre-fetch tất cả articles
all_articles = Article.query.filter(
    Article.published_url.isnot(None),
    Article.published_url != ''
).all()

# Tạo map: published_url -> [Article, Article, ...]
articles_map = {}
for article in all_articles:
    if article.published_url:
        if article.published_url not in articles_map:
            articles_map[article.published_url] = []
        articles_map[article.published_url].append(article)
```

**Ví dụ:**
```python
articles_map = {
    '/samfund/article-title/123456': [
        Article(id=100, language='da', ...),  # DA article
        Article(id=200, language='en', ...),  # EN article (cùng published_url!)
    ],
    ...
}
```

### Step 3: Link Articles với Layout

Với mỗi `layout_item` trong layout:

```python
published_url = layout_item.get('published_url')  # DA URL từ layout
current_language = 'en'  # User chọn EN

# Tìm article trong articles_map
if published_url in articles_map:
    matched_article = None
    
    # Cách 1: Tìm trực tiếp bằng published_url + language
    for article in articles_map[published_url]:
        if article.language == current_language:  # Tìm EN article
            matched_article = article
            break
    
    # Cách 2: Nếu không tìm thấy (EN chưa được link), tìm qua canonical_id
    if not matched_article and current_language == 'en':
        # Tìm DA article trước
        da_article = None
        for article in articles_map[published_url]:
            if article.language == 'da':
                da_article = article
                break
        
        if da_article:
            # Tìm EN article qua canonical_id
            en_article = Article.query.filter_by(
                canonical_id=da_article.id,  # EN có canonical_id = DA.id
                language='en'
            ).first()
            
            if en_article:
                matched_article = en_article
```

---

## 4. Vấn đề hiện tại và giải pháp

### Vấn đề:
- View hiện tại **chưa có logic tìm EN articles qua canonical_id**
- Chỉ tìm trực tiếp bằng `published_url + language`
- Nếu EN article chưa được link vào layout (chưa có `is_home=True`), sẽ không tìm thấy

### Giải pháp:
1. **Thêm logic tìm EN articles qua canonical_id** (như trong `link_home_articles.py`)
2. **Thêm logging chi tiết** để debug

---

## 5. Flow hoàn chỉnh

```
1. User chọn language = 'en'
   ↓
2. Load DA layout (chứa DA URLs)
   ↓
3. Tạo articles_map: published_url -> [DA article, EN article, ...]
   ↓
4. Với mỗi layout_item:
   a. Lấy published_url (DA URL) từ layout
   b. Tìm trong articles_map[published_url]:
      - Nếu có EN article → dùng
      - Nếu không có:
        * Tìm DA article
        * Tìm EN article qua canonical_id = DA.id
        * Nếu tìm thấy → dùng
   c. Thay thế article trong layout
   ↓
5. Render với EN articles
```

---

## 6. Ví dụ cụ thể

### Layout Item:
```json
{
  "published_url": "/samfund/article-title/123456",
  "layout_type": "1_full",
  "display_order": 0
}
```

### Articles trong DB:
```python
# DA article
Article(id=100, language='da', published_url='/samfund/article-title/123456', canonical_id=None)

# EN article
Article(id=200, language='en', published_url='/samfund/article-title/123456', canonical_id=100)
```

### Quá trình link:
1. Layout có URL: `/samfund/article-title/123456`
2. `articles_map['/samfund/article-title/123456']` = `[DA article (id=100), EN article (id=200)]`
3. Tìm EN article: `article.language == 'en'` → Tìm thấy `id=200`
4. Dùng EN article để render

### Nếu EN article chưa có trong articles_map:
1. Layout có URL: `/samfund/article-title/123456`
2. `articles_map['/samfund/article-title/123456']` = `[DA article (id=100)]` (chưa có EN)
3. Tìm EN article trực tiếp: Không tìm thấy
4. Tìm DA article: Tìm thấy `id=100`
5. Tìm EN qua canonical_id: `Article.query.filter_by(canonical_id=100, language='en')` → Tìm thấy `id=200`
6. Dùng EN article để render

---

## 7. Tóm tắt

**Layout:**
- Luôn là DA layout (crawl từ DA URL)
- Chứa DA URLs

**EN Articles:**
- Có `published_url` = DA URL (giống layout)
- Có `canonical_id` = DA article.id
- Có `published_url_en` = EN URL (đã translate)

**Link Process:**
1. Tìm trực tiếp: `published_url + language='en'`
2. Nếu không có: Tìm qua `canonical_id`
3. Thay thế article trong layout

