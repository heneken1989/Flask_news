from flask import Blueprint, render_template
from utils import apply_grid_size_pattern
from database import Article, Category

article_view_bp = Blueprint('article_views', __name__)

@article_view_bp.route('/')
def index():
    """Home page - displays article list với grid layout theo pattern 2-3-2-3-2-3..."""
    from database import db
    
    # Thử lấy articles từ database
    articles = []
    try:
        # Query articles từ database, sắp xếp theo published_date DESC để lấy mới nhất
        articles = Article.query.order_by(Article.published_date.desc().nullslast()).limit(50).all()
        
        # Set display_order cho pattern 2-3-2-3-2-3... (0, 1, 2, ...)
        for idx, article in enumerate(articles):
            article.display_order = idx
        
        # Convert to dict và áp dụng pattern grid_size
        articles = [article.to_dict() for article in articles]
        articles = apply_grid_size_pattern(articles)
        
    except Exception as e:
        print(f"⚠️  Database query failed: {e}")
        articles = []
    
    # Nếu không có articles từ database, dùng mock data
    if not articles:
        # Tạo 50 mock articles với display_order từ 0-49
        articles = []
        for i in range(50):
            articles.append({
                'element_guid': f'mock-{i:03d}',
                'title': f'Article {i+1} - Test Pattern 2-3-2-3',
                'url': f'/erhverv/article-{i+1}/2329{i:04d}',
                'k5a_url': f'/a/2329{i:04d}',
                'section': 'erhverv',
                'site_alias': 'sermitsiaq',
                'instance': f'1000{i:02d}',
                'published_date': f'2026-01-{15-i%30:02d}T10:00:00+01:00',
                'is_paywall': i % 3 == 0,  # Một số articles có paywall
                'paywall_class': 'paywall' if i % 3 == 0 else '',
                'display_order': i,  # Quan trọng: set display_order
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
    
    # articles_per_row không còn cần thiết vì logic trong main_body.html tự động xử lý
    # Nhưng vẫn truyền vào để tương thích
    articles_per_row = 2  # Default, nhưng sẽ bị override bởi grid_size pattern
    
    return render_template('front_page.html',
        articles=articles,
        section_title='Tag: erhverv',
        articles_per_row=articles_per_row,
        section='erhverv',
        show_top_ad=True,
        show_bottom_ad=False
    )

@article_view_bp.route('/home')
def home():
    """Home page với articles grid - test route"""
    # Mock articles data
    # TODO: Sẽ lấy từ API sau
    mock_articles = [
        {
            'element_guid': '1d8fc071-5df6-43e1-8879-f9eab34d3c45',
            'title': 'Udenlandske journalister skaber nyt marked',
            'url': '/erhverv/udenlandske-journalister-skaber-nyt-marked/2329217',
            'k5a_url': '/a/2329217',
            'section': 'erhverv',
            'site_alias': 'sermitsiaq',
            'instance': '100090',
            'published_date': '2026-01-15T20:29:57+01:00',
            'is_paywall': True,
            'paywall_class': 'paywall',
            'grid_size': 6,
            'image': {
                'element_guid': 'd614121f-9a2d-4264-ba21-98d8f8a43458',
                'desktop_webp': 'https://image.sermitsiaq.ag/2329220.jpg?imageId=2329220&width=1048&height=682&format=webp',
                'desktop_jpeg': 'https://image.sermitsiaq.ag/2329220.jpg?imageId=2329220&width=1048&height=682&format=jpg',
                'mobile_webp': 'https://image.sermitsiaq.ag/2329220.jpg?imageId=2329220&width=960&height=624&format=webp',
                'mobile_jpeg': 'https://image.sermitsiaq.ag/2329220.jpg?imageId=2329220&width=960&height=624&format=jpg',
                'fallback': 'https://image.sermitsiaq.ag/2329220.jpg?imageId=2329220&width=960&height=624',
                'desktop_width': '524',
                'desktop_height': '341',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': '',
                'title': 'Udenlandske journalister skaber nyt marked'
            }
        },
        {
            'element_guid': '5e32d4a0-f3d6-48c8-b3d3-bf336d11074b',
            'title': 'Direktør i GE: Geopolitisk usikkerhed påvirker virksomhederne og investeringsmiljøet',
            'url': '/erhverv/direktor-i-ge/2328803',
            'k5a_url': '/a/2328803',
            'section': 'erhverv',
            'site_alias': 'sermitsiaq',
            'instance': '100088',
            'published_date': '2026-01-13T21:00:00+01:00',
            'is_paywall': True,
            'paywall_class': 'paywall',
            'grid_size': 6,
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
                'title': 'Direktør i GE: Geopolitisk usikkerhed påvirker virksomhederne'
            }
        },
        {
            'element_guid': 'cd0bdf4f-1963-496f-afd8-d67eed81cb9a',
            'title': 'Article 3 - Test với 3 articles per row',
            'url': '/erhverv/article-3/2328804',
            'k5a_url': '/a/2328804',
            'section': 'erhverv',
            'site_alias': 'sermitsiaq',
            'instance': '100096',
            'published_date': '2026-01-12T10:00:00+01:00',
            'is_paywall': False,
            'paywall_class': '',
            'grid_size': 4,  # 3 per row
            'image': {
                'desktop_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=1058&height=688&format=webp',
                'mobile_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624&format=webp',
                'fallback': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': '',
                'title': 'Article 3'
            }
        },
        {
            'element_guid': '14dc5b86-a14a-4735-bc9a-e983e2e8684a',
            'title': 'Article 4 - Test với 3 articles per row',
            'url': '/erhverv/article-4/2328805',
            'k5a_url': '/a/2328805',
            'section': 'erhverv',
            'site_alias': 'sermitsiaq',
            'instance': '100094',
            'published_date': '2026-01-11T10:00:00+01:00',
            'is_paywall': False,
            'paywall_class': '',
            'grid_size': 4,  # 3 per row
            'image': {
                'desktop_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=1058&height=688&format=webp',
                'mobile_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624&format=webp',
                'fallback': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': '',
                'title': 'Article 4'
            }
        },
        {
            'element_guid': '721210dd-3321-434c-b1cc-18ee67cb900f',
            'title': 'Article 5 - Test với 3 articles per row',
            'url': '/erhverv/article-5/2328806',
            'k5a_url': '/a/2328806',
            'section': 'erhverv',
            'site_alias': 'sermitsiaq',
            'instance': '100092',
            'published_date': '2026-01-10T10:00:00+01:00',
            'is_paywall': False,
            'paywall_class': '',
            'grid_size': 4,  # 3 per row
            'image': {
                'desktop_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=1058&height=688&format=webp',
                'mobile_webp': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624&format=webp',
                'fallback': 'https://image.sermitsiaq.ag/2295465.jpg?imageId=2295465&width=960&height=624',
                'desktop_width': '529',
                'desktop_height': '344',
                'mobile_width': '480',
                'mobile_height': '312',
                'alt': '',
                'title': 'Article 5'
            }
        }
    ]
    
    # Tính toán articles_per_row dựa trên grid_size của articles
    articles_per_row = 2
    if mock_articles and len(mock_articles) > 0:
        first_grid_size = mock_articles[0].get('grid_size', 6)
        if first_grid_size == 4:
            articles_per_row = 3
        elif first_grid_size == 6:
            articles_per_row = 2
    
    return render_template('front_page.html',
        articles=mock_articles,
        section_title='Tag: erhverv',
        articles_per_row=articles_per_row,
        section='erhverv',
        show_top_ad=True,
        show_bottom_ad=False
    )

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


