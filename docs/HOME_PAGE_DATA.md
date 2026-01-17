# Trang Home - Cách Lấy Data từ Database

## Tổng Quan

Trang home (`/`) hiển thị articles với nhiều layout types khác nhau. Để một article xuất hiện trên trang home, nó cần:

1. **`is_home = True`** - Đánh dấu article thuộc trang home
2. **`layout_type` không null** - Xác định cách hiển thị (1_full, 2_articles, 3_articles, etc.)
3. **`display_order`** - Thứ tự hiển thị (0, 1, 2, ...)

## Query Hiện Tại

```python
articles = Article.query.filter(
    Article.is_home == True,
    Article.layout_type.isnot(None)
).order_by(Article.display_order.asc()).limit(100).all()
```

## Các Field Quan Trọng

### 1. `is_home` (Boolean)
- **Mục đích**: Đánh dấu article thuộc trang home
- **Default**: `False`
- **Khi nào set**: Khi muốn đưa article lên trang home

### 2. `layout_type` (String)
- **Mục đích**: Xác định cách hiển thị article trên trang home
- **Các giá trị**:
  - `'1_full'`: 1 article full width (headline t46)
  - `'2_articles'`: 2 articles 1 row (headline t38)
  - `'3_articles'`: 3 articles 1 row (headline t24)
  - `'1_special_bg'`: 1 article với special background (bg-black, headline t48)
  - `'1_with_list_left'`: 1 article + list titles bên trái
  - `'1_with_list_right'`: 1 article + list titles bên phải

### 3. `layout_data` (JSON)
- **Mục đích**: Lưu thêm data cho layout đặc biệt
- **Ví dụ**:
  ```json
  {
    "kicker": "Breaking News",
    "list_title": "SENESTE",
    "list_items": [
      {"title": "Article 1", "url": "/article1"},
      {"title": "Article 2", "url": "/article2"}
    ]
  }
  ```

### 4. `display_order` (Integer)
- **Mục đích**: Thứ tự hiển thị trên trang home
- **Default**: `0`
- **Sắp xếp**: ASC (0, 1, 2, ...)

## Workflow Để Đưa Article Lên Home

### Cách 1: Set khi crawl (nếu crawl từ trang home)
```python
article = Article(
    title="...",
    is_home=True,  # Đánh dấu thuộc home
    layout_type='1_full',  # Chọn layout type
    display_order=0,  # Set thứ tự
    layout_data={'kicker': 'Breaking'}  # Nếu cần
)
```

### Cách 2: Update sau khi crawl
```python
# Lấy article từ database
article = Article.query.filter_by(id=article_id).first()

# Set để đưa lên home
article.is_home = True
article.layout_type = '2_articles'
article.display_order = 5
article.layout_data = {'kicker': 'News'}

db.session.commit()
```

### Cách 3: Bulk update nhiều articles
```python
# Đưa tất cả articles của section 'samfund' lên home
articles = Article.query.filter_by(section='samfund').all()
for idx, article in enumerate(articles):
    article.is_home = True
    article.layout_type = '3_articles'  # Hoặc layout khác
    article.display_order = idx

db.session.commit()
```

## Phân Biệt: Home vs Section Pages

| Field | Home Page | Section Page |
|-------|-----------|--------------|
| `is_home` | `True` | `False` (hoặc `NULL`) |
| `layout_type` | Required (không null) | Optional (có thể null) |
| `display_order` | Quan trọng (sắp xếp) | Quan trọng (sắp xếp) |
| `section` | Có thể từ nhiều sections | Chỉ 1 section |

## Ví Dụ: Query Articles cho Home

```python
# Lấy tất cả articles cho home, sắp xếp theo display_order
home_articles = Article.query.filter(
    Article.is_home == True,
    Article.layout_type.isnot(None)
).order_by(Article.display_order.asc()).all()

# Lấy articles cho home với layout type cụ thể
full_width_articles = Article.query.filter(
    Article.is_home == True,
    Article.layout_type == '1_full'
).order_by(Article.display_order.asc()).all()
```

## Migration

Để thêm field `is_home` vào database:

```bash
cd flask
python deploy/migrate_add_is_home.py
```

## Notes

- Articles crawl từ sections thông thường (`/tag/samfund`, `/tag/erhverv`) **KHÔNG** tự động có `is_home=True`
- Cần **manually set** `is_home=True` và `layout_type` để đưa article lên home
- Có thể có script riêng để crawl từ trang home và tự động set các fields này

