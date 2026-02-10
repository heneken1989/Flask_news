# Translation trong link_home_articles.py

## Tóm tắt

**File `link_home_articles.py` CÓ dịch articles từ DA sang EN**, sử dụng 2 methods khác nhau:

1. **Dịch toàn bộ article**: Dùng `translate_article()` từ `services.translation_service`
2. **Dịch các field riêng lẻ**: Dùng `GoogleTranslator` từ `deep_translator` library

## Library dịch

### 1. `deep_translator.GoogleTranslator`
- **Library**: `deep_translator` (Python package)
- **Method**: `GoogleTranslator(source='da', target='en')`
- **Dùng cho**: Dịch các field riêng lẻ (kicker, title_parts, slider_title, etc.)

### 2. `services.translation_service.translate_article()`
- **Function**: `translate_article(dk_article, target_language='en', delay=0.5)`
- **Bên trong**: Cũng dùng `GoogleTranslator` từ `deep_translator`
- **Dùng cho**: Dịch toàn bộ article (title, content, excerpt, layout_data)

## Các vị trí dịch trong file

### 1. Dịch toàn bộ article (dòng 544, 1316, 1612)

**Khi nào**: Khi tạo EN article mới từ DA article

```python
# Dòng 544: Trong link_articles_with_layout()
en_article = translate_article(
    da_article,
    target_language='en',
    delay=0.5
)

# Dòng 1316: Trong create_or_update_5_articles_en()
en_article = translate_article(
    da_latest,
    target_language='en',
    delay=delay
)

# Dòng 1612: Trong create_missing_en_articles()
en_article = translate_article(
    da_article,
    target_language='en',
    delay=delay
)
```

**Method**: `translate_article()` từ `services.translation_service`
- Dịch: `title`, `content`, `excerpt`, và các field trong `layout_data` (kicker, kicker_floating, kicker_below, title_parts, list_items, list_title, slider_title, etc.)

### 2. Dịch các field riêng lẻ trong layout_data (dòng 683-770)

**Khi nào**: Khi update DA article và cần sync EN article tương ứng

```python
# Dòng 683-684: Import và khởi tạo
from deep_translator import GoogleTranslator
translator = GoogleTranslator(source='da', target='en')

# Dòng 691-696: Dịch kicker_floating
translated_kicker = translator.translate(merged_layout_data['kicker_floating'])

# Dòng 705-709: Dịch kicker_below
translated_kicker_below = translator.translate(merged_layout_data['kicker_below'])

# Dòng 717-770: Dịch title_parts
# ⚠️ QUAN TRỌNG: Dùng EN article's title để reconstruct title_parts
# thay vì dịch từng part riêng lẻ (tránh dịch sai tên riêng)
if en_article.title:
    translated_title = en_article.title
    # Reconstruct title_parts từ translated_title
    # ...
else:
    # Fallback: Dịch từng part như cũ
    for part in merged_layout_data['title_parts']:
        translated_text = translator.translate(text_to_translate)
```

**Method**: `GoogleTranslator.translate()` trực tiếp
- Dịch: `kicker_floating`, `kicker_below`, `title_parts` (fallback)

### 3. Dịch slider containers (dòng 1155-1203)

**Khi nào**: Khi translate slider/job_slider containers từ DA sang EN

```python
# Dòng 1158-1159: Import và khởi tạo
from deep_translator import GoogleTranslator
translator = GoogleTranslator(source='da', target='en')

# Dòng 1163: Dịch slider title
en_slider.title = translator.translate(da_slider.title)

# Dòng 1172: Dịch slider_title trong layout_data
translated_title = translator.translate(en_layout_data['slider_title'])

# Dòng 1181: Dịch header_link text
translated_text = translator.translate(header_link['text'])

# Dòng 1194: Dịch slider_articles titles
article_copy['title'] = translator.translate(article_copy['title'])
```

**Method**: `GoogleTranslator.translate()` trực tiếp
- Dịch: `title`, `slider_title`, `header_link.text`, `slider_articles[].title`, `slider_articles[].kicker`

### 4. Dịch URL (dòng 553, 1565, 1621)

**Khi nào**: Khi tạo EN article và cần translate URL

```python
# Dòng 553, 1565, 1621: Dùng translate_url()
from scripts.translate_article_urls import translate_url

en_url = translate_url(da_article.published_url, delay=0.3)
if en_url:
    en_article.published_url_en = en_url
```

**Method**: `translate_url()` từ `scripts.translate_article_urls`
- Dịch: `published_url` → `published_url_en`

## Flow dịch article

### Khi link articles với layout:

1. **Tìm article trong DB** (dòng 461-586)
   - Nếu không tìm thấy EN article → Tạo mới bằng `translate_article()` (dòng 544)

2. **Update layout_data cho DA article** (dòng 604-650)
   - Nếu DA article có display fields thay đổi → Tự động update EN article tương ứng (dòng 672-787)
   - Dùng `GoogleTranslator` để dịch các field riêng lẻ

3. **Tạo EN articles còn thiếu** (dòng 1466-1709)
   - Function `create_missing_en_articles()`: Tạo EN articles cho các DA articles trong layout chưa có EN version
   - Dùng `translate_article()` để dịch toàn bộ article

### Khi translate slider containers:

1. **Function `translate_slider_containers()`** (dòng 1055-1248)
   - Tìm DA sliders
   - Tạo/update EN sliders
   - Dùng `GoogleTranslator` để dịch các field trong slider

## Tóm tắt methods và libraries

| Vị trí | Method | Library | Dùng cho |
|--------|--------|---------|----------|
| Dòng 544, 1316, 1612 | `translate_article()` | `deep_translator.GoogleTranslator` (bên trong) | Dịch toàn bộ article |
| Dòng 683-770 | `GoogleTranslator.translate()` | `deep_translator` | Dịch field riêng lẻ trong layout_data |
| Dòng 1158-1203 | `GoogleTranslator.translate()` | `deep_translator` | Dịch slider containers |
| Dòng 553, 1565, 1621 | `translate_url()` | `scripts.translate_article_urls` | Dịch URL |

## Kết luận

✅ **File `link_home_articles.py` CÓ dịch articles từ DA sang EN**

✅ **Library**: `deep_translator` (Python package)
- Class: `GoogleTranslator`
- Method: `GoogleTranslator(source='da', target='en').translate(text)`

✅ **Methods dịch**:
1. `translate_article()` - Dịch toàn bộ article (wrapper function)
2. `GoogleTranslator.translate()` - Dịch text trực tiếp
3. `translate_url()` - Dịch URL

✅ **Tất cả đều dùng Google Translate API** (qua `deep_translator` library)
