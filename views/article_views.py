from flask import Blueprint, render_template, request, make_response
from utils import apply_grid_size_pattern, prepare_home_layouts
from database import Article, Category

article_view_bp = Blueprint('article_views', __name__)

@article_view_bp.route('/home-test')
def home_test():
    """Simple test route để kiểm tra có phải do route /home không"""
    user_agent = request.headers.get('User-Agent', 'Unknown')
    return f"""
    <h1>Home Test Route</h1>
    <p>User-Agent: {user_agent}</p>
    <p>Method: {request.method}</p>
    <p>URL: {request.url}</p>
    <p>If you see this, the route is working!</p>
    <a href="/">Go to / (home)</a>
    """

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
    
    # Query articles từ database cho trang home
    articles = []
    try:
        # Query articles từ database, sắp xếp theo display_order
        # Lấy articles có section='home' (articles crawl từ trang home)
        # VÀ có layout_type (để biết cách hiển thị)
        articles = Article.query.filter(
            Article.section == 'home',
            Article.layout_type.isnot(None)
        ).order_by(Article.display_order.asc()).limit(100).all()
        
        # Convert to dict
        articles = [article.to_dict() for article in articles]
        
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

@article_view_bp.route('/tag/<section>')
def tag_section(section):
    """
    Display articles by section/category
    Route: /tag/samfund, /tag/erhverv, /tag/kultur, /tag/sport
    Shows 50 newest articles from the specified section
    """
    from database import db
    
    # Validate section
    valid_sections = ['samfund', 'erhverv', 'kultur', 'sport', 'job']
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
        'job': 'Job'
    }
    
    # Query articles từ database theo section
    articles = []
    try:
        # Query articles từ database, filter theo section
        # Sắp xếp theo published_date DESC để lấy mới nhất, sau đó set display_order
        articles = Article.query.filter_by(section=section)\
                                .order_by(Article.published_date.desc().nullslast())\
                                .limit(50).all()
        
        # Set display_order cho pattern 2-3-2-3-2-3... (0, 1, 2, ...)
        for idx, article in enumerate(articles):
            article.display_order = idx
        
        # Convert to dict và áp dụng pattern grid_size
        articles = [article.to_dict() for article in articles]
        articles = apply_grid_size_pattern(articles)
        
    except Exception as e:
        print(f"⚠️  Database query failed for section {section}: {e}")
        articles = []
    
    # Nếu không có articles từ database, dùng mock data
    if not articles:
        # Tạo 50 mock articles với display_order từ 0-49
        articles = []
        for i in range(50):
            articles.append({
                'element_guid': f'mock-{section}-{i:03d}',
                'title': f'Article {i+1} - {section_names.get(section, section).upper()}',
                'url': f'/{section}/article-{i+1}/2329{i:04d}',
                'k5a_url': f'/a/2329{i:04d}',
                'section': section,
                'site_alias': 'sermitsiaq',
                'instance': f'1000{i:02d}',
                'published_date': f'2026-01-{15-i%30:02d}T10:00:00+01:00',
                'is_paywall': i % 3 == 0,
                'paywall_class': 'paywall' if i % 3 == 0 else '',
                'display_order': i,
                'image': {
                    'desktop_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=1058&height=688&format=webp',
                    'desktop_jpeg': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=1058&height=688&format=jpg',
                    'mobile_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624&format=webp',
                    'mobile_jpeg': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624&format=jpg',
                    'fallback': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624',
                    'desktop_width': '529',
                    'desktop_height': '344',
                    'mobile_width': '480',
                    'mobile_height': '312',
                    'alt': '',
                    'title': f'Article {i+1}'
                }
            })
        
        # Áp dụng pattern grid_size dựa trên display_order
        articles = apply_grid_size_pattern(articles)
    
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
def article(article_id=None):
    """Display article page - có thể dùng template mới hoặc 1.html"""
    # Option 1: Dùng template mới với header/footer reuse
    # return render_template('article.html', 
    #     article_id=article_id,
    #     article={'title': 'Article Title', 'description': 'Description'},
    #     section='samfund',
    #     tags='tag1,tag2'
    # )
    
    # Option 2: Giữ nguyên 1.html (backward compatible)
    return render_template('1.html', article_id=article_id)


