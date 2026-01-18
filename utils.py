"""
Utility functions for Flask app
"""
from database import Article

def calculate_grid_size_pattern(display_order):
    """
    Tính grid_size dựa trên pattern: 2-3-2-3-2-3...
    Pattern: Row 1 (2 articles), Row 2 (3 articles), Row 3 (2 articles), ...
    
    Args:
        display_order: Thứ tự hiển thị của article (0, 1, 2, ...)
    
    Returns:
        grid_size: 6 (2 per row) hoặc 4 (3 per row)
    """
    # Pattern: 2-3-2-3-2-3...
    # Row 0: articles 0-1 (2 articles, mỗi article grid_size=6)
    # Row 1: articles 2-4 (3 articles, mỗi article grid_size=4)
    # Row 2: articles 5-6 (2 articles, mỗi article grid_size=6)
    # Row 3: articles 7-9 (3 articles, mỗi article grid_size=4)
    # ...
    
    # Tính row index dựa trên display_order
    # Pattern: 2, 3, 2, 3, 2, 3...
    current_pos = 0
    row_index = 0
    
    while current_pos <= display_order:
        # Pattern: row chẵn (0, 2, 4...) = 2 articles, row lẻ (1, 3, 5...) = 3 articles
        articles_in_row = 2 if row_index % 2 == 0 else 3
        
        if current_pos + articles_in_row > display_order:
            # Article này nằm trong row này
            # Row chẵn (0, 2, 4...) = 2 articles per row = grid_size 6
            # Row lẻ (1, 3, 5...) = 3 articles per row = grid_size 4
            return 6 if row_index % 2 == 0 else 4
        
        current_pos += articles_in_row
        row_index += 1
    
    # Fallback
    return 6


def apply_grid_size_pattern(articles):
    """
    Áp dụng pattern grid_size cho danh sách articles
    Pattern: 2-3-2-3-2-3... (hàng 1: 2 articles, hàng 2: 3 articles, ...)
    
    Args:
        articles: List of article objects hoặc dictionaries
    
    Returns:
        List of articles với grid_size đã được tính toán
    """
    if not articles:
        return articles
    
    for idx, article in enumerate(articles):
        # Nếu article chưa có grid_size hoặc muốn override
        # Tính dựa trên display_order hoặc index
        display_order = getattr(article, 'display_order', None) if hasattr(article, 'display_order') else article.get('display_order', idx)
        
        # Tính grid_size theo pattern
        grid_size = calculate_grid_size_pattern(display_order)
        
        # Set grid_size
        if hasattr(article, 'grid_size'):
            article.grid_size = grid_size
        elif isinstance(article, dict):
            article['grid_size'] = grid_size
        else:
            # Nếu là SQLAlchemy object, update trực tiếp
            article.grid_size = grid_size
    
    return articles


def group_articles_by_row(articles, articles_per_row=2):
    """
    Group articles into rows for grid layout
    
    Args:
        articles: List of article dictionaries
        articles_per_row: Number of articles per row (2 or 3)
    
    Returns:
        List of lists, each inner list contains articles for one row
    """
    if not articles:
        return []
    
    # Calculate grid_size based on articles_per_row
    grid_size = 6 if articles_per_row == 2 else 4
    
    # Set grid_size for each article
    for article in articles:
        if 'grid_size' not in article:
            article['grid_size'] = grid_size
    
    # Group articles into rows
    rows = []
    for i in range(0, len(articles), articles_per_row):
        rows.append(articles[i:i + articles_per_row])
    
    return rows


