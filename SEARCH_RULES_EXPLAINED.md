# 🔍 SEARCH FUNCTION - QUY TẮC VÀ GIẢI THÍCH

## 📋 Tóm Tắt

Search function tìm kiếm articles dựa trên **5 trường chính**:
1. **Title** (Tiêu đề)
2. **Excerpt** (Trích dẫn/Mô tả ngắn)
3. **Content** (Nội dung đầy đủ)
4. **Tags** (Thẻ tag - JSON array)
5. **Author** (Tác giả - trong article_details.content_blocks) ✨ **NEW!**

**❌ KHÔNG search trong:**
- Category name
- Section name
- Published date
- Image metadata (ngoại trừ author info trong article_meta block)

---

## 🎯 Chi Tiết Từng Trường

### 1️⃣ **Title** (Tiêu đề bài viết)

**Database field:** `articles.title`  
**Type:** `VARCHAR(500)`  
**Search method:** `ILIKE` (case-insensitive, partial match)

**Ví dụ:**
```sql
-- User search: "USA"
-- Query: title ILIKE '%USA%'

✓ Match: "Debat om USA i Inatsisartut"
✓ Match: "USA vil ikke acceptere"
✓ Match: "Grønland og USA's forhold"
✗ No match: "Debat om Grønland" (không có "USA")
```

**Đặc điểm:**
- ✅ Case-insensitive: "usa" = "USA" = "UsA"
- ✅ Partial match: tìm được "USA" trong "USA's forhold"
- ✅ Match ở bất kỳ vị trí: đầu, giữa, cuối title

---

### 2️⃣ **Excerpt** (Trích dẫn/Mô tả ngắn)

**Database field:** `articles.excerpt`  
**Type:** `TEXT`  
**Search method:** `ILIKE` (case-insensitive, partial match)

**Ví dụ:**
```sql
-- User search: "selvstændig"
-- Query: excerpt ILIKE '%selvstændig%'

✓ Match: "...et selvstændigt Grønland..."
✓ Match: "...selvstændighed er vigtig..."
✗ No match: "...uafhængighed..." (từ khác)
```

**Đặc điểm:**
- ✅ Tìm trong đoạn mô tả ngắn (summary)
- ✅ Thường chứa keywords quan trọng
- ✅ Hiển thị dưới title trong kết quả search

**Excerpt là gì?**
```
Title: "Debat om USA i Inatsisartut"
Excerpt: "USA vil ikke acceptere et selvstændigt Grønland, 
          siger ekspert efter møde i parlamentet"
          ↑ Đây là excerpt - 1-2 câu tóm tắt
```

---

### 3️⃣ **Content** (Nội dung đầy đủ)

**Database field:** `articles.content`  
**Type:** `TEXT` (có thể rất dài - HTML content)  
**Search method:** `ILIKE` (case-insensitive, partial match)

**Ví dụ:**
```sql
-- User search: "Meningsmåling"
-- Query: content ILIKE '%Meningsmåling%'

✓ Match: Article có "Meningsmåling" trong body text
✓ Match: Cả khi từ xuất hiện 1 lần hoặc nhiều lần
```

**Đặc điểm:**
- ✅ Search trong toàn bộ nội dung article
- ✅ Bao gồm cả paragraphs, quotes, lists
- ⚠️ Có thể match nhiều results (vì content dài)

**Content structure:**
```html
<p>Paragraph 1 with some text about Meningsmåling...</p>
<p>Paragraph 2...</p>
<blockquote>Quote about topic...</blockquote>
↑ Tất cả đều được search
```

---

### 4️⃣ **Tags** (Thẻ tag - JSON Array)

**Database field:** `articles.tags`  
**Type:** `JSON` (array of strings)  
**Search method:** `LOWER(tags::text) LIKE '%search_term%'` (case-insensitive)

**Ví dụ tags:**
```json
{
  "tags": ["EU-KOMMISSIONEN", "GRØNLAND", "POLITIK", "USA"]
}
```

