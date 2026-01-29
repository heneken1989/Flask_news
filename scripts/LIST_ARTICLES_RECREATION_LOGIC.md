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
│ Step 1-N: Process articles như bình thường             │
│ - Link articles với layout                            │
│ - Match DA ↔ KL                                        │
│ - Create EN articles                                   │
│ - CHƯA DELETE articles cũ → user vẫn thấy old data   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Step Final: Delete old marked articles                │
│ - DELETE articles có is_deleted=True                  │
│ - Theo ngôn ngữ: KL, DA, EN                           │
│ - SAU BƯỚC NÀY: User chỉ thấy new data                │
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
Link  │ Old articles still visible      │ Old: is_deleted=True
  ↓   │ (but new articles prepared)     │ New: is_deleted=False, linked ✓
  ↓   │                                 │
Delete│ 🔄 SWITCH: Old → New            │ Old: DELETED ✓
  ↓   │                                 │ New: is_deleted=False, linked
Final │ ✅ New articles visible         │ New: is_deleted=False, linked
```

**⚠️ QUAN TRỌNG**: Thời gian user thấy sự không ổn định được minimize:
- Mark + Crawl + Link: User vẫn thấy old data (stable)
- Delete: Instant switch từ old → new (< 1 giây)

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

# ... (crawl, link, translate)

# Step Final: Delete marked articles (AFTER link)
if should_process_all:
    for lang in ['kl', 'da', 'en']:
        delete_marked_articles(language=lang, dry_run=args.dry_run)
else:
    delete_marked_articles(language=args.language, dry_run=args.dry_run)
```

## ✅ Benefits

1. **Always fresh data**: Mỗi lần chạy đều tạo mới `1_with_list` articles
2. **Minimize downtime**: User chỉ thấy sự không ổn định trong vài giây (khi delete old)
3. **No URL conflicts**: Không lo trùng URL vì articles cũ đã bị mark deleted
4. **Clean database**: Articles cũ được xóa sau khi link xong

## ⚠️ Notes

### Why mark instead of delete immediately?

- **Mark first**: Cho phép crawl tạo mới mà không lo trùng URL
- **Delete later**: Sau khi new articles đã sẵn sàng và linked
- **Result**: User experience tốt hơn (không thấy "missing articles")

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