def prepare_home_layouts(articles):
    """
    Chuẩn bị articles cho trang home với các layout types khác nhau
    Group articles theo layout_type và chuẩn bị data cho rendering
    
    Args:
        articles: List of article dictionaries với layout_type
    
    Returns:
        List of layout items, mỗi item có:
        - layout_type: '1_full', '2_articles', '3_articles', '1_special_bg', '1_with_list_left', '1_with_list_right'
        - data: Data cần thiết cho layout (article, articles, list_items, etc.)
        - row_guid: GUID cho row
    """
    if not articles:
        return []
    
    layouts = []
    i = 0
    row_index = 0
    
    while i < len(articles):
        article = articles[i]
        layout_type = article.get('layout_type') or '1_full'  # Default to 1_full
        
        row_guid = f"home-row-{row_index}"
        layout_item = {
            'layout_type': layout_type,
            'row_guid': row_guid,
            'data': {}
        }
        
        if layout_type == '1_full':
            # 1 article full width
            layout_item['data'] = {
                'article': article
            }
            i += 1
            
        elif layout_type == '2_articles':
            # 2 articles 1 row
            layout_item['data'] = {
                'articles': articles[i:i+2]
            }
            i += 2
            
        elif layout_type == '3_articles':
            # 3 articles 1 row
            layout_item['data'] = {
                'articles': articles[i:i+3]
            }
            i += 3
            
        elif layout_type == '5_articles':
            # 5 articles 1 row (NUUK)
            layout_item['data'] = {
                'articles': articles[i:i+5]
            }
            i += 5
            
        elif layout_type == '1_special_bg':
            # 1 article với special background
            layout_item['data'] = {
                'article': article,
                'kicker': article.get('kicker') or (article.get('layout_data', {}).get('kicker') if article.get('layout_data') else None)
            }
            i += 1
            
        elif layout_type == '1_with_list_left':
            # 1 article + list bên trái
            layout_data = article.get('layout_data', {})
            layout_item['data'] = {
                'article': article,
                'list_title': layout_data.get('list_title', 'LIST'),
                'list_items': layout_data.get('list_items', []),
                'list_position': 'left'
            }
            i += 1
            
        elif layout_type == '1_with_list_right':
            # 1 article + list bên phải
            layout_data = article.get('layout_data', {})
            layout_item['data'] = {
                'article': article,
                'list_title': layout_data.get('list_title', 'LIST'),
                'list_items': layout_data.get('list_items', []),
                'list_position': 'right'
            }
            i += 1
            
        elif layout_type == 'slider':
            # Article slider
            layout_data = article.get('layout_data', {})
            slider_articles = layout_data.get('slider_articles', [])
            slider_title = layout_data.get('slider_title', '')
            has_nav = layout_data.get('has_nav', True)  # Default có nav
            items_per_view = layout_data.get('items_per_view', 4)  # Default 4 items
            source_class = layout_data.get('source_class', 'source_nyheder')  # Default source_nyheder
            
            # Debug: Log số articles trong slider
            if not isinstance(slider_articles, list):
                print(f"⚠️  WARNING: slider_articles is not a list, type: {type(slider_articles)}")
                slider_articles = []
            else:
                print(f"🎠 Preparing slider '{slider_title}': {len(slider_articles)} articles")
                if len(slider_articles) < 4:
                    print(f"   ⚠️  WARNING: Slider has only {len(slider_articles)} articles")
            
            layout_item['data'] = {
                'slider_title': slider_title,
                'slider_articles': slider_articles,
                'slider_id': layout_data.get('slider_id', f'slider-{row_index}'),
                'has_nav': has_nav,
                'items_per_view': items_per_view,
                'source_class': source_class
            }
            i += 1
            
        elif layout_type == 'job_slider':
            # JOB slider với header link và background đặc biệt
            layout_data = article.get('layout_data', {})
            slider_articles = layout_data.get('slider_articles', [])
            slider_title = layout_data.get('slider_title', '')
            has_nav = layout_data.get('has_nav', True)
            items_per_view = layout_data.get('items_per_view', 4)
            source_class = layout_data.get('source_class', 'source_job-dk')
            header_link = layout_data.get('header_link')
            extra_classes = layout_data.get('extra_classes', [])
            header_classes = layout_data.get('header_classes', [])
            
            print(f"💼 Preparing JOB slider '{slider_title}': {len(slider_articles)} articles")
            
            layout_item['data'] = {
                'slider_title': slider_title,
                'slider_articles': slider_articles,
                'slider_id': layout_data.get('slider_id', f'job-slider-{row_index}'),
                'has_nav': has_nav,
                'items_per_view': items_per_view,
                'source_class': source_class,
                'header_link': header_link,
                'extra_classes': extra_classes,
                'header_classes': header_classes
            }
            i += 1
            
            # Debug: Log số articles trong slider
            if not isinstance(slider_articles, list):
                print(f"⚠️  WARNING: slider_articles is not a list, type: {type(slider_articles)}")
                slider_articles = []
            else:
                print(f"🎠 Preparing slider '{slider_title}': {len(slider_articles)} articles")
                if len(slider_articles) < 4:
                    print(f"   ⚠️  WARNING: Slider has only {len(slider_articles)} articles")
            
            layout_item['data'] = {
                'slider_title': slider_title,
                'slider_articles': slider_articles,
                'slider_id': layout_data.get('slider_id', f'slider-{row_index}'),
                'has_nav': has_nav,
                'items_per_view': items_per_view,
                'source_class': source_class
            }
            i += 1
            
        else:
            # Unknown layout type, default to 1_full
            layout_item['layout_type'] = '1_full'
            layout_item['data'] = {
                'article': article
            }
            i += 1
        
        layouts.append(layout_item)
        row_index += 1
    
    return layouts