**Search logic:**
```sql
-- User search: "politik"
-- Query: LOWER(tags::text) LIKE '%politik%'

✓ Match: tags = ["POLITIK", "SAMFUND"]
✓ Match: tags = ["politik", "ØKONOMI"]
✓ Match: tags = ["lokalpolitik", "valg"]  (partial match trong tag)
✗ No match: tags = ["SAMFUND", "KULTUR"]
```

**Đặc điểm:**
- ✅ Search trong tất cả tags của article
- ✅ Case-insensitive: "POLITIK" = "politik"
- ✅ Partial match: "politik" match "lokalpolitik"
- ⚠️ Convert JSON → string trước khi search

---

### 5️⃣ **Author** (Tác giả) - ✨ **NEW!**

**Database field:** `article_details.content_blocks`  
**Type:** `JSON` (array of content blocks, tìm trong block type='article_meta')  
**Search method:** `LOWER(content_blocks::text) LIKE '%search_term%'` (case-insensitive)

**Structure:**
```json
{
  "type": "article_meta",
  "bylines": [
    {
      "firstname": "Jette",
      "lastname": "Andersen",
      "fullname": "Jette Andersen",
      "description": "REDAKTØR",
      "author_url": null,
      "author_image": null
    }
  ]
}
```

**Search logic:**
```sql
-- User search: "Jette"
-- Query: LOWER(content_blocks::text) LIKE '%jette%'

✓ Match: author fullname = "Jette Andersen"
✓ Match: author firstname = "Jette"
✓ Match: description = "Redaktør Jette"
✗ No match: article without author info
```

**Đặc điểm:**
- ✅ Search trong: fullname, firstname, lastname, description
- ✅ Case-insensitive: "JETTE" = "jette"
- ✅ Partial match: "Jette" match "Jette Andersen"
- ⚠️ Requires JOIN với `article_details` table
- ⚠️ Articles without ArticleDetail sẽ không match author search

**Ví dụ:**
```
Search: "Redaktør"
→ Tìm tất cả articles có author với title "Redaktør"

Search: "Arne Mølgaard"
→ Tìm articles do "Arne Mølgaard" viết

Search: "Tusagassiortoq"
→ Tìm articles có author với description "Tusagassiortoq"
```

**JOIN Logic:**
```python
# LEFT OUTER JOIN để không miss articles không có detail
Article.query.outerjoin(
    ArticleDetail,
    and_(
        Article.published_url == ArticleDetail.published_url,
        Article.language == ArticleDetail.language
    )
)
```

---

## 🔄 Search Flow (Luồng Tìm Kiếm)

```
User nhập: "USA"
    ↓
┌─────────────────────────────────────────────┐
│  Step 1: Parse search query                 │
│  - Trim whitespace                          │
│  - Convert to search pattern: "%USA%"       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Step 2: Search trong 5 fields (OR logic)  │
│  - title ILIKE '%USA%'        OR            │
│  - excerpt ILIKE '%USA%'      OR            │
│  - content ILIKE '%USA%'      OR            │
│  - LOWER(tags) LIKE '%usa%'   OR            │
│  - LOWER(author) LIKE '%usa%' (NEW!)        │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Step 3: Deduplication                      │
│  - Group by image_element_guid              │
│  - Keep only MAX(id) per group              │
│  - Remove duplicate article versions        │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Step 4: Ordering & Pagination              │
│  - ORDER BY created_at DESC                 │
│  - Limit 20 per page                        │
│  - Calculate total pages                    │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Step 5: Return Results                     │
│  - JSON (AJAX) or HTML (first page)         │
│  - Include pagination info                  │
└─────────────────────────────────────────────┘
```

---

## 🎨 OR Logic (Tìm Trong Nhiều Fields)

Search sử dụng **OR logic** - tìm được trong **BẤT KỲ** field nào là OK:

