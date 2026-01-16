# 📋 Cấu trúc Template với Jinja2

Hướng dẫn cách reuse header và footer trong Flask project.

## 🎯 Cấu trúc Template

```
templates/
├── base.html              # Base template (chứa head, header, footer)
├── partials/
│   ├── header.html        # Header partial
│   └── footer.html        # Footer partial
├── article.html           # Article page (extend từ base)
└── 1.html                # File gốc (giữ nguyên)
```

## 📝 Cách sử dụng

### **1. Template Inheritance (Khuyến nghị)**

**base.html:**
```jinja2
<!DOCTYPE html>
<html lang="da-DK" dir="ltr" class="resp_fonts">
<head>
    {% block head %}{% endblock %}
</head>
<body>
    {% include 'partials/header.html' %}
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    {% include 'partials/footer.html' %}
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

**article.html:**
```jinja2
{% extends "base.html" %}

{% block head %}
    <title>Article Title</title>
    <!-- CSS, meta tags, etc. -->
{% endblock %}

{% block content %}
    <!-- Article content here -->
{% endblock %}

{% block scripts %}
    <!-- Page-specific scripts -->
{% endblock %}
```

### **2. Include Direct (Đơn giản hơn)**

**article.html:**
```jinja2
<!DOCTYPE html>
<html>
<head>
    <title>Article</title>
</head>
<body>
    {% include 'partials/header.html' %}
    
    <main>
        <!-- Content -->
    </main>
    
    {% include 'partials/footer.html' %}
</body>
</html>
```

## 🔧 Tách Header và Footer từ 1.html

Header: dòng 450-1229
Footer: dòng 1283-1370

