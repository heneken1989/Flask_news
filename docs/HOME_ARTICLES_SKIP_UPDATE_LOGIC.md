# Logic Skip và Update cho EN Home Articles

Tài liệu này giải thích chi tiết logic skip và update cho việc tạo EN home articles, giúp debug các vấn đề liên quan.

## 📍 Các File Liên Quan

1. **`flask/services/crawl_service.py`** - Logic crawl và tạo/update home articles
2. **`flask/services/translation_service.py`** - Logic skip khi translate DA -> EN
3. **`flask/scripts/crawl_sections_multi_language.py`** - Logic translate home articles và remove duplicates

---

## 1. Logic Crawl Home Articles (`crawl_service.py`)

### 1.1. Vị trí: `crawl_home()` method (dòng 245-800)

### 1.2. Flow chính:

```
1. Crawl articles từ home page
2. Pre-fetch existing articles vào existing_articles_map
3. Loop qua từng article:
   a. Check nếu là slider container (không có URL)
   b. Check nếu article đã tồn tại trong existing_articles_map
   c. Nếu tồn tại → thêm vào articles_to_update (sẽ update sau)
   d. Nếu không tồn tại → tạo mới
4. Commit tất cả articles mới
5. Update các articles đã tồn tại (display_order, layout_type, etc.)
```

### 1.3. Logic Skip/Update hiện tại:

**⚠️ LƯU Ý:** Hiện tại logic update đang bị comment out (dòng 456-682), luôn tạo mới articles.

#### A. Pre-fetch existing articles (dòng 360-378):

```python
# Pre-fetch existing articles cho current language và section='home'
all_existing_articles = Article.query.filter_by(
    section='home',
    is_home=True,
    language=article_language
).all()

# Tạo map để lookup nhanh:
# - Slider containers: key = (layout_type, display_order)
# - Articles có URL: key = published_url
existing_articles_map = {}
for art in all_existing_articles:
    if art.layout_type in ['slider', 'job_slider']:
        key = (art.layout_type, art.display_order)
        existing_articles_map[key] = art
    elif art.published_url:
        existing_articles_map[art.published_url] = art
```

#### B. Check existing article (dòng 550-575) - **CHI TIẾT**:

Đây là bước quan trọng nhất để quyết định article có bị skip (update) hay tạo mới.

**Bước 1: Xác định loại article**

```python
# Xác định article có phải slider container không
is_slider_container = layout_type in ['slider', 'job_slider'] and not article_url
article_url = article_data.get('url', '')
layout_type = article_data.get('layout_type', '')
display_order = article_data.get('display_order', idx)
```

**Bước 2: Check trong existing_articles_map**

Có 2 trường hợp:

**Trường hợp A: Slider Container (không có URL)**

```python
if is_slider_container:
    # Tạo key để lookup: (layout_type, display_order)
    key = (layout_type, display_order)
    # Ví dụ: key = ('slider', 5) hoặc ('job_slider', 10)
    
    if key in existing_articles_map:
        # ✅ ĐÃ TỒN TẠI trong database
        # Lấy article object từ map
        existing_article = existing_articles_map[key]
        
        # Thêm vào danh sách articles cần update (sẽ update sau)
        articles_to_update.append({
            'type': 'slider',
            'key': key,                    # ('slider', 5)
            'article': existing_article,    # Article object từ DB
            'article_data': article_data,  # Data mới từ crawl
            'display_order': display_order  # display_order mới
        })
        
        # ⚠️ QUAN TRỌNG: Skip tạo mới, sẽ update sau
        continue
    else:
        # ❌ CHƯA TỒN TẠI → sẽ tạo mới ở bước tiếp theo
        pass
```

**Ví dụ cụ thể cho Slider:**

```
Crawl được slider với:
- layout_type = 'slider'
- display_order = 5
- published_url = '' (rỗng)

→ Tạo key = ('slider', 5)

Check trong existing_articles_map:
- Nếu có key ('slider', 5) → Đã tồn tại → Skip tạo mới, thêm vào articles_to_update
- Nếu không có → Chưa tồn tại → Tạo mới
```

**Trường hợp B: Article có URL**