```python
or_(
    Article.title.ilike(search_pattern),      # Field 1
    Article.excerpt.ilike(search_pattern),    # Field 2
    Article.content.ilike(search_pattern),    # Field 3
    func.lower(func.cast(Article.tags, db.String)).contains(search_query.lower()),  # Field 4
    func.lower(func.cast(ArticleDetail.content_blocks, db.String)).contains(search_query.lower())  # Field 5 - Author
)
```

**Ví dụ:**
```
User search: "Grønland"

Article A:
  title: "Debat om Grønland"  ← Match!
  excerpt: "..."
  content: "..."
  tags: ["POLITIK"]
  → Result: ✓ INCLUDED (match in title)

Article B:
  title: "USA forhold"
  excerpt: "..."
  content: "...Grønland er..."  ← Match!
  tags: ["USA"]
  → Result: ✓ INCLUDED (match in content)

Article C:
  title: "Økonomisk situation"
  excerpt: "..."
  content: "..."
  tags: ["GRØNLAND", "ØKONOMI"]  ← Match!
  → Result: ✓ INCLUDED (match in tags)

Article D:
  title: "Sport nyheder"
  excerpt: "..."
  content: "..."
  tags: ["SPORT"]
  → Result: ✗ EXCLUDED (no match anywhere)
```

---

## 🌍 Multi-Language Support

Search **CHỈ trong 1 ngôn ngữ** tại 1 thời điểm:

```python
Article.language == current_language  # 'da', 'kl', or 'en'
```

**Ví dụ:**
```
User on Danish site → search in Danish articles only
User on Kalaallisut site → search in Kalaallisut articles only
User on English site → search in English articles only
```

**Cross-language search: ❌ KHÔNG hỗ trợ**
- Search "USA" trên site DA → CHỈ tìm trong DA articles
- Không tìm trong EN hoặc KL articles

---

## ⚙️ Search Options & Filters

### ✅ Đang Có:

1. **Language filter** (tự động dựa vào current_language)
2. **Exclude temp articles** (`is_temp = False`)
3. **Deduplication** (by image_element_guid)
4. **Pagination** (20 results per page)
5. **Load More** (AJAX)

### ❌ Chưa Có (Có thể thêm sau):

1. **Author filter** (vì không có author field)
2. **Date range filter** (chưa implement)
3. **Section/Category filter** (chưa implement)
4. **Sort options** (hiện tại chỉ sort by created_at DESC)
5. **Advanced search** (AND/OR/NOT operators)
6. **Fuzzy search** (typo tolerance)
7. **Synonyms** (tìm từ đồng nghĩa)

---

## 📊 SQL Query Example

```sql
-- Full search query với deduplication

WITH latest_articles AS (
    -- Subquery: Get MAX(id) for each unique image_element_guid
    SELECT MAX(id) as max_id
    FROM articles
    WHERE 
        language = 'da' 
        AND is_temp = FALSE
        AND (
            -- OR logic: Match ANY of these fields
            title ILIKE '%Grønland%'
            OR excerpt ILIKE '%Grønland%'
            OR content ILIKE '%Grønland%'
            OR LOWER(tags::text) LIKE '%grønland%'
        )
    GROUP BY COALESCE(
        image_data->>'element_guid',
        id::text
    )
)

-- Main query: Get full article data
SELECT 
    a.id,
    a.title,
    a.excerpt,
    a.published_date,
    a.image_data,
    a.published_url,
    a.section,
    a.created_at
FROM articles a
WHERE a.id IN (SELECT max_id FROM latest_articles)
ORDER BY a.created_at DESC
LIMIT 20 OFFSET 0;  -- Page 1
```

---

## 🎯 Ranking (Thứ Tự Ưu Tiên)

**Hiện tại:** Simple date-based ranking
```
ORDER BY created_at DESC
→ Articles mới nhất hiển thị trước
```

