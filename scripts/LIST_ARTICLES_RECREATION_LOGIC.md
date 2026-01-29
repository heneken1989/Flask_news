# Logic tạo mới 1_with_list Articles

## 🎯 Mục đích

Tạo mới các articles có `layout_type = '1_with_list_left'` hoặc `'1_with_list_right'` mỗi lần chạy update, để đảm bảo:
1. Articles luôn có dữ liệu mới nhất từ trang gốc
2. Minimize thời gian user thấy sự không ổn định khi hệ thống đang update

## 🔄 Flow

```
┌─────────────────────────────────────────────────────────┐
│ Step 0: Mark old 1_with_list articles                  │
│ - Set is_deleted=True cho tất cả 1_with_list articles │
│ - Theo ngôn ngữ: KL, DA, EN                           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Step 0a: Crawl home layout                             │
│ - crawl_home_layout() tạo MỚI 1_with_list articles    │
│ - Query chỉ tìm: section='home' AND is_deleted=False  │
│ - Vì articles cũ đã mark deleted, query không tìm thấy│
│ → Tạo mới (is_deleted=False, section='home')          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Step 0b: DELETE old marked articles                   │
│ - DELETE articles có is_deleted=True NGAY             │
│ - SAU BƯỚC NÀY: Chỉ còn new articles                  │
│ ⚠️ DELETE TRƯỚC KHI link để tránh duplicate!          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Step 1-N: Process articles như bình thường             │
│ - Link articles với layout (chỉ new articles)         │
│ - Match DA ↔ KL                                        │
│ - Create EN articles                                   │
│ - Translate slider containers                         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ ✅ DONE: User thấy new data, no duplicates            │
└─────────────────────────────────────────────────────────┘
```

## 📊 Timeline

```
Time  │ User Experience                 │ Database State
──────┼─────────────────────────────────┼────────────────────────────
  0   │ Old articles visible            │ Old: is_deleted=False
  ↓   │                                 │
Mark  │ Old articles still visible      │ Old: is_deleted=True ✓
  ↓   │                                 │
Crawl │ Old articles still visible      │ Old: is_deleted=True
  ↓   │                                 │ New: is_deleted=False ✓
  ↓   │                                 │
Delete│ 🔄 INSTANT SWITCH: Old → New    │ Old: DELETED ✓
  ↓   │ (< 1 giây)                      │ New: is_deleted=False
  ↓   │                                 │
Link  │ ✅ New articles visible         │ New: is_deleted=False, linked ✓
  ↓   │                                 │
Final │ ✅ New articles fully linked    │ New: is_deleted=False, linked
```

**⚠️ QUAN TRỌNG**: Thời gian user thấy sự không ổn định được minimize:
- Mark + Crawl: User vẫn thấy old data (stable)
- Delete: Instant switch từ old → new (< 1 giây)
- Link: User thấy new data (stable), chỉ cần update metadata

**Lý do delete TRƯỚC link:**
- Tránh có 2 articles cùng URL cùng `is_home=True` trong DB
- Nếu delete SAU link, có thể có duplicate trong khoảng thời gian link

## 🔧 Implementation Details

### 1. Database Schema

**Added field:**
```sql
ALTER TABLE articles 
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;

CREATE INDEX ix_articles_is_deleted 
ON articles (is_deleted);
```

### 2. New Functions in `link_home_articles.py`

#### `mark_list_articles_for_deletion(language, dry_run)`
- Mark các `1_with_list_left/right` articles là `is_deleted=True`
- Filter: `layout_type IN ('1_with_list_left', '1_with_list_right')` AND `section='home'`
- Chỉ mark articles chưa bị deleted (`is_deleted=False OR is_deleted IS NULL`)

#### `delete_marked_articles(language, dry_run)`
- DELETE các articles có `is_deleted=True`
- Sử dụng `db.session.delete(article)` để xóa vĩnh viễn

### 3. Updated `crawl_home_layout.py`

**Special handling for 1_with_list articles:**
```python
# Với 1_with_list_left/right: chỉ tìm articles có section='home' và chưa bị deleted
if layout_type in ['1_with_list_left', '1_with_list_right']:
    existing = Article.query.filter_by(
        published_url=article_url,
        language=language,
        section='home'  # ⚠️ REQUIRE section='home'
    ).filter(
        or_(Article.is_deleted == False, Article.is_deleted.is_(None))
    ).first()
    
    if existing:
        # Đã có article mới (tạo trong session này) → skip
        skip()
    else:
        # Không tìm thấy (đã bị mark deleted hoặc chưa có) → tạo mới
        create_new_article(section='home', is_deleted=False)
```

**Why this works:**
1. Old articles đã bị mark `is_deleted=True` → query không tìm thấy
2. Articles từ section khác (e.g., `section='samfund'`) → query không tìm thấy (vì require `section='home'`)
3. → Tạo mới article với `section='home'` và `is_deleted=False`

### 4. Updated Queries in `link_home_articles.py`

**All queries now filter out deleted articles:**
```python
# Before
Article.query.filter_by(language='da', is_home=True).all()

# After
Article.query.filter_by(language='da', is_home=True).filter(
    or_(Article.is_deleted == False, Article.is_deleted.is_(None))
).all()
```

