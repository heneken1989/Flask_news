from flask import Blueprint, render_template, request, make_response, session, jsonify
from datetime import datetime
from utils import apply_grid_size_pattern, prepare_home_layouts, get_home_articles_by_language
from database import Article, Category, db
from sqlalchemy import or_, func

article_view_bp = Blueprint('article_views', __name__)

@article_view_bp.route('/home-test')
def home_test():
    """
    Home page test - Load layout từ file và link với articles trong DB (chỉ trong memory)
    
    Flow:
    1. Load layout structure từ JSON file mới nhất
    2. Link với articles đã có trong DB (không update DB, chỉ trong memory)
    3. Hiển thị view
    
    Nếu không có file JSON, sẽ query trực tiếp từ DB (articles đã được link trước đó)
    """
    from database import db
    import json
    from pathlib import Path
    
    # Get current language - Default to 'da' cho home-test để test
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'da'  # Default 'da' cho home-test
    except:
        current_language = session.get('language', 'da')  # Default 'da' cho home-test
    
    # Check URL parameter for language override (highest priority)
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    print(f"\n{'='*60}")
    print(f"🏠 Home Test View")
    print(f"{'='*60}")
    print(f"   Language: {current_language}")
    print(f"   Session language: {session.get('language', 'N/A')}")
    print(f"   Request args: {dict(request.args)}")
    
    # ⚠️ QUAN TRỌNG: Luôn dùng DA layout cho tất cả languages
    # Layout được crawl từ DA URL, sau đó thay thế articles bằng version tương ứng
    layouts_dir = Path(__file__).parent.parent / 'scripts' / 'home_layouts'
    layout_items = []
    
    if layouts_dir.exists():
        # Luôn tìm DA layout (không phụ thuộc vào current_language)
        json_files = list(layouts_dir.glob('home_layout_da_*.json'))
        if json_files:
            # Lấy file mới nhất
            latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"   📄 Loading DA layout from: {latest_json.name} (for language: {current_language})")
            
            try:
                with open(latest_json, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    layout_items = layout_data.get('layout_items', [])
                print(f"   ✅ Loaded {len(layout_items)} layout items from DA layout")
                print(f"   ℹ️  Will replace with {current_language} articles")
            except Exception as e:
                print(f"   ⚠️  Error loading JSON: {e}")
    
    articles = []
    
    if layout_items:
        # Có layout structure → Link với articles trong DB
        print(f"   🔗 Linking articles with layout...")
        
        # Pre-fetch tất cả articles của language này
        all_articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).all()
        
        articles_map = {}
        for article in all_articles:
            if article.published_url:
                if article.published_url not in articles_map:
                    articles_map[article.published_url] = []
                articles_map[article.published_url].append(article)
        
        print(f"   📚 Found {len(articles_map)} unique URLs in database")
        
        if len(articles_map) == 0:
            print(f"   ⚠️  WARNING: No articles found in database! Cannot link layout.")
            articles = []
        
        # Link articles với layout
        for layout_item in layout_items:
            published_url = layout_item.get('published_url', '')
            layout_type = layout_item.get('layout_type', '')
            display_order = layout_item.get('display_order', 0)
            
            # Xử lý containers (slider, job_slider, 5_articles)
            if layout_type in ['slider', 'job_slider', '5_articles']:
                # ⚠️ ƯU TIÊN: Tìm container trong DB trước
                # ⚠️ Nếu có nhiều containers cùng display_order, lấy cái mới nhất (created_at DESC)
                db_container = Article.query.filter_by(
                    layout_type=layout_type,
                    section='home',
                    language=current_language,
                    display_order=display_order,
                    is_home=True
                ).order_by(Article.created_at.desc()).first()
                
                if db_container:
                    # ✅ Tìm thấy trong DB - Dùng toàn bộ dữ liệu từ DB
                    container_data = {
                        'id': db_container.id,
                        'title': db_container.title or (db_container.layout_data.get('slider_title', '') if db_container.layout_data else ''),
                        'layout_type': layout_type,
                        'display_order': db_container.display_order,
                        'layout_data': db_container.layout_data.copy() if db_container.layout_data else {},
                        'published_url': '',
                        'is_home': True,
                        'section': 'home'
                    }
                    print(f"      ✅ Using {layout_type} from DB (ID: {db_container.id}, display_order: {db_container.display_order})")
                else:
                    # ⚠️ Không tìm thấy trong DB - Fallback sang layout file
                    print(f"      ⚠️  {layout_type} not found in DB (display_order: {display_order}), using layout file")
                    
                    # Get layout_data from layout_item
                    layout_item_data = layout_item.get('layout_data', {})
                    
                    # Set default items_per_view dựa trên layout_type
                    default_items_per_view = 5 if layout_type == '5_articles' else 4
                    default_source_class = 'source_nuuk' if layout_type == '5_articles' else 'source_nyheder'
                    
                    container_data = {
                        'id': None,
                        'title': layout_item_data.get('slider_title', ''),
                        'layout_type': layout_type,
                        'display_order': display_order,
                        'layout_data': {
                            'slider_title': layout_item_data.get('slider_title', ''),
                            'slider_articles': [],
                            'has_nav': layout_item_data.get('has_nav', False if layout_type == '5_articles' else True),
                            'items_per_view': layout_item_data.get('items_per_view', default_items_per_view),
                            'source_class': layout_item_data.get('source_class', default_source_class)
                        },
                        'published_url': '',
                        'is_home': True,
                        'section': 'home'
                    }
                    
                    # Job slider specific fields
                    if layout_type == 'job_slider':
                        container_data['layout_data']['header_link'] = layout_item_data.get('header_link')
                        container_data['layout_data']['extra_classes'] = layout_item_data.get('extra_classes', [])
                        container_data['layout_data']['header_classes'] = layout_item_data.get('header_classes', [])
                    
                    # Link các articles trong container từ layout file
                    slider_articles = layout_item_data.get('slider_articles', [])
                    for slider_article in slider_articles:
                        slider_url = slider_article.get('published_url') or slider_article.get('url', '')
                        if slider_url and slider_url in articles_map:
                            for article in articles_map[slider_url]:
                                if article.language == current_language:
                                    article_dict = article.to_dict()
                                    container_data['layout_data']['slider_articles'].append(article_dict)
                                    break
                        elif slider_url:
                            # Job slider articles từ sjob.gl - không có trong DB
                            container_data['layout_data']['slider_articles'].append(slider_article)
                
                articles.append(container_data)
                continue
            
            # Xử lý articles thông thường
            if not published_url:
                continue
            
            # Tìm article trong DB
            if published_url in articles_map:
                matched_article = None
                
                # ⚠️ QUAN TRỌNG: 
                # - Với 1_with_list_left/right: chỉ lấy article có section='home'
                # - Với các layout khác: lấy từ tất cả section (không ưu tiên section='home')
                require_home_section = layout_type in ['1_with_list_left', '1_with_list_right']
                
                if require_home_section:
                    # Chỉ lấy article có section='home'
                    for article in articles_map[published_url]:
                        if article.language == current_language and article.section == 'home':
                            matched_article = article
                            break
                else:
                    # Lấy article đầu tiên cùng language (từ bất kỳ section nào)
                    # ⚠️ QUAN TRỌNG: Ưu tiên article có is_home=True (vì đang ở home page)
                    for article in articles_map[published_url]:
                        if article.language == current_language:
                            if article.is_home:
                                matched_article = article
                                break
                    
                    # Nếu không có article với is_home=True, lấy article đầu tiên
                    if not matched_article:
                        for article in articles_map[published_url]:
                            if article.language == current_language:
                                matched_article = article
                                break
                
                if matched_article:
                    article_dict = matched_article.to_dict()
                    # Update metadata từ layout (chỉ trong memory)
                    # ⚠️ QUAN TRỌNG: Giữ nguyên section gốc (samfund, sport, etc.)
                    # Chỉ set is_home=True để articles vẫn hiển thị được ở các tag
                    article_dict['display_order'] = display_order
                    article_dict['layout_type'] = layout_type
                    
                    # Merge layout_data: giữ lại từ DB, update với data từ layout_item
                    existing_layout_data = article_dict.get('layout_data', {}) or {}
                    
                    new_layout_data = {
                        'row_index': layout_item.get('row_index', -1),
                        'article_index_in_row': layout_item.get('article_index_in_row', -1),
                        'total_rows': layout_item.get('total_rows', 0)
                    }
                    
                    # Thêm list_items và list_title cho 1_with_list_left/right
                    if layout_type in ['1_with_list_left', '1_with_list_right']:
                        # ⚠️ QUAN TRỌNG: Ưu tiên lấy từ EN article's layout_data (nếu đã được translate)
                        # Nếu không có, mới lấy từ layout_item (DA layout)
                        if current_language == 'en' and existing_layout_data.get('list_items'):
                            # EN article đã có list_items được translate → dùng
                            list_items = existing_layout_data.get('list_items', [])
                            list_title = existing_layout_data.get('list_title', '')
                            if display_order < 5:
                                print(f"         📋 Using translated list_items from EN article's layout_data: {len(list_items)} items")
                        else:
                            # Lấy từ layout_item (DA layout)
                            list_items = layout_item.get('list_items', []) or layout_item.get('layout_data', {}).get('list_items', [])
                            list_title = layout_item.get('list_title', '') or layout_item.get('layout_data', {}).get('list_title', '')
                            if current_language == 'en' and display_order < 5:
                                print(f"         📋 Using list_items from DA layout (not translated): {len(list_items)} items")
                        
                        if list_items:
                            new_layout_data['list_items'] = list_items
                        if list_title:
                            new_layout_data['list_title'] = list_title
                    
                    # Merge với existing (ưu tiên existing cho list_items và list_title nếu không có trong new)
                    layout_item_data = layout_item.get('layout_data', {}) or {}
                    for key, value in layout_item_data.items():
                        existing_layout_data[key] = value
                    
                    # Merge new_layout_data vào existing
                    for key, value in new_layout_data.items():
                        if key in ['list_items', 'list_title']:
                            # Chỉ update nếu có giá trị mới
                            if value:
                                existing_layout_data[key] = value
                        else:
                            # Update bình thường
                            existing_layout_data[key] = value
                    
                    article_dict['layout_data'] = existing_layout_data
                    
                    article_dict['grid_size'] = layout_item.get('grid_size', 6)
                    article_dict['is_home'] = True
                    # KHÔNG set section='home' - giữ nguyên section gốc
                    # article_dict['section'] giữ nguyên từ matched_article
                    articles.append(article_dict)
        
        # Sort theo display_order
        articles.sort(key=lambda x: x.get('display_order', 0))
        print(f"   ✅ Linked {len(articles)} articles with layout")
    else:
        # Không có layout file → Query trực tiếp từ DB (articles đã được link trước đó)
        print(f"   📊 No layout file found, querying from DB...")
        try:
            article_objects = get_home_articles_by_language(
                language=current_language,
                limit=None,
                exclude_temp=True  # ⚠️ Chỉ lấy articles đã hoàn thành (is_temp=False)
            )
            print(f"   📚 Query returned {len(article_objects)} articles (before filter)")
            
            # Filter chỉ lấy articles có layout_type
            article_objects = [a for a in article_objects if a.layout_type]
            print(f"   📐 After layout_type filter: {len(article_objects)} articles")
            
            if article_objects:
                print(f"   📋 First 5 articles:")
                for idx, art in enumerate(article_objects[:5], 1):
                    print(f"      {idx}. ID={art.id}, layout_type={art.layout_type}, display_order={art.display_order}, title={art.title[:50]}...")
            
            articles = [article.to_dict() for article in article_objects]
            print(f"   ✅ Found {len(articles)} articles from DB")
        except Exception as e:
            print(f"   ⚠️  Error loading articles: {e}")
            import traceback
            traceback.print_exc()
            articles = []
    
    # Debug: Log số lượng articles trước khi prepare
    print(f"\n📊 Before prepare_home_layouts: {len(articles)} articles")
    if articles:
        print(f"   First article: layout_type={articles[0].get('layout_type')}, display_order={articles[0].get('display_order')}")
    
    # Prepare layouts
    layouts = []
    if articles:
        layouts = prepare_home_layouts(articles)
        print(f"📐 After prepare_home_layouts: {len(layouts)} layouts")
    else:
        print(f"⚠️  No articles to prepare, returning empty layouts")
    
    # Apply grid size pattern (nếu cần)
    # Note: prepare_home_layouts đã xử lý grid_size, không cần apply_grid_size_pattern nữa
    
    # Debug: Log final layouts count
    print(f"\n✅ Final layouts count: {len(layouts)}")
    if not layouts:
        print(f"⚠️  WARNING: No layouts to display!")
        if articles:
            print(f"   ⚠️  But we have {len(articles)} articles - check prepare_home_layouts logic")
    
    # Generate SEO meta tags cho home test page - thay đổi theo ngôn ngữ
    from utils_seo import get_seo_meta, get_structured_data
    
    # Title và description theo ngôn ngữ
    home_titles = {
        'da': "Sermitsiaq.AG Nyheder",
        'kl': "Sermitsiaq.AG Allat",  # Greenlandic
        'en': "Sermitsiaq.AG News"
    }
    home_descriptions = {
        'da': "Sermitsiaq er Grønlands største nyhedssite med nyheder, debat og kultur.",
        'kl': "Sermitsiaq Kalaallit Nunaanni allanngortitsineqartarpoq allat, oqaatigineq aamma kulturi.",  # Greenlandic
        'en': "Sermitsiaq is Greenland's largest news site with news, debate and culture."
    }
    
    seo_meta = get_seo_meta(
        page_type='home',
        language=current_language,
        title=home_titles.get(current_language, home_titles['da']),
        description=home_descriptions.get(current_language, home_descriptions['da'])
    )
    structured_data = get_structured_data(
        page_type='home',
        language=current_language
    )
    
    # Render template (template expect 'layouts', not 'articles')
    return render_template('home_page.html',
        layouts=layouts,  # Template expect 'layouts'
        section_title='Home Test',
        articles_per_row=2,
        section='home',
        is_home_page=True,
        show_top_ad=False,
        show_bottom_ad=False,
        seo_meta=seo_meta,
        structured_data=structured_data
    )