```python
elif article_url:
    # Article có URL: check bằng published_url
    if article_url in existing_articles_map:
        # ✅ ĐÃ TỒN TẠI trong database
        # Lấy article object từ map
        existing_article = existing_articles_map[article_url]
        
        # Thêm vào danh sách articles cần update (sẽ update sau)
        articles_to_update.append({
            'type': 'article',
            'key': article_url,            # 'https://www.sermitsiaq.ag/...'
            'article': existing_article,    # Article object từ DB
            'article_data': article_data,   # Data mới từ crawl
            'display_order': display_order  # display_order mới
        })
        
        # ⚠️ QUAN TRỌNG: Skip tạo mới, sẽ update sau
        continue
    else:
        # ❌ CHƯA TỒN TẠI → sẽ tạo mới ở bước tiếp theo
        pass
```

**Ví dụ cụ thể cho Article có URL:**

```
Crawl được article với:
- published_url = 'https://www.sermitsiaq.ag/samfund/article-title/1234567'
- display_order = 10
- layout_type = '1_full'

→ Sử dụng published_url làm key

Check trong existing_articles_map:
- Nếu có key 'https://www.sermitsiaq.ag/samfund/article-title/1234567' 
  → Đã tồn tại → Skip tạo mới, thêm vào articles_to_update
- Nếu không có → Chưa tồn tại → Tạo mới
```

**Bước 3: Nếu không tồn tại → Tạo mới**

```python
# Nếu không match trong existing_articles_map (không có trong cả 2 trường hợp trên)
# → Article chưa tồn tại → Tạo mới
print(f"  ➕ Will create new article: {article_data.get('title', 'Untitled')[:50]}...")
# ... (logic tạo mới article)
```

**⚠️ LƯU Ý QUAN TRỌNG:**

1. **existing_articles_map chỉ chứa articles với:**
   - `section='home'`
   - `is_home=True`
   - `language` = `article_language` (DA, KL, hoặc EN)

2. **Nếu article tồn tại nhưng không thỏa điều kiện trên:**
   - Sẽ KHÔNG có trong `existing_articles_map`
   - → Sẽ tạo mới (có thể dẫn đến duplicate)

3. **Logic này chỉ CHECK, không UPDATE ngay:**
   - Articles tồn tại được thêm vào `articles_to_update`
   - Chỉ update sau khi đã save đầy đủ articles mới (bước 5)

4. **Với Slider containers:**
   - Key là `(layout_type, display_order)` - tuple
   - Nếu có 2 sliders cùng `display_order` → chỉ giữ 1 trong map (ghi đè)

5. **Với Articles có URL:**
   - Key là `published_url` - string
   - Nếu có 2 articles cùng `published_url` → chỉ giữ 1 trong map (ghi đè)

#### C. Update existing articles (dòng 740-791):

```python
# Sau khi save đầy đủ articles mới, mới update các articles cũ
for update_info in articles_to_update:
    existing_article = update_info['article']
    
    # Update các fields:
    existing_article.display_order = display_order
    existing_article.layout_type = layout_type
    existing_article.layout_data = layout_data
    existing_article.grid_size = grid_size
    existing_article.is_home = True
    existing_article.section = 'home'
    
    db.session.commit()  # Commit sau mỗi update
```

### 1.4. Điều kiện để Skip (không tạo mới):

- ✅ Article đã tồn tại trong `existing_articles_map` với:
  - `section='home'`
  - `is_home=True`
  - `language` trùng với `article_language`
  - Và một trong hai:
    - Slider: `(layout_type, display_order)` trùng
    - Article có URL: `published_url` trùng

**Các trường hợp đặc biệt:**

1. **Article tồn tại nhưng `section != 'home'`:**
   - ❌ KHÔNG có trong `existing_articles_map` (vì filter `section='home'`)
   - → Sẽ tạo mới → Có thể duplicate

2. **Article tồn tại nhưng `is_home=False`:**
   - ❌ KHÔNG có trong `existing_articles_map` (vì filter `is_home=True`)
   - → Sẽ tạo mới → Có thể duplicate

3. **Article tồn tại nhưng `language` khác:**
   - ❌ KHÔNG có trong `existing_articles_map` (vì filter `language=article_language`)
   - → Sẽ tạo mới → Đúng (cần tạo cho language khác)

