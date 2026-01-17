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
    published_url = db.Column(db.String(500))  # URL đầy đủ từ website gốc
    
    # Phân loại
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    section = db.Column(db.String(50), nullable=False)  # 'erhverv', 'samfund', 'kultur', 'sport', 'job'
    
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
    
    # Indexes để query nhanh
    __table_args__ = (
        db.Index('idx_section_order', 'section', 'display_order'),
        db.Index('idx_featured', 'is_featured', 'display_order'),
        db.Index('idx_is_home', 'is_home', 'display_order'),  # Index cho home page query
        db.Index('idx_published_date', 'published_date'),
        db.Index('idx_element_guid', 'element_guid'),  # Index để query nhanh, không unique
    )
    
    def to_dict(self):
        """Convert article to dictionary for API/template"""
        return {
            'id': self.id,
            'element_guid': self.element_guid,
            'title': self.title,
            'url': self.published_url or f'/{self.section}/{self.slug}',
            'k5a_url': self.k5a_url or f'/a/{self.id}',
            'section': self.section,
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
            'title_parts': (self.layout_data or {}).get('title_parts') if self.layout_data else None  # Title parts với highlights
        }
    
    def __repr__(self):
        return f'<Article {self.title[:50]}>'


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