@article_view_bp.route('/')
def index():
    """
    Home page - Load layout từ file và link với articles trong DB
    Sử dụng logic từ home_test() đã được test và ổn định
    
    Flow:
    1. Load layout structure từ JSON file mới nhất:
       - KL: Dùng KL layout riêng (home_layout_kl_*.json)
       - DA: Dùng DA layout (home_layout_da_*.json)
       - EN: Dùng DA layout (vì EN articles link với DA articles)
    2. Link với articles đã có trong DB (không update DB, chỉ trong memory)
    3. Hiển thị view
    
    Nếu không có file JSON, sẽ query trực tiếp từ DB (articles đã được link trước đó)
    """
    from database import db
    import json
    from pathlib import Path
    
    # Get current language - Default to 'da' for home page
    # Priority: URL param > Session > Flask-Babel locale > 'da' (default)
    current_language = 'da'  # Default to 'da' for home page
    
    # Check Flask-Babel locale first
    from flask_babel import get_locale
    try:
        locale = get_locale()
        if locale and str(locale) in ['da', 'kl', 'en']:
            current_language = str(locale)
    except:
        pass  # Keep default 'da'
    
    # Check session (override Flask-Babel if session has language)
    session_lang = session.get('language')
    if session_lang and session_lang in ['da', 'kl', 'en']:
        current_language = session_lang  # Session có priority cao hơn Flask-Babel
    
    # Check URL parameter for language override (highest priority)
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    print(f"\n{'='*60}")
    print(f"🏠 Home Page")
    print(f"{'='*60}")
    print(f"   Language: {current_language}")
    print(f"   Session language: {session.get('language', 'N/A')}")
    print(f"   Request args: {dict(request.args)}")
    
    # ⚠️ QUAN TRỌNG: 
    # - KL: Dùng KL layout riêng (độc lập)
    # - DA: Dùng DA layout
    # - EN: Dùng DA layout (vì EN articles link với DA articles qua published_url)
    layouts_dir = Path(__file__).parent.parent / 'scripts' / 'home_layouts'
    layout_items = []
    
    if layouts_dir.exists():
        # Xác định layout file cần dùng dựa trên current_language
        # ⚠️ Sử dụng tên file cố định (ghi đè mỗi lần crawl)
        if current_language == 'kl':
            # KL dùng layout KL riêng
            layout_file = layouts_dir / 'home_layout_kl.json'
            layout_type_name = 'KL'
        else:
            # DA và EN đều dùng DA layout
            layout_file = layouts_dir / 'home_layout_da.json'
            layout_type_name = 'DA'
        
        if layout_file.exists():
            print(f"   📄 Loading {layout_type_name} layout from: {layout_file.name} (for language: {current_language})")
            
            try:
                with open(layout_file, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    layout_items = layout_data.get('layout_items', [])
                print(f"   ✅ Loaded {len(layout_items)} layout items from {layout_type_name} layout")
                print(f"   ℹ️  Will use {current_language} articles")
            except Exception as e:
                print(f"   ⚠️  Error loading JSON: {e}")
        else:
            # Fallback: Tìm file mới nhất nếu không có file cố định
            if current_language == 'kl':
                json_files = list(layouts_dir.glob('home_layout_kl_*.json'))
            else:
                json_files = list(layouts_dir.glob('home_layout_da_*.json'))
            
            if json_files:
                latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
                print(f"   📄 Loading {layout_type_name} layout from: {latest_json.name} (fallback, for language: {current_language})")
                
                try:
                    with open(latest_json, 'r', encoding='utf-8') as f:
                        layout_data = json.load(f)
                        layout_items = layout_data.get('layout_items', [])
                    print(f"   ✅ Loaded {len(layout_items)} layout items from {layout_type_name} layout")
                    print(f"   ℹ️  Will use {current_language} articles")
                except Exception as e:
                    print(f"   ⚠️  Error loading JSON: {e}")
    
    articles = []
    
    if layout_items:
        # Có layout structure → Link với articles trong DB
        print(f"   🔗 Linking articles with layout...")
        
        # Pre-fetch articles - chỉ lấy articles có is_home=True cho home page
        # ⚠️ QUAN TRỌNG: Chỉ lấy articles đã được link vào home (is_home=True) và is_temp=False
        # ⚠️ QUAN TRỌNG: Bao gồm cả containers (slider, job_slider, 5_articles) không có published_url
        all_articles = Article.query.filter(
            Article.is_home == True,  # Chỉ lấy articles đã được link vào home
            Article.is_temp == False  # ⚠️ Chỉ lấy articles đã hoàn thành (đã crawl detail)
        ).filter(
            # Articles có published_url HOẶC containers (slider, job_slider, 5_articles)
            db.or_(
                db.and_(
                    Article.published_url.isnot(None),
                    Article.published_url != ''
                ),
                Article.layout_type.in_(['slider', 'job_slider', '5_articles'])
            )
        ).all()
        
        articles_map = {}
        containers_list = []  # List để lưu containers (slider, job_slider, 5_articles)
        for article in all_articles:
            if article.published_url:
                if article.published_url not in articles_map:
                    articles_map[article.published_url] = []
                articles_map[article.published_url].append(article)
            elif article.layout_type in ['slider', 'job_slider', '5_articles']:
                # Containers không có published_url, lưu riêng
                containers_list.append(article)
        
        print(f"   📚 Found {len(articles_map)} unique URLs in database (is_home=True)")
        
        # Debug: Count articles by language
        lang_counts = {}
        for url, article_list in articles_map.items():
            for article in article_list:
                lang = article.language
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        print(f"   📊 Articles by language (is_home=True): {lang_counts}")
        
        # Debug: Show sample EN articles if current_language is EN
        if current_language == 'en':
            en_sample_count = 0
            print(f"   🔍 Sample EN articles in articles_map:")
            for url, article_list in articles_map.items():
                for article in article_list:
                    if article.language == 'en' and en_sample_count < 5:
                        print(f"      - URL: {url[:60]}... | ID: {article.id} | Title: {article.title[:60]}...")
                        en_sample_count += 1
                if en_sample_count >= 5:
                    break
        
        if len(articles_map) == 0:
            print(f"   ⚠️  WARNING: No articles found in database! Cannot link layout.")
            articles = []
        
        # Link articles với layout
        for layout_item in layout_items:
            published_url = layout_item.get('published_url', '')
            layout_type = layout_item.get('layout_type', '')
            display_order = layout_item.get('display_order', 0)
            
            # Xử lý containers (slider, job_slider, 5_articles)
            if layout_type in ['slider', 'job_slider', '5_articles']:
                # ⚠️ ƯU TIÊN: Tìm container trong DB trước
                # ⚠️ Nếu có nhiều containers cùng display_order, lấy cái mới nhất (created_at DESC)
                db_container = Article.query.filter_by(
                    layout_type=layout_type,
                    section='home',
                    language=current_language,
                    display_order=display_order,
                    is_home=True
                ).order_by(Article.created_at.desc()).first()
                
                if db_container:
                    # ✅ Tìm thấy trong DB - Dùng toàn bộ dữ liệu từ DB
                    container_data = {
                        'id': db_container.id,
                        'title': db_container.title or (db_container.layout_data.get('slider_title', '') if db_container.layout_data else ''),
                        'layout_type': layout_type,
                        'display_order': db_container.display_order,
                        'layout_data': db_container.layout_data.copy() if db_container.layout_data else {},
                        'published_url': '',
                        'is_home': True,
                        'section': 'home'
                    }
                    print(f"      ✅ Using {layout_type} from DB (ID: {db_container.id}, display_order: {db_container.display_order})")
                else:
                    # ⚠️ Không tìm thấy trong DB - Fallback sang layout file
                    print(f"      ⚠️  {layout_type} not found in DB (display_order: {display_order}), using layout file")
                    
                    # Get layout_data from layout_item
                    layout_item_data = layout_item.get('layout_data', {})
                    
                    # Set default items_per_view dựa trên layout_type
                    default_items_per_view = 5 if layout_type == '5_articles' else 4
                    default_source_class = 'source_nuuk' if layout_type == '5_articles' else 'source_nyheder'
                    
                    container_data = {
                        'id': None,
                        'title': layout_item_data.get('slider_title', ''),
                        'layout_type': layout_type,
                        'display_order': display_order,
                        'layout_data': {
                            'slider_title': layout_item_data.get('slider_title', ''),
                            'slider_articles': [],
                            'has_nav': layout_item_data.get('has_nav', False if layout_type == '5_articles' else True),
                            'items_per_view': layout_item_data.get('items_per_view', default_items_per_view),
                            'source_class': layout_item_data.get('source_class', default_source_class)
                        },
                        'published_url': '',
                        'is_home': True,
                        'section': 'home'
                    }
                    
                    # Job slider specific fields
                    if layout_type == 'job_slider':
                        container_data['layout_data']['header_link'] = layout_item_data.get('header_link')
                        container_data['layout_data']['extra_classes'] = layout_item_data.get('extra_classes', [])
                        container_data['layout_data']['header_classes'] = layout_item_data.get('header_classes', [])
                    
                    # Link các articles trong container từ layout file
                    slider_articles = layout_item_data.get('slider_articles', [])
                    for slider_article in slider_articles:
                        slider_url = slider_article.get('published_url') or slider_article.get('url', '')
                        if slider_url and slider_url in articles_map:
                            for article in articles_map[slider_url]:
                                if article.language == current_language:
                                    article_dict = article.to_dict()
                                    container_data['layout_data']['slider_articles'].append(article_dict)
                                    break
                        elif slider_url:
                            # Job slider articles từ sjob.gl - không có trong DB
                            container_data['layout_data']['slider_articles'].append(slider_article)
                
                articles.append(container_data)
                continue
            
            # Xử lý articles thông thường
            if not published_url:
                continue
            
            # Tìm article trong DB
            if published_url in articles_map:
                matched_article = None
                
                # ⚠️ QUAN TRỌNG: 
                # - Với 1_with_list_left/right: chỉ lấy article có section='home'
                # - Với các layout khác: lấy từ tất cả section (không ưu tiên section='home')
                require_home_section = layout_type in ['1_with_list_left', '1_with_list_right']
                
                if require_home_section:
                    # Chỉ lấy article có section='home'
                    for article in articles_map[published_url]:
                        if article.language == current_language and article.section == 'home':
                            matched_article = article
                            break
                else:
                    # Lấy article đầu tiên cùng language (từ bất kỳ section nào)
                    # ⚠️ QUAN TRỌNG: Ưu tiên article có is_home=True (vì đang ở home page)
                    for article in articles_map[published_url]:
                        if article.language == current_language:
                            if article.is_home:
                                matched_article = article
                                break
                    
                    # Nếu không có article với is_home=True, lấy article đầu tiên
                    if not matched_article:
                        for article in articles_map[published_url]:
                            if article.language == current_language:
                                matched_article = article
                                break
                
                if matched_article:
                    article_dict = matched_article.to_dict()
                    # Update metadata từ layout (chỉ trong memory)
                    # ⚠️ QUAN TRỌNG: Giữ nguyên section gốc (samfund, sport, etc.)
                    # Chỉ set is_home=True để articles vẫn hiển thị được ở các tag
                    article_dict['display_order'] = display_order
                    article_dict['layout_type'] = layout_type
                    
                    # Merge layout_data: giữ lại từ DB, update với data từ layout_item
                    existing_layout_data = article_dict.get('layout_data', {}) or {}
                    
                    new_layout_data = {
                        'row_index': layout_item.get('row_index', -1),
                        'article_index_in_row': layout_item.get('article_index_in_row', -1),
                        'total_rows': layout_item.get('total_rows', 0)
                    }
                    
                    # Thêm list_items và list_title cho 1_with_list_left/right
                    if layout_type in ['1_with_list_left', '1_with_list_right']:
                        # ⚠️ QUAN TRỌNG: Ưu tiên lấy từ EN article's layout_data (nếu đã được translate)
                        # Nếu không có, mới lấy từ layout_item (DA layout)
                        if current_language == 'en' and existing_layout_data.get('list_items'):
                            # EN article đã có list_items được translate → dùng
                            list_items = existing_layout_data.get('list_items', [])
                            list_title = existing_layout_data.get('list_title', '')
                            if display_order < 5:
                                print(f"         📋 Using translated list_items from EN article's layout_data: {len(list_items)} items")
                        else:
                            # Lấy từ layout_item (DA layout)
                            list_items = layout_item.get('list_items', []) or layout_item.get('layout_data', {}).get('list_items', [])
                            list_title = layout_item.get('list_title', '') or layout_item.get('layout_data', {}).get('list_title', '')
                            if current_language == 'en' and display_order < 5:
                                print(f"         📋 Using list_items from DA layout (not translated): {len(list_items)} items")
                        
                        if list_items:
                            new_layout_data['list_items'] = list_items
                        if list_title:
                            new_layout_data['list_title'] = list_title
                    
                    # Merge với existing (ưu tiên existing cho list_items và list_title nếu không có trong new)
                    layout_item_data = layout_item.get('layout_data', {}) or {}
                    for key, value in layout_item_data.items():
                        existing_layout_data[key] = value
                    
                    # Merge new_layout_data vào existing
                    for key, value in new_layout_data.items():
                        if key in ['list_items', 'list_title']:
                            # Chỉ update nếu có giá trị mới
                            if value:
                                existing_layout_data[key] = value
                        else:
                            # Update bình thường
                            existing_layout_data[key] = value
                    
                    article_dict['layout_data'] = existing_layout_data
                    
                    article_dict['grid_size'] = layout_item.get('grid_size', 6)
                    article_dict['is_home'] = True
                    # KHÔNG set section='home' - giữ nguyên section gốc
                    # article_dict['section'] giữ nguyên từ matched_article
                    articles.append(article_dict)
        
        # Sort theo display_order
        articles.sort(key=lambda x: x.get('display_order', 0))
        print(f"   ✅ Linked {len(articles)} articles with layout")
    else:
        # Không có layout file → Query trực tiếp từ DB (articles đã được link trước đó)
        print(f"   📊 No layout file found, querying from DB...")
        try:
            article_objects = get_home_articles_by_language(
                language=current_language,
                limit=None,
                exclude_temp=True  # ⚠️ Chỉ lấy articles đã hoàn thành (is_temp=False)
            )
            print(f"   📚 Query returned {len(article_objects)} articles (before filter)")
            
            # Filter chỉ lấy articles có layout_type
            article_objects = [a for a in article_objects if a.layout_type]
            print(f"   📐 After layout_type filter: {len(article_objects)} articles")
            
            if article_objects:
                print(f"   📋 First 5 articles:")
                for idx, art in enumerate(article_objects[:5], 1):
                    print(f"      {idx}. ID={art.id}, layout_type={art.layout_type}, display_order={art.display_order}, title={art.title[:50]}...")
            
            articles = [article.to_dict() for article in article_objects]
            print(f"   ✅ Found {len(articles)} articles from DB")
        except Exception as e:
            print(f"   ⚠️  Error loading articles: {e}")
            import traceback
            traceback.print_exc()
            articles = []
    
    # Debug: Log số lượng articles trước khi prepare
    print(f"\n📊 Before prepare_home_layouts: {len(articles)} articles")
    if articles:
        first_article = articles[0]
        print(f"   First article: layout_type={first_article.get('layout_type')}, display_order={first_article.get('display_order')}")
        print(f"   First article title: {first_article.get('title', 'N/A')[:60]}...")
        print(f"   First article language: {first_article.get('language', 'N/A')}")
        print(f"   First article ID: {first_article.get('id', 'N/A')}")
        
        # Debug: Kiểm tra articles xung quanh job slider và row 20
        row_20_articles_in_list = [a for a in articles if a.get('display_order', 0) >= 20000 and a.get('display_order', 0) < 20100]
        print(f"   📊 Articles với display_order 20000-20099 trong list: {len(row_20_articles_in_list)}")
        for a in row_20_articles_in_list:
            print(f"      - display_order: {a.get('display_order')}, layout_type: {a.get('layout_type')}, id: {a.get('id', 'N/A')}, title: {a.get('title', 'N/A')[:40]}...")
        
        # Kiểm tra job slider
        job_sliders_in_list = [a for a in articles if a.get('layout_type') == 'job_slider' and a.get('display_order') == 19000]
        print(f"   📊 Job sliders với display_order=19000 trong list: {len(job_sliders_in_list)}")
        for a in job_sliders_in_list:
            print(f"      - display_order: {a.get('display_order')}, id: {a.get('id', 'N/A')}")
        
        # Tìm vị trí của job slider và row 20 articles trong list
        for idx, a in enumerate(articles):
            if a.get('layout_type') == 'job_slider' and a.get('display_order') == 19000:
                print(f"   📍 Job slider tại index: {idx}")
            if a.get('display_order') == 20000:
                print(f"   📍 Article 20000 tại index: {idx}, layout_type: {a.get('layout_type')}")
            if a.get('display_order') == 20001:
                print(f"   📍 Article 20001 tại index: {idx}, layout_type: {a.get('layout_type')}")
            if a.get('display_order') == 20002:
                print(f"   📍 Article 20002 tại index: {idx}, layout_type: {a.get('layout_type')}")
    
    # Prepare layouts
    layouts = []
    if articles:
        layouts = prepare_home_layouts(articles)
        print(f"📐 After prepare_home_layouts: {len(layouts)} layouts")
        
        # Debug: Check first layout's article title
        if layouts and len(layouts) > 0:
            first_layout = layouts[0]
            if first_layout.get('layout_type') == '1_full' and first_layout.get('data', {}).get('article'):
                first_layout_article = first_layout['data']['article']
                print(f"   🔍 First layout article title: {first_layout_article.get('title', 'N/A')[:60]}...")
                print(f"   🔍 First layout article language: {first_layout_article.get('language', 'N/A')}")
                print(f"   🔍 First layout article ID: {first_layout_article.get('id', 'N/A')}")
    else:
        print(f"⚠️  No articles to prepare, returning empty layouts")
    
    # Generate SEO meta tags cho home page - thay đổi theo ngôn ngữ
    from utils_seo import get_seo_meta, get_structured_data
    
    # Title và description theo ngôn ngữ
    home_titles = {
        'da': "Sermitsiaq.COM Nyheder",
        'kl': "Sermitsiaq.COM Allat",  # Greenlandic
        'en': "Sermitsiaq.COM News"
    }
    home_descriptions = {
        'da': "Sermitsiaq er Grønlands største nyhedssite med nyheder, debat og kultur.",
        'kl': "Sermitsiaq Kalaallit Nunaanni allanngortitsineqartarpoq allat, oqaatigineq aamma kulturi.",  # Greenlandic
        'en': "Sermitsiaq is Greenland's largest news site with news, debate and culture."
    }
    
    seo_meta = get_seo_meta(
        page_type='home',
        language=current_language,
        title=home_titles.get(current_language, home_titles['da']),
        description=home_descriptions.get(current_language, home_descriptions['da'])
    )
    structured_data = get_structured_data(
        page_type='home',
        language=current_language
    )
    
    # Tạo response với headers để tránh cache issues
    response = make_response(render_template('home_page.html',
        layouts=layouts,
        section_title='Home',
        section='home',
        is_home_page=True,
        show_top_ad=False,
        show_bottom_ad=False,
        seo_meta=seo_meta,
        structured_data=structured_data
    ))
    
    # Thêm headers để tránh cache và CORS issues
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    print(f"✅ / (home) response sent successfully")
    return response

# Route /home đã được chuyển sang route / (root)
# @article_view_bp.route('/home')
# def home():
#     ... (code đã được chuyển sang route /)

@article_view_bp.route('/podcasti')
def podcasti_section():
    """
    Display podcasti articles
    Route: /podcasti (direct route, không qua /tag/)
    Shows 50 newest articles from podcasti section
    """
    # Gọi trực tiếp tag_section với section='podcasti'
    return tag_section('podcasti')


@article_view_bp.route('/tag/<section>')
def tag_section(section):
    """
    Display articles by section/category or tag
    Routes:
    - /tag/samfund, /tag/erhverv, /tag/kultur, /tag/sport, /tag/podcasti (sections)
    - /tag/{tag_name} (dynamic tags from article.layout_data['tags'])
    
    Shows articles filtered by section (if valid section) or by tag name
    """
    from database import db
    from sqlalchemy import func, or_
    
    # Decode URL-encoded tag name (replace %20 with space, etc.)
    import urllib.parse
    section = urllib.parse.unquote(section)
    
    # Validate section - check if it's a predefined section
    valid_sections = ['samfund', 'erhverv', 'kultur', 'sport', 'podcasti']
    is_section = section.lower() in valid_sections
    
    # If not a valid section, treat it as a tag name
    if not is_section:
        # Query articles by tag name in layout_data['tags']
        # This will be handled later in the query logic
        pass
    
    # Get current language from session or default
    # Use get_locale() from flask_babel to be consistent with app default
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'da'
    except:
        # Fallback: check session or default to 'da'
        current_language = session.get('language', 'da')
    
    # Check URL parameter for language override (highest priority)
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    # Section name mapping theo ngôn ngữ
    section_names = {
        'da': {
            'samfund': 'Samfund',
            'erhverv': 'Erhverv',
            'kultur': 'Kultur',
            'sport': 'Sport',
            'podcasti': 'Podcasti'
        },
        'kl': {
            'samfund': 'Nalunaarsuit',  # Greenlandic translation
            'erhverv': 'Suliniartitsisut',
            'kultur': 'Kulturi',
            'sport': 'Sport',
            'podcasti': 'Podcasti'
        },
        'en': {
            'samfund': 'Society',
            'erhverv': 'Business',
            'kultur': 'Culture',
            'sport': 'Sport',
            'podcasti': 'Podcast'
        }
    }
    
    # Determine section_name and query logic
    if is_section:
        # Lấy section name theo ngôn ngữ hiện tại
        section_name = section_names.get(current_language, section_names['da']).get(section, section)
        
        # Query articles theo section
        query = Article.query.filter_by(
            section=section,
            language=current_language
        )
    else:
        # Treat as tag name - query articles by tag in layout_data['tags']
        tag_name = section  # Use the decoded tag name
        section_name = tag_name  # Use tag name as display name
        
        # Query articles where tags field contains the tag name
        # PostgreSQL JSONB: check if tags array contains the tag name (case-insensitive)
        # Use jsonb_array_elements_text to extract tags and compare case-insensitively
        from sqlalchemy import text as sql_text
        
        # Method: Use PostgreSQL jsonb_array_elements_text with LOWER() for case-insensitive match
        # This is more reliable than ILIKE on cast to text, especially for Unicode characters
        query = Article.query.filter(
            Article.language == current_language,
            Article.tags.isnot(None)
        ).filter(
            sql_text("""
                EXISTS (
                    SELECT 1 
                    FROM jsonb_array_elements_text(articles.tags) AS tag
                    WHERE LOWER(tag) = LOWER(:tag_name)
                )
            """).bindparams(tag_name=tag_name)
        )
    
    # Chỉ filter is_temp=False cho EN và KL (translated articles)
    # DA articles không bao giờ là temp vì chúng là ngôn ngữ gốc
    if current_language in ['en', 'kl']:
        query = query.filter_by(is_temp=False)
    
    # Query articles từ database
    articles = []
    try:
        
        # Order by: ưu tiên articles có section != 'home' trước, sau đó mới đến published_date
        # Sử dụng CASE WHEN để sort: section != 'home' = 0 (ưu tiên), section = 'home' = 1 (sau)
        from sqlalchemy import case
        articles = query.order_by(
            case((Article.section != 'home', 0), else_=1),  # Ưu tiên section != 'home'
            Article.published_date.desc().nullslast()
        ).limit(100).all()  # Lấy nhiều hơn để filter duplicate
        
        # ⚠️ QUAN TRỌNG: Loại bỏ duplicate articles theo k5a_url hoặc published_url
        # Nếu có nhiều articles cùng published_url, ưu tiên article có section != 'home'
        k5a_url_to_article = {}  # Dict: {k5a_url: Article} - giữ article ưu tiên
        seen_urls = set()  # Track published_url để tránh duplicate theo URL (cho articles không có k5a_url)
        
        for article in articles:
            if not article.published_url:
                # Articles không có URL (sliders) vẫn giữ lại, xử lý sau
                continue
            
            # Xử lý articles có published_url
            if article.k5a_url:
                # Có k5a_url → check duplicate theo k5a_url
                if article.k5a_url not in k5a_url_to_article:
                    # Chưa có article với k5a_url này → thêm vào
                    k5a_url_to_article[article.k5a_url] = article
                else:
                    # Đã có article với k5a_url này → ưu tiên section != 'home'
                    existing_article = k5a_url_to_article[article.k5a_url]
                    
                    # Ưu tiên: section != 'home' > section == 'home'
                    if existing_article.section == 'home' and article.section != 'home':
                        # Article mới không phải home, article cũ là home → thay thế
                        k5a_url_to_article[article.k5a_url] = article
                    elif existing_article.section != 'home' and article.section == 'home':
                        # Article cũ không phải home, article mới là home → giữ article cũ
                        pass
                    else:
                        # Cả hai cùng loại (cùng home hoặc cùng không home) → giữ article mới hơn (created_at)
                        if article.created_at and existing_article.created_at:
                            if article.created_at > existing_article.created_at:
                                k5a_url_to_article[article.k5a_url] = article
                        elif article.created_at:
                            k5a_url_to_article[article.k5a_url] = article
            else:
                # Không có k5a_url → filter theo published_url
                if article.published_url not in seen_urls:
                    seen_urls.add(article.published_url)
                    k5a_url_to_article[article.published_url] = article
                else:
                    # Đã có article với published_url này → ưu tiên section != 'home'
                    existing_article = k5a_url_to_article[article.published_url]
                    
                    # Ưu tiên: section != 'home' > section == 'home'
                    if existing_article.section == 'home' and article.section != 'home':
                        # Article mới không phải home, article cũ là home → thay thế
                        k5a_url_to_article[article.published_url] = article
                    elif existing_article.section != 'home' and article.section == 'home':
                        # Article cũ không phải home, article mới là home → giữ article cũ
                        pass
                    else:
                        # Cả hai cùng loại → giữ article mới hơn (created_at)
                        if article.created_at and existing_article.created_at:
                            if article.created_at > existing_article.created_at:
                                k5a_url_to_article[article.published_url] = article
                        elif article.created_at:
                            k5a_url_to_article[article.published_url] = article
        
        # Tạo list unique articles từ k5a_url_to_article
        unique_articles = list(k5a_url_to_article.values())
        
        # Thêm lại articles không có URL (sliders)
        for article in articles:
            if not article.published_url:
                unique_articles.append(article)
        
        # Sắp xếp lại theo published_date desc
        unique_articles.sort(key=lambda x: (x.published_date or datetime.min, x.created_at or datetime.min), reverse=True)
        
        # Giới hạn lại 50 articles
        articles = unique_articles[:50]
        
        # Set display_order cho pattern 2-3-2-3-2-3... (0, 1, 2, ...)
        for idx, article in enumerate(articles):
            article.display_order = idx
        
        # Convert to dict và áp dụng pattern grid_size
        articles = [article.to_dict() for article in articles]
        articles = apply_grid_size_pattern(articles)
        
    except Exception as e:
        print(f"⚠️  Database query failed for section {section}: {e}")
        articles = []
    
    # Nếu không có articles từ database, hiển thị view trống (không dùng mock data)
    # Đặc biệt cho podcasti, nếu không có articles thì hiển thị trống
    if not articles:
        print(f"ℹ️  No articles found for section {section} (language: {current_language})")
        articles = []  # Giữ empty list để hiển thị view trống
    
    # Section title - dùng section name theo ngôn ngữ
    section_title = f'Tag: {section_name}'
    
    # Generate SEO meta tags cho section page
    # Title format: "Tag: Kultur" (giống trang gốc) - thay đổi theo ngôn ngữ
    from utils_seo import get_seo_meta, get_structured_data
    
    # Description theo ngôn ngữ
    descriptions = {
        'da': f"Læs de seneste nyheder om {section_name} på Sermitsiaq.",
        'kl': f"Allat najugaqat {section_name} Sermitsiaq-mi.",  # Greenlandic
        'en': f"Read the latest news about {section_name} on Sermitsiaq."
    }
    description = descriptions.get(current_language, descriptions['da'])
    
    seo_meta = get_seo_meta(
        page_type='section',
        language=current_language,
        section=section if is_section else None,  # Only pass section if it's a valid section
        title=f"Tag: {section_name}",
        description=description
    )
    structured_data = get_structured_data(
        page_type='section',
        language=current_language
    )
    
    return render_template('front_page.html',
        articles=articles,
        section_title=section_title,
        articles_per_row=2,  # Default, sẽ bị override bởi grid_size pattern
        section=section,
        show_top_ad=False,
        show_bottom_ad=False,
        seo_meta=seo_meta,
        structured_data=structured_data
    )


@article_view_bp.route('/article')
@article_view_bp.route('/article/<int:article_id>')
@article_view_bp.route('/<section>/<slug>/<int:article_id>')
@article_view_bp.route('/<path:url_path>', methods=['GET'], strict_slashes=False)
def article_detail(article_id=None, section=None, slug=None, url_path=None):
    """
    Display article detail page
    Routes:
    - /article/<article_id>
    - /<section>/<slug>/<article_id>
    - /<path:url_path> - Match với published_url để giữ nguyên URL structure
    """
    from database import db
    from urllib.parse import urlparse
    
    # Get current language
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'en'
    except:
        current_language = session.get('language', 'en')
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    article = None
    
    # Debug: Log tất cả parameters
    print(f"🔍 article_detail called with:")
    print(f"   article_id: {article_id}")
    print(f"   section: {section}")
    print(f"   slug: {slug}")
    print(f"   url_path: {url_path}")
    print(f"   request.path: {request.path}")
    print(f"   request.url: {request.url}")
    
    # Ưu tiên: Tìm article bằng path từ published_url (giữ nguyên URL structure)
    # Nếu có url_path HOẶC có section+slug (route /<section>/<slug>/<int:article_id> match)
    # thì tìm bằng path thay vì dùng article_id
    path_only = request.path
    
    # Nếu có section và slug, đây là route /<section>/<slug>/<int:article_id>
    # article_id ở đây là số từ URL gốc, không phải ID trong database
    # Nên cần tìm bằng path thay vì article_id
    if url_path or (section and slug):
        # Lấy path từ request (không có domain)
        
        # Debug logging
        print(f"🔍 Looking for article with path: {path_only}")
        
        # Tìm article bằng cách match path với published_url
        # published_url: https://www.sermitsiaq.ag/samfund/article/123
        # path: /samfund/article/123
        # Cần match path với path trong published_url
        
        # Query tất cả articles có published_url HOẶC published_url_en
        # (Articles tiếng Anh có thể chỉ có published_url_en)
        from sqlalchemy import or_, and_
        all_articles = Article.query.filter(
            or_(
                and_(Article.published_url.isnot(None), Article.published_url != ''),
                and_(Article.published_url_en.isnot(None), Article.published_url_en != '')
            )
        ).all()
        
        print(f"   Found {len(all_articles)} articles with published_url or published_url_en")
        
        # Tìm article có path match
        # Logic: 
        # 1. Ưu tiên tìm article có language phù hợp với session language (nếu có)
        # 2. Nếu không có session language, ưu tiên article không có canonical_id (article gốc DA)
        # 3. Nếu path match với published_url_en → đó là article EN
        # 4. Nếu path match với published_url → có thể là DA hoặc EN (cần check language)
        
        # Get session language để ưu tiên
        session_lang = session.get('language')
        
        # First pass: Tìm tất cả articles match với path
        matched_articles = []
        for art in all_articles:
            # Check published_url_en (EN) - nếu match thì đó là article EN
            if art.published_url_en:
                art_en_parsed = urlparse(art.published_url_en)
                art_en_path = art_en_parsed.path
                if art_en_path == path_only:
                    matched_articles.append(art)
                    continue
            
            # Check published_url - có thể là DA hoặc EN (EN articles cũng có published_url = DA URL)
            if art.published_url:
                art_parsed = urlparse(art.published_url)
                art_path = art_parsed.path
                if art_path == path_only:
                    matched_articles.append(art)
        
        # Second pass: Chọn article phù hợp nhất
        if matched_articles:
            # Ưu tiên 1: Article có language phù hợp với session language
            if session_lang:
                for art in matched_articles:
                    if art.language == session_lang:
                        article = art
                        print(f"   ✅ Found article by session language ({session_lang}): Article #{article.id} (lang: {article.language})")
                        break
            
            # Ưu tiên 2: Nếu chưa tìm thấy, ưu tiên article không có canonical_id (article gốc DA)
            if not article:
                for art in matched_articles:
                    if not art.canonical_id and art.language == 'da':
                        article = art
                        print(f"   ✅ Found article (canonical DA): Article #{article.id} (lang: {article.language})")
                        break
            
            # Ưu tiên 3: Nếu vẫn chưa tìm thấy, lấy article đầu tiên match
            if not article:
                article = matched_articles[0]
                print(f"   ✅ Found article (first match): Article #{article.id} (lang: {article.language})")
        
        if not article:
            print(f"   ❌ No article found for path '{path_only}'")
            # Debug: Show first few published_urls for reference
            print(f"   Sample published_urls:")
            for art in all_articles[:5]:
                if art.published_url:
                    art_parsed = urlparse(art.published_url)
                    print(f"      - {art_parsed.path}")
                if art.published_url_en:
                    art_en_parsed = urlparse(art.published_url_en)
                    print(f"      - {art_en_parsed.path} (EN)")
    
    # Nếu không tìm thấy article chính xác → 404 (không có fallback)
    if not article:
        from flask import abort
        abort(404)
    
    # ⚠️ QUAN TRỌNG: Update current_language dựa trên language của article đã tìm được
    # NHƯNG: Chỉ auto-detect nếu session chưa có language được set (user chưa chọn ngôn ngữ)
    # Nếu user đã chọn ngôn ngữ (có session['language']), giữ nguyên session language
    # Điều này cho phép user đổi ngôn ngữ bằng icon mà không bị override bởi URL
    
    # Check xem user đã chọn ngôn ngữ chưa (có session language)
    user_selected_language = session.get('language')
    
    if not user_selected_language:
        # User chưa chọn ngôn ngữ → auto-detect từ URL
        if article.language != current_language:
            print(f"   🔄 Auto-detecting language from URL: {current_language} → {article.language}")
            current_language = article.language
            # Update session để UI hiển thị đúng ngôn ngữ
            if article.language == 'da':
                # DA là default, remove from session
                session.pop('language', None)
            else:
                session['language'] = article.language
    else:
        # User đã chọn ngôn ngữ → dùng session language, không override
        print(f"   ℹ️  User has selected language: {user_selected_language}, keeping it (not overriding from URL)")
        current_language = user_selected_language
    
    # Format published date
    published_date_str = None
    if article.published_date:
        from flask_babel import format_date
        published_date_str = format_date(article.published_date, format='long')
    
    # Get related articles (cùng section, cùng language với article hiện tại, exclude current article)
    # ⚠️ Bỏ is_home=False vì articles có thể có is_home=True nhưng vẫn thuộc section này
    # Dùng article.language thay vì current_language để đảm bảo lấy articles cùng language với article hiện tại
    related_articles = Article.query.filter_by(
        section=article.section,
        language=article.language,  # Dùng language của article hiện tại, không dùng current_language
        is_temp=False
    ).filter(
        Article.id != article.id
    ).order_by(Article.published_date.desc().nullslast()).limit(20).all()  # Lấy nhiều hơn để filter duplicate
    
    # ⚠️ Loại bỏ duplicate articles theo published_url và k5a_url
    # Nếu có nhiều articles cùng published_url hoặc k5a_url, chỉ giữ lại article đầu tiên (mới nhất theo published_date)
    seen_published_urls = set()  # Track published_url để tránh duplicate
    seen_k5a_urls = set()  # Track k5a_url để tránh duplicate (cùng article ID từ trang gốc)
    unique_related_articles = []
    
    for art in related_articles:
        if not art.published_url:
            # Articles không có URL (sliders, containers) → skip
            continue
        
        # Check duplicate theo k5a_url trước (ưu tiên vì unique hơn)
        if art.k5a_url and art.k5a_url in seen_k5a_urls:
            # Đã có article với k5a_url này → skip
            continue
        
        # Check duplicate theo published_url
        if art.published_url in seen_published_urls:
            # Đã có article với published_url này → skip
            continue
        
        # Article này chưa duplicate → thêm vào
        if art.k5a_url:
            seen_k5a_urls.add(art.k5a_url)
        seen_published_urls.add(art.published_url)
        unique_related_articles.append(art)
    
    # Sắp xếp lại theo published_date desc và giới hạn 5 articles
    unique_related_articles.sort(key=lambda x: (x.published_date or datetime.min, x.created_at or datetime.min), reverse=True)
    related_articles = unique_related_articles[:5]
    
    # Get job slider data từ home page (section='home', is_home=True)
    job_slider_data = None
    # Query tất cả job sliders từ home page và filter trong Python
    all_home_sliders = Article.query.filter_by(
        section='home',
        language=current_language,
        is_temp=False,
        is_home=True,
        layout_type='job_slider'
    ).all()
    
    # Tìm job slider (có thể có nhiều, lấy cái đầu tiên)
    job_articles = None
    for slider in all_home_sliders:
        if slider.layout_data and slider.layout_data.get('source_class') in ['source_job-dk', 'source_feed_random_kl_jobs', 'source_job']:
            job_articles = slider
            break
    
    if job_articles and job_articles.layout_data:
        layout_data = job_articles.layout_data
        if layout_data.get('slider_articles'):
            # Lấy 10 articles đầu tiên
            slider_articles = layout_data.get('slider_articles', [])[:10]
            
            # Update URLs từ published_url sang Flask app URL
            from database import Article as ArticleModel
            updated_slider_articles = []
            for item in slider_articles:
                updated_item = item.copy()
                # Tìm Article bằng published_url hoặc id
                if item.get('id'):
                    try:
                        article_obj = ArticleModel.query.get(item['id'])
                        if article_obj:
                            article_dict = article_obj.to_dict()
                            updated_item['url'] = article_dict.get('url', item.get('url', '#'))
                    except:
                        updated_item['url'] = item.get('url', '#')
                else:
                    published_url = item.get('url') or item.get('published_url')
                    if published_url:
                        try:
                            article_obj = ArticleModel.query.filter_by(published_url=published_url).first()
                            if article_obj:
                                article_dict = article_obj.to_dict()
                                updated_item['url'] = article_dict.get('url', published_url)
                            else:
                                updated_item['url'] = published_url
                        except:
                            updated_item['url'] = published_url
                updated_slider_articles.append(updated_item)
            
            job_slider_data = {
                'slider_title': layout_data.get('slider_title', 'JOB'),
                'slider_articles': updated_slider_articles,
                'slider_id': layout_data.get('slider_id', 'job-slider-detail'),
                'source_class': layout_data.get('source_class', 'source_job-dk'),
                'items_per_view': layout_data.get('items_per_view', 4),
                'has_nav': layout_data.get('has_nav', True),
                'header_link': layout_data.get('header_link'),
                'extra_classes': layout_data.get('extra_classes', []),
                'header_classes': layout_data.get('header_classes', [])
            }
    
    # Get podcasti slider data (từ home page hoặc section)
    podcasti_slider_data = None
    # Tìm podcasti slider từ home page trước
    # Query tất cả sliders và filter trong Python (vì JSON field query phức tạp)
    all_sliders = Article.query.filter_by(
        section='home',
        language=current_language,
        is_temp=False,
        is_home=True,
        layout_type='slider'
    ).all()
    
    # Filter trong Python để tìm podcasti slider
    podcasti_articles = None
    for slider in all_sliders:
        if slider.layout_data and slider.layout_data.get('source_class') in ['source_podcasti_dk', 'source_podcasti']:
            podcasti_articles = slider
            break
    
    # Nếu không có trong home, tìm trong section podcasti
    # ⚠️ Bỏ is_home=False vì articles có thể có is_home=True nhưng vẫn thuộc section này
    if not podcasti_articles:
        podcasti_articles = Article.query.filter_by(
            section='podcasti',
            language=current_language,
            is_temp=False,
            layout_type='slider'
        ).first()
    
    if podcasti_articles and podcasti_articles.layout_data:
        layout_data = podcasti_articles.layout_data
        if layout_data.get('slider_articles'):
            podcasti_slider_data = {
                'slider_title': layout_data.get('slider_title', 'PODCASTI'),
                'slider_articles': layout_data.get('slider_articles', [])[:10],
                'slider_id': layout_data.get('slider_id', 'article_list_podcasti'),
                'source_class': layout_data.get('source_class', 'source_podcasti_dk'),
                'items_per_view': layout_data.get('items_per_view', 4),
                'has_nav': layout_data.get('has_nav', True),
                'extra_classes': layout_data.get('extra_classes', ['border-side-bottom', 'mobile_border-side-bottom', 'border_width_4', 'border_width_mobile_4']),
                'header_classes': layout_data.get('header_classes', ['t24', 'tm25', 'color_mobile_no_bg_color', 'primary', 'color_mobile_primary', 'align-left', 'mobile_text_align_align-left', 'font-IBMPlexSans'])
            }
    
    # Get article detail content blocks - filter theo language hiện tại
    article_detail = None
    if article.published_url:
        from services.article_detail_parser import ArticleDetailParser
        # Lấy article_detail theo language hiện tại (tự động chuyển đổi URL nếu cần)
        article_detail = ArticleDetailParser.get_article_detail_by_article(article, language=current_language)
        
        # Nếu article_detail có published_url khác với article.published_url, 
        # tìm article tương ứng và cập nhật title
        if article_detail and article_detail.published_url != article.published_url:
            # Tìm article với published_url của article_detail
            article_by_url = Article.query.filter_by(published_url=article_detail.published_url).first()
            if article_by_url and article_by_url.language == current_language:
                # Cập nhật article title từ article tương ứng
                article.title = article_by_url.title
                # Cũng cập nhật excerpt nếu cần
                if article_by_url.excerpt:
                    article.excerpt = article_by_url.excerpt
    
    # Get 5 articles đầu tiên từ section "SAMFUND" để hiển thị dưới Job slider
    # ⚠️ Bỏ is_home=False vì articles có thể có is_home=True nhưng vẫn thuộc section này
    samfund_articles = Article.query.filter_by(
        section='samfund',
        language=current_language,
        is_temp=False
    ).filter(
        Article.id != article.id  # Exclude current article
    ).order_by(Article.published_date.desc().nullslast()).limit(10).all()  # Lấy nhiều hơn để filter duplicate
    
    # Loại bỏ duplicate articles (cùng k5a_url hoặc published_url)
    seen_k5a_urls = set()
    seen_published_urls = set()
    unique_samfund_articles = []
    for art in samfund_articles:
        if not art.published_url:
            # Articles không có URL → skip
            continue
        
        # Check duplicate theo k5a_url trước (ưu tiên vì unique hơn)
        if art.k5a_url and art.k5a_url in seen_k5a_urls:
            continue
        
        # Check duplicate theo published_url
        if art.published_url in seen_published_urls:
            continue
        
        # Article này chưa duplicate → thêm vào
        if art.k5a_url:
            seen_k5a_urls.add(art.k5a_url)
        seen_published_urls.add(art.published_url)
        unique_samfund_articles.append(art)
        
        if len(unique_samfund_articles) >= 5:
            break
    
    # Convert to dict và update URLs
    samfund_articles_list = []
    for idx, art in enumerate(unique_samfund_articles):
        art_dict = art.to_dict()
        # Set grid_size theo pattern 2-3-2-3... (row đầu 2 articles = 6+6, row sau 3 articles = 4+4+4)
        if idx < 2:
            art_dict['grid_size'] = 6  # Row 1: 2 articles
        else:
            art_dict['grid_size'] = 4  # Row 2: 3 articles
        samfund_articles_list.append(art_dict)
    
    # Get 10 articles từ section "PODCASTI" để hiển thị slider dưới SAMFUND articles
    # ⚠️ Bỏ is_home=False vì articles có thể có is_home=True nhưng vẫn thuộc section này
    podcasti_articles = Article.query.filter_by(
        section='podcasti',
        language=current_language,
        is_temp=False
    ).filter(
        Article.id != article.id  # Exclude current article
    ).order_by(Article.published_date.desc().nullslast()).limit(15).all()  # Lấy nhiều hơn để filter duplicate
    
    # Loại bỏ duplicate articles (cùng k5a_url hoặc published_url)
    seen_k5a_urls = set()
    seen_published_urls = set()
    unique_podcasti_articles = []
    for art in podcasti_articles:
        if not art.published_url:
            # Articles không có URL → skip
            continue
        
        # Check duplicate theo k5a_url trước (ưu tiên vì unique hơn)
        if art.k5a_url and art.k5a_url in seen_k5a_urls:
            continue
        
        # Check duplicate theo published_url
        if art.published_url in seen_published_urls:
            continue
        
        # Article này chưa duplicate → thêm vào
        if art.k5a_url:
            seen_k5a_urls.add(art.k5a_url)
        seen_published_urls.add(art.published_url)
        unique_podcasti_articles.append(art)
        
        if len(unique_podcasti_articles) >= 10:
            break
    
    # Convert to dict và update URLs
    podcasti_articles_list = []
    for art in unique_podcasti_articles:
        art_dict = art.to_dict()
        podcasti_articles_list.append(art_dict)
    
    # Tạo slider data cho PODCASTI slider (giống NYHEDER slider)
    podcasti_slider_detail_data = None
    if podcasti_articles_list:
        podcasti_slider_detail_data = {
            'slider_title': 'PODCASTI',
            'slider_articles': podcasti_articles_list,
            'slider_id': 'article_list_podcasti_detail',
            'source_class': 'source_nyheder',  # Giống NYHEDER slider
            'items_per_view': 4,
            'has_nav': True,
            'row_guid': 'podcasti-slider-detail'
        }
    
    # Generate SEO meta tags từ database
    # Dùng article.language thay vì current_language để đảm bảo SEO data đúng với article được hiển thị
    from utils_seo import get_seo_meta, get_structured_data
    seo_meta = get_seo_meta(
        article=article,
        page_type='article',
        language=article.language,  # Dùng language của article, không dùng current_language
        section=article.section
    )
    structured_data = get_structured_data(
        article=article,
        page_type='article',
        language=article.language  # Dùng language của article, không dùng current_language
    )
    
    return render_template('article_detail.html',
        article=article,
        published_date_str=published_date_str,
        related_articles=related_articles,
        job_slider_data=job_slider_data,
        podcasti_slider_data=podcasti_slider_data,
        article_detail=article_detail,
        samfund_articles=samfund_articles_list,
        podcasti_slider_detail_data=podcasti_slider_detail_data,
        show_top_ad=False,
        show_bottom_ad=False,
        seo_meta=seo_meta,
        structured_data=structured_data
    )


@article_view_bp.route('/article/test')
def article_detail_test():
    """
    Test route với fake data để test UI
    """
    from datetime import datetime
    from flask_babel import format_date
    
    # Get current language
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'en'
    except:
        current_language = session.get('language', 'en')
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    # Mock article object
    class MockArticle:
        def __init__(self):
            self.id = 9999
            self.title = "Trump vil lægge told på Danmark på grund af Grønland"
            self.excerpt = "Told mod Danmark og andre lande vil gælde, indtil USA og Danmark har en aftale om Grønland, skriver Trump."
            self.content = """
            <p><span data-lab-font_weight="font-weight-bold" class="font-weight-bold m-font-weight-bold">Der vil blive lagt</span> ti procent told på varer fra Danmark og flere andre europæiske lande fra 1. februar på grund af situationen omkring Grønland.</p>
            <p>Det skriver USA's præsident, Donald Trump, på sit sociale medie, Truth Social, lørdag.</p>
            <p>De øvrige lande er Norge, Sverige, Frankrig, Tyskland, Storbritannien, Holland og Finland.</p>
            <p>Fra 1. juni 2026 vil tolden blive øget til 25 procent, skriver Trump.</p>
            <p>Toldsatsen vil være gældende, indtil der er indgået en aftale om amerikansk "anskaffelse" af Grønland, skriver Trump.</p>
            <p>- USA har forsøgt at gennemføre denne handel i over 150 år. Mange præsidenter har forsøgt - og med god grund - men Danmark har altid nægtet det, skriver præsidenten.</p>
            <p>Trump gentager påstande om, at Grønland er truet af Kina og Rusland, som "vil have" øen.</p>
            <p>- Verdensfreden er på spil, skriver den amerikanske præsident.</p>
            """
            self.section = "samfund"
            self.language = "en"
            self.element_guid = "2095b6bd-d14e-4712-aa41-c1e7d6a17169"
            self.published_date = datetime.now()
            self.published_url = "https://www.sermitsiaq.ag/samfund/trump-vil-laegge-told-pa-danmark-pa-grund-af-gronland/2331902"
            self.image_data = {
                'element_guid': 'c85f0d49-dda2-47e6-a3a1-81a4d65ffa50',
                'desktop_webp': 'https://image.sermitsiaq.ag/2331906.webp?imageId=2331906&width=2116&height=1208&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2331906.webp?imageId=2331906&width=2116&height=1208&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2331906.webp?imageId=2331906&width=960&height=548&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2331906.webp?imageId=2331906&width=960&height=548&format=jpg',
                'desktop_width': 1058,
                'desktop_height': 604,
                'mobile_width': 480,
                'mobile_height': 274,
                'fallback': 'https://image.sermitsiaq.ag/2331906.webp?imageId=2331906&width=960&height=548&format=jpg',
                'caption': '',
                'author': 'Brendan Smialowski/AFP/Ritzau Scanpix',
                'alt': ''
            }
            self.layout_data = {
                'author': 'Ritzau',
                'tags': ['grønland', 'donald trump', 'danmark', 'usa', 'told', 'samfund']
            }
        
        def isoformat(self):
            return self.published_date.isoformat()
    
    article = MockArticle()
    published_date_str = format_date(article.published_date, format='long')
    
    # Mock related articles
    class MockRelatedArticle:
        def __init__(self, title, section, id_num):
            self.id = id_num
            self.title = title
            self.section = section
            self.element_guid = f"mock-{id_num}"
            self.is_paywall = id_num % 2 == 0
            self.site_alias = "sermitsiaq"
            self.instance = f"mock{id_num}"
            self.published_date = datetime.now()
            self.published_url = f"https://www.sermitsiaq.ag/{section}/article-{id_num}"
            self.k5a_url = f"https://www.sermitsiaq.ag/a/{id_num}"
            self.image_data = {
                'element_guid': f"img-{id_num}",
                'desktop_webp': f'https://image.sermitsiaq.ag/{id_num}.webp?format=webp',
                'desktop_jpeg': f'https://image.sermitsiaq.ag/{id_num}.jpg?format=jpg',
                'mobile_webp': f'https://image.sermitsiaq.ag/{id_num}.webp?format=webp',
                'mobile_jpeg': f'https://image.sermitsiaq.ag/{id_num}.jpg?format=jpg',
                'desktop_width': 353,
                'desktop_height': 230,
                'mobile_width': 480,
                'mobile_height': 312,
                'fallback': f'https://image.sermitsiaq.ag/{id_num}.jpg',
                'alt': title
            }
        
        def to_dict(self):
            return {
                'id': self.id,
                'title': self.title,
                'section': self.section,
                'element_guid': self.element_guid,
                'is_paywall': self.is_paywall,
                'site_alias': self.site_alias,
                'instance': self.instance,
                'published_date': self.published_date,
                'published_url': self.published_url,
                'k5a_url': self.k5a_url,
                'image_data': self.image_data
            }
        
        def isoformat(self):
            return self.published_date.isoformat()
    
    related_articles = [
        MockRelatedArticle("Mand sigtes for forsøg på manddrab i Aasiaat", "samfund", 1001),
        MockRelatedArticle("Har vi glemt det største problem?", "samfund", 1002),
        MockRelatedArticle("EU-ambassadører er indkaldt til hastemøde om Grønland", "samfund", 1003),
        MockRelatedArticle("Ud i mørket med gule jakker, bolsjer og kondomer", "samfund", 1004),
        MockRelatedArticle("Ny podcast: Formanden fylder 67 – men giver ikke slip", "samfund", 1005)
    ]
    
    # Mock job slider data
    job_slider_data = {
        'slider_title': 'JOB',
        'slider_articles': [
            {
                'title': 'Medarbejder søges som Flyver til institution Puiaq',
                'url': 'https://www.sjob.gl/job-dk/medarbejder-soges-som-flyver-til-institution-puiaq/2319547',
                'section': 'job dk',
                'is_paywall': False,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2065376.jpg?imageId=2065376&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': '2 medhjælpere søges til Sikkersoq',
                'url': 'https://www.sjob.gl/job-dk/2-medhjaelpere-soges-til-sikkersoq/2326433',
                'section': 'job dk',
                'is_paywall': False,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2065376.jpg?imageId=2065376&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Departementet for Børn, Unge, Familier og Indenrigsanliggender søger en Juridisk Fuldmægtig',
                'url': 'https://www.sjob.gl/job-dk/departementet-for-born-unge-familier-og-indenrigsanliggender-soger-en-juridisk-fuldmaegtig/2327006',
                'section': 'job dk',
                'is_paywall': False,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2200481.jpg?imageId=2200481&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Tilsynsførende pædagogisk konsulent til Dagtilbudsafdelingen',
                'url': 'https://www.sjob.gl/job-dk/tilsynsforende-paedagogisk-konsulent-til-dagtilbudsafdelingen/2326014',
                'section': 'job dk',
                'is_paywall': False,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2065376.jpg?imageId=2065376&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'GUX Nuuk søger en psykoterapeut',
                'url': 'https://www.sjob.gl/job-dk/gux-nuuk-soger-en-psykoterapeut/2328017',
                'section': 'job dk',
                'is_paywall': False,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2136657.jpg?imageId=2136657&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            }
        ],
        'slider_id': 'article_list_test_job',
        'source_class': 'source_feed_random_dk_jobs',
        'items_per_view': 4,
        'has_nav': True,
        'header_link': {
            'url': 'https://www.sjob.gl/',
            'text': 'Se alle jobs'
        },
        'extra_classes': ['bg-custom-2', 'color_mobile_bg-custom-2', 'hasContentPadding', 'mobile-hasContentPadding'],
        'header_classes': ['t25', 'octonary', 'color_mobile_octonary', 'font-IBMPlexSans']
    }
    
    # Mock podcasti slider data
    podcasti_slider_data = {
        'slider_title': 'PODCASTI',
        'slider_articles': [
            {
                'title': 'Nuuk Lufthavn giver guld til taxaerne',
                'url': 'https://www.sermitsiaq.ag/erhverv/nuuk-lufthavn-giver-guld-til-taxaerne/2283978',
                'section': 'erhverv',
                'is_paywall': False,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2283995.webp?imageId=2283995&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Naja Lyberth: Der er stadig mange kampe at kæmpe',
                'url': 'https://www.sermitsiaq.ag/samfund/naja-lyberth-der-er-stadig-mange-kampe-at-kaempe/2279487',
                'section': 'samfund',
                'is_paywall': True,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2279490.webp?imageId=2279490&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Bentiaraq Ottosen: Vi kan ikke undvære udenlandsk arbejdskraft',
                'url': 'https://www.sermitsiaq.ag/podcasti/bentiaraq-ottosen-vi-kan-ikke-undvaere-udenlandsk-arbejdskraft/2259171',
                'section': 'podcasti',
                'is_paywall': True,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2259182.webp?imageId=2259182&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Kaos i lufthavnen – direktøren forklarer sig',
                'url': 'https://www.sermitsiaq.ag/podcasti/kaos-i-lufthavnen-direktoren-forklarer-sig/2258058',
                'section': 'podcasti',
                'is_paywall': True,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2258165.webp?imageId=2258165&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Stålkvinden er tilbage – men udenfor maskinrummet',
                'url': 'https://www.sermitsiaq.ag/podcasti/stalkvinden-er-tilbage-men-udenfor-maskinrummet/2254259',
                'section': 'podcasti',
                'is_paywall': True,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2254269.webp?imageId=2254269&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            },
            {
                'title': 'Voksede op i svigt og misbrug – i dag er han naalakkersuisoq',
                'url': 'https://www.sermitsiaq.ag/samfund/voksede-op-i-svigt-og-misbrug-i-dag-er-han-naalakkersuisoq/2243782',
                'section': 'samfund',
                'is_paywall': True,
                'image': {
                    'src': 'https://image.sermitsiaq.ag/2243793.webp?imageId=2243793&width=530&height=344',
                    'width': 265,
                    'height': 172,
                    'alt': ''
                }
            }
        ],
        'slider_id': 'article_list_test_podcasti',
        'source_class': 'source_podcasti_dk',
        'items_per_view': 4,
        'has_nav': True,
        'extra_classes': ['border-side-bottom', 'mobile_border-side-bottom', 'border_width_4', 'border_width_mobile_4'],
        'header_classes': ['t24', 'tm25', 'color_mobile_no_bg_color', 'primary', 'color_mobile_primary', 'align-left', 'mobile_text_align_align-left', 'font-IBMPlexSans']
    }
    
    # Get article detail content blocks - filter theo language hiện tại
    article_detail = None
    if article.published_url:
        from services.article_detail_parser import ArticleDetailParser
        # Lấy article_detail theo language hiện tại (tự động chuyển đổi URL nếu cần)
        article_detail = ArticleDetailParser.get_article_detail_by_article(article, language=current_language)
    
    return render_template('article_detail.html',
        article=article,
        published_date_str=published_date_str,
        related_articles=related_articles,
        job_slider_data=job_slider_data,
        podcasti_slider_data=podcasti_slider_data,
        article_detail=article_detail,
        show_top_ad=False,
        show_bottom_ad=False
    )


@article_view_bp.route('/article/detail/test')
def article_detail_test_structured():
    """
    Test route để xem structured article detail content
    Usage: /article/detail/test?url=<published_url>
    """
    from services.article_detail_parser import ArticleDetailParser
    from datetime import datetime
    from app import app
    
    url = request.args.get('url')
    if not url:
        return "Please provide ?url parameter", 400
    
    # Get language from query parameter, default to 'da'
    lang = request.args.get('lang', 'da')
    
    with app.app_context():
        article_detail = ArticleDetailParser.get_article_detail(url, language=lang)
        
        if not article_detail:
            return f"Article detail not found for URL: {url}<br><br>Run: python scripts/crawl_article_detail.py '{url}'", 404
        
        # Get article
        article = Article.query.filter_by(published_url=url).first()
        
        return render_template('article_detail.html',
            article=article or type('MockArticle', (), {
                'id': 0,
                'title': 'Test Article',
                'excerpt': 'Test excerpt',
                'section': 'kultur',
                'published_url': url,
                'published_date': datetime.now(),
                'image_data': None,
                'layout_data': {}
            })(),
            published_date_str='Test date',
            related_articles=[],
            job_slider_data=None,
            podcasti_slider_data=None,
            article_detail=article_detail
        )


@article_view_bp.route('/contact')
@article_view_bp.route('/kontakt')
def contact():
    """
    Contact page - hiển thị thông tin liên hệ
    Hỗ trợ cả /contact (tiếng Anh) và /kontakt (tiếng Đan Mạch)
    """
    # Get current language from session or default
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'en'
    except:
        current_language = session.get('language', 'en')
    
    # Check URL parameter for language override
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    return render_template('contact.html', current_language=current_language)


@article_view_bp.route('/advertise')
@article_view_bp.route('/annoncer')
def advertise():
    """
    Advertise page - hiển thị thông tin về quảng cáo
    Hỗ trợ cả /advertise (tiếng Anh) và /annoncer (tiếng Đan Mạch)
    """
    # Get current language from session or default
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'en'
    except:
        current_language = session.get('language', 'en')
    
    # Check URL parameter for language override
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    return render_template('advertise.html', current_language=current_language)


@article_view_bp.route('/cse')
@article_view_bp.route('/search')
def search():
    """
    Search page - tìm kiếm bài viết theo query
    Hỗ trợ cả /cse (giống trang gốc) và /search
    
    Query parameters:
    - q: search query (required)
    - query: alternative parameter name for 'q'
    - page: pagination (default: 1)
    """
    from flask_babel import get_locale
    
    # Get current language
    current_language = 'da'  # Default
    try:
        locale = get_locale()
        if locale and str(locale) in ['da', 'kl', 'en']:
            current_language = str(locale)
    except:
        pass
    
    # Check session
    session_lang = session.get('language')
    if session_lang and session_lang in ['da', 'kl', 'en']:
        current_language = session_lang
    
    # Check URL parameter for language override
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    # Get search query from 'q' or 'query' parameter
    search_query = request.args.get('query', request.args.get('q', '')).strip()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of results per page
    
    print(f"\n{'='*60}")
    print(f"🔍 Search Page")
    print(f"{'='*60}")
    print(f"   Language: {current_language}")
    print(f"   Query: {search_query}")
    print(f"   Page: {page}")
    
    articles = []
    total_results = 0
    
    if search_query:
        try:
            # Build search query - PostgreSQL full-text search
            # Search in: title, excerpt, content, tags
            
            # Search pattern (case-insensitive)
            search_pattern = f"%{search_query}%"
            
            # Use DISTINCT ON to get only the latest article per image_header_id (image_data->>'element_guid')
            # This removes duplicates when same article has multiple versions
            from sqlalchemy import distinct, select, literal_column
            from sqlalchemy.sql import text
            
            # Import ArticleDetail for author search
            from database import ArticleDetail
            
            # Subquery to get the latest article ID for each unique image element_guid
            # LEFT JOIN với ArticleDetail để search trong author info
            subquery = db.session.query(
                func.max(Article.id).label('max_id')
            ).outerjoin(
                ArticleDetail,
                db.and_(
                    Article.published_url == ArticleDetail.published_url,
                    Article.language == ArticleDetail.language
                )
            ).filter(
                Article.language == current_language,
                Article.is_temp == False,
                or_(
                    Article.title.ilike(search_pattern),
                    Article.excerpt.ilike(search_pattern),
                    Article.content.ilike(search_pattern),
                    func.lower(func.cast(Article.tags, db.String)).contains(search_query.lower()),
                    # Search trong author info (content_blocks JSON)
                    func.lower(func.cast(ArticleDetail.content_blocks, db.String)).contains(search_query.lower())
                )
            ).group_by(
                # Group by article ID in URL (extracted from published_url)
                # Example: .../debat-om-usa/2338049 -> 2338049
                # This handles live-blog articles that get updated with different images/titles
                func.regexp_replace(
                    Article.published_url,
                    '.*/([0-9]+)$',  # Match digits at end of URL
                    '\\1'  # Extract just the number
                )
            ).subquery()
            
            # Main query - get articles with IDs from subquery
            query = Article.query.filter(
                Article.id.in_(
                    db.session.query(subquery.c.max_id)
                )
            )
            
            # Count total unique results
            total_results = query.count()
            
            print(f"   📊 Found {total_results} unique results (after deduplication)")
            
            # Apply pagination and ordering
            articles_query = query.order_by(
                Article.created_at.desc()  # Order by created_at DESC to show newest first
            ).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            # Convert to dict for template
            articles = [article.to_dict() for article in articles_query.items]
            
            print(f"   📄 Showing {len(articles)} results on page {page}")
            
        except Exception as e:
            print(f"   ⚠️  Error searching articles: {e}")
            import traceback
            traceback.print_exc()
    
    # Calculate pagination info
    total_pages = (total_results + per_page - 1) // per_page if total_results > 0 else 0
    has_prev = page > 1
    has_next = page < total_pages
    
    # Check if this is an AJAX request
    is_ajax = request.args.get('ajax') == '1'
    
    if is_ajax:
        # Return JSON response for AJAX load more
        return jsonify({
            'articles': articles,
            'total_results': total_results,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next
        })
    
    # Regular request - render template
    # Get the pagination object for template (using same deduplication logic)
    if search_query:
        search_pattern = f"%{search_query}%"
        
        # Import ArticleDetail for author search
        from database import ArticleDetail
        
        # Subquery to get the latest article ID for each unique image element_guid
        # LEFT JOIN với ArticleDetail để search trong author info
        subquery = db.session.query(
            func.max(Article.id).label('max_id')
        ).outerjoin(
            ArticleDetail,
            db.and_(
                Article.published_url == ArticleDetail.published_url,
                Article.language == ArticleDetail.language
            )
        ).filter(
            Article.language == current_language,
            Article.is_temp == False,
            or_(
                Article.title.ilike(search_pattern),
                Article.excerpt.ilike(search_pattern),
                Article.content.ilike(search_pattern),
                func.lower(func.cast(Article.tags, db.String)).contains(search_query.lower()),
                # Search trong author info (content_blocks JSON)
                func.lower(func.cast(ArticleDetail.content_blocks, db.String)).contains(search_query.lower())
            )
        ).group_by(
            # Group by article ID in URL (same as main query)
            func.regexp_replace(
                Article.published_url,
                '.*/([0-9]+)$',
                '\\1'
            )
        ).subquery()
        
        query = Article.query.filter(
            Article.id.in_(
                db.session.query(subquery.c.max_id)
            )
        )
    else:
        query = Article.query.filter(
            Article.language == current_language,
            Article.is_temp == False
        )
    
    # Get pagination object (order by created_at DESC to show newest versions first)
    pagination = query.order_by(
        Article.created_at.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return render_template('search_results.html',
        search_query=search_query,
        articles=articles,
        total_results=total_results,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        current_language=current_language,
        pagination=pagination  # Pass pagination object for template
    )