# Article Detail Structure

## Tổng quan

Bảng `article_details` lưu trữ cấu trúc chi tiết của bài viết, sử dụng `published_url` để link với bảng `articles`.

## Database Schema

### Bảng `article_details`

```sql
CREATE TABLE article_details (
    id SERIAL PRIMARY KEY,
    published_url VARCHAR(1000) UNIQUE NOT NULL,
    content_blocks JSONB,
    language VARCHAR(10) DEFAULT 'en',
    element_guid VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_article_details_published_url ON article_details(published_url);
```

### Link với bảng `articles`

- Sử dụng `published_url` để link (không dùng foreign key để tránh ràng buộc)
- Một `published_url` chỉ có một `article_detail`
- Có thể query: `ArticleDetail.query.filter_by(published_url=article.published_url).first()`

## Cấu trúc Content Blocks

`content_blocks` là một JSON array chứa các blocks theo thứ tự:

### 1. Intro Block

```json
{
  "type": "paragraph",
  "order": 0,
  "html": "<p>...</p>",
  "text": "Text content",
  "classes": ["class1", "class2"]
}
```

### 2. Paragraph Block

```json
{
  "type": "paragraph",
  "order": 1,
  "html": "<p>...</p>",
  "text": "Text content",
  "classes": []
}
```

### 3. Heading Block

```json
{
  "type": "heading",
  "order": 2,
  "level": "h3",
  "html": "<h3>...</h3>",
  "text": "Heading text",
  "classes": []
}
```

### 4. Image Block

```json
{
  "type": "image",
  "order": 3,
  "element_guid": "32eb8d42-ccd7-43ad-a529-ff443357dccf",
  "image_sources": {
    "desktop_webp": "https://...",
    "desktop_jpeg": "https://...",
    "mobile_webp": "https://...",
    "mobile_jpeg": "https://...",
    "fallback": "https://...",
    "alt": "Image alt text",
    "title": "Image title",
    "width": "678",
    "height": "841"
  },
  "caption": "Image caption text",
  "author": "Foto: Privat",
  "float_class": "floatLeft",
  "classes": ["column", "desktop-floatLeft", "mobile-floatLeft"],
  "html": "<figure>...</figure>"
}
```

### 5. Ad Block

```json
{
  "type": "ad",
  "order": 4,
  "element_guid": "31b92396-3977-4ce4-ddeb-24eff9ca5150",
  "ad_id": "2018-Artikelbanner",
  "classes": ["column", "google-ad", "floatRight"],
  "html": "<div>...</div>"
}
```

### 6. Paywall Offer Block

```json
{
  "type": "paywall_offer",
  "order": 5,
  "offers": [
    {
      "name": "Sermitsiaq.gl - web artikler",
      "pros": [
        "Adgang til alle artikler på Sermitsiaq.gl",
        "Pr. måned kr. 59.00",
        "Pr. år kr. 650.00"
      ],
      "cta_text": "Vælg",
      "cta_url": "/køb-abonnement"
    }
  ],
  "description": "Kære Læser, ...",
  "html": "<div class='iteras-offers'>...</div>"
}
```

## Usage

### Parse và lưu content

```python
from services.article_detail_parser import ArticleDetailParser

# Parse và lưu content
article_detail = ArticleDetailParser.save_article_detail(
    published_url='https://www.sermitsiaq.ag/samfund/article/123',
    html_content=raw_html,
    language='en',
    element_guid='guid-123'
)
```

### Lấy article detail

```python
from services.article_detail_parser import ArticleDetailParser

# Lấy từ published_url
article_detail = ArticleDetailParser.get_article_detail(
    published_url='https://www.sermitsiaq.ag/samfund/article/123'
)

# Lấy từ Article object
article_detail = ArticleDetailParser.get_article_detail_by_article(article)
```

### Render trong template

```jinja2
{% if article_detail %}
    {% for block in article_detail.content_blocks %}
        {% if block.type == 'paragraph' %}
            <div class="bodytext content-text">
                {{ block.html|safe }}
            </div>
        {% elif block.type == 'heading' %}
            <{{ block.level }}>{{ block.text }}</{{ block.level }}>
        {% elif block.type == 'image' %}
            {# Render image với picture element #}
            <figure class="{{ block.classes|join(' ') }}">
                <picture>
                    {% if block.image_sources.desktop_webp %}
                    <source srcset="{{ block.image_sources.desktop_webp }}" 
                        media="(min-width: 768px)" type="image/webp">
                    {% endif %}
                    <img src="{{ block.image_sources.fallback }}" 
                        alt="{{ block.image_sources.alt }}">
                </picture>
                {% if block.caption %}
                <div class="caption">
                    <figcaption>{{ block.caption }}</figcaption>
                    {% if block.author %}
                    <figcaption>{{ block.author }}</figcaption>
                    {% endif %}
                </div>
                {% endif %}
            </figure>
        {% elif block.type == 'ad' %}
            {# Render Google Ad #}
            <div class="google-ad" id="{{ block.ad_id }}"></div>
        {% elif block.type == 'paywall_offer' %}
            {# Render paywall offers #}
            <div class="iteras-offers">
                {% for offer in block.offers %}
                    <div class="offer">
                        <h3>{{ offer.name }}</h3>
                        <ul>
                            {% for pro in offer.pros %}
                            <li>{{ pro }}</li>
                            {% endfor %}
                        </ul>
                        <a href="{{ offer.cta_url }}">{{ offer.cta_text }}</a>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endfor %}
{% endif %}
```

## Migration

Chạy migration script:

```bash
cd flask
python deploy/migrate_add_article_details.py
```

## Lợi ích

1. **Tách biệt**: Content detail tách riêng khỏi article metadata
2. **Structured**: Dữ liệu được tổ chức rõ ràng theo blocks
3. **Flexible**: JSON field cho phép lưu bất kỳ cấu trúc nào
4. **Queryable**: Có thể query theo published_url
5. **Maintainable**: Dễ dàng maintain và extend
6. **Multi-language**: Hỗ trợ nhiều ngôn ngữ