4. **Slider container có cùng `display_order` nhưng `layout_type` khác:**
   - ✅ Key khác nhau: `('slider', 5)` vs `('job_slider', 5)`
   - → Không match → Tạo mới → Đúng

5. **Article có URL nhưng `display_order` thay đổi:**
   - ✅ Key vẫn là `published_url` (không phụ thuộc `display_order`)
   - → Match → Skip tạo mới, update `display_order` → Đúng

**Debug tips:**

```python
# Thêm log để debug
if is_slider_container:
    key = (layout_type, display_order)
    print(f"  🔍 Checking slider: key={key}, in_map={key in existing_articles_map}")
    if key in existing_articles_map:
        existing = existing_articles_map[key]
        print(f"     ✅ Found existing: ID={existing.id}, section={existing.section}, is_home={existing.is_home}")
elif article_url:
    print(f"  🔍 Checking article: url={article_url[:60]}..., in_map={article_url in existing_articles_map}")
    if article_url in existing_articles_map:
        existing = existing_articles_map[article_url]
        print(f"     ✅ Found existing: ID={existing.id}, section={existing.section}, is_home={existing.is_home}")
```

**SQL để check articles không được skip đúng:**

```sql
-- Tìm articles có cùng published_url nhưng section hoặc is_home khác
SELECT 
    a1.id as id1, a1.published_url, a1.section as section1, a1.is_home as is_home1,
    a2.id as id2, a2.section as section2, a2.is_home as is_home2
FROM articles a1
JOIN articles a2 ON a1.published_url = a2.published_url
WHERE a1.id != a2.id
  AND a1.published_url IS NOT NULL
  AND a1.published_url != ''
  AND (a1.section != a2.section OR a1.is_home != a2.is_home);
```

### 1.5. Điều kiện để Update:

- Article đã tồn tại (theo điều kiện trên)
- Update các fields: `display_order`, `layout_type`, `layout_data`, `grid_size`
- Đảm bảo `is_home=True` và `section='home'`

---

## 2. Logic Translate DA -> EN (`translation_service.py`)

### 2.1. Vị trí: `translate_articles_batch()` method (dòng 168-257)

### 2.2. Flow chính:

```
1. Loop qua từng DA article
2. Check xem đã có EN article chưa (dựa trên published_url + language='en' + section + is_home)
3. Nếu đã có:
   a. Set is_temp=False nếu cần
   b. Set canonical_id nếu chưa có
   c. Skip translation
4. Nếu chưa có:
   a. Translate article
   b. Save vào database
```

### 2.3. Logic Skip (dòng 190-219):

```python
# Check if translation already exists
if dk_article.published_url:
    existing = Article.query.filter_by(
        published_url=dk_article.published_url,  # ⚠️ QUAN TRỌNG: Check bằng published_url
        language='en',
        section=dk_article.section,              # ⚠️ QUAN TRỌNG: Check section
        is_home=dk_article.is_home               # ⚠️ QUAN TRỌNG: Check is_home
    ).first()

if existing:
    # Đã tồn tại → skip translation
    if existing.is_temp:
        existing.is_temp = False
        db.session.commit()
    
    if not existing.canonical_id:
        existing.canonical_id = dk_article.id
        db.session.commit()
    
    skipped_count += 1
    continue  # Skip translation
```

### 2.4. Điều kiện để Skip (không translate):

- ✅ Đã có EN article với:
  - `published_url` = DA article's `published_url`
  - `language='en'`
  - `section` = DA article's `section`
  - `is_home` = DA article's `is_home`

### 2.5. ⚠️ VẤN ĐỀ TIỀM ẨN:

**Nếu DA article có `published_url` nhưng EN article có `published_url_en` khác:**
- Logic này vẫn check bằng `published_url` (DA URL)
- Nếu EN article chỉ có `published_url_en` mà không có `published_url`, sẽ không match được
- → Có thể tạo duplicate EN articles

---

## 3. Logic Translate Home và Remove Duplicates (`crawl_sections_multi_language.py`)

### 3.1. Vị trí: `translate_dk_home_to_en()` function (dòng 438-628)