**Locations:**
- `link_articles_with_layout()`: Pre-fetch articles
- `link_articles_with_layout()`: Find articles to disable
- `link_articles_with_layout()`: Find existing sliders
- `link_articles_with_layout()`: Find EN articles via canonical_id
- `link_articles_with_layout()`: Final check for EN articles
- `create_missing_en_articles()`: Fetch DA articles
- `create_missing_en_articles()`: Check existing EN articles
- `create_missing_en_articles()`: Final check for EN articles
- Matching DA ↔ KL: Get DA and KL articles

### 5. Main Flow Updates

```python
# Step 0: Mark old articles (BEFORE crawl)
if should_process_all:
    for lang in ['kl', 'da', 'en']:
        mark_list_articles_for_deletion(language=lang, dry_run=args.dry_run)
else:
    mark_list_articles_for_deletion(language=args.language, dry_run=args.dry_run)

# Step 1: Crawl KL layout (tạo mới KL articles)
kl_layout_items = crawl_home_layout(language='kl', ...)

# Step 1.1: ⚠️ DELETE old KL articles NGAY sau khi crawl, TRƯỚC KHI link
delete_marked_articles(language='kl', dry_run=args.dry_run)

# Step 1.2: Link KL articles (chỉ new articles, no duplicates)
link_articles_with_layout(kl_layout_items, language='kl', ...)

# Step 2: Crawl DA layout (tạo mới DA articles)
layout_items = crawl_home_layout(language='da', ...)

# Step 2.1: ⚠️ DELETE old DA articles NGAY sau khi crawl, TRƯỚC KHI link
delete_marked_articles(language='da', dry_run=args.dry_run)

# Step 2.2: Link DA articles (chỉ new articles, no duplicates)
link_articles_with_layout(layout_items, language='da', ...)

# Step 3: Create EN articles từ DA
create_missing_en_articles(layout_items, language='da', ...)

# Step 3.1: ⚠️ DELETE old EN articles NGAY sau khi tạo mới, TRƯỚC KHI link
delete_marked_articles(language='en', dry_run=args.dry_run)

# Step 3.2: Link EN articles (chỉ new articles, no duplicates)
link_articles_with_layout(layout_items, language='en', ...)
```

**⚠️ KEY CHANGE:** Delete AFTER crawl (create new), BEFORE link
- Tránh duplicate: Old (is_deleted=True, is_home=True) + New (is_deleted=False, is_home=True)

## ✅ Benefits

1. **Always fresh data**: Mỗi lần chạy đều tạo mới `1_with_list` articles
2. **Minimize downtime**: User chỉ thấy sự không ổn định trong vài giây (khi delete old)
3. **No URL conflicts**: Không lo trùng URL vì articles cũ đã bị mark deleted
4. **Clean database**: Articles cũ được xóa sau khi link xong

## ⚠️ Notes

### Why mark → crawl → delete → link (not delete immediately)?

- **Mark first**: Đánh dấu old articles để crawl biết cần tạo mới
- **Crawl**: Tạo new articles (is_deleted=False, section='home')
- **Delete BEFORE link**: Xóa old articles TRƯỚC KHI link
  - ✅ Tránh duplicate: Old + New cùng URL cùng is_home=True
  - ✅ Khi link, chỉ còn new articles
- **Link**: Update metadata cho new articles (display_order, layout_data, etc.)

**Result:**
- No duplicates trên home page
- User experience ổn định (thấy old → instant switch → thấy new)
- Link step đơn giản hơn (không lo conflict với old articles)

### Why only for 1_with_list_left/right?

- Các layout type này thường có `list_items` phức tạp
- Khó merge/update vì cấu trúc lồng nhau
- Dễ nhất là recreate từ đầu

### What about other layout types?

- Các layout type khác (1_full, 2_articles, etc.) vẫn update như bình thường
- Chỉ update metadata, không recreate

## 🧪 Testing

### Dry Run
```bash
python scripts/link_home_articles.py --dry-run
```
- Sẽ log tất cả actions nhưng không thực hiện
- Kiểm tra xem có bao nhiêu articles sẽ bị mark/delete

### Production Run
```bash
python scripts/link_home_articles.py
```
- Thực hiện đầy đủ flow
- Mark → Crawl → Link → Delete

### Check Database
```sql
-- Check marked articles (should be 0 after delete step)
SELECT COUNT(*) FROM articles WHERE is_deleted = TRUE;

-- Check 1_with_list articles
SELECT id, language, layout_type, section, is_deleted, created_at 
FROM articles 
WHERE layout_type IN ('1_with_list_left', '1_with_list_right')
ORDER BY language, created_at DESC;
```

## 📝 Migration

Run migration script để thêm `is_deleted` field:
```bash
cd flask
python deploy/migrate_add_is_deleted.py
```

Rollback nếu cần:
```bash
python deploy/migrate_add_is_deleted.py --rollback
```

---

**Last Updated**: 2026-01-29
**Status**: ✅ Implemented

