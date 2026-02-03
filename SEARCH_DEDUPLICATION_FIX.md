# 🔍 Search Function Deduplication Fix

## 📋 Vấn Đề

Khi search, có nhiều kết quả trùng lặp vì:
- 1 article có thể được update nhiều lần (content update)
- Mỗi version có `title` và `published_url` khác nhau
- Nhưng cùng `image_data->>'element_guid'` (image header ID)
- Hiển thị tất cả versions → trùng lặp trong kết quả search

**Ví dụ:**
```
Article 1: title="Debat om USA..." created_at=2026-02-01, image_element_guid="abc123"
Article 2: title="Debat om USA..." created_at=2026-02-02, image_element_guid="abc123"
Article 3: title="Debat om USA..." created_at=2026-02-03, image_element_guid="abc123"

→ Hiển thị cả 3 → TRÙNG LẶP!
```

---

## ✅ Giải Pháp

### Logic Deduplication:

1. **Group by `image_data->>'element_guid'`**
   - Nhóm các articles có cùng image header ID

2. **Lấy `MAX(id)` trong mỗi group**
   - Article có ID lớn nhất = version mới nhất (vì ID auto-increment)
   - Alternatively: có thể dùng `MAX(created_at)` nhưng ID an toàn hơn

3. **Order by `created_at DESC`**
   - Hiển thị articles mới nhất trước

4. **Fallback cho articles không có image**
   - Nếu `image_data` = NULL → dùng `article.id` để không bị lọc nhầm

---

## 🔧 Implementation

### File: `views/article_views.py` - Route `/cse` (search)

**Trước (có duplicate):**
```python
# Simple query - lấy TẤT CẢ articles match
query = Article.query.filter(
    Article.language == current_language,
    Article.is_temp == False
).filter(
    or_(
        Article.title.ilike(search_pattern),
        Article.excerpt.ilike(search_pattern),
        ...
    )
)
```

**Sau (đã deduplicate):**
```python
# Subquery: Get MAX(id) for each unique image element_guid
subquery = db.session.query(
    func.max(Article.id).label('max_id')
).filter(
    # Search conditions...
).group_by(
    func.coalesce(
        func.cast(Article.image_data['element_guid'], db.String),
        func.cast(Article.id, db.String)  # Fallback
    )
).subquery()

# Main query: Only get articles with IDs from subquery
query = Article.query.filter(
    Article.id.in_(
        db.session.query(subquery.c.max_id)
    )
)

# Order by created_at DESC (newest first)
query = query.order_by(Article.created_at.desc())
```

---

## 📊 SQL Query Equivalent

```sql
-- Subquery: Get max ID for each unique image_element_guid
WITH latest_articles AS (
    SELECT MAX(id) as max_id
    FROM articles
    WHERE language = 'da'
      AND is_temp = FALSE
      AND (
          title ILIKE '%search_term%'
          OR excerpt ILIKE '%search_term%'
          OR content ILIKE '%search_term%'
          OR LOWER(tags::text) LIKE '%search_term%'
      )
    GROUP BY COALESCE(
        image_data->>'element_guid',
        id::text
    )
)

-- Main query: Get full article data for latest versions only
SELECT a.*
FROM articles a
WHERE a.id IN (SELECT max_id FROM latest_articles)
ORDER BY a.created_at DESC
LIMIT 20 OFFSET 0;  -- pagination
```

---

## 🧪 Testing

### Test Case 1: Articles với cùng image_header_id

**Setup:**
```sql
-- Tạo 3 versions của cùng 1 article
INSERT INTO articles (title, image_data, created_at, language) VALUES
('Version 1', '{"element_guid": "test-123"}', '2026-02-01', 'da'),
('Version 2', '{"element_guid": "test-123"}', '2026-02-02', 'da'),
('Version 3', '{"element_guid": "test-123"}', '2026-02-03', 'da');
```

**Expected:**
- Search "Version" → CHỈ return 1 result: "Version 3" (mới nhất)

### Test Case 2: Articles không có image_data