# ==================== Multi-Language Support Functions ====================

def get_articles_by_language(language='en', section=None, is_home=False, limit=None, exclude_temp=True):
    """
    Get articles filtered by language
    
    Args:
        language: Language code ('da', 'kl', 'en') - can be Locale object or string
        section: Section name (optional, e.g., 'erhverv', 'samfund')
        is_home: Whether to filter by is_home=True
        limit: Maximum number of articles to return
        exclude_temp: Whether to exclude temp articles (default: True - chỉ show articles đã hoàn thành)
    
    Returns:
        List of Article objects
    """
    # Convert Locale object to string if needed
    language_str = str(language) if language else 'en'
    query = Article.query.filter_by(language=language_str)
    
    if section:
        query = query.filter_by(section=section)
    
    if is_home:
        query = query.filter_by(is_home=True)
    
    # Exclude temp articles (chỉ show articles đã hoàn thành translate)
    if exclude_temp:
        query = query.filter_by(is_temp=False)
    
    query = query.order_by(Article.display_order.asc(), Article.published_date.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_article_with_fallback(article_id, preferred_language='en'):
    """
    Get article với fallback logic:
    1. Nếu article có language = preferred_language → return article
    2. Nếu có translation (canonical_id) → return translation
    3. Nếu không có translation → return original article
    
    Args:
        article_id: Article ID
        preferred_language: Preferred language ('da', 'kl', 'en') - can be Locale object or string
    
    Returns:
        Article object
    """
    # Convert Locale object to string if needed
    preferred_language_str = str(preferred_language) if preferred_language else 'en'
    
    article = Article.query.get(article_id)
    
    if not article:
        return None
    
    # Nếu article đã có language mong muốn
    if article.language == preferred_language_str:
        return article
    
    # Tìm translation qua canonical_id
    if article.canonical_id:
        # Article này là translation, tìm canonical
        canonical = Article.query.get(article.canonical_id)
        if canonical and canonical.language == preferred_language_str:
            return canonical
    
    # Tìm translation của article này
    translation = Article.query.filter_by(
        canonical_id=article.id,
        language=preferred_language_str
    ).first()
    
    if translation:
        return translation
    
    # Fallback: return original article
    return article


def get_home_articles_by_language(language='en', limit=100):
    """
    Get home page articles filtered by language
    
    Args:
        language: Language code ('da', 'kl', 'en') - can be Locale object or string
        limit: Maximum number of articles
    
    Returns:
        List of Article objects
    """
    # Convert Locale object to string if needed
    language_str = str(language) if language else 'en'
    return get_articles_by_language(
        language=language_str,
        is_home=True,
        limit=limit
    )