**Có thể cải thiện:**
```sql
-- Relevance-based ranking (nâng cao)
ORDER BY 
    CASE 
        WHEN title ILIKE '%search%' THEN 1        -- Title match = highest priority
        WHEN excerpt ILIKE '%search%' THEN 2      -- Excerpt match = medium
        WHEN tags::text ILIKE '%search%' THEN 3   -- Tags match = medium-low
        WHEN content ILIKE '%search%' THEN 4      -- Content match = lowest
    END ASC,
    created_at DESC
```

---

## 🔍 Case-Insensitive Search

Tất cả searches đều **case-insensitive** (không phân biệt hoa/thường):

```sql
-- ILIKE operator (PostgreSQL)
title ILIKE '%usa%'

-- Equivalent to:
LOWER(title) LIKE LOWER('%usa%')

-- Results:
"USA"           → Match ✓
"usa"           → Match ✓
"UsA"           → Match ✓
"USA's"         → Match ✓
"united states" → No match ✗
```

---

## 📝 Special Characters & Danish Letters

**Danish/Kalaallisut letters được hỗ trợ:**
```
Search: "Grønland"
Match:  "Grønland" ✓
Match:  "grønland" ✓
Match:  "GRØNLAND" ✓

Search: "æøå"
Match:  "Københa vn" ✓
Match:  "Måling" ✓
Match:  "Næste år" ✓
```

**Special characters:**
```
Search: "EU-KOMMISSIONEN"
Match:  "EU-KOMMISSIONEN" ✓
Match:  "EU-kommissionen" ✓

Search: "USA's"
Match:  "USA's politik" ✓
```

---

## ⚡ Performance Notes

### Fast Searches:
- ✅ Short queries (1-3 words)
- ✅ Common words (in title/excerpt)
- ✅ With pagination (20 results limit)

### Slow Searches:
- ⚠️ Very long queries (10+ words)
- ⚠️ Rare words (only in content)
- ⚠️ Wildcard at beginning: `%search`

### Optimization Tips:
1. **Add indexes** (if not exist):
   ```sql
   CREATE INDEX idx_articles_title_gin ON articles USING gin(to_tsvector('danish', title));
   CREATE INDEX idx_articles_content_gin ON articles USING gin(to_tsvector('danish', content));
   ```

2. **Full-text search** (future upgrade):
   ```sql
   -- Instead of ILIKE, use to_tsvector
   SELECT * FROM articles
   WHERE to_tsvector('danish', title || ' ' || content) @@ to_tsquery('danish', 'Grønland');
   ```

---

## 🧪 Testing Examples

### Test 1: Title Search
```
Query: "USA"
Expected: Articles with "USA" in title
```

### Test 2: Content Search
```
Query: "selvstændigt"
Expected: Articles with "selvstændigt" in content (even if not in title)
```

### Test 3: Tag Search
```
Query: "politik"
Expected: Articles tagged with "POLITIK" or containing "politik" in other tags
```

### Test 4: Multi-word
```
Query: "Debat om USA"
Expected: Articles containing "Debat om USA" phrase (partial matches OK)
```

### Test 5: Special Characters
```
Query: "Grønland's økonomi"
Expected: Handle Danish letters correctly
```

---

## 📚 Summary

### Fields Searched (Các trường được tìm):
1. ✅ **Title** (Tiêu đề)
2. ✅ **Excerpt** (Trích dẫn)
3. ✅ **Content** (Nội dung)
4. ✅ **Tags** (Thẻ tag)
5. ✅ **Author** (Tác giả - fullname, firstname, lastname, description) ✨ **NEW!**

### NOT Searched (KHÔNG tìm trong):
- ❌ Category name
- ❌ Section name
- ❌ Date
- ❌ Image metadata (except author info)

### Search Logic:
- **OR** between fields (match ANY field)
- **Case-insensitive** (ILIKE)
- **Partial match** ("%search%")
- **Deduplication** (by image_element_guid)
- **Ordered by** created_at DESC

---

**📅 Last Updated:** 2026-02-03  
**💡 Tip:** Để search chính xác hơn, user nên dùng keywords quan trọng từ title hoặc tags!
