# Multi-Language Architecture

## Tổng Quan

Hệ thống hỗ trợ 3 ngôn ngữ:
- **DK (Danish)**: Crawl từ `https://www.sermitsiaq.ag/`
- **KL (Greenlandic)**: Crawl từ `https://kl.sermitsiaq.ag/`
- **EN (English)**: Translate từ DK (không crawl)

## Cấu Trúc Database

### 1. Thêm Field `language` vào Article Model

```python
class Article(db.Model):
    # ... existing fields ...
    
    # Multi-language support
    language = db.Column(db.String(2), nullable=False, default='da')  # 'da', 'kl', 'en'
    canonical_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=True)  # Link các bài cùng nội dung
    original_language = db.Column(db.String(2), default='da')  # Ngôn ngữ gốc (thường là 'da')
    
    # Indexes
    __table_args__ = (
        # ... existing indexes ...
        db.Index('idx_language', 'language'),
        db.Index('idx_canonical_language', 'canonical_id', 'language'),
    )
```

### 2. Relationship

```python
# Trong Article model
canonical_article = db.relationship('Article', remote_side=[id], backref='translations')
```

## Workflow

### 1. Crawl DK (Danish)
```python
crawler = SermitsiaqCrawler(base_url='https://www.sermitsiaq.ag')
articles = crawler.crawl_section(section_url, section_name='erhverv')
# Set language='da' cho tất cả articles
```

### 2. Crawl KL (Greenlandic)
```python
crawler = SermitsiaqCrawler(base_url='https://kl.sermitsiaq.ag')
articles = crawler.crawl_section(section_url, section_name='erhverv')
# Set language='kl' cho tất cả articles
# Link với DK article qua element_guid hoặc published_url
```

### 3. Translate DK → EN
```python
# Chỉ translate articles có language='da' và chưa có bản EN
dk_articles = Article.query.filter_by(language='da', canonical_id=None).all()
for dk_article in dk_articles:
    en_article = translate_article(dk_article)
    en_article.language = 'en'
    en_article.canonical_id = dk_article.id  # Link với DK version
    en_article.original_language = 'da'
```

## Matching Articles giữa DK và KL

### Cách 1: Match qua `element_guid`
- Nếu cả 2 trang có cùng `element_guid` → match

### Cách 2: Match qua `published_url`
- Convert URL: `https://www.sermitsiaq.ag/...` ↔ `https://kl.sermitsiaq.ag/...`
- Nếu path giống nhau → match

### Cách 3: Match qua `instance` ID
- Nếu cả 2 có cùng `instance` → match

## Query Articles theo Language

```python
# Get articles by language
def get_articles_by_language(language='en', section=None, limit=10):
    query = Article.query.filter_by(language=language)
    if section:
        query = query.filter_by(section=section)
    return query.order_by(Article.published_date.desc()).limit(limit).all()

# Get article với fallback
def get_article_with_fallback(article_id, preferred_language='en'):
    article = Article.query.get(article_id)
    if article.language == preferred_language:
        return article
    
    # Try to find translation
    if article.canonical_id:
        translated = Article.query.filter_by(
            canonical_id=article.canonical_id,
            language=preferred_language
        ).first()
        if translated:
            return translated
    
    # Fallback to original
    return article
```

## Translation Service

```python
# services/translation_service.py
from deep_translator import GoogleTranslator

def translate_article(article, target_language='en'):
    """Translate article from Danish to English"""
    translator = GoogleTranslator(source='da', target='en')
    
    translated = Article(
        title=translator.translate(article.title),
        content=translator.translate(article.content) if article.content else None,
        excerpt=translator.translate(article.excerpt) if article.excerpt else None,
        language='en',
        canonical_id=article.id,
        original_language='da',
        # Copy other fields
        section=article.section,
        element_guid=article.element_guid,
        instance=article.instance,
        published_url=article.published_url,
        # ... other fields
    )
    return translated
```

## Migration Script

```python
# deploy/migrate_add_language_support.py
def upgrade():
    # Add language column
    op.add_column('articles', sa.Column('language', sa.String(2), nullable=False, server_default='da'))
    op.add_column('articles', sa.Column('canonical_id', sa.Integer(), nullable=True))
    op.add_column('articles', sa.Column('original_language', sa.String(2), server_default='da'))
    
    # Add foreign key
    op.create_foreign_key('fk_article_canonical', 'articles', 'articles', ['canonical_id'], ['id'])
    
    # Add indexes
    op.create_index('idx_language', 'articles', ['language'])
    op.create_index('idx_canonical_language', 'articles', ['canonical_id', 'language'])
```

## Benefits

1. **Giảm chi phí**: Chỉ translate DK → EN (không cần translate KL)
2. **Dữ liệu gốc**: KL từ nguồn chính thức, không bị lỗi translate
3. **Flexible**: Có thể thêm ngôn ngữ khác sau (chỉ cần translate từ DK)
4. **Performance**: Query nhanh với indexes
5. **Fallback**: Nếu không có bản dịch, hiển thị bản gốc

## Next Steps

1. ✅ Tạo migration script để thêm language fields
2. ✅ Update Article model
3. ✅ Update crawl service để support multi-language
4. ✅ Tạo translation service
5. ✅ Update query functions để filter theo language
6. ✅ Update views để hiển thị đúng language

