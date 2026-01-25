# Home Layout Workflow - Thứ tự chạy Scripts

## 📋 Tổng quan Flow

```
1. Crawl Layout Structure → JSON/CSV
   ↓
2. Link Articles với Layout → Update DB (is_home=True)
   ↓
3. View hiển thị từ DB
```

## 🔄 Chi tiết từng bước

### Bước 1: Crawl Layout Structure

**Script:** `flask/scripts/crawl_home_layout.py`

**Mục đích:** Crawl cấu trúc layout của trang home (chỉ metadata, không crawl nội dung articles)

**Command:**
```bash
cd flask
python scripts/crawl_home_layout.py --language da --save --csv
```

**Options:**
- `--language` hoặc `-l`: Language code (`da`, `kl`, `en`) - default: `da`
- `--save` hoặc `-s`: Lưu vào file JSON
- `--csv`: Lưu vào file CSV (để xem dễ hơn)
- `--max-articles` hoặc `-n`: Số lượng articles tối đa (0 = tất cả)
- `--no-headless`: Chạy browser ở chế độ visible (để debug)
- `--url` hoặc `-u`: URL của trang home (mặc định: `https://www.sermitsiaq.ag`)

**Output:**
- File JSON: `flask/scripts/home_layouts/home_layout_da_YYYYMMDD_HHMMSS.json`
- File CSV: `flask/scripts/home_layouts/home_layout_da_YYYYMMDD_HHMMSS.csv`

**Nội dung:**
- `published_url`: URL của từng article
- `layout_type`: Loại layout (1_full, 2_articles, 3_articles, slider, etc.)
- `display_order`: Thứ tự hiển thị
- `row_index`, `article_index_in_row`: Vị trí trong layout
- `slider_articles`: Danh sách articles trong slider (nếu có)

**Ví dụ:**
```bash
# Crawl DA home layout
python scripts/crawl_home_layout.py --language da --save --csv

# Crawl KL home layout
python scripts/crawl_home_layout.py --language kl --url https://kl.sermitsiaq.ag --save --csv

# Crawl với giới hạn số lượng
python scripts/crawl_home_layout.py --language da --save --csv --max-articles 30
```

---

### Bước 2: Link Articles với Layout → Update DB

**Script:** `flask/scripts/link_home_articles.py`

**Mục đích:** Link articles đã có trong DB với layout structure, update metadata (is_home=True, display_order, layout_type)

**Command:**
```bash
cd flask
python scripts/link_home_articles.py --crawl --language da
```

**Hoặc load từ file JSON đã crawl:**
```bash
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_20260124_115345.json --language da
```

**Options:**
- `--crawl` hoặc `-c`: Crawl layout trực tiếp (không cần --layout-file)
- `--layout-file` hoặc `-f`: Path to layout JSON file
- `--language` hoặc `-l`: Language code (`da`, `kl`, `en`) - default: `da`
- `--url` hoặc `-u`: URL của trang home (chỉ dùng khi --crawl)
- `--dry-run`: Chỉ log, không update database
- `--no-reset`: Không reset `is_home=False` trước (mặc định: có reset)
- `--no-headless`: Chạy browser ở chế độ visible (chỉ dùng khi --crawl)

**Quá trình:**
1. **Reset** (mặc định): Set `is_home=False` cho tất cả articles của language đó
2. **Load layout** từ JSON hoặc crawl trực tiếp
3. **Link articles**: Với mỗi layout item:
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

**Ví dụ:**
```bash
# Link từ file JSON đã crawl
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_20260124_115345.json --language da

# Crawl và link trực tiếp
python scripts/link_home_articles.py --crawl --language da

# Dry run (chỉ xem, không update)
python scripts/link_home_articles.py --crawl --language da --dry-run

# Không reset (giữ lại articles cũ)
python scripts/link_home_articles.py --crawl --language da --no-reset
```

---

### Bước 3: View hiển thị từ DB

**Route:** `/home-test`

**Mục đích:** Hiển thị home page với articles đã được link

**URL:**
```
http://localhost:5000/home-test
http://localhost:5000/home-test?lang=da
http://localhost:5000/home-test?lang=kl
http://localhost:5000/home-test?lang=en
```

