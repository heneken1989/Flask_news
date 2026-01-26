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
    Group articles theo row (dựa vào display_order) và layout_type
    
    Args:
        articles: List of article dictionaries với layout_type và display_order
    
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
    
    # Debug: Log display_order của articles đầu tiên
    if articles:
        print(f"📐 prepare_home_layouts: Processing {len(articles)} articles")
        print(f"   First 5 articles display_order: {[a.get('display_order', 0) for a in articles[:5]]}")
        
        # Debug: Kiểm tra articles xung quanh job slider và row 20
        row_20_articles_in_list = [a for a in articles if a.get('display_order', 0) >= 20000 and a.get('display_order', 0) < 20100]
        print(f"   📊 Articles với display_order 20000-20099 trong list: {len(row_20_articles_in_list)}")
        for a in row_20_articles_in_list:
            print(f"      - display_order: {a.get('display_order')}, layout_type: {a.get('layout_type')}, id: {a.get('id', 'N/A')}")
        
        # Kiểm tra job slider
        job_sliders_in_list = [a for a in articles if a.get('layout_type') == 'job_slider' and a.get('display_order') == 19000]
        print(f"   📊 Job sliders với display_order=19000 trong list: {len(job_sliders_in_list)}")
        for a in job_sliders_in_list:
            print(f"      - display_order: {a.get('display_order')}, id: {a.get('id', 'N/A')}")
    
    while i < len(articles):
        article = articles[i]
        layout_type = article.get('layout_type') or '1_full'  # Default to 1_full
        display_order = article.get('display_order', 0)
        
        # Tính row_index từ display_order (display_order = row_idx * 1000 + article_idx)
        row_index = display_order // 1000
        row_guid = f"home-row-{row_index}"
        
        # Debug log cho articles xung quanh job slider và row 20
        if display_order >= 19000 and display_order <= 20100:
            print(f"📐 Layout {i}: layout_type={layout_type}, display_order={display_order}, row_index={row_index}, id={article.get('id', 'N/A')}, title={article.get('title', 'N/A')[:40]}")
        elif i < 10:
            print(f"📐 Layout {i}: layout_type={layout_type}, display_order={display_order}, row_index={row_index}, title={article.get('title', 'N/A')[:40]}")
        
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
            # 2 articles 1 row - chỉ lấy articles trong cùng row và cùng layout_type
            row_articles = []
            for j in range(i, min(i+2, len(articles))):
                next_article = articles[j]
                next_display_order = next_article.get('display_order', 0)
                next_row_index = next_display_order // 1000
                next_layout_type = next_article.get('layout_type') or '1_full'
                
                # Chỉ lấy nếu cùng row và cùng layout_type
                if next_row_index == row_index and next_layout_type == '2_articles':
                    row_articles.append(next_article)
                else:
                    break
            
            if len(row_articles) >= 2:
                layout_item['data'] = {
                    'articles': row_articles[:2]
                }
                i += len(row_articles)
            elif len(row_articles) > 0:
                # Không đủ 2 articles, chỉ hiển thị articles có sẵn
                print(f"   ⚠️  Row {row_index} has only {len(row_articles)} articles for 2_articles layout, expected 2. Displaying available articles only.")
                layout_item['data'] = {
                    'articles': row_articles
                }
                i += len(row_articles)
            else:
                # Không có articles nào, skip layout item
                print(f"   ⚠️  Row {row_index} has no articles for 2_articles layout. Skipping this layout item.")
                i += 1
                continue
            
        elif layout_type == '3_articles':
            # 3 articles 1 row - lấy tất cả articles trong cùng row
            row_articles = []
            
            # ⚠️ QUAN TRỌNG: Bắt đầu từ article hiện tại (index i) - đây là article đầu tiên của row
            # Article tại index i chắc chắn có layout_type='3_articles' và cùng row_index
            row_articles.append(article)
            
            # Tìm các articles tiếp theo trong cùng row (bắt đầu từ i+1)
            for j in range(i + 1, len(articles)):
                next_article = articles[j]
                next_display_order = next_article.get('display_order', 0)
                next_row_index = next_display_order // 1000
                next_layout_type = next_article.get('layout_type') or '1_full'
                
                # Chỉ lấy nếu cùng row và cùng layout_type là 3_articles
                # ⚠️ QUAN TRỌNG: Chỉ lấy articles có layout_type='3_articles' trong cùng row
                if next_row_index == row_index and next_layout_type == '3_articles':
                    row_articles.append(next_article)
                elif next_row_index > row_index:
                    # Đã qua row khác, dừng lại
                    break
            
            print(f"   🔍 Row {row_index}: Found {len(row_articles)} articles in same row with layout_type=3_articles")
            if row_articles:
                article_info = [f"ID:{a.get('id', 'N/A')} DO:{a.get('display_order', 'N/A')} ({a.get('layout_type', 'N/A')})" for a in row_articles]
                print(f"      Articles: {article_info}")
            else:
                print(f"      ⚠️  No articles found! Current article: ID={article.get('id', 'N/A')}, display_order={display_order}, layout_type={layout_type}")
            
            # Nếu có đúng 3 articles trong cùng row, group lại
            if len(row_articles) == 3:
                layout_item['data'] = {
                    'articles': row_articles
                }
                i += len(row_articles)
                print(f"   ✅ Grouped 3 articles in row {row_index}: {[a.get('title', 'N/A')[:30] for a in row_articles]}")
            elif len(row_articles) >= 3:
                # Nếu có nhiều hơn 3, chỉ lấy 3 đầu tiên
                layout_item['data'] = {
                    'articles': row_articles[:3]
                }
                i += len(row_articles)
                print(f"   ✅ Grouped 3 articles (from {len(row_articles)}) in row {row_index}")
            elif len(row_articles) > 0:
                # Không đủ 3 articles - chỉ hiển thị articles có sẵn
                print(f"   ⚠️  Row {row_index} has only {len(row_articles)} articles, expected 3. Displaying available articles only.")
                
                # Chỉ dùng articles có sẵn, không tạo fake
                layout_item['data'] = {
                    'articles': row_articles
                }
                i += len(row_articles)
                print(f"   ✅ Grouped {len(row_articles)} articles in row {row_index} (expected 3, but only have {len(row_articles)})")
            else:
                # Không có articles nào trong row, skip layout item này
                print(f"   ⚠️  Row {row_index} has no articles. Skipping this layout item.")
                i += 1
                continue  # Skip thêm layout item này vào result
            
        elif layout_type == '5_articles':
            # 5 articles 1 row (NUUK) - chỉ lấy articles trong cùng row
            row_articles = []
            for j in range(i, min(i+5, len(articles))):
                next_article = articles[j]
                next_display_order = next_article.get('display_order', 0)
                next_row_index = next_display_order // 1000
                if next_row_index == row_index:
                    row_articles.append(next_article)
                else:
                    break
            
            if len(row_articles) >= 5:
                layout_item['data'] = {
                    'articles': row_articles[:5]
                }
                i += len(row_articles)
            elif len(row_articles) > 0:
                # Không đủ 5 articles, chỉ hiển thị những articles có sẵn
                print(f"   ⚠️  Row {row_index} has only {len(row_articles)} articles for 5_articles layout, expected 5. Displaying available articles only.")
                layout_item['data'] = {
                    'articles': row_articles
                }
                i += len(row_articles)
            else:
                # Không có articles nào, skip layout item
                print(f"   ⚠️  Row {row_index} has no articles for 5_articles layout. Skipping this layout item.")
                i += 1
                continue
            
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
            
            # Debug: Log layout_data structure
            if i < 10:
                print(f"   📋 1_with_list_left - Article ID: {article.get('id', 'N/A')}")
                print(f"      layout_data type: {type(layout_data)}")
                print(f"      layout_data keys: {list(layout_data.keys()) if isinstance(layout_data, dict) else 'Not a dict'}")
            
            list_title = layout_data.get('list_title', 'LIST') if isinstance(layout_data, dict) else 'LIST'
            list_items = layout_data.get('list_items', []) if isinstance(layout_data, dict) else []
            
            # Debug logging
            if i < 10:
                print(f"      list_title='{list_title}', list_items count={len(list_items)}")
                if list_items:
                    print(f"      First list item: {list_items[0]}")
                    print(f"      All list items: {list_items}")
                else:
                    print(f"      ⚠️  No list_items found!")
                    print(f"      layout_data value: {layout_data}")
            
            layout_item['data'] = {
                'article': article,
                'list_title': list_title,
                'list_items': list_items,
                'list_position': 'left'
            }
            i += 1
            
        elif layout_type == '1_with_list_right':
            # 1 article + list bên phải
            layout_data = article.get('layout_data', {})
            
            # Debug: Log layout_data structure
            if i < 10:
                print(f"   📋 1_with_list_right - Article ID: {article.get('id', 'N/A')}")
                print(f"      layout_data type: {type(layout_data)}")
                print(f"      layout_data keys: {list(layout_data.keys()) if isinstance(layout_data, dict) else 'Not a dict'}")
            
            list_title = layout_data.get('list_title', 'LIST') if isinstance(layout_data, dict) else 'LIST'
            list_items = layout_data.get('list_items', []) if isinstance(layout_data, dict) else []
            
            # Debug logging
            if i < 10:
                print(f"      list_title='{list_title}', list_items count={len(list_items)}")
                if list_items:
                    print(f"      First list item: {list_items[0]}")
                    print(f"      All list items: {list_items}")
                else:
                    print(f"      ⚠️  No list_items found!")
                    print(f"      layout_data value: {layout_data}")
            
            layout_item['data'] = {
                'article': article,
                'list_title': list_title,
                'list_items': list_items,
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
                
                # Convert slider_articles URLs từ published_url sang Flask app URL
                from flask import url_for
                from database import Article
                updated_slider_articles = []
                for item in slider_articles:
                    updated_item = item.copy()
                    # Nếu item có id, tìm Article và dùng to_dict() để get Flask URL
                    if item.get('id'):
                        try:
                            article_obj = Article.query.get(item['id'])
                            if article_obj:
                                article_dict = article_obj.to_dict()
                                updated_item['url'] = article_dict.get('url', item.get('url', '#'))
                        except:
                            # Fallback: dùng published_url nếu không tìm thấy Article
                            updated_item['url'] = item.get('url', '#')
                    else:
                        # Nếu không có id, giữ nguyên url (có thể là published_url)
                        # Hoặc có thể tìm Article bằng published_url
                        published_url = item.get('url') or item.get('published_url')
                        if published_url:
                            try:
                                article_obj = Article.query.filter_by(published_url=published_url).first()
                                if article_obj:
                                    article_dict = article_obj.to_dict()
                                    updated_item['url'] = article_dict.get('url', published_url)
                                else:
                                    # Không tìm thấy, giữ nguyên published_url
                                    updated_item['url'] = published_url
                            except:
                                updated_item['url'] = published_url
                    updated_slider_articles.append(updated_item)
                slider_articles = updated_slider_articles
            
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
            # Job slider - giống slider nhưng có thêm header_link, extra_classes, header_classes
            layout_data = article.get('layout_data', {})
            slider_articles = layout_data.get('slider_articles', [])
            slider_title = layout_data.get('slider_title', '')
            has_nav = layout_data.get('has_nav', True)
            items_per_view = layout_data.get('items_per_view', 4)
            source_class = layout_data.get('source_class', 'source_job')
            
            # Job slider specific fields
            header_link = layout_data.get('header_link')
            extra_classes = layout_data.get('extra_classes', [])
            header_classes = layout_data.get('header_classes', [])
            
            # Debug: Log số articles trong job slider
            if not isinstance(slider_articles, list):
                print(f"⚠️  WARNING: job_slider articles is not a list, type: {type(slider_articles)}")
                slider_articles = []
            else:
                print(f"🎠 Preparing job_slider '{slider_title}': {len(slider_articles)} articles")
                if len(slider_articles) < 4:
                    print(f"   ⚠️  WARNING: Job slider has only {len(slider_articles)} articles")
                
                # Convert slider_articles URLs từ published_url sang Flask app URL
                from flask import url_for
                from database import Article
                updated_slider_articles = []
                for item in slider_articles:
                    updated_item = item.copy()
                    # Nếu item có id, tìm Article và dùng to_dict() để get Flask URL
                    if item.get('id'):
                        try:
                            article_obj = Article.query.get(item['id'])
                            if article_obj:
                                article_dict = article_obj.to_dict()
                                updated_item['url'] = article_dict.get('url', item.get('url', '#'))
                        except:
                            # Fallback: dùng published_url nếu không tìm thấy Article
                            updated_item['url'] = item.get('url', '#')
                    else:
                        # Nếu không có id, giữ nguyên url (có thể là published_url)
                        # Hoặc có thể tìm Article bằng published_url
                        published_url = item.get('url') or item.get('published_url')
                        if published_url:
                            try:
                                article_obj = Article.query.filter_by(published_url=published_url).first()
                                if article_obj:
                                    article_dict = article_obj.to_dict()
                                    updated_item['url'] = article_dict.get('url', published_url)
                                else:
                                    # Không tìm thấy, giữ nguyên published_url
                                    updated_item['url'] = published_url
                            except:
                                updated_item['url'] = published_url
                    updated_slider_articles.append(updated_item)
                slider_articles = updated_slider_articles
            
            layout_item['data'] = {
                'slider_title': slider_title,
                'slider_articles': slider_articles,
                'slider_id': layout_data.get('slider_id', f'slider-{row_index}'),
                'has_nav': has_nav,
                'items_per_view': items_per_view,
                'source_class': source_class,
                'header_link': header_link,
                'extra_classes': extra_classes,
                'header_classes': header_classes
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
        # ⚠️ REMOVED: row_index += 1
        # row_index được tính lại từ display_order ở đầu mỗi iteration (dòng 141)
        # Không cần tăng row_index ở đây vì nó sẽ được tính lại từ display_order của article tiếp theo
    
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
    
    # Order theo display_order (quan trọng nhất), sau đó id để đảm bảo thứ tự ổn định
    query = query.order_by(Article.display_order.asc(), Article.id.asc())
    
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
    
    Note:
        Chỉ filter by is_home=True, KHÔNG filter by section='home'
        Để articles vẫn giữ nguyên section gốc (samfund, sport, etc.)
        và có thể hiển thị được ở cả home và tag pages
    """
    # Convert Locale object to string if needed
    language_str = str(language) if language else 'en'
    return get_articles_by_language(
        language=language_str,
        is_home=True,  # Chỉ filter is_home=True, không filter section
        limit=limit
    )


def get_article_url_from_published_url(published_url: str, base_url: str = None) -> str:
    """
    Generate article URL từ published_url (giữ nguyên path, chỉ thay domain)
    
    Args:
        published_url: URL gốc từ website sermitsiaq.ag
        base_url: Base URL (scheme + host), nếu None sẽ dùng từ request context
    
    Returns:
        URL mới với domain mới, giữ nguyên path
    
    Examples:
        get_article_url_from_published_url('https://www.sermitsiaq.ag/samfund/article/123')
        -> '/samfund/article/123' (nếu base_url=None)
        -> 'https://sermitsiaq.com/samfund/article/123' (nếu base_url='https://sermitsiaq.com')
    """
    if not published_url:
        return None
    
    from urllib.parse import urlparse
    from flask import request, has_request_context
    
    # Parse published_url để lấy path
    parsed = urlparse(published_url)
    path_only = parsed.path
    
    # Nếu có base_url, tạo full URL
    if base_url:
        # Remove trailing slash từ base_url
        base_url = base_url.rstrip('/')
        return f"{base_url}{path_only}"
    
    # Nếu có request context, tạo full URL từ request
    if has_request_context():
        try:
            scheme = request.scheme
            host = request.host
            return f"{scheme}://{host}{path_only}"
        except:
            pass
    
    # Fallback: chỉ trả về path
    return path_only