### 3.2. Flow chính:

```
1. Lấy tất cả DA home articles
2. Translate sang EN (sử dụng translate_articles_batch)
3. Translate URLs cho EN articles (published_url → published_url_en)
4. Remove duplicate EN articles (cùng published_url)
5. Check và tạo EN version cho DA articles còn thiếu
```

### 3.3. Step 1: Translate articles (dòng 456-462):

```python
translated, errors, stats = translate_articles_batch(
    dk_articles,
    target_language='en',
    save_to_db=True,
    delay=0.5
)
# Sử dụng logic skip từ translation_service.py
```

### 3.4. Step 2: Translate URLs (dòng 468-513):

```python
en_articles = Article.query.filter_by(
    language='en',
    is_home=True
).all()

for article in en_articles:
    # Skip nếu đã có published_url_en
    if article.published_url_en and article.published_url_en.strip():
        url_skipped_count += 1
        continue
    
    # Translate URL
    en_url = translate_url(article.published_url, delay=0.3)
    if en_url:
        article.published_url_en = en_url
        db.session.commit()
```

### 3.5. Step 3: Remove duplicates (dòng 515-555):

```python
# Lấy tất cả EN home articles
all_en_articles = Article.query.filter_by(
    language='en',
    is_home=True
).all()

# Group by published_url
url_to_articles = {}
for article in all_en_articles:
    if article.published_url:
        if article.published_url not in url_to_articles:
            url_to_articles[article.published_url] = []
        url_to_articles[article.published_url].append(article)

# Xóa duplicates (giữ lại article có ID nhỏ nhất)
for published_url, articles in url_to_articles.items():
    if len(articles) > 1:
        articles_sorted = sorted(articles, key=lambda x: x.id)
        article_to_keep = articles_sorted[0]
        articles_to_delete = articles_sorted[1:]
        
        for article_to_delete in articles_to_delete:
            db.session.delete(article_to_delete)
```

### 3.6. Step 4: Create missing EN versions (dòng 557-627):

```python
# Lấy tất cả DA home articles
dk_articles = Article.query.filter_by(
    language='da',
    is_home=True
).all()

for dk_article in dk_articles:
    # Check xem đã có EN version chưa
    existing_en = Article.query.filter_by(
        published_url=dk_article.published_url,  # ⚠️ Check bằng published_url
        language='en',
        is_home=True
    ).first()
    
    if not existing_en:
        # Chưa có → translate
        en_article = translate_article(dk_article, ...)
        # Translate URL
        en_url = translate_url(dk_article.published_url, delay=0.3)
        if en_url:
            en_article.published_url_en = en_url
        db.session.add(en_article)
        db.session.commit()
```

---

## 🔍 Các Vấn Đề Tiềm Ẩn và Cách Debug

### Vấn đề 1: Duplicate EN articles

**Nguyên nhân:**
- Logic skip trong `translate_articles_batch()` check bằng `published_url` (DA URL)
- Nhưng sau khi translate URL, EN article có `published_url_en` khác
- Nếu có 2 DA articles với cùng `published_url` nhưng khác `display_order`, có thể tạo 2 EN articles

**Cách debug:**
```sql
-- Tìm duplicate EN home articles
SELECT published_url, COUNT(*) as count
FROM articles
WHERE language='en' AND is_home=True
GROUP BY published_url
HAVING COUNT(*) > 1;
```

**Giải pháp:**
- Logic remove duplicates ở step 3 đã xử lý vấn đề này
- Nhưng cần chạy sau mỗi lần translate

### Vấn đề 2: EN article không được tạo từ DA article

**Nguyên nhân:**
- Logic skip trong `translate_articles_batch()` check quá strict
- Nếu DA article có `published_url` nhưng EN article có `published_url_en` khác, không match được

**Cách debug:**
```sql
-- Tìm DA home articles chưa có EN version
SELECT da.id, da.published_url, da.title
FROM articles da
LEFT JOIN articles en ON (
    en.published_url = da.published_url
    AND en.language = 'en'
    AND en.is_home = da.is_home
    AND en.section = da.section
)
WHERE da.language = 'da'
  AND da.is_home = True
  AND en.id IS NULL;
```

