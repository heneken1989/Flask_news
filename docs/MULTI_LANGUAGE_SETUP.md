1# Multi-Language Setup Guide

## Tổng Quan

Hệ thống hỗ trợ 3 ngôn ngữ:
- **DK (Danish)**: Crawl từ `https://www.sermitsiaq.ag/`
- **KL (Greenlandic)**: Crawl từ `https://kl.sermitsiaq.ag/`
- **EN (English)**: Translate từ DK (không crawl)

## Cài Đặt

### 1. Chạy Migration

Thêm language support vào database:

```bash
cd flask
source ../venv/bin/activate
python deploy/migrate_add_language_support.py
```

### 2. Crawl Dữ Liệu

#### Crawl Danish (DK)
```bash
python scripts/crawl_multi_language.py --step 1
```

#### Crawl Greenlandic (KL)
```bash
python scripts/crawl_multi_language.py --step 2
```

#### Crawl cả 2 ngôn ngữ
```bash
python scripts/crawl_multi_language.py --step all
```

### 3. Match Articles

Match DK và KL articles (link qua canonical_id):

```bash
python scripts/crawl_multi_language.py --step 3
```

### 4. Translate DK → EN

Translate Danish articles sang English:

```bash
python scripts/crawl_multi_language.py --step 4
```

## Workflow Hoàn Chỉnh

```bash
# 1. Crawl DK
python scripts/crawl_multi_language.py --step 1

# 2. Crawl KL
python scripts/crawl_multi_language.py --step 2

# 3. Match DK và KL
python scripts/crawl_multi_language.py --step 3

# 4. Translate DK → EN
python scripts/crawl_multi_language.py --step 4
```

Hoặc chạy tất cả một lúc:

```bash
python scripts/crawl_multi_language.py --step all
```

## Sử Dụng Trong Code

### Query Articles theo Language

```python
from utils import get_articles_by_language, get_home_articles_by_language

# Get home articles by language
articles = get_home_articles_by_language(language='en', limit=100)

# Get articles by section and language
articles = get_articles_by_language(
    language='en',
    section='erhverv',
    limit=10
)
```

### Get Article với Fallback

```python
from utils import get_article_with_fallback

# Get article với fallback logic
article = get_article_with_fallback(
    article_id=123,
    preferred_language='en'
)
# Nếu không có EN, sẽ return DK hoặc KL
```

### Manual Translation

```python
from services.translation_service import translate_article

# Translate một article
dk_article = Article.query.filter_by(id=123, language='da').first()
en_article = translate_article(dk_article, target_language='en')

# Save to database
db.session.add(en_article)
db.session.commit()
```

## Database Schema

### Article Model - New Fields

```python
language = db.Column(db.String(2), nullable=False, default='da')  # 'da', 'kl', 'en'
canonical_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=True)
original_language = db.Column(db.String(2), default='da')
```

### Relationships

- `canonical_article`: Article gốc (DK)
- `translations`: List các translations (KL, EN)

## Matching Logic

Articles được match qua:
1. **element_guid** (ưu tiên cao nhất)
2. **published_url** (convert domain)
3. **instance** ID

## Translation

- Chỉ translate **DK → EN**
- **KL** không cần translate (crawl trực tiếp)
- Sử dụng Google Translate API (via `deep-translator`)
- Delay 0.5s giữa các lần translate để tránh rate limit

## Lưu Ý

1. **Rate Limiting**: Google Translate có rate limit, nên delay 0.5s giữa các lần translate
2. **Matching**: Không phải tất cả DK articles đều có KL version
3. **Translation Quality**: Translation tự động có thể không hoàn hảo, cần review
4. **Performance**: Indexes đã được tạo để query nhanh

## Troubleshooting

### Migration failed
```bash
# Check if columns already exist
python deploy/migrate_add_language_support.py --downgrade
python deploy/migrate_add_language_support.py
```

### Translation failed
- Check internet connection
- Check Google Translate API quota
- Increase delay between translations

### Matching failed
- Check if articles have element_guid or published_url
- Verify both DK and KL articles exist

