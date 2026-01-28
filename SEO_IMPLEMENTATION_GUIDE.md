# 📋 Hướng Dẫn Triển Khai SEO Meta Tags Động

## ✅ Đã tạo

1. **`flask/utils_seo.py`** - Helper functions để generate SEO meta tags
2. **`flask/templates/macros/seo_meta.html`** - Jinja2 macro để render meta tags
3. **`flask/SEO_AUDIT_REPORT.md`** - Báo cáo audit SEO

## 🔧 Cần làm tiếp

### 1. Cập nhật views để pass SEO meta vào template

#### **`flask/views/article_views.py`**

**Trong `article_detail()` function:**
```python
from utils_seo import get_seo_meta, get_structured_data

# Sau khi lấy article, thêm:
seo_meta = get_seo_meta(
    article=article,
    page_type='article',
    language=current_language,
    section=article.section
)
structured_data = get_structured_data(
    article=article,
    page_type='article',
    language=current_language
)

# Pass vào render_template:
return render_template('article_detail.html',
    article=article,
    seo_meta=seo_meta,
    structured_data=structured_data,
    # ... other variables
)
```

**Trong `index()` và `home_test()` functions:**
```python
from utils_seo import get_seo_meta, get_structured_data

# Thêm SEO meta cho home page:
seo_meta = get_seo_meta(
    page_type='home',
    language=current_language,
    title="Sermitsiaq - Grønlands største nyhedssite",
    description="Sermitsiaq er Grønlands største nyhedssite med nyheder, debat og kultur."
)
structured_data = get_structured_data(
    page_type='home',
    language=current_language
)

# Pass vào render_template:
return render_template('home.html',
    seo_meta=seo_meta,
    structured_data=structured_data,
    # ... other variables
)
```

**Trong `tag_section()` function:**
```python
from utils_seo import get_seo_meta, get_structured_data

# Thêm SEO meta cho section page:
seo_meta = get_seo_meta(
    page_type='section',
    language=current_language,
    section=section,
    title=f"Tag: {section_names.get(section, section)} - Sermitsiaq"
)
structured_data = get_structured_data(
    page_type='section',
    language=current_language
)

# Pass vào render_template:
return render_template('tag_section.html',
    seo_meta=seo_meta,
    structured_data=structured_data,
    # ... other variables
)
```

### 2. Cập nhật templates để sử dụng SEO meta

#### **`flask/templates/base.html`**

Thay thế phần hardcoded trong `head.html`:

```jinja2
{% block head %}
    {% if seo_meta %}
        {% from 'macros/seo_meta.html' import render_seo_meta %}
        {{ render_seo_meta(seo_meta) }}
    {% else %}
        {# Fallback: include old head.html #}
        {% include 'partials/head.html' %}
    {% endif %}
    
    {# Structured data #}
    {% if structured_data %}
        {% from 'macros/seo_meta.html' import render_structured_data %}
        {{ render_structured_data(structured_data) }}
    {% endif %}
    
    {# Other head content (CSS, scripts, etc.) #}
    {% include 'partials/head_content.html' %}
{% endblock %}
```

#### **Tạo `flask/templates/partials/head_content.html`**

Tách phần CSS, scripts từ `head.html` sang file mới này (giữ lại phần không phải meta tags).

### 3. Sửa macro `seo_meta.html`

Có một lỗi nhỏ trong macro - `<html>` tag không nên ở trong macro. Sửa như sau:

```jinja2
{# Remove this line from macro: #}
{# <html lang="..." dir="ltr" class="resp_fonts"> #}

{# Keep lang attribute in base.html instead #}
```

Và trong `base.html`:
```jinja2
<html lang="{{ seo_meta.language }}-{{ seo_meta.language.upper() if seo_meta.language == 'da' else 'GL' if seo_meta.language == 'kl' else 'US' }}" dir="ltr" class="resp_fonts">
```

## 🧪 Testing

Sau khi implement, test các trang:

1. **Home page** (`/`):
   - Check title, description, og:image
   - Check hreflang tags

2. **Article page** (`/<section>/<slug>/<id>`):
   - Check title = article.title
   - Check description = article.excerpt
   - Check og:image = article.image_data
   - Check canonical URL
   - Check structured data (JSON-LD)

3. **Section page** (`/tag/<section>`):
   - Check title, description
   - Check hreflang tags

## 📝 Notes

- **Image URLs**: Đảm bảo `article.image_data` có format đúng
- **URLs**: Function `get_seo_meta()` tự động convert relative URLs thành absolute
- **Hreflang**: Chỉ hiển thị nếu article có translations
- **Fallback**: Nếu không có `seo_meta`, sẽ dùng `head.html` cũ (backward compatible)

## 🚀 Deployment

Sau khi test xong, deploy:
1. `flask/utils_seo.py`
2. `flask/templates/macros/seo_meta.html`
3. Updated views và templates