**Setup:**
```sql
-- Articles without image_data
INSERT INTO articles (title, image_data, created_at, language) VALUES
('No Image 1', NULL, '2026-02-01', 'da'),
('No Image 2', NULL, '2026-02-02', 'da');
```

**Expected:**
- Search "No Image" → Return CẢ 2 (vì không có element_guid để group)

### Test Case 3: Mixed (có và không có image)

**Expected:**
- Articles có image → deduplicate
- Articles không có image → giữ nguyên
- Tất cả order by created_at DESC

---

## 📝 Test Script

```python
# File: flask/scripts/test_search_deduplication.py

from app import app
from database import db, Article
from datetime import datetime, timedelta

with app.app_context():
    # Test 1: Create duplicate articles with same image_guid
    print("Creating test articles...")
    
    for i in range(1, 4):
        article = Article(
            title=f"Test Debat Version {i}",
            slug=f"test-debat-v{i}",
            content="Test content",
            excerpt="Test excerpt",
            section="samfund",
            language="da",
            is_temp=False,
            image_data={
                "element_guid": "test-duplicate-123",
                "desktop_jpeg": "/static/test.jpg"
            },
            created_at=datetime.now() - timedelta(days=3-i)  # V3 newest
        )
        db.session.add(article)
    
    db.session.commit()
    print("✓ Created 3 duplicate articles")
    
    # Test 2: Search and verify deduplication
    from views.article_views import search
    from flask import request
    
    print("\nSearching for 'Debat'...")
    
    # Simulate search request
    with app.test_request_context('/?q=Debat&lang=da'):
        results = search()
        # Should return only 1 article (Version 3)
    
    print(f"✓ Search returned {len(results)} result(s)")
    print(f"  Expected: 1 (only newest version)")
```

---

## 🎯 Benefits

### Trước:
```
Search "Debat" → 15 results
  - Debat om USA v1 (2026-01-01)
  - Debat om USA v2 (2026-01-15)
  - Debat om USA v3 (2026-02-01)  ← cùng article
  - Debat om USA v4 (2026-02-02)  ← cùng article
  - ...
→ User thấy nhiều kết quả trùng lặp 😕
```

### Sau:
```
Search "Debat" → 8 unique results
  - Debat om USA v4 (2026-02-02)  ← CHỈ version mới nhất
  - Other Debat article 1
  - Other Debat article 2
  - ...
→ User chỉ thấy unique articles 😊
```

---

## ⚠️ Trade-offs

### Pros:
- ✅ Loại bỏ duplicate results
- ✅ User experience tốt hơn
- ✅ Hiển thị version mới nhất (chính xác nhất)

### Cons:
- ⚠️ Query phức tạp hơn (subquery)
- ⚠️ Có thể chậm hơn chút với large dataset
- ⚠️ Nếu 2 articles khác nhau có cùng image → chỉ show 1

### Performance:
- Với < 10,000 articles: No noticeable impact
- Với > 100,000 articles: Có thể cần index trên `image_data->>'element_guid'`

**Tạo index nếu cần:**
```sql
CREATE INDEX idx_articles_image_element_guid 
ON articles ((image_data->>'element_guid'));
```

---

## 🔄 Rollback Plan

Nếu có issue, revert lại query cũ:

```python
# Simple query (no deduplication)
query = Article.query.filter(
    Article.language == current_language,
    Article.is_temp == False,
    or_(
        Article.title.ilike(search_pattern),
        Article.excerpt.ilike(search_pattern),
        Article.content.ilike(search_pattern),
        func.lower(func.cast(Article.tags, db.String)).contains(search_query.lower())
    )
).order_by(
    Article.published_date.desc().nullslast()
)
```

---

## 📅 Timeline

- **2026-02-03:** Identified duplicate issue in search results
- **2026-02-03:** Implemented deduplication using GROUP BY image_element_guid
- **2026-02-03:** Testing in progress

---

## 👤 Maintenance Notes

- Nếu article được update (new version), old version sẽ tự động bị filter out
- Không cần manual cleanup old versions
- Search luôn hiển thị version mới nhất dựa vào MAX(id)
