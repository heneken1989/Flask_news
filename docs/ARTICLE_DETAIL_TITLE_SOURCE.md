# Nguồn Title trong Article Detail Page

## Tóm tắt

**Title trong `article_header` của trang `article_detail` LUÔN dùng từ `article.title`** để đồng nhất với trang home.

### Thứ tự ưu tiên (đã cập nhật):

1. **Priority 1**: `article.title_parts` (nếu có, từ `layout_data`) - để hiển thị với highlights
2. **Priority 2**: `article.title` (fallback)

**⚠️ Đã thay đổi**: Trước đây ưu tiên `article_detail.content_blocks`, nhưng đã được sửa để luôn dùng `article.title` làm nguồn duy nhất.

## Flow chi tiết

### 1. Trong View (`article_views.py`)

```python
# Dòng 1416: Lấy article_detail từ database
article_detail = ArticleDetailParser.get_article_detail_by_article(
    article, 
    language=current_language
)

# Dòng 1420-1428: Nếu article_detail có published_url khác với article.published_url,
# tìm article tương ứng và cập nhật title
if article_detail and article_detail.published_url != article.published_url:
    article_by_url = Article.query.filter_by(
        published_url=article_detail.published_url
    ).first()
    if article_by_url and article_by_url.language == current_language:
        # Cập nhật article title từ article tương ứng
        article.title = article_by_url.title
```

### 2. Trong Template (`article_detail.html`)

```jinja2
{# Dòng 166-179: Luôn dùng article.title để đồng nhất với trang home #}
{% if article.title_parts %}
    {# Priority 1: Dùng title_parts nếu có (từ layout_data) để hiển thị với highlights #}
    <h1 class="headline mainTitle">
        {% for part in article.title_parts %}
            {% if part.color_class %}
                <span class="{{ part.color_class }}">{{ part.text }}</span>
            {% else %}
                {{ part.text }}
            {% endif %}
        {% endfor %}
    </h1>
{% else %}
    {# Priority 2: Fallback về article.title #}
    <h1 class="headline mainTitle">{{ article.title }}</h1>
{% endif %}
```

### 3. Nguồn của `article_detail.content_blocks`

`article_detail` được lấy từ bảng `ArticleDetail` trong database, được crawl từ HTML của article detail page.

Title trong `content_blocks` được parse từ HTML (trong `article_detail_parser.py` dòng 72-92):

```python
# Parse title (h1.headline.mainTitle) - ưu tiên cao nhất
title_elem = article_header.find('h1', class_='headline')
if not title_elem:
    title_elem = article_header.find('h1', class_='mainTitle')
if not title_elem:
    title_elem = article_header.find('h1')

if title_elem:
    title_text = title_elem.get_text(strip=True)
    if title_text:
        blocks.append({
            'type': 'title',
            'order': order,
            'level': 'h1',
            'html': str(title_elem),
            'text': title_text,  # ← Title được lấy từ HTML
            'classes': title_elem.get('class', [])
        })
```

## Kết luận

**Title trong `article_header` LUÔN dùng từ `article.title`** để đồng nhất với trang home:

1. **Ưu tiên**: `article.title_parts` (nếu có, từ `layout_data`) - để hiển thị với highlights
2. **Fallback**: `article.title` từ database

### Lưu ý quan trọng:

- ✅ **Đã đồng nhất**: Cả trang `home` và `article_detail` đều dùng `article.title` hoặc `article.title_parts` làm nguồn
- ✅ **Consistency**: Không còn sự khác biệt giữa title trên home page và article detail page
- `layout_data.title_parts` được dùng cho cả **home page layout** và **article detail page** (để hiển thị title với highlights)

### Thay đổi:

**Trước đây**:
- Trang `article_detail` ưu tiên title từ `article_detail.content_blocks` (parse từ HTML)
- Có thể gây khác biệt với title trên trang home

**Hiện tại**:
- Trang `article_detail` luôn dùng `article.title` hoặc `article.title_parts`
- Đảm bảo đồng nhất với trang home
