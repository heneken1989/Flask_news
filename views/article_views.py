from flask import Blueprint, render_template, request, make_response, session
from utils import apply_grid_size_pattern, prepare_home_layouts, get_home_articles_by_language
from database import Article, Category

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
            
            # Xử lý slider containers
            if layout_type in ['slider', 'job_slider']:
                slider_data = {
                    'id': None,
                    'title': layout_item.get('slider_title', ''),
                    'layout_type': layout_type,
                    'display_order': display_order,
                    'layout_data': {
                        'slider_title': layout_item.get('slider_title', ''),
                        'slider_articles': []
                    },
                    'published_url': '',
                    'is_home': True,
                    'section': 'home'
                }
                
                # Link các articles trong slider
                slider_articles = layout_item.get('slider_articles', [])
                for slider_article in slider_articles:
                    slider_url = slider_article.get('published_url', '')
                    if slider_url and slider_url in articles_map:
                        for article in articles_map[slider_url]:
                            if article.language == current_language:
                                article_dict = article.to_dict()
                                slider_data['layout_data']['slider_articles'].append(article_dict)
                                break
                
                articles.append(slider_data)
                continue
            
            # Xử lý articles thông thường
            if not published_url:
                continue
            
            # Tìm article trong DB
            if published_url in articles_map:
                matched_article = None
                
                # Ưu tiên article đã có section='home'
                for article in articles_map[published_url]:
                    if article.language == current_language and article.section == 'home':
                        matched_article = article
                        break
                
                # Nếu không có, lấy article đầu tiên cùng language
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
                        list_items = layout_item.get('list_items', []) or layout_item.get('layout_data', {}).get('list_items', [])
                        list_title = layout_item.get('list_title', '') or layout_item.get('layout_data', {}).get('list_title', '')
                        if list_items:
                            new_layout_data['list_items'] = list_items
                        if list_title:
                            new_layout_data['list_title'] = list_title
                    
                    # Merge với existing (ưu tiên existing cho list_items và list_title nếu không có trong new)
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
                limit=None
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
    
    # Render template (template expect 'layouts', not 'articles')
    return render_template('home_page.html',
        layouts=layouts,  # Template expect 'layouts'
        section_title='Home Test',
        articles_per_row=2,
        section='home',
        show_top_ad=True,
        show_bottom_ad=False
    )

