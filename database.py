"""
Database models for Flask app
Using PostgreSQL with SQLAlchemy
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Category(db.Model):
    """Categories/Sections table"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # 'erhverv', 'samfund', etc.
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles = db.relationship('Article', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Article(db.Model):
    """Articles table - chứa thông tin bài viết được crawl"""
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Thông tin cơ bản
    title = db.Column(db.String(500), nullable=False)
    slug = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text)
    excerpt = db.Column(db.Text)
    
    # Thông tin từ website gốc
    element_guid = db.Column(db.String(100))  # GUID từ website gốc (không unique, chỉ để reference)
    instance = db.Column(db.String(50))  # Instance ID
    site_alias = db.Column(db.String(50), default='sermitsiaq')
    k5a_url = db.Column(db.String(500))  # URL cho K5A
    published_url = db.Column(db.String(500))  # URL đầy đủ từ website gốc (DA)
    published_url_en = db.Column(db.String(500), index=True, comment='URL tiếng Anh (dịch từ DA)')
    
    # Phân loại
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    section = db.Column(db.String(50), nullable=False)  # 'erhverv', 'samfund', 'kultur', 'sport', 'podcasti'
    
    # Đặc trưng hiển thị (quan trọng!)
    display_order = db.Column(db.Integer, default=0)  # Thứ tự hiển thị (0, 1, 2, ...)
    is_featured = db.Column(db.Boolean, default=False)  # Bài viết chủ đạo (hình ảnh lớn)
    is_home = db.Column(db.Boolean, default=False)  # Đánh dấu article thuộc trang home
    article_type = db.Column(db.String(50))  # 'standard', 'featured', 'small', 'large', etc.
    position = db.Column(db.String(50))  # 'top', 'main', 'sidebar', 'bottom'
    grid_size = db.Column(db.Integer, default=6)  # 6 (2 per row), 4 (3 per row), 12 (full width)
    layout_type = db.Column(db.String(50))  # '1_full', '2_articles', '3_articles', '1_special_bg', '1_with_list_left', '1_with_list_right'
    layout_data = db.Column(db.JSON)  # Lưu thêm data cho layout (kicker, list_items, list_title, etc.)
    
    # Paywall
    is_paywall = db.Column(db.Boolean, default=False)
    paywall_class = db.Column(db.String(50), default='')
    
    # Translation temp flag (để tránh duplicate khi translate)
    is_temp = db.Column(db.Boolean, default=False)  # True = đang trong quá trình translate, chưa show
    
    # Soft delete flag (đặc biệt cho 1_with_list_left/right articles)
    is_deleted = db.Column(db.Boolean, default=False)  # True = đã mark để xóa, chờ replace bằng version mới
    
    # Thời gian
    published_date = db.Column(db.DateTime)  # Thời gian publish từ website gốc
    crawled_at = db.Column(db.DateTime, default=datetime.utcnow)  # Thời gian crawl
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Image data (lưu dạng JSON)
    image_data = db.Column(db.JSON)  # {
    #   'element_guid': '...',
    #   'desktop_webp': '...',
    #   'desktop_jpeg': '...',
    #   'mobile_webp': '...',
    #   'mobile_jpeg': '...',
    #   'fallback': '...',
    #   'desktop_width': '524',
    #   'desktop_height': '341',
    #   'mobile_width': '480',
    #   'mobile_height': '312',
    #   'alt': '...',
    #   'title': '...'
    # }
    
    # Metadata từ crawl
    crawl_metadata = db.Column(db.JSON)  # Lưu thêm metadata nếu cần
    
    # Tags (extracted from article detail)
    tags = db.Column(db.JSON)  # Array of tags: ["EU-KOMMISSIONEN", "GRØNLAND", "POLITIK"]
    
    # Multi-language support
    language = db.Column(db.String(2), nullable=False, default='da')  # 'da', 'kl', 'en'
    canonical_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=True)  # Link các bài cùng nội dung khác ngôn ngữ
    original_language = db.Column(db.String(2), default='da')  # Ngôn ngữ gốc (thường là 'da')
    
    # Relationship để link các translations
    canonical_article = db.relationship('Article', remote_side=[id], backref='translations', foreign_keys=[canonical_id])
    
    # Indexes để query nhanh
    __table_args__ = (
        db.Index('idx_section_order', 'section', 'display_order'),
        db.Index('idx_featured', 'is_featured', 'display_order'),
        db.Index('idx_is_home', 'is_home', 'display_order'),  # Index cho home page query
        db.Index('idx_published_date', 'published_date'),
        db.Index('idx_element_guid', 'element_guid'),  # Index để query nhanh, không unique
        db.Index('idx_language', 'language'),  # Index cho language filtering
        db.Index('idx_canonical_language', 'canonical_id', 'language'),  # Index cho translation lookup
        db.Index('idx_section_language', 'section', 'language', 'display_order'),  # Index cho section + language query
    )
    
    def to_dict(self):
        """Convert article to dictionary for API/template"""
        from flask import url_for, has_request_context, request
        from utils import get_article_url_from_published_url
        from urllib.parse import urlparse
        
        # Generate URL từ published_url hoặc published_url_en
        # Nếu là Article EN và có published_url_en, dùng published_url_en
        url_to_use = None
        if self.language == 'en' and self.published_url_en:
            url_to_use = self.published_url_en
        elif self.published_url:
            url_to_use = self.published_url
        
        article_url = '#'
        if url_to_use:
            # Lấy path từ published_url hoặc published_url_en
            parsed = urlparse(url_to_use)
            path_only = parsed.path
            
            # Nếu có request context, tạo full URL
            if has_request_context():
                try:
                    scheme = request.scheme
                    host = request.host
                    article_url = f"{scheme}://{host}{path_only}"
                except:
                    article_url = path_only
            else:
                # Outside request context, chỉ dùng path
                article_url = path_only
        else:
            # Fallback: dùng article_id route nếu không có published_url
            try:
                if has_request_context():
                    article_url = url_for('article_views.article_detail', article_id=self.id)
                else:
                    article_url = f'/article/{self.id}'
            except Exception as e:
                article_url = f'/article/{self.id}'
        
        # Extract excerpt with fallback logic
        # Priority:
        # 1. article.excerpt
        # 2. ArticleDetail.content_blocks (type='subtitle')
        # 3. ArticleDetail.content_blocks (type='intro')
        # 4. ArticleDetail.content_blocks (type='paragraph' - first one)
        # 5. article.content (first paragraph)
        excerpt_text = self.excerpt or ''
        
        if not excerpt_text and self.published_url:
            # Try to get from ArticleDetail.content_blocks
            try:
                article_detail = ArticleDetail.query.filter_by(
                    published_url=self.published_url,
                    language=self.language
                ).first()
                
                if article_detail and article_detail.content_blocks:
                    # Priority 2: subtitle block
                    for block in article_detail.content_blocks:
                        if block.get('type') == 'subtitle':
                            excerpt_text = block.get('text', '').strip()
                            if excerpt_text:
                                break
                    
                    # Priority 3: intro block
                    if not excerpt_text:
                        for block in article_detail.content_blocks:
                            if block.get('type') == 'intro':
                                excerpt_text = block.get('text', '').strip()
                                if excerpt_text:
                                    break
                    
                    # Priority 4: first paragraph block
                    if not excerpt_text:
                        for block in article_detail.content_blocks:
                            if block.get('type') == 'paragraph':
                                text = block.get('text', '')
                                if not text:
                                    # Try to extract from HTML
                                    html = block.get('html', '')
                                    if html:
                                        from bs4 import BeautifulSoup
                                        soup = BeautifulSoup(html, 'html.parser')
                                        text = soup.get_text(strip=True)
                                if text:
                                    excerpt_text = text.strip()
                                    break
            except Exception:
                # If query fails, fall back to content
                pass
        
        # Priority 5: Extract from article.content if still no excerpt
        if not excerpt_text and self.content:
            # Fallback: Extract first paragraph from content (strip HTML)
            import re
            # Remove HTML tags using regex
            text_only = re.sub(r'<[^>]+>', '', self.content or '')
            # Remove extra whitespace and newlines
            text_only = ' '.join(text_only.split())
            # Get first 200 characters
            if text_only:
                excerpt_text = text_only[:200]
                # Don't cut mid-word if possible
                if len(text_only) > 200:
                    last_space = excerpt_text.rfind(' ')
                    if last_space > 150:  # Only use if we have enough text
                        excerpt_text = excerpt_text[:last_space] + '...'
                    else:
                        excerpt_text = excerpt_text + '...'
        
        # Get current language for multilingual section display
        current_language = self.language  # Default to article's language
        try:
            from flask_babel import get_locale
            from flask import has_request_context
            if has_request_context():
                locale = get_locale()
                if locale and str(locale) in ['da', 'kl', 'en']:
                    current_language = str(locale)
                # Check session as fallback
                from flask import session
                session_lang = session.get('language')
                if session_lang and session_lang in ['da', 'kl', 'en']:
                    current_language = session_lang
        except:
            pass  # Use article's language as fallback
        
        # Section mappings for all languages
        section_mappings = {
            # Base sections (internal keys)
            'kultur': {
                'da': 'kultur',
                'kl': 'kulturi',
                'en': 'culture'
            },
            'samfund': {
                'da': 'samfund',
                'kl': 'inuiaqatigiit',
                'en': 'society'
            },
            'erhverv': {
                'da': 'erhverv',
                'kl': 'inuussutissarsiutit',
                'en': 'business'
            },
            'sport': {
                'da': 'sport',
                'kl': 'timersorneq',
                'en': 'sport'
            },
            'podcasti': {
                'da': 'podcasti',
                'kl': 'podcasti',
                'en': 'podcast'
            }
        }
        
        # Extract section from URL if section='home'
        # Priority: section from URL > section from database
        display_section = self.section
        
        if display_section == 'home' and url_to_use:
            # Extract section from URL path
            path = urlparse(url_to_use).path.strip('/')
            
            # Reverse mapping: URL section → base section
            url_to_base = {}
            for base_section, lang_map in section_mappings.items():
                for lang, url_section in lang_map.items():
                    url_to_base[url_section] = base_section
            
            path_parts = path.split('/')
            if path_parts:
                section_from_url = path_parts[0].lower()
                
                # Find base section from URL
                base_section = url_to_base.get(section_from_url)
                if base_section:
                    # Map to current language
                    display_section = section_mappings[base_section].get(current_language, base_section)
                elif section_from_url in ['kultur', 'samfund', 'erhverv', 'sport', 'podcasti']:
                    # Direct Danish section match
                    display_section = section_mappings[section_from_url].get(current_language, section_from_url)
        
        # Map section to current language (for all sections, not just 'home')
        if display_section in section_mappings:
            display_section = section_mappings[display_section].get(current_language, display_section)
        
        return {
            'id': self.id,
            'element_guid': self.element_guid,
            'title': self.title,
            'excerpt': excerpt_text,  # Subtitle/description with fallback from content
            'url': article_url,  # URL với path gốc (giữ nguyên structure từ published_url)
            'published_url': self.published_url,  # Giữ lại URL gốc để reference
            'k5a_url': self.k5a_url or f'/a/{self.id}',
            'section': display_section,  # Section từ URL nếu section='home', else từ DB
            'site_alias': self.site_alias,
            'instance': self.instance,
            'published_date': self.published_date.isoformat() if self.published_date else '',
            'is_paywall': self.is_paywall,
            'paywall_class': self.paywall_class,
            'grid_size': self.grid_size,
            'display_order': self.display_order,  # Thêm display_order
            'is_featured': self.is_featured,
            'article_type': self.article_type,
            'layout_type': self.layout_type,
            'layout_data': self.layout_data or {},
            'image': self.image_data or {},  # image_data từ database -> image cho template
            'kicker': (self.layout_data or {}).get('kicker') if self.layout_data else None,
            'kicker_floating': (self.layout_data or {}).get('kicker_floating') if self.layout_data else None,
            'kicker_below': (self.layout_data or {}).get('kicker_below') if self.layout_data else None,  # Kicker below (ví dụ "OPDATERET")
            'kicker_below_classes': (self.layout_data or {}).get('kicker_below_classes', 'kicker below primary color_mobile_primary') if self.layout_data else None,
            'title_parts': (self.layout_data or {}).get('title_parts') if self.layout_data else None,  # Title parts với highlights
            'tags': self.tags or [],  # Tags field (array of tag strings)
            'language': self.language,  # Thêm language
            'canonical_id': self.canonical_id,  # Thêm canonical_id
            'original_language': self.original_language  # Thêm original_language
        }
    
    def __repr__(self):
        return f'<Article {self.title[:50]}>'


