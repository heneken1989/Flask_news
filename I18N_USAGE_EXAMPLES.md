# Ví dụ Sử dụng i18n trong Flask App

## 📝 Trong Templates (Jinja2)

### Cơ bản

```jinja2
{# Sử dụng gettext #}
<h1>{{ _('Welcome') }}</h1>
<p>{{ _('This is a news portal') }}</p>

{# Với variables #}
<p>{{ _('Hello, %(name)s!', name=user_name) }}</p>
<p>{{ _('Article: %(title)s', title=article.title) }}</p>
```

### Trong home_page.html

```jinja2
{% extends "base.html" %}

{% block head %}
    <title>{{ _('Home') }} - Sermitsiaq</title>
{% endblock %}

{% block content %}
    <h1>{{ _('Latest News') }}</h1>
    <p>{{ _('Read the latest articles from Greenland') }}</p>
    
    {# Language switcher #}
    <div class="language-switcher">
        <a href="{{ url_for('set_language', lang='da') }}">Dansk</a>
        <a href="{{ url_for('set_language', lang='en') }}">English</a>
        <a href="{{ url_for('set_language', lang='kl') }}">Kalaallisut</a>
    </div>
{% endblock %}
```

### Trong header/footer

```jinja2
{# partials/header.html #}
<nav>
    <a href="/">{{ _('Home') }}</a>
    <a href="/articles">{{ _('Articles') }}</a>
    <a href="/about">{{ _('About') }}</a>
</nav>
```

## 🐍 Trong Python Code

### Trong View Functions

```python
from flask_babel import gettext as _

@article_view_bp.route('/')
def index():
    title = _('Home Page')
    description = _('Welcome to our news portal')
    return render_template('home_page.html', title=title, description=description)
```

### Lazy Translation (cho constants)

```python
from flask_babel import lazy_gettext as _l

# Constants được dịch khi sử dụng
MESSAGES = {
    'error': _l('An error occurred'),
    'success': _l('Operation successful'),
    'loading': _l('Loading...')
}

# Sử dụng
message = str(MESSAGES['error'])  # Dịch theo ngôn ngữ hiện tại
```

### Pluralization

```python
from flask_babel import ngettext

count = 5
message = ngettext('%(num)d article', '%(num)d articles', count, num=count)
# Danish: "5 artikler"
# English: "5 articles"
```

### Format Date/Time

```python
from flask_babel import format_date, format_time, format_datetime
from datetime import datetime

date = datetime.now()
formatted = format_date(date)  # Format theo locale
formatted_time = format_time(date)
formatted_datetime = format_datetime(date)
```

## 🌍 Chuyển đổi Ngôn ngữ

### Trong URL

```
http://localhost:5000/?lang=en
http://localhost:5000/?lang=da
http://localhost:5000/?lang=kl
```

### Trong Template (Language Switcher)

```jinja2
<div class="language-switcher">
    <a href="{{ url_for('set_language', lang='da') }}" 
       class="{% if session.get('language', 'da') == 'da' %}active{% endif %}">
        🇩🇰 Dansk
    </a>
    <a href="{{ url_for('set_language', lang='en') }}"
       class="{% if session.get('language', 'da') == 'en' %}active{% endif %}">
        🇬🇧 English
    </a>
    <a href="{{ url_for('set_language', lang='kl') }}"
       class="{% if session.get('language', 'da') == 'kl' %}active{% endif %}">
        🇬🇱 Kalaallisut
    </a>
</div>
```

## 📋 Workflow

### 1. Extract strings

```bash
pybabel extract -F babel.cfg -k _ -o messages.pot .
```

### 2. Tạo translation files

```bash
pybabel init -i messages.pot -d translations -l en
pybabel init -i messages.pot -d translations -l kl
```

### 3. Tự động dịch (Google Translate)

```bash
python scripts/translate_strings.py
```

### 4. Review và chỉnh sửa translations

Edit file `translations/en/LC_MESSAGES/messages.po` và `translations/kl/LC_MESSAGES/messages.po`

### 5. Compile translations

```bash
pybabel compile -d translations
```

### 6. Update translations (khi có strings mới)

```bash
pybabel extract -F babel.cfg -k _ -o messages.pot .
pybabel update -i messages.pot -d translations
python scripts/translate_strings.py  # Tự động dịch strings mới
pybabel compile -d translations
```

## 🎯 Best Practices

1. **Luôn sử dụng `_()` cho user-facing strings**
2. **Sử dụng `_l()` cho constants** (lazy translation)
3. **Sử dụng `ngettext()` cho pluralization**
4. **Format dates/times với `format_date()`, `format_time()`, `format_datetime()`**
5. **Review bản dịch tự động** - Google Translate không hoàn hảo
6. **Giữ context trong strings** - Ví dụ: `_('Delete article')` thay vì `_('Delete')`

## 📖 Ví dụ thực tế

Xem file `templates/home_page.html` và `views/article_views.py` để xem ví dụ sử dụng trong code thực tế.

