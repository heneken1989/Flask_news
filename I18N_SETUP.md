# Hướng dẫn Setup Đa Ngôn Ngữ (i18n) cho Flask App

## 📚 Libraries được sử dụng

1. **Flask-Babel** - Library tiêu chuẩn cho Flask i18n (hỗ trợ gettext)
2. **googletrans** - Tự động dịch bằng Google Translate API (miễn phí, không cần API key)
3. **deep-translator** - Alternative với nhiều dịch vụ (Google, Microsoft, etc.)

## 🚀 Cài đặt

```bash
pip install Flask-Babel googletrans==4.0.0rc1 deep-translator
```

## 📁 Cấu trúc thư mục

```
flask/
├── babel.cfg              # Cấu hình Babel
├── translations/          # Thư mục chứa translations
│   ├── da/               # Tiếng Đan Mạch (Danish)
│   │   └── LC_MESSAGES/
│   │       ├── messages.po
│   │       └── messages.mo
│   ├── en/              # Tiếng Anh
│   │   └── LC_MESSAGES/
│   │       ├── messages.po
│   │       └── messages.mo
│   └── kl/              # Tiếng Greenland (Kalaallisut)
│       └── LC_MESSAGES/
│           ├── messages.po
│           └── messages.mo
└── scripts/
    └── translate_strings.py  # Script để tự động dịch
```

## 🔧 Cấu hình

### 1. Cập nhật `app.py`

Đã được cập nhật với:
- Flask-Babel initialization
- Language detection từ URL hoặc browser
- Helper functions để dịch

### 2. Sử dụng trong Templates

```jinja2
{# Sử dụng gettext #}
<h1>{{ _('Welcome') }}</h1>
<p>{{ _('This is a news portal') }}</p>

{# Sử dụng với variables #}
<p>{{ _('Hello, %(name)s!', name=user_name) }}</p>

{# Sử dụng với context #}
<p>{{ _('Article') }}: {{ article.title }}</p>
```

### 3. Sử dụng trong Python Code

```python
from flask_babel import gettext as _, lazy_gettext as _l

# Trong view functions
def index():
    title = _('Home Page')
    return render_template('home_page.html', title=title)

# Lazy translation (cho constants)
MESSAGES = {
    'error': _l('An error occurred'),
    'success': _l('Operation successful')
}
```

## 🌐 Ngôn ngữ được hỗ trợ

- **da** (Danish) - Ngôn ngữ mặc định
- **en** (English)
- **kl** (Kalaallisut/Greenlandic)

## 📝 Workflow

### Bước 1: Extract strings từ code

```bash
pybabel extract -F babel.cfg -k _ -o messages.pot .
```

**Lưu ý:** Bạn cần thêm `_('...')` vào code/templates trước khi extract. Ví dụ:
- Trong template: `{{ _('Welcome') }}`
- Trong Python: `title = _('Home Page')`

### Bước 2: Tạo file translation mới (chỉ lần đầu)

```bash
pybabel init -i messages.pot -d translations -l en
pybabel init -i messages.pot -d translations -l kl
```

### Bước 3: Cập nhật translations (khi có strings mới)

```bash
pybabel update -i messages.pot -d translations
```

### Bước 4: Tự động dịch bằng Google Translate

```bash
python scripts/translate_strings.py
```

**Lưu ý:** 
- Chỉ hỗ trợ English (en). Greenlandic (kl) không được Google Translate hỗ trợ, cần dịch thủ công.
- Script sẽ tự động bỏ qua metadata và chỉ dịch các strings thực sự.

### Bước 5: Review và chỉnh sửa translations

Edit file `translations/en/LC_MESSAGES/messages.po` để review và chỉnh sửa bản dịch.

### Bước 6: Compile translations

```bash
pybabel compile -d translations
```

**Sau khi compile, restart Flask app để áp dụng translations mới.**

## 🔄 Tự động dịch với Google Translate

Script `scripts/translate_strings.py` sẽ:
1. Đọc file `.po` chưa dịch
2. Tự động dịch bằng Google Translate
3. Cập nhật file `.po` với bản dịch

**Lưu ý:** 
- Google Translate có giới hạn rate limit
- Nên review bản dịch sau khi tự động dịch
- Có thể dùng API key để tăng rate limit

## 🌍 Chuyển đổi ngôn ngữ

### Trong URL

```
http://localhost:5000/?lang=en
http://localhost:5000/?lang=da
http://localhost:5000/?lang=kl
```

### Trong Template

```jinja2
<a href="{{ url_for('set_language', lang='en') }}">English</a>
<a href="{{ url_for('set_language', lang='da') }}">Dansk</a>
<a href="{{ url_for('set_language', lang='kl') }}">Kalaallisut</a>
```

## 📖 Ví dụ sử dụng

Xem file `templates/home_page.html` để xem ví dụ sử dụng `_()` function.

## ⚠️ Lưu ý

1. **Performance**: Lazy translation (`_l`) cho constants, `_()` cho dynamic content
2. **Pluralization**: Sử dụng `ngettext()` cho số nhiều
3. **Context**: Sử dụng `pgettext()` nếu cần context
4. **Date/Time**: Sử dụng `format_date()`, `format_time()`, `format_datetime()` từ Flask-Babel

