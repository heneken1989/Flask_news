# Luồng chạy của `crawl_sections_multi_language.py`

## 📋 Tổng quan

Script này crawl và translate articles từ các sections (tags) và home page cho cả 3 ngôn ngữ (DA, KL, EN).

## 🔄 Luồng chạy hiện tại

### 1. Main Entry Point (`main()`)

```
main()
├── Parse arguments (--section, --max-articles, --skip-crawl)
└── Xử lý theo section type:
    ├── 'home' → process_home()
    ├── 'sections' → process_section() cho mỗi section
    ├── 'all' → process_section() cho tất cả sections → process_home()
    └── single section → process_section()
```

### 2. Process Section (`process_section()`)

```
process_section(section_name)
├── [Nếu không skip_crawl]
│   ├── crawl_danish_section()      # Crawl DK articles từ section URL
│   └── crawl_greenlandic_section() # Crawl KL articles từ section URL
│
├── [TẠM COMMENT] remove_duplicate_da_articles_in_section()
│   └── ⚠️ Hiện đang bị comment để track duplicate
│
├── match_dk_kl_section_articles()
│   ├── Query DK articles (language='da', section=section_name, is_home=False)
│   ├── Query KL articles (language='kl', section=section_name, is_home=False)
│   └── match_and_link_articles()  # Match và link DK ↔ KL
│
└── translate_dk_section_to_en()
    ├── translate_articles_batch()  # Translate DK → EN (batch)
    ├── Translate URLs cho EN articles (loop từng article)
    ├── Remove duplicate EN articles
    └── [COMMENTED] Check và translate missing EN articles
        └── ⚠️ Không cần thiết: translate_articles_batch() đã check và skip
```

### 3. Process Home - ⚠️ CHANGED: Dùng `link_home_articles.py` thay vì `process_home()`

```
[COMMENTED] process_home()  # ← Không dùng nữa
└── ⚠️ Thay bằng subprocess: link_home_articles.py
```

**Lý do:**
- `link_home_articles.py` đầy đủ chức năng (đã thêm matching step)
- Có thể chạy standalone khi cần refresh layout
- Linh hoạt hơn (có dry-run, crawl options, etc.)

### 4. Sau khi xử lý tất cả sections/home

```
Sau khi xong tất cả sections/home:
├── Print overall summary (count articles)
│
├── crawl_article_details()  # ⚠️ FUNCTION CALL (không phải subprocess)
│   ├── Query tất cả articles chưa có ArticleDetail
│   ├── Crawl từng article detail (DA và KL)
│   ├── Download images (nếu --no-download-images không set)
│   ├── Extract và save tags vào article.tags
│   └── Auto translate DA → EN (nếu auto_translate=True)
│
└── subprocess.run(link_home_articles.py)  # ⚠️ QUAN TRỌNG: Đây là cách CHÍNH để process home
    ├── Crawl home layout (DA và KL)
    ├── Link articles với layout (update metadata)
    ├── Match DA ↔ KL (set canonical_id) ← ✅ Đã thêm
    ├── Create missing EN articles
    └── Generate sitemaps
```

## ⚠️ Vấn đề hiện tại

### 1. **Subprocess cho `link_home_articles.py`**
   - **Vấn đề**: Sử dụng `subprocess.run()` để chạy script khác
   - **Hệ quả**: 
     - Tốn thời gian khởi tạo Python process mới
     - Không thể chia sẻ database connection
     - Khó debug và handle errors
   - **Giải pháp**: Import và gọi function trực tiếp

### 2. **Crawl article details chạy tuần tự**
   - **Vấn đề**: `crawl_article_details()` chạy sau khi xong tất cả sections
   - **Hệ quả**: 
     - Phải đợi tất cả sections xong mới crawl details
     - Không tận dụng được thời gian chờ giữa các sections
   - **Giải pháp**: 
     - Option 1: Chạy song song với sections (threading/async)
     - Option 2: Chạy theo batch sau mỗi section (nếu section nhỏ)

### 3. **Duplicate removal bị comment**
   - **Vấn đề**: Logic remove duplicate đang bị comment
   - **Hệ quả**: Duplicate articles tích tụ trong database
   - **Giải pháp**: Bật lại và tối ưu logic

