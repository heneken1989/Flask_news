# Grid Pattern Logic: 2-3-2-3-2-3...

## Pattern Mô Tả

Hiển thị 50 articles theo pattern:
- **Hàng 1**: 2 articles (mỗi article `grid_size = 6`)
- **Hàng 2**: 3 articles (mỗi article `grid_size = 4`)
- **Hàng 3**: 2 articles (mỗi article `grid_size = 6`)
- **Hàng 4**: 3 articles (mỗi article `grid_size = 4`)
- ... và lặp lại

## Cách Hoạt Động

### 1. Tính `grid_size` dựa trên `display_order`

File: `utils.py` → `calculate_grid_size_pattern(display_order)`

```python
# Pattern: 2-3-2-3-2-3...
# Row 0: articles 0-1 (2 articles, grid_size=6)
# Row 1: articles 2-4 (3 articles, grid_size=4)
# Row 2: articles 5-6 (2 articles, grid_size=6)
# Row 3: articles 7-9 (3 articles, grid_size=4)
```

**Ví dụ:**
- `display_order = 0, 1` → `grid_size = 6` (row 0)
- `display_order = 2, 3, 4` → `grid_size = 4` (row 1)
- `display_order = 5, 6` → `grid_size = 6` (row 2)
- `display_order = 7, 8, 9` → `grid_size = 4` (row 3)

### 2. Áp dụng Pattern cho Articles

File: `utils.py` → `apply_grid_size_pattern(articles)`

Hàm này:
1. Lặp qua từng article
2. Lấy `display_order` từ article (hoặc dùng index nếu không có)
3. Tính `grid_size` dựa trên `display_order`
4. Set `grid_size` vào article

### 3. Render trong Template

File: `templates/partials/main_body.html`

Logic tự động:
- Tạo row mới khi `current_row_size == 0` hoặc `current_row_size + article_grid_size > 12`
- Mỗi row có tổng `grid_size` = 12 (Foundation grid system)
- Row 0: 6 + 6 = 12 → đóng row
- Row 1: 4 + 4 + 4 = 12 → đóng row
- Row 2: 6 + 6 = 12 → đóng row
- ...

## Sử Dụng

### Trong View (`views/article_views.py`):

```python
from utils import apply_grid_size_pattern
from database import Article

# Query articles từ database
articles = Article.query.order_by(Article.display_order.asc()).limit(50).all()
articles = [article.to_dict() for article in articles]

# Áp dụng pattern grid_size
articles = apply_grid_size_pattern(articles)

# Render template
return render_template('front_page.html', articles=articles, ...)
```

### Trong Database:

Mỗi article cần có `display_order`:
- Article đầu tiên: `display_order = 0`
- Article thứ hai: `display_order = 1`
- ...
- Article thứ 50: `display_order = 49`

## Kết Quả

Với 50 articles:
- **Row 0**: Articles 0-1 (2 articles, grid_size=6 mỗi)
- **Row 1**: Articles 2-4 (3 articles, grid_size=4 mỗi)
- **Row 2**: Articles 5-6 (2 articles, grid_size=6 mỗi)
- **Row 3**: Articles 7-9 (3 articles, grid_size=4 mỗi)
- ...
- **Row 19**: Articles 48-49 (2 articles, grid_size=6 mỗi)

Tổng: ~20 rows với pattern 2-3-2-3-2-3...

## Lưu Ý

1. **`display_order` là bắt buộc**: Mỗi article phải có `display_order` để tính đúng pattern
2. **Logic tự động**: Template `main_body.html` tự động tạo row mới khi tổng `grid_size` > 12
3. **Flexible**: Có thể thay đổi pattern bằng cách sửa `calculate_grid_size_pattern()` trong `utils.py`

