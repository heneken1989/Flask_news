# Quy Tắc Phát Hiện Layout Type

Tài liệu này mô tả chi tiết các quy tắc để tự động phát hiện `layout_type` của articles khi crawl từ trang home.

## Tổng Quan

Khi crawl trang home, parser sẽ tự động phân tích cấu trúc HTML để xác định `layout_type` của mỗi article. Các quy tắc được áp dụng theo thứ tự ưu tiên.

## Các Layout Types

1. **`1_full`**: 1 article full width (headline t46)
2. **`2_articles`**: 2 articles 1 row (headline t38)
3. **`3_articles`**: 3 articles 1 row (headline t24)
4. **`1_special_bg`**: 1 article với special background (bg-black, headline t48)
5. **`1_with_list_left`**: 1 article + list titles bên trái
6. **`1_with_list_right`**: 1 article + list titles bên phải

## Quy Tắc Phát Hiện (Theo Thứ Tự Ưu Tiên)

### 1. Kiểm Tra Special Background (Ưu Tiên Cao Nhất)

**Quy tắc:**
- Tìm `<div class="content">` trong article element
- Kiểm tra classes của div này
- Nếu có class `bg-black` → **`1_special_bg`**

**Ví dụ HTML:**
```html
<article class="column small-12 large-12">
    <div class="content bg-black color_mobile_bg-black ...">
        <!-- Article content -->
    </div>
</article>
```

**Code:**
```python
content_div = article_elem.find('div', class_='content')
if content_div:
    content_classes = content_div.get('class', [])
    if 'bg-black' in ' '.join(content_classes):
        return '1_special_bg'
```

---

### 2. Kiểm Tra Grid Size từ Article Classes

**Quy tắc:**
- Lấy tất cả classes của `<article>` element
- Kiểm tra các class liên quan đến grid size

#### 2.1. Full Width (`large-12`)

**Quy tắc:**
- Nếu article có class `large-12` → **`1_full`**

**Ví dụ HTML:**
```html
<article class="column small-12 large-12 small-abs-12 large-abs-12">
    <!-- Article content -->
</article>
```

**Code:**
```python
if 'large-12' in article_class_str:
    return '1_full'
```

---

#### 2.2. Two Articles Per Row (`large-6`)

**Quy tắc:**
- Nếu article có class `large-6` → Có thể là `2_articles` hoặc `1_with_list_*`
- Cần kiểm tra thêm xem có list bên cạnh không

**Ví dụ HTML (2 articles):**
```html
<div class="row">
    <article class="column small-12 large-6">
        <!-- Article 1 -->
    </article>
    <article class="column small-12 large-6">
        <!-- Article 2 -->
    </article>
</div>
```

**Code:**
```python
elif 'large-6' in article_class_str:
    # Check xem có list bên cạnh không
    if row_elem:
        list_elem = row_elem.find('div', class_='articlesByTag')
        if list_elem:
            # Có list → check vị trí
            # ...
        else:
            return '2_articles'  # Không có list → 2 articles
```

---

#### 2.3. Three Articles Per Row (`large-4`)

**Quy tắc:**
- Nếu article có class `large-4` → **`3_articles`**

**Ví dụ HTML:**
```html
<div class="row">
    <article class="column small-12 large-4">
        <!-- Article 1 -->
    </article>
    <article class="column small-12 large-4">
        <!-- Article 2 -->
    </article>
    <article class="column small-12 large-4">
        <!-- Article 3 -->
    </article>
</div>
```

**Code:**
```python
elif 'large-4' in article_class_str:
    return '3_articles'
```

---

### 3. Kiểm Tra List Position (Chỉ khi `large-6`)

**Quy tắc:**
- Chỉ áp dụng khi article có class `large-6`
- Tìm row element chứa article
- Trong row, tìm `<div class="articlesByTag">` hoặc `<div class="toplist">`
- So sánh vị trí của article và list trong row:
  - Nếu list đứng trước article → **`1_with_list_left`**
  - Nếu list đứng sau article → **`1_with_list_right`**
  - Nếu không có list → **`2_articles`**

**Ví dụ HTML (List bên trái):**
```html
<div class="row">
    <div class="column articlesByTag toplist small-12 large-6">
        <!-- List titles -->
    </div>
    <article class="column small-12 large-6">
        <!-- Article -->
    </article>
</div>
```

**Ví dụ HTML (List bên phải):**
```html
<div class="row">
    <article class="column small-12 large-6">
        <!-- Article -->
    </article>
    <div class="column articlesByTag toplist small-12 large-6">
        <!-- List titles -->
    </div>
</div>
```

**Code:**
```python
if row_elem:
    list_elem = row_elem.find('div', class_='articlesByTag')
    if list_elem:
        # Lấy tất cả children của row
        row_children = list(row_elem.children)
        article_index = None
        list_index = None
        
        # Tìm index của article và list
        for idx, child in enumerate(row_children):
            if hasattr(child, 'name'):
                if child.name == 'article' and child == article_elem:
                    article_index = idx
                elif child.name == 'div' and 'articlesByTag' in child.get('class', []):
                    list_index = idx
        
        # So sánh vị trí
        if article_index is not None and list_index is not None:
            if list_index < article_index:
                return '1_with_list_left'  # List đứng trước
            else:
                return '1_with_list_right'  # List đứng sau
```

---

## Default Fallback

**Quy tắc:**
- Nếu không phát hiện được layout type nào → **`1_full`** (default)

**Code:**
```python
# Default
return '1_full'
```

---

