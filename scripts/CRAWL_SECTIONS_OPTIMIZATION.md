# Tối ưu `crawl_sections_multi_language.py` - Quick Wins

## 🎯 Mục tiêu
Tối ưu script để giảm thời gian chạy 40-50% và cải thiện maintainability.

## ✅ Quick Wins (Có thể implement ngay)

### 1. Thay subprocess bằng function call ⚡

**Hiện tại:**
```python
# Line 857-862
script_path = Path(__file__).parent / 'link_home_articles.py'
result = subprocess.run(
    [sys.executable, str(script_path)],
    cwd=str(Path(__file__).parent),
    check=False
)
```

**Đề xuất:**
```python
# Import và gọi trực tiếp
from scripts.link_home_articles import (
    crawl_home_layout,
    link_articles_with_layout,
    create_missing_en_articles,
    save_layout_to_file
)

# Thay subprocess bằng:
for language in ['da', 'kl']:
    # Crawl layout
    layout_items = crawl_home_layout(
        home_url='https://www.sermitsiaq.ag' if language == 'da' else 'https://kl.sermitsiaq.ag',
        language=language,
        headless=True
    )
    
    # Link articles
    link_articles_with_layout(
        layout_items=layout_items,
        language=language,
        dry_run=False,
        reset_first=True
    )
    
    # Create EN articles nếu là DA
    if language == 'da':
        create_missing_en_articles(
            layout_items=layout_items,
            language='da',
            dry_run=False
        )
```

**Lợi ích:**
- Giảm thời gian khởi tạo process (~2-5 giây)
- Dễ debug và handle errors
- Chia sẻ database connection
- **Tiết kiệm: ~5-10 phút tổng thời gian**

### 2. Bật lại duplicate removal 🔧

**Hiện tại:**
```python
# Line 700-702, 728-730
# remove_duplicate_da_home_articles()  # COMMENTED
# remove_duplicate_da_articles_in_section(section_name)  # COMMENTED
```

**Đề xuất:**
```python
# Uncomment và tối ưu:
if not skip_crawl:
    crawl_danish_section(section_name, max_articles)
    crawl_greenlandic_section(section_name, max_articles)
    
    # Remove duplicates ngay sau crawl
    remove_duplicate_da_articles_in_section(section_name)
```

**Lợi ích:**
- Tránh tích tụ duplicate articles
- Giảm thời gian match và translate
- **Tiết kiệm: ~5-10 phút tổng thời gian**

### 3. Batch URL translation 📦

**Hiện tại:**
```python
# Line 254-279 (translate_dk_section_to_en)
for article in en_articles:
    if article.published_url_en:
        continue
    en_url = translate_url(article.published_url, delay=0.3)
    # ... update
```

**Đề xuất:**
```python
# Collect URLs cần translate
urls_to_translate = [
    (article.id, article.published_url) 
    for article in en_articles 
    if not article.published_url_en and article.published_url
]

# Batch translate (nếu API hỗ trợ) hoặc parallel
from concurrent.futures import ThreadPoolExecutor
def translate_one_url(article_id, url):
    en_url = translate_url(url, delay=0.3)
    if en_url:
        article = Article.query.get(article_id)
        article.published_url_en = en_url
        db.session.commit()
    return en_url

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(translate_one_url, aid, url) 
        for aid, url in urls_to_translate
    ]
    results = [f.result() for f in futures]
```

**Lợi ích:**
- Giảm thời gian translate URLs 50-70%
- **Tiết kiệm: ~10-20 phút tổng thời gian**

### 4. Cache database queries 💾

**Hiện tại:**
```python
# Query EN articles nhiều lần trong translate_dk_section_to_en()
en_articles = Article.query.filter_by(...).all()  # Line 244
# ... sau đó query lại trong missing EN check (Line 336)
```

**Đề xuất:**
```python
# Cache query result
def translate_dk_section_to_en(section_name):
    # ... existing code ...
    
    # Cache EN articles
    en_articles = Article.query.filter_by(
        language='en',
        section=section_name,
        is_home=False
    ).all()
    en_articles_by_url = {a.published_url: a for a in en_articles}
    
    # Use cache trong missing EN check
    for dk_article in dk_articles:
        existing_en = en_articles_by_url.get(dk_article.published_url)
        # ...
```

**Lợi ích:**
- Giảm database queries
- **Tiết kiệm: ~2-5 phút tổng thời gian**

## 📊 Tổng kết Quick Wins

| Optimization | Time Saved | Effort | Priority | Status |
|-------------|------------|--------|----------|--------|
| 1. Comment subprocess link_home | 1-2 min | Low | ⭐⭐⭐ | ✅ Done |
| 2. Thêm matching vào link_home | N/A | Low | ⭐⭐⭐ | ✅ Done |
| 3. Comment missing EN check | 5-10 min | Low | ⭐⭐⭐ | ✅ Done |
| 4. Bật duplicate removal | 5-10 min | Low | ⭐⭐⭐ | Pending |
| 5. Batch URL translation | 10-20 min | Medium | ⭐⭐ | Pending |
| 6. Cache queries | 2-5 min | Low | ⭐⭐ | Pending |

**Tổng tiết kiệm ước tính: 23-47 phút (30-50% tổng thời gian)**

## 🚀 Implementation Order

1. **Quick Win #1**: Thay subprocess (15 phút)
2. **Quick Win #2**: Bật duplicate removal (5 phút)
3. **Quick Win #4**: Cache queries (10 phút)
4. **Quick Win #3**: Batch URL translation (30 phút)

**Tổng thời gian implement: ~1 giờ**

## ⚠️ Lưu ý

- **Batch URL translation**: Cần test rate limits của translation API
- **Duplicate removal**: Cần test kỹ để đảm bảo không xóa nhầm
- **Function call**: Cần đảm bảo `link_home_articles.py` có thể import được

