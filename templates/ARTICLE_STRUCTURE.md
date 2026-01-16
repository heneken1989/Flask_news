# 📋 Cấu trúc Article Grid Template

Hướng dẫn sử dụng template cho body section với articles grid.

## 🎯 Cấu trúc

```
templates/
├── partials/
│   ├── article_item.html      # Single article item
│   ├── article_row.html       # Row chứa articles
│   └── main_body.html         # Main section body
├── front_page.html            # Front page template
└── base.html                 # Base template
```

## 📝 Article Data Structure

Mỗi article cần có cấu trúc dữ liệu như sau:

```python
article = {
    'element_guid': '1d8fc071-5df6-43e1-8879-f9eab34d3c45',
    'title': 'Article Title',
    'url': 'https://www.sermitsiaq.ag/erhverv/article-slug/2329217',
    'k5a_url': 'https://www.sermitsiaq.ag/a/2329217',
    'section': 'erhverv',
    'site_alias': 'sermitsiaq',
    'instance': '100090',
    'published_date': '2026-01-15T20:29:57+01:00',
    'is_paywall': True,  # hoặc False
    'paywall_class': 'paywall',  # hoặc '' nếu không phải paywall
    'grid_size': 6,  # 6 = 2 per row, 4 = 3 per row
    'image': {
        'element_guid': 'd614121f-9a2d-4264-ba21-98d8f8a43458',
        'desktop_webp': 'https://image.sermitsiaq.ag/2329220.jpg?...&format=webp',
        'desktop_jpeg': 'https://image.sermitsiaq.ag/2329220.jpg?...&format=jpg',
        'mobile_webp': 'https://image.sermitsiaq.ag/2329220.jpg?...&format=webp',
        'mobile_jpeg': 'https://image.sermitsiaq.ag/2329220.jpg?...&format=jpg',
        'fallback': 'https://image.sermitsiaq.ag/2329220.jpg?...',
        'desktop_width': '524',
        'desktop_height': '341',
        'mobile_width': '480',
        'mobile_height': '312',
        'alt': 'Image alt text',
        'title': 'Image title'
    }
}
```

## 🚀 Cách sử dụng

### **1. Trong View (Python)**

```python
from flask import render_template

@app.route('/')
def front_page():
    # Mock data - sau này sẽ lấy từ API
    articles = [
        {
            'title': 'Article 1',
            'url': '/article/1',
            'section': 'erhverv',
            'grid_size': 6,  # 2 per row
            'is_paywall': False,
            'image': {
                'desktop_webp': 'https://image.sermitsiaq.ag/1.jpg?...',
                'mobile_webp': 'https://image.sermitsiaq.ag/1.jpg?...',
                'fallback': 'https://image.sermitsiaq.ag/1.jpg'
            }
        },
        {
            'title': 'Article 2',
            'url': '/article/2',
            'section': 'erhverv',
            'grid_size': 6,  # 2 per row
            'is_paywall': True,
            'paywall_class': 'paywall',
            'image': {...}
        },
        # ... more articles
    ]
    
    return render_template('front_page.html',
        articles=articles,
        section_title='Tag: erhverv',
        articles_per_row=2,  # 2 articles per row
        section='erhverv'
    )
```

### **2. Grid Layout Options**

- **2 articles per row**: `grid_size: 6` (large-6)
- **3 articles per row**: `grid_size: 4` (large-4)
- **1 article per row**: `grid_size: 12` (large-12)

### **3. Template Usage**

```jinja2
{# Trong base.html hoặc template khác #}
{# Jinja2 không hỗ trợ 'with' trong include, dùng set trước #}
{% set articles = articles %}
{% set section_title = 'Tag: erhverv' %}
{% set articles_per_row = 2 %}
{% include 'partials/main_body.html' %}
```

## 📐 Grid System

Dựa trên Foundation Grid (12 columns):

- `large-6` = 6/12 = 50% → **2 articles per row**
- `large-4` = 4/12 = 33.33% → **3 articles per row**
- `large-8` = 8/12 = 66.67% → **1.5 articles per row** (ít dùng)

## 🔧 Customization

### **Custom Article Item**

Nếu cần custom article item, tạo template mới:

```jinja2
{# templates/partials/article_item_custom.html #}
<article class="column large-{{ grid_size }}">
    {# Custom structure #}
</article>
```

### **Mixed Grid Layout**

Để có mixed layout (2 articles, rồi 3 articles), group articles:

```python
# Trong view
articles_row_1 = articles[:2]  # 2 articles
articles_row_2 = articles[2:5]  # 3 articles
```

## ✅ Checklist

- [x] Article item template
- [x] Article row template  
- [x] Main body section template
- [x] Front page template
- [ ] API integration (sẽ làm sau)
- [ ] Image optimization helper
- [ ] Pagination support

