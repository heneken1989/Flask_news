# Flow từ Layout Home đến View

## 📋 Tổng quan Flow

```
1. Crawl Layout Structure (CSV/JSON)
   ↓
2. Link Articles với Layout → Update DB
   ↓
3. View Query từ DB → Hiển thị
```

## 🔄 Chi tiết từng bước

### Bước 1: Crawl Layout Structure

**Script:** `crawl_home_layout.py`

```bash
# Crawl và lưu vào CSV + JSON
python scripts/crawl_home_layout.py --language da --save --csv
```

**Kết quả:**
- File CSV: `scripts/home_layouts/home_layout_da_20260124_115345.csv`
- File JSON: `scripts/home_layouts/home_layout_da_20260124_115345.json`

**Nội dung:**
- Layout structure: published_url, layout_type, display_order
- Chưa có articles trong DB được link

### Bước 2: Link Articles với Layout → Update DB

**Script:** `link_home_articles.py`

```bash
# Link articles với layout và update DB
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_20260124_115345.json --language da
```

**Quá trình:**
1. **Reset tất cả articles** (mặc định):
   - Set `is_home = False` cho tất cả articles của language này
   - Vì mỗi lần crawl, articles trên home sẽ khác nhau
   
2. Load layout structure từ JSON

3. Với mỗi layout item:
   - Tìm article trong DB bằng `published_url`
   - Nếu tìm thấy → Update:
     - `is_home = True` ⚠️ **QUAN TRỌNG**: Chỉ update is_home, KHÔNG update section
     - Giữ nguyên `section` gốc (samfund, sport, etc.) để articles vẫn hiển thị ở tag pages
     - `display_order` = từ layout
     - `layout_type` = từ layout
     - `layout_data` = từ layout
   - Nếu không tìm thấy → Log warning (không tạo mới)

**Kết quả:**
- Articles trong DB được update với metadata từ layout
- Articles có `is_home=True` → hiển thị ở home
- Articles vẫn giữ `section` gốc → vẫn hiển thị ở tag pages

**Options:**
- `--no-reset`: Không reset `is_home=False` trước (mặc định: có reset)
- `--dry-run`: Chỉ log, không update DB

### Bước 3: View Query từ DB → Hiển thị

**Route:** `/home-test`

**Quá trình:**
1. Query articles từ DB:
   ```python
   articles = Article.query.filter_by(
       is_home=True,
       section='home',
       language=current_language
   ).order_by(Article.display_order).all()
   ```
2. Render template với articles đã được link

## ⚠️ Vấn đề hiện tại

Nếu bạn chưa chạy **Bước 2** (link_home_articles.py), thì:
- Layout structure đã có (CSV/JSON)
- Nhưng articles trong DB chưa được link (`is_home=False` hoặc `section != 'home'`)
- → View sẽ không có articles để hiển thị

## ✅ Giải pháp

### Option 1: Chạy link_home_articles.py trước

```bash
# 1. Crawl layout (nếu chưa có)
python scripts/crawl_home_layout.py --language da --save --csv

# 2. Link articles với layout (sẽ reset is_home=False trước)
python scripts/link_home_articles.py --crawl --language da

# 3. Xem view
http://localhost:5000/home-test
```

**Lưu ý:** Mỗi lần chạy `link_home_articles.py`:
- Sẽ reset tất cả `is_home=False` trước (cho language đó)
- Sau đó mới set `is_home=True` cho articles trong layout mới
- → Đảm bảo home page luôn hiển thị đúng articles mới nhất

### Option 2: View tự động link (tạm thời)

View `/home-test` tự động link layout với articles khi load (không update DB, chỉ trong memory).

## 🔍 Kiểm tra

**Check articles đã được link chưa:**
```sql
SELECT COUNT(*) FROM articles 
WHERE is_home=True AND section='home' AND language='da';
```

**Nếu = 0 → Chưa chạy link_home_articles.py**