class ArticleDetail(db.Model):
    """
    Bảng lưu trữ cấu trúc chi tiết của bài viết
    Sử dụng published_url để link với bảng articles
    """
    __tablename__ = 'article_details'
    
    id = db.Column(db.Integer, primary_key=True)
    published_url = db.Column(db.String(1000), nullable=False, index=True, comment='URL của article (link với articles.published_url)')
    
    # Structured content blocks (lưu dạng JSON)
    content_blocks = db.Column(db.JSON, comment='Array of content blocks: intro, paragraphs, headings, images, ads, paywall_offers')
    
    # Metadata
    language = db.Column(db.String(10), default='en', nullable=False, index=True, comment='Language code: da, kl, en')
    element_guid = db.Column(db.String(100), comment='Element GUID từ HTML gốc')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint: (published_url, language) để cho phép cùng URL nhưng khác language
    __table_args__ = (
        db.UniqueConstraint('published_url', 'language', name='uq_article_details_url_language'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'published_url': self.published_url,
            'content_blocks': self.content_blocks if isinstance(self.content_blocks, list) else json.loads(self.content_blocks) if self.content_blocks else [],
            'language': self.language,
            'element_guid': self.element_guid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ArticleDetail {self.published_url[:50]}>'


class CrawlLog(db.Model):
    """Log table để track quá trình crawl"""
    __tablename__ = 'crawl_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    crawl_type = db.Column(db.String(50))  # 'full', 'incremental', 'section'
    section = db.Column(db.String(50))  # Section được crawl
    status = db.Column(db.String(50))  # 'success', 'failed', 'partial'
    articles_crawled = db.Column(db.Integer, default=0)
    articles_created = db.Column(db.Integer, default=0)
    articles_updated = db.Column(db.Integer, default=0)
    errors = db.Column(db.Text)  # Lỗi nếu có
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<CrawlLog {self.crawl_type} - {self.status}>'


class User(db.Model):
    """User table cho login system"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    subscriber_number = db.Column(db.String(50), unique=True, nullable=True, index=True)  # Abonnentnummer
    password_hash = db.Column(db.String(255), nullable=False)  # Sẽ hash password
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def check_password(self, password):
        """Check password - đơn giản, có thể nâng cấp sau với werkzeug.security"""
        # Tạm thời dùng plain text comparison, nên upgrade sau với werkzeug.security.check_password_hash
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.password_hash