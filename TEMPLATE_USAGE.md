# 📖 Hướng dẫn sử dụng Template với Header/Footer Reuse

## ✅ Đã tạo

1. **`templates/base.html`** - Base template với cấu trúc chung
2. **`templates/partials/header.html`** - Header partial (tách từ 1.html)
3. **`templates/partials/footer.html`** - Footer partial (tách từ 1.html)
4. **`templates/partials/head.html`** - Head section (tách từ 1.html)
5. **`templates/article.html`** - Ví dụ template sử dụng base

## 🎯 Cách sử dụng

### **Cách 1: Template Inheritance (Khuyến nghị)**

Tạo template mới extend từ `base.html`:

```jinja2
{% extends "base.html" %}

{% block head %}
    {# Custom head nếu cần #}
    {% include 'partials/head.html' %}
    <title>My Custom Page</title>
{% endblock %}

{% block content %}
    <h1>My Content</h1>
    <p>Content goes here...</p>
{% endblock %}
```

### **Cách 2: Include Direct**

Sử dụng trực tiếp trong template:

```jinja2
<!DOCTYPE html>
<html>
<head>
    <title>My Page</title>
</head>
<body>
    {% include 'partials/header.html' %}
    
    <main>
        <h1>My Content</h1>
    </main>
    
    {% include 'partials/footer.html' %}
</body>
</html>
```

## 📝 Ví dụ trong View

```python
from flask import render_template

@app.route('/article/<int:article_id>')
def article(article_id):
    article_data = {
        'title': 'Article Title',
        'description': 'Article description',
        'id': article_id
    }
    
    return render_template('article.html',
        article=article_data,
        article_id=article_id,
        section='samfund',
        tags='tag1,tag2'
    )
```

## 🔄 So sánh

| Cách | Ưu điểm | Nhược điểm |
|------|---------|------------|
| **Template Inheritance** | ✅ Cấu trúc rõ ràng<br>✅ Dễ maintain<br>✅ Flexible | Cần hiểu Jinja2 |
| **Include Direct** | ✅ Đơn giản<br>✅ Dễ hiểu | ❌ Lặp lại code<br>❌ Khó maintain |

## 📂 Cấu trúc files

```
templates/
├── base.html              # Base template
├── article.html           # Article template (extend base)
├── 1.html                # File gốc (giữ nguyên)
└── partials/
    ├── header.html        # Header (reuse)
    ├── footer.html        # Footer (reuse)
    └── head.html          # Head section (reuse)
```

## 🚀 Lợi ích

1. **DRY (Don't Repeat Yourself)**: Header và footer chỉ định nghĩa 1 lần
2. **Dễ maintain**: Sửa header/footer ở 1 chỗ, tất cả pages đều update
3. **Flexible**: Có thể override từng phần trong child templates
4. **Backward compatible**: File `1.html` vẫn hoạt động bình thường