**Quá trình:**
1. Tìm file JSON mới nhất cho language (nếu có)
2. Nếu có JSON → Load và link với articles trong DB (chỉ trong memory)
3. Nếu không có JSON → Query trực tiếp từ DB (articles đã được link ở Bước 2)
4. Prepare layouts bằng `prepare_home_layouts()`
5. Render template `home_page.html`

**Lưu ý:**
- View không update DB, chỉ đọc và hiển thị
- Nếu chưa chạy Bước 2, view sẽ trống (không có articles với `is_home=True`)

---

## 📝 Workflow hoàn chỉnh

### Workflow mới (khuyến nghị)

```bash
# 1. Crawl layout structure
cd flask
python scripts/crawl_home_layout.py --language da --save --csv

# 2. Link articles với layout (reset và update DB)
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_YYYYMMDD_HHMMSS.json --language da

# 3. Xem view
# Mở browser: http://localhost:5000/home-test?lang=da
```

### Workflow nhanh (crawl và link cùng lúc)

```bash
# Crawl và link trực tiếp (không lưu file)
cd flask
python scripts/link_home_articles.py --crawl --language da

# Xem view
# Mở browser: http://localhost:5000/home-test?lang=da
```

---

## 🔄 Cập nhật định kỳ

**Khi nào cần chạy lại:**
- Khi trang home có articles mới
- Khi layout structure thay đổi
- Định kỳ (ví dụ: mỗi giờ, mỗi ngày)

**Command:**
```bash
# Crawl layout mới
python scripts/crawl_home_layout.py --language da --save --csv

# Link với articles (sẽ reset is_home=False trước)
python scripts/link_home_articles.py --layout-file scripts/home_layouts/home_layout_da_YYYYMMDD_HHMMSS.json --language da
```

**Lưu ý:**
- Mỗi lần chạy `link_home_articles.py` sẽ reset `is_home=False` trước
- Sau đó mới set `is_home=True` cho articles trong layout mới
- → Đảm bảo home page luôn hiển thị đúng articles mới nhất

---

## 📂 File Structure

```
flask/
├── scripts/
│   ├── crawl_home_layout.py          # Bước 1: Crawl layout structure
│   ├── link_home_articles.py         # Bước 2: Link articles với layout
│   └── home_layouts/                 # Thư mục chứa layout files
│       ├── home_layout_da_YYYYMMDD_HHMMSS.json
│       └── home_layout_da_YYYYMMDD_HHMMSS.csv
├── views/
│   └── article_views.py               # Bước 3: View /home-test
└── templates/
    └── home_page.html                 # Template hiển thị
```

---

## ⚠️ Troubleshooting

### View trống

**Nguyên nhân:**
1. Chưa chạy `link_home_articles.py` → Không có articles với `is_home=True`
2. Language mismatch → Articles là 'da' nhưng view query 'en'
3. Articles không có `layout_type` → Bị filter ra

**Giải pháp:**
```bash
# Kiểm tra articles trong DB
python -c "from app import app; from database import Article; app.app_context().push(); articles = Article.query.filter_by(is_home=True, language='da').limit(10).all(); print(f'Found {len(articles)} articles'); [print(f'  - {a.id}: {a.title[:50]}... (layout_type={a.layout_type})') for a in articles]"

# Chạy lại link_home_articles.py
python scripts/link_home_articles.py --crawl --language da
```

### Articles không hiển thị ở tag pages

**Nguyên nhân:** Script đã update `section='home'` → Articles không còn thuộc tag gốc

**Giải pháp:** Script đã được sửa để giữ nguyên `section` gốc. Nếu vẫn bị, kiểm tra:
```bash
# Kiểm tra section của articles
python -c "from app import app; from database import Article; app.app_context().push(); articles = Article.query.filter_by(is_home=True, language='da').limit(10).all(); [print(f'  - {a.id}: section={a.section}, is_home={a.is_home}') for a in articles]"
```

---

## 📚 Related Documentation

- `HOME_LAYOUT_TO_VIEW_FLOW.md`: Chi tiết flow từ layout đến view
- `README_HOME_LAYOUT.md`: Hướng dẫn sử dụng scripts
- `HOME_ARTICLES_SKIP_UPDATE_LOGIC.md`: Logic skip và update articles

