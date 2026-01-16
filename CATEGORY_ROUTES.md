# 📂 Category Routes - /tag/<section>

## 🎯 Tổng Quan

Mỗi category trong menu sẽ có route riêng để hiển thị 50 articles mới nhất từ category đó.

## 🛣️ Routes

### **Available Routes:**
- `/tag/samfund` - Articles từ section "samfund"
- `/tag/erhverv` - Articles từ section "erhverv"
- `/tag/kultur` - Articles từ section "kultur"
- `/tag/sport` - Articles từ section "sport"
- `/tag/job` - Articles từ section "job" (nếu có)

### **Home Page:**
- `/` - Hiển thị 50 articles mới nhất (tất cả sections hoặc section mặc định)

## 📋 Logic

### **1. Route Handler** (`views/article_views.py`)

```python
@article_view_bp.route('/tag/<section>')
def tag_section(section):
    # Query articles từ database theo section
    articles = Article.query.filter_by(section=section)\
                            .order_by(Article.display_order.asc())\
                            .limit(50).all()
    
    # Convert và áp dụng pattern grid_size
    articles = [article.to_dict() for article in articles]
    articles = apply_grid_size_pattern(articles)
    
    # Render template
    return render_template('front_page.html', ...)
```

### **2. Database Query**

- **Filter:** `Article.query.filter_by(section=section)`
- **Order:** `order_by(Article.display_order.asc())`
- **Limit:** `.limit(50)`

### **3. Template**

Sử dụng cùng template `front_page.html` như home page, nhưng với:
- `section` khác nhau
- `section_title` khác nhau (ví dụ: "Tag: Erhverv")
- Articles được filter theo section

## 🎨 Menu Links

Menu đã có sẵn links trong `templates/partials/header.html`:
- `/tag/samfund`
- `/tag/erhverv`
- `/tag/kultur`
- `/tag/sport`
- `https://job.sermitsiaq.ag` (JOB - external link)

## 📊 Data Flow

```
User clicks menu → /tag/erhverv
    ↓
Route handler: tag_section('erhverv')
    ↓
Query: Article.query.filter_by(section='erhverv').limit(50)
    ↓
Apply grid_size pattern (2-3-2-3-2-3...)
    ↓
Render: front_page.html với articles từ section 'erhverv'
```

## ✅ Features

1. ✅ **Filter theo section**: Chỉ hiển thị articles từ section được chọn
2. ✅ **50 articles mới nhất**: Sắp xếp theo `display_order`
3. ✅ **Pattern 2-3-2-3-2-3...**: Tự động áp dụng grid_size pattern
4. ✅ **Cùng template**: Sử dụng `front_page.html` như home page
5. ✅ **Section title**: Hiển thị "Tag: [Section Name]"

## 🧪 Test

### **Test routes:**
```bash
# Start Flask app
python3 app.py

# Test routes:
# http://localhost:5000/tag/samfund
# http://localhost:5000/tag/erhverv
# http://localhost:5000/tag/kultur
# http://localhost:5000/tag/sport
```

### **Test với database:**
```bash
# Crawl articles cho từng section
python3 scripts/crawl_articles.py samfund
python3 scripts/crawl_articles.py erhverv
python3 scripts/crawl_articles.py kultur
python3 scripts/crawl_articles.py sport
```

## 📝 Lưu ý

1. **Section validation**: Chỉ accept các sections hợp lệ (samfund, erhverv, kultur, sport, job)
2. **Fallback**: Nếu không có articles trong database, sẽ hiển thị mock data
3. **Display order**: Quan trọng để match pattern 2-3-2-3-2-3...
4. **Menu links**: Đã có sẵn trong header template, không cần sửa

## 🔄 Workflow

1. User click vào menu "ERHVERV"
2. Navigate đến `/tag/erhverv`
3. Route handler query 50 articles từ section "erhverv"
4. Áp dụng grid_size pattern
5. Render với `front_page.html`
6. Hiển thị 50 articles theo pattern 2-3-2-3-2-3...