@article_view_bp.route('/')
def index():
    """
    Home page với nhiều layout types khác nhau
    Layout types: 1_full, 2_articles, 3_articles, 1_special_bg, 1_with_list_left, 1_with_list_right
    """
    from database import db
    
    # Log request info để debug
    user_agent = request.headers.get('User-Agent', 'Unknown')
    print(f"🌐 / (home) request from: {user_agent[:50]}...")
    print(f"   Method: {request.method}")
    print(f"   URL: {request.url}")
    
    # Get current language from session or default
    # Use get_locale() from flask_babel to be consistent with app default
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'en'
    except:
        # Fallback: check session or default to 'en' (matching app.config['BABEL_DEFAULT_LOCALE'])
        current_language = session.get('language', 'en')
    
    # Check URL parameter for language override (highest priority)
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    # Query articles từ database cho trang home, filtered by language
    articles = []
    try:
        # Query articles với language filter
        article_objects = get_home_articles_by_language(
            language=current_language,
            limit=None  # Không giới hạn để hiển thị tất cả
        )
        
        # Filter chỉ lấy articles có layout_type
        article_objects = [a for a in article_objects if a.layout_type]
        
        # Log số lượng articles để debug
        print(f"📊 Found {len(article_objects)} articles for home page (language: {current_language})")
        
        # Log display_order của 10 articles đầu để debug
        if article_objects:
            print(f"📐 Display order của 10 articles đầu:")
            for idx, article in enumerate(article_objects[:10]):
                print(f"   [{idx}] display_order={article.display_order}, layout_type={article.layout_type}, title={article.title[:50]}")
        
        # Convert to dict - giữ nguyên thứ tự
        articles = [article.to_dict() for article in article_objects]
        
        # Log số lượng articles để debug
        print(f"📊 Found {len(articles)} articles for home page")
        if articles:
            print(f"   First article: display_order={articles[0].get('display_order', 'N/A')}, layout_type={articles[0].get('layout_type', 'N/A')}, title={articles[0].get('title', 'N/A')[:50]}...")
            print(f"   Last article: display_order={articles[-1].get('display_order', 'N/A')}, layout_type={articles[-1].get('layout_type', 'N/A')}, title={articles[-1].get('title', 'N/A')[:50]}...")
        
        # Debug: Kiểm tra sliders
        sliders = [a for a in articles if a.get('layout_type') == 'slider']
        if sliders:
            print(f"🎠 Found {len(sliders)} sliders:")
            for idx, slider in enumerate(sliders):
                layout_data = slider.get('layout_data', {})
                slider_articles = layout_data.get('slider_articles', [])
                slider_title = layout_data.get('slider_title', 'Untitled')
                
                # Debug chi tiết
                print(f"   Slider {idx+1}: '{slider_title}' - {len(slider_articles)} articles")
                print(f"      layout_data type: {type(layout_data)}")
                print(f"      slider_articles type: {type(slider_articles)}")
                if isinstance(slider_articles, list):
                    print(f"      First 3 article titles: {[a.get('title', 'N/A')[:30] for a in slider_articles[:3]]}")
                else:
                    print(f"      ⚠️  slider_articles is not a list! Value: {slider_articles}")
                
                if len(slider_articles) < 4:
                    print(f"      ⚠️  WARNING: Slider has only {len(slider_articles)} articles (expected >= 4)")
        
    except Exception as e:
        print(f"⚠️  Database query failed: {e}")
        articles = []
    
    # Nếu không có articles từ database, dùng mock data với các layout types
    if not articles:
        articles = [
            {
                'element_guid': '1d8fc071-5df6-43e1-8879-f9eab34d3c45',
                'title': 'Pressemøde om amerikansk delegations besøg i Danmark',
                'url': '/samfund/pressemode-om-amerikansk-delegations-besog-i-danmark/2331441',
                'k5a_url': '/a/2331441',
                'section': 'samfund',
                'site_alias': 'sermitsiaq',
                'instance': '2331441',
                'published_date': '2026-01-16T15:25:38+01:00',
                'is_paywall': False,
                'paywall_class': '',
                'layout_type': '1_full',
                'image': {
                    'desktop_webp': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=2116&height=1418&format=webp',
                    'desktop_jpeg': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=2116&height=1418&format=jpg',
                    'mobile_webp': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=960&height=644&format=webp',
                    'mobile_jpeg': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=960&height=644&format=jpg',
                    'fallback': 'https://image.sermitsiaq.ag/2331462.webp?imageId=2331462&width=960&height=644&format=jpg',
                    'desktop_width': '1058',
                    'desktop_height': '709',
                    'mobile_width': '480',
                    'mobile_height': '322',
                    'alt': '',
                    'title': 'Pressemøde om amerikansk delegations besøg i Danmark'
                }
            },
            {
                'element_guid': 'c6e0c689-1c51-4b97-80db-7b39988eca17',
                'title': 'Trumps særlige udsending vil besøge Grønland i marts',
                'url': '/samfund/trumps-saerlige-udsending-vil-besoge-gronland-i-marts/2331321',
                'k5a_url': '/a/2331321',
                'section': 'samfund',
                'site_alias': 'sermitsiaq',
                'instance': '2331321',
                'published_date': '2026-01-16T13:23:06+01:00',
                'is_paywall': False,
                'paywall_class': '',
                'layout_type': '2_articles',
                'image': {
                    'desktop_webp': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=1058&height=688&format=webp',
                    'fallback': 'https://image.sermitsiaq.ag/2331325.webp?imageId=2331325&width=960&height=624&format=jpg',
                    'desktop_width': '529',
                    'desktop_height': '344',
                    'mobile_width': '480',
                    'mobile_height': '312',
                    'alt': '',
                    'title': 'Trumps særlige udsending vil besøge Grønland i marts'
                }
            },
            {
                'element_guid': 'c7ee8684-56fe-41de-91b7-b6ad1a91a888',
                'title': 'Trump sætter igen gang i forretningen',
                'url': '/erhverv/trump-saetter-igen-gang-i-forretningen/2328783',
                'k5a_url': '/a/2328783',
                'section': 'erhverv',
                'site_alias': 'sermitsiaq',
                'instance': '2328783',
                'published_date': '2026-01-16T15:21:54+01:00',
                'is_paywall': True,
                'paywall_class': 'paywall',
                'layout_type': '2_articles',
                'image': {
                    'desktop_webp': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=1058&height=688&format=webp',
                    'fallback': 'https://image.sermitsiaq.ag/2328786.webp?imageId=2328786&width=960&height=624&format=jpg',
                    'desktop_width': '529',
                    'desktop_height': '344',
                    'mobile_width': '480',
                    'mobile_height': '312',
                    'alt': '',
                    'title': 'Trump sætter igen gang i forretningen'
                }
            }
        ]
    
    # Chuẩn bị layouts cho rendering
    layouts = prepare_home_layouts(articles)
    print(f"📐 Prepared {len(layouts)} layouts from {len(articles)} articles")
    
    # Tạo response với headers để tránh cache issues
    response = make_response(render_template('home_page.html',
        layouts=layouts,
        section_title='Home',
        section='home',
        show_top_ad=True,
        show_bottom_ad=False
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
    Display articles by section/category
    Route: /tag/samfund, /tag/erhverv, /tag/kultur, /tag/sport, /tag/podcasti
    Shows 50 newest articles from the specified section
    """
    from database import db
    
    # Validate section
    valid_sections = ['samfund', 'erhverv', 'kultur', 'sport', 'podcasti']
    if section not in valid_sections:
        # Return 404 or redirect to home
        from flask import abort
        abort(404)
    
    # Section name mapping (Danish)
    section_names = {
        'samfund': 'Samfund',
        'erhverv': 'Erhverv',
        'kultur': 'Kultur',
        'sport': 'Sport',
        'podcasti': 'Podcasti'
    }
    
    # Get current language from session or default
    # Use get_locale() from flask_babel to be consistent with app default
    from flask_babel import get_locale
    try:
        current_language = str(get_locale()) if get_locale() else 'en'
    except:
        # Fallback: check session or default to 'en' (matching app.config['BABEL_DEFAULT_LOCALE'])
        current_language = session.get('language', 'en')
    
    # Check URL parameter for language override (highest priority)
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in ['da', 'kl', 'en']:
            current_language = lang
    
    # Query articles từ database theo section và language
    articles = []
    try:
        # Query articles với language filter
        # Đối với DA (Danish) - ngôn ngữ gốc, không cần filter is_temp
        # Đối với EN/KL - chỉ show articles đã hoàn thành translate (is_temp=False)
        # ⚠️ Bỏ is_home=False vì articles có thể có is_home=True nhưng vẫn thuộc section này
        query = Article.query.filter_by(
            section=section,
            language=current_language
        )
        
        # Chỉ filter is_temp=False cho EN và KL (translated articles)
        # DA articles không bao giờ là temp vì chúng là ngôn ngữ gốc
        if current_language in ['en', 'kl']:
            query = query.filter_by(is_temp=False)
        
        articles = query.order_by(Article.published_date.desc().nullslast())\
                       .limit(50).all()
        
        # Loại bỏ duplicate articles (cùng published_url + language)
        # Chỉ giữ lại article đầu tiên (theo published_date desc)
        seen_urls = set()
        unique_articles = []
        for article in articles:
            if article.published_url:
                if article.published_url not in seen_urls:
                    seen_urls.add(article.published_url)
                    unique_articles.append(article)
            else:
                # Articles không có URL (sliders) vẫn giữ lại
                unique_articles.append(article)
        
        articles = unique_articles
        
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
    
    # Section title
    section_title = f'Tag: {section_names.get(section, section)}'
    
    return render_template('front_page.html',
        articles=articles,
        section_title=section_title,
        articles_per_row=2,  # Default, sẽ bị override bởi grid_size pattern
        section=section,
        show_top_ad=True,
        show_bottom_ad=False
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
    from utils import get_article_with_fallback
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
        
        # Query tất cả articles có published_url
        all_articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).all()
        
        print(f"   Found {len(all_articles)} articles with published_url")
        
        # Tìm tất cả articles có path match
        # Check cả published_url (DA) và published_url_en (EN)
        matching_articles = []
        for art in all_articles:
            # Check published_url (DA)
            if art.published_url:
                art_parsed = urlparse(art.published_url)
                art_path = art_parsed.path
                if art_path == path_only:
                    matching_articles.append(art)
                    continue  # Đã match, không cần check published_url_en
            
            # Check published_url_en (EN) nếu chưa match
            if art.published_url_en:
                art_en_parsed = urlparse(art.published_url_en)
                art_en_path = art_en_parsed.path
                if art_en_path == path_only:
                    matching_articles.append(art)
        
        print(f"   Found {len(matching_articles)} articles with matching path")
        
        # Ưu tiên 1: Chọn article với language hiện tại
        if matching_articles:
            for art in matching_articles:
                if art.language == current_language:
                    article = art
                    print(f"   ✅ Found match with language '{current_language}': Article #{article.id}")
                    break
            
            # Ưu tiên 2: Nếu không có, chọn article đầu tiên
            if not article:
                article = matching_articles[0]
                print(f"   ⚠️  No match with language '{current_language}', using first match: Article #{article.id} (lang: {article.language})")
        
        if not article:
            print(f"   ❌ No article found for path: {path_only}")
            # Debug: Show first few published_urls for reference
            print(f"   Sample published_urls:")
            for art in all_articles[:5]:
                if art.published_url:
                    art_parsed = urlparse(art.published_url)
                    print(f"      - {art_parsed.path}")
    
    # Fallback: Nếu không tìm thấy bằng path và có article_id (route /article/<article_id>)
    # Thì mới dùng article_id để tìm (đây là ID thực sự trong database)
    if not article and article_id and not section and not slug:
        # Chỉ dùng article_id nếu không có section/slug (route /article/<article_id>)
        article = get_article_with_fallback(article_id, preferred_language=current_language)
    
    if not article:
        from flask import abort
        abort(404)
    
    # Format published date
    published_date_str = None
    if article.published_date:
        from flask_babel import format_date
        published_date_str = format_date(article.published_date, format='long')
    
    # Get related articles (cùng section, cùng language, exclude current article)
    # ⚠️ Bỏ is_home=False vì articles có thể có is_home=True nhưng vẫn thuộc section này
    related_articles = Article.query.filter_by(
        section=article.section,
        language=current_language,
        is_temp=False
    ).filter(
        Article.id != article.id
    ).order_by(Article.published_date.desc().nullslast()).limit(10).all()  # Lấy nhiều hơn để filter duplicate
    
    # Loại bỏ duplicate articles (cùng published_url)
    seen_urls = set()
    unique_related_articles = []
    for art in related_articles:
        if art.published_url and art.published_url not in seen_urls:
            seen_urls.add(art.published_url)
            unique_related_articles.append(art)
        elif not art.published_url:
            # Articles không có URL vẫn giữ lại
            unique_related_articles.append(art)
        if len(unique_related_articles) >= 5:
            break
    
    related_articles = unique_related_articles
    
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
    
    # Loại bỏ duplicate articles (cùng published_url)
    seen_urls = set()
    unique_samfund_articles = []
    for art in samfund_articles:
        if art.published_url and art.published_url not in seen_urls:
            seen_urls.add(art.published_url)
            unique_samfund_articles.append(art)
        elif not art.published_url:
            # Articles không có URL vẫn giữ lại
            unique_samfund_articles.append(art)
        if len(unique_samfund_articles) >= 5:
            break
    
    # Convert to dict và update URLs
    samfund_articles_list = []
    for art in unique_samfund_articles:
        art_dict = art.to_dict()
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
    
    # Loại bỏ duplicate articles (cùng published_url)
    seen_urls = set()
    unique_podcasti_articles = []
    for art in podcasti_articles:
        if art.published_url and art.published_url not in seen_urls:
            seen_urls.add(art.published_url)
            unique_podcasti_articles.append(art)
        elif not art.published_url:
            # Articles không có URL vẫn giữ lại
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
    
    return render_template('article_detail.html',
        article=article,
        published_date_str=published_date_str,
        related_articles=related_articles,
        job_slider_data=job_slider_data,
        podcasti_slider_data=podcasti_slider_data,
        article_detail=article_detail,
        samfund_articles=samfund_articles_list,
        podcasti_slider_detail_data=podcasti_slider_detail_data
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
        article_detail=article_detail
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
    
    # Get language from query parameter, default to 'en'
    lang = request.args.get('lang', 'en')
    
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