**Giải pháp:**
- Step 4 trong `translate_dk_home_to_en()` đã xử lý vấn đề này
- Nhưng cần chạy sau mỗi lần translate

### Vấn đề 3: Article bị skip không đúng

**Nguyên nhân:**
- Logic skip trong `crawl_home()` check bằng `existing_articles_map`
- Nếu article đã tồn tại nhưng `section` hoặc `is_home` không đúng, vẫn tạo mới

**Cách debug:**
```sql
-- Tìm articles có section='home' nhưng is_home=False
SELECT id, published_url, section, is_home, language
FROM articles
WHERE section='home' AND is_home=False;

-- Tìm articles có is_home=True nhưng section != 'home'
SELECT id, published_url, section, is_home, language
FROM articles
WHERE is_home=True AND section != 'home';
```

**Giải pháp:**
- Logic update ở step 5 trong `crawl_home()` đảm bảo `is_home=True` và `section='home'`
- Nhưng cần chạy sau mỗi lần crawl

### Vấn đề 4: Display order không đúng

**Nguyên nhân:**
- Logic update `display_order` chỉ chạy sau khi save đầy đủ articles mới
- Nếu có lỗi trong quá trình save, `display_order` có thể không được update

**Cách debug:**
```sql
-- Tìm articles có display_order NULL hoặc không đúng
SELECT id, published_url, display_order, layout_type, is_home
FROM articles
WHERE is_home=True
ORDER BY display_order NULLS LAST;
```

**Giải pháp:**
- Đảm bảo logic update chạy đầy đủ
- Commit sau mỗi update để tránh mất dữ liệu

---

## 📝 Checklist Debug

Khi gặp vấn đề với EN home articles, check theo thứ tự:

1. ✅ **Check duplicate EN articles:**
   ```sql
   SELECT published_url, COUNT(*) FROM articles 
   WHERE language='en' AND is_home=True GROUP BY published_url HAVING COUNT(*) > 1;
   ```

2. ✅ **Check DA articles chưa có EN version:**
   ```sql
   SELECT da.id, da.published_url FROM articles da
   LEFT JOIN articles en ON en.published_url=da.published_url AND en.language='en' AND en.is_home=da.is_home
   WHERE da.language='da' AND da.is_home=True AND en.id IS NULL;
   ```

3. ✅ **Check articles có section/is_home không đúng:**
   ```sql
   SELECT id, published_url, section, is_home FROM articles
   WHERE (section='home' AND is_home=False) OR (is_home=True AND section != 'home');
   ```

4. ✅ **Check display_order:**
   ```sql
   SELECT id, published_url, display_order FROM articles
   WHERE is_home=True ORDER BY display_order NULLS LAST LIMIT 20;
   ```

5. ✅ **Check published_url_en:**
   ```sql
   SELECT id, published_url, published_url_en FROM articles
   WHERE language='en' AND is_home=True AND (published_url_en IS NULL OR published_url_en='');
   ```

---

## 🔧 Các Script Hữu Ích

1. **Translate URLs cho EN home articles:**
   ```bash
   python flask/scripts/translate_home_urls_en.py
   ```

2. **Remove duplicate EN articles:**
   - Đã được tích hợp trong `translate_dk_home_to_en()` (step 3)

3. **Create missing EN versions:**
   - Đã được tích hợp trong `translate_dk_home_to_en()` (step 4)

---

## 📌 Tóm Tắt Logic Skip/Update

### Khi Crawl Home (DA):
- **Skip nếu:** Article đã tồn tại với `(published_url, language, section='home', is_home=True)`
- **Update nếu:** Article đã tồn tại → update `display_order`, `layout_type`, `layout_data`

### Khi Translate DA → EN:
- **Skip nếu:** EN article đã tồn tại với `(published_url, language='en', section, is_home)`
- **Tạo mới nếu:** Chưa có EN article

### Khi Remove Duplicates:
- **Giữ lại:** Article có ID nhỏ nhất
- **Xóa:** Các articles còn lại có cùng `published_url`

### Khi Create Missing EN:
- **Check:** DA article có EN version chưa (bằng `published_url`)
- **Tạo nếu:** Chưa có EN version