### 4. **Nhiều database queries lặp lại**
   - **Vấn đề**: 
     - `translate_dk_section_to_en()` query EN articles nhiều lần
     - `translate_dk_home_to_en()` query EN articles nhiều lần
   - **Hệ quả**: Chậm và tốn tài nguyên
   - **Giải pháp**: Cache queries hoặc batch queries

### 5. **URL translation chạy tuần tự**
   - **Vấn đề**: Loop từng article để translate URL
   - **Hệ quả**: Chậm nếu có nhiều articles
   - **Giải pháp**: Batch translation hoặc parallel processing

### 6. **Missing EN articles check chạy tuần tự** ✅ FIXED
   - **Vấn đề**: Loop từng DA article để check và translate
   - **Hệ quả**: Chậm nếu có nhiều articles
   - **Giải pháp**: ✅ Đã comment logic này vì duplicate với translate_articles_batch()

## 🚀 Đề xuất tối ưu

### Priority 1: High Impact, Low Effort

#### 1.1. Thay subprocess bằng function call
```python
# Thay vì:
subprocess.run([sys.executable, str(script_path)])

# Nên:
from scripts.link_home_articles import link_articles_with_layout, create_missing_en_articles
# Gọi trực tiếp functions
```

#### 1.2. Bật lại duplicate removal
```python
# Uncomment và tối ưu:
remove_duplicate_da_articles_in_section(section_name)
remove_duplicate_da_home_articles()
```

#### 1.3. Batch URL translation
```python
# Thay vì loop từng article:
for article in en_articles:
    en_url = translate_url(article.published_url, delay=0.3)

# Nên batch:
urls_to_translate = [a.published_url for a in en_articles if not a.published_url_en]
translated_urls = translate_urls_batch(urls_to_translate)
```

### Priority 2: Medium Impact, Medium Effort

#### 2.1. Cache database queries
```python
# Cache EN articles query:
en_articles_cache = {}
def get_en_articles(section_name, is_home=False):
    key = (section_name, is_home)
    if key not in en_articles_cache:
        en_articles_cache[key] = Article.query.filter_by(...).all()
    return en_articles_cache[key]
```

#### 2.2. Parallel section processing
```python
# Chạy sections song song (nếu không phụ thuộc):
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(process_section, section) for section in sections]
    results = [f.result() for f in futures]
```

#### 2.3. Incremental article details crawl
```python
# Crawl details sau mỗi section thay vì đợi tất cả:
for section in sections:
    process_section(section)
    crawl_article_details(section=section, limit=50)  # Crawl một phần
```

### Priority 3: Low Impact, High Effort

#### 3.1. Async/await cho I/O operations
```python
# Sử dụng async/await cho network requests:
async def crawl_section_async(section_name):
    # Async crawl operations
```

#### 3.2. Database connection pooling
```python
# Tối ưu database connections
```

## 📊 Thời gian ước tính

### Hiện tại (ước tính):
- Crawl 1 section: ~5-10 phút
- Translate 1 section: ~10-20 phút
- Crawl article details: ~30-60 phút (tùy số lượng)
- Link home articles: ~5-10 phút
- **Tổng**: ~2-3 giờ cho tất cả sections + home

### Sau tối ưu (ước tính):
- Crawl 1 section: ~5-10 phút (không đổi)
- Translate 1 section: ~5-10 phút (giảm 50% nhờ batch)
- Crawl article details: ~20-40 phút (giảm 30% nhờ incremental)
- Link home articles: ~2-5 phút (giảm 50% nhờ function call)
- **Tổng**: ~1-1.5 giờ (giảm 40-50%)

## 🔧 Implementation Plan

### Phase 1: Quick Wins (1-2 giờ)
1. ✅ Thay subprocess bằng function call
2. ✅ Bật lại duplicate removal
3. ✅ Batch URL translation (nếu có function sẵn)

### Phase 2: Medium Optimizations (2-4 giờ)
1. Cache database queries
2. Incremental article details crawl
3. Optimize missing EN articles check

### Phase 3: Advanced Optimizations (4-8 giờ)
1. Parallel section processing
2. Async I/O operations
3. Database connection pooling

## 📝 Notes

- **Duplicate removal**: Cần test kỹ để đảm bảo không xóa nhầm articles
- **Batch operations**: Cần kiểm tra rate limits của translation API
- **Parallel processing**: Cần đảm bảo thread-safety cho database operations
- **Error handling**: Cần improve error handling cho tất cả operations