## Parse Layout Data

Ngoài việc phát hiện `layout_type`, parser còn extract thêm `layout_data` cho các layout đặc biệt:

### 1. `1_special_bg` - Kicker

**Quy tắc:**
- Tìm `<div class="kicker">` trong article
- Extract text từ kicker element

**Ví dụ HTML:**
```html
<div class="kicker below">
    Breaking News
</div>
```

**Code:**
```python
if layout_type == '1_special_bg':
    kicker_elem = article_elem.find('div', class_='kicker')
    if kicker_elem:
        layout_data['kicker'] = kicker_elem.get_text(strip=True)
```

---

### 2. `1_with_list_left` / `1_with_list_right` - List Items

**Quy tắc:**
- Tìm `<div class="articlesByTag">` trong row
- Extract list title từ `<h3>`
- Extract list items từ các `<li>` elements
- Mỗi item có title từ `<h4 class="abt-title">` và URL từ `<a>`

**Ví dụ HTML:**
```html
<div class="column articlesByTag toplist">
    <h3>SENESTE</h3>
    <ul>
        <li>
            <a href="/article1">
                <h4 class="abt-title">Article Title 1</h4>
            </a>
        </li>
        <li>
            <a href="/article2">
                <h4 class="abt-title">Article Title 2</h4>
            </a>
        </li>
    </ul>
</div>
```

**Code:**
```python
if layout_type in ['1_with_list_left', '1_with_list_right']:
    if row_elem:
        list_elem = row_elem.find('div', class_='articlesByTag')
        if list_elem:
            # Extract list title
            list_title_elem = list_elem.find('h3')
            if list_title_elem:
                layout_data['list_title'] = list_title_elem.get_text(strip=True)
            
            # Extract list items
            list_items = []
            for li in list_elem.find_all('li'):
                link = li.find('a')
                if link:
                    title_elem = li.find('h4', class_='abt-title')
                    if title_elem:
                        list_items.append({
                            'title': title_elem.get_text(strip=True),
                            'url': link.get('href', '')
                        })
            if list_items:
                layout_data['list_items'] = list_items
```

---

## Thứ Tự Kiểm Tra (Flowchart)

```
Start
  ↓
Check content div có class "bg-black"?
  ├─ YES → Return '1_special_bg'
  └─ NO  ↓
         Check article class có "large-12"?
         ├─ YES → Return '1_full'
         └─ NO  ↓
                Check article class có "large-6"?
                ├─ YES → Check có list trong row?
                │   ├─ YES → Check vị trí list
                │   │   ├─ List trước → Return '1_with_list_left'
                │   │   └─ List sau → Return '1_with_list_right'
                │   └─ NO → Return '2_articles'
                └─ NO  ↓
                       Check article class có "large-4"?
                       ├─ YES → Return '3_articles'
                       └─ NO  → Return '1_full' (default)
```

---

## Ví Dụ Thực Tế

### Ví dụ 1: Full Width Article
```html
<article class="column small-12 large-12">
    <div class="content">
        <h2 class="headline t46">Title</h2>
    </div>
</article>
```
**Kết quả:** `layout_type = '1_full'`

---

### Ví dụ 2: Two Articles
```html
<div class="row">
    <article class="column small-12 large-6">
        <h2 class="headline t38">Title 1</h2>
    </article>
    <article class="column small-12 large-6">
        <h2 class="headline t38">Title 2</h2>
    </article>
</div>
```
**Kết quả:** `layout_type = '2_articles'` (cho cả 2 articles)

---

### Ví dụ 3: Special Background
```html
<article class="column small-12 large-12">
    <div class="content bg-black">
        <h2 class="headline t48 white">Title</h2>
    </div>
</article>
```
**Kết quả:** `layout_type = '1_special_bg'`, `layout_data = {'kicker': '...'}` (nếu có)

---

### Ví dụ 4: Article với List
```html
<div class="row">
    <div class="column articlesByTag large-6">
        <h3>SENESTE</h3>
        <ul>
            <li><a href="/1"><h4 class="abt-title">Item 1</h4></a></li>
        </ul>
    </div>
    <article class="column large-6">
        <h2 class="headline t38">Article Title</h2>
    </article>
</div>
```
**Kết quả:** 
- Article: `layout_type = '1_with_list_left'`
- `layout_data = {'list_title': 'SENESTE', 'list_items': [{'title': 'Item 1', 'url': '/1'}]}`

---

## Lưu Ý

1. **Row Element**: Để phát hiện chính xác `1_with_list_left/right`, cần có `row_elem` (row chứa article). Nếu không có, sẽ fallback về `2_articles`.

2. **Multiple Classes**: Article có thể có nhiều classes, parser sẽ check tất cả.

3. **Error Handling**: Nếu có lỗi trong quá trình detect, sẽ return `'1_full'` (default).

4. **Priority**: Special background (`bg-black`) được check đầu tiên vì có thể override grid size.

5. **List Detection**: Chỉ detect list khi article có `large-6` (vì list chỉ xuất hiện với 2-column layout).

---

## Testing

Để test các quy tắc phát hiện, có thể:

1. Crawl trang home và xem logs:
```bash
python scripts/crawl_articles.py home
```

2. Kiểm tra database:
```sql
SELECT layout_type, COUNT(*) 
FROM articles 
WHERE section='home' 
GROUP BY layout_type;
```

3. Xem chi tiết một article:
```python
article = Article.query.filter_by(section='home').first()
print(f"Layout: {article.layout_type}")
print(f"Data: {article.layout_data}")
```

