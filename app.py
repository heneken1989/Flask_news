from flask import Flask, render_template, jsonify, send_from_directory, request, session, redirect, url_for
from flask_babel import Babel, gettext as _, lazy_gettext as _l, format_date, format_time, format_datetime
from api.article_api import article_bp
from views.article_views import article_view_bp
from views.admin_views import admin_bp
from database import db
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Babel configuration for i18n
app.config['BABEL_DEFAULT_LOCALE'] = 'da'  # Danish as default
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'da', 'kl']  # English, Danish, Greenlandic
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# Language detection function
def get_locale():
    """Determine the best match with our supported languages"""
    # Check if language is in URL parameter (highest priority)
    if request.args.get('lang'):
        lang = request.args.get('lang')
        if lang in app.config['BABEL_SUPPORTED_LOCALES']:
            # If setting to default language, remove from session to use default
            if lang == app.config['BABEL_DEFAULT_LOCALE']:
                session.pop('language', None)
            else:
                session['language'] = lang
            return lang
    
    # Check if language is set in session
    if 'language' in session:
        return session['language']
    
    # Skip browser detection - always use default locale
    # This ensures consistent behavior and prevents unwanted language switching
    # Default to Danish
    return app.config['BABEL_DEFAULT_LOCALE']

# Initialize Babel with locale_selector
babel = Babel(app, locale_selector=get_locale)

# Database configuration
# Có thể dùng PostgreSQL từ VPS hoặc SQLite local
# Priority: DATABASE_URL env var > .env file > SQLite fallback

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    # Thử load từ .env file
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        db_url = os.environ.get('DATABASE_URL')

if db_url:
    # Dùng PostgreSQL (từ VPS hoặc local)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    print(f"✅ Using PostgreSQL: {db_url.split('@')[1] if '@' in db_url else 'remote'}")
else:
    # Fallback to SQLite for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
    print("⚠️  Using SQLite (local development)")
    print("   Set DATABASE_URL to use PostgreSQL")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Register Jinja2 filters
@app.template_filter('group_articles')
def group_articles_filter(articles, articles_per_row=2):
    """Jinja2 filter to group articles into rows"""
    if not articles:
        return []
    grid_size = 6 if articles_per_row == 2 else 4
    for article in articles:
        if 'grid_size' not in article:
            article['grid_size'] = grid_size
    rows = []
    for i in range(0, len(articles), articles_per_row):
        rows.append(articles[i:i + articles_per_row])
    return rows

# Add error handler để log errors
@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    import traceback
    print(f"❌ 403 Forbidden Error:")
    print(f"   Request: {request.method} {request.url}")
    print(f"   User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    print(f"   Traceback:")
    traceback.print_exc()
    return "403 Forbidden", 403

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    import traceback
    print(f"❌ 500 Internal Server Error:")
    print(f"   Request: {request.method} {request.url}")
    print(f"   User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    print(f"   Traceback:")
    traceback.print_exc()
    return "500 Internal Server Error", 500

@app.route('/set_language/<lang>')
def set_language(lang):
    """Set language and redirect back"""
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        # If setting to default language, remove from session to use default
        if lang == app.config['BABEL_DEFAULT_LOCALE']:
            session.pop('language', None)  # Remove language from session
        else:
            session['language'] = lang
    # Redirect to home page if no referrer
    return redirect(request.referrer or '/')

# Make translation functions available to all templates
@app.context_processor
def inject_translations():
    """Make translation functions available in all templates"""
    # Get current locale
    current_locale = get_locale()
    return dict(
        _=_,
        _l=_l,
        format_date=format_date,
        format_time=format_time,
        format_datetime=format_datetime,
        current_locale=current_locale
    )

# Register blueprints
app.register_blueprint(article_bp, url_prefix='/api')
app.register_blueprint(article_view_bp)  # Register views blueprint
app.register_blueprint(admin_bp)  # Register admin blueprint

# Serve view-resources for local development
# On VPS, Nginx will handle this directly
@app.route('/view-resources/<path:filename>')
def serve_view_resources(filename):
    """Serve files from view-resources directory for local development"""
    view_resources_dir = os.path.join(app.root_path, 'view-resources')
    return send_from_directory(view_resources_dir, filename)

# Serve sitemap.xml
# Helper function để generate sitemap cho một ngôn ngữ
def generate_sitemap_xml(language='en', base_domain='www.sermitsiaq.com'):
    """Generate sitemap XML cho một ngôn ngữ"""
    from flask import Response
    from database import Article
    from datetime import datetime
    from urllib.parse import urlparse, urlunparse
    import xml.etree.ElementTree as ET
    import re
    
    def extract_image_id_from_image_data(image_data):
        """Extract imageId từ image_data"""
        if not image_data:
            return None
        
        image_urls = [
            image_data.get('desktop_webp'),
            image_data.get('desktop_jpeg'),
            image_data.get('mobile_webp'),
            image_data.get('mobile_jpeg'),
            image_data.get('fallback')
        ]
        
        for url in image_urls:
            if not url:
                continue
            match = re.search(r'[?&]imageId=(\d+)', url)
            if match:
                return match.group(1)
            match = re.search(r'/(\d+)\.(webp|jpg|jpeg)', url)
            if match:
                return match.group(1)
        return None
    
    def get_article_url(article, lang, domain):
        """Lấy URL của article theo ngôn ngữ"""
        url_to_use = None
        if lang == 'en' and article.published_url_en:
            url_to_use = article.published_url_en
        elif article.published_url:
            url_to_use = article.published_url
        else:
            return None
        
        if not url_to_use:
            return None
        
        parsed = urlparse(url_to_use)
        return urlunparse(('https', domain, parsed.path, parsed.params, parsed.query, parsed.fragment))
    
    def format_lastmod(published_date):
        """Format published_date thành format: 2026-01-22T00:00+01:00"""
        if not published_date:
            return None
        if isinstance(published_date, datetime):
            return published_date.strftime('%Y-%m-%dT00:00+01:00')
        try:
            if isinstance(published_date, str):
                dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%dT00:00+01:00')
        except:
            pass
        date_str = str(published_date)[:10]
        if len(date_str) == 10:
            return f"{date_str}T00:00+01:00"
        return None
    
    # Query articles theo language
    articles = Article.query.filter_by(
        language=language,
        is_temp=False
    ).filter(
        Article.published_url.isnot(None),
        Article.published_url != ''
    ).order_by(
        Article.published_date.desc().nullslast()
    ).all()
    
    # Create XML root
    root = ET.Element('urlset')
    root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    root.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
    
    for article in articles:
        article_url = get_article_url(article, language, base_domain)
        if not article_url:
            continue
        
        url_elem = ET.SubElement(root, 'url')
        
        # Loc
        loc_elem = ET.SubElement(url_elem, 'loc')
        loc_elem.text = article_url
        
        # Lastmod
        lastmod = format_lastmod(article.published_date)
        if lastmod:
            lastmod_elem = ET.SubElement(url_elem, 'lastmod')
            lastmod_elem.text = lastmod
        
        # Image - Ưu tiên lấy link từ domain của chúng ta
        if article.image_data:
            image_url = None
            
            # Ưu tiên 1: Kiểm tra xem có URL từ domain của chúng ta không
            # Check theo thứ tự: desktop_webp, fallback, desktop_jpeg, mobile_webp, mobile_jpeg
            for key in ['desktop_webp', 'fallback', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg']:
                url = article.image_data.get(key)
                if url:
                    # Check xem có phải URL từ domain của chúng ta không
                    # (chứa sermitsiaq.com và static/uploads/images, hoặc không chứa image.sermitsiaq.ag)
                    if ('sermitsiaq.com' in url and 'static/uploads/images' in url) or \
                       ('sermitsiaq.com' in url and 'image.sermitsiaq.ag' not in url):
                        # Đây là URL từ domain của chúng ta
                        image_url = url
                        break
            
            # Ưu tiên 2: Nếu không có URL từ domain của chúng ta, dùng URL từ trang gốc
            if not image_url:
                image_id = extract_image_id_from_image_data(article.image_data)
                if image_id:
                    # Fallback về URL gốc từ image.sermitsiaq.ag
                    image_url = f'https://image.sermitsiaq.ag?imageId={image_id}&format=webp&width=1200'
            
            if image_url:
                image_elem = ET.SubElement(url_elem, 'image:image')
                image_loc_elem = ET.SubElement(image_elem, 'image:loc')
                image_loc_elem.text = image_url
    
    # Create XML string
    ET.indent(root, space='  ')
    xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    
    return Response(xml_str, mimetype='application/xml')

# Serve Google verification file
@app.route('/googlef7214e31e303b929.html')
def google_verification():
    """Serve Google site verification file"""
    try:
        verification_path = os.path.join(os.path.dirname(__file__), 'templates', 'googlef7214e31e303b929.html')
        with open(verification_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except FileNotFoundError:
        return "File not found", 404

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    from database import User
    from datetime import datetime
    import hashlib
    
    # If already logged in, show logout button (don't redirect)
    if session.get('user_id') and request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        subscriber = request.form.get('subscriber', '').strip()
        password = request.form.get('password', '')
        
        if not subscriber or not password:
            return render_template('login.html', error='Vær venlig at udfylde alle felter')
        
        # Find user by email or subscriber_number
        user = User.query.filter(
            (User.email == subscriber) | (User.subscriber_number == subscriber)
        ).first()
        
        if user and user.is_active:
            # Check password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == user.password_hash:
                # Login successful
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['user_subscriber'] = user.subscriber_number
                
                # Update last_login
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Redirect to article details list page for editing
                next_page = request.args.get('next') or url_for('admin.list_article_details')
                return redirect(next_page)
            else:
                return render_template('login.html', error='Forkert e-mail eller adgangskode')
        else:
            return render_template('login.html', error='Forkert e-mail eller adgangskode')
    
    # GET request - show login form
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('article_views.index'))

# Serve sitemap for EN
@app.route('/sitemap.xml')
def sitemap():
    """Generate and serve sitemap.xml for EN"""
    return generate_sitemap_xml(language='en', base_domain='www.sermitsiaq.com')

# Serve sitemap for DA
@app.route('/sitemap-DK.xml')
def sitemap_dk():
    """Generate and serve sitemap-DK.xml for DA"""
    return generate_sitemap_xml(language='da', base_domain='www.sermitsiaq.com')

# Serve sitemap for KL
@app.route('/sitemap-KL.xml')
def sitemap_kl():
    """Generate and serve sitemap-KL.xml for KL"""
    return generate_sitemap_xml(language='kl', base_domain='www.sermitsiaq.com')

# Serve Google News sitemap
@app.route('/sitemap_news.xml')
def sitemap_news():
    """Generate and serve Google News sitemap.xml"""
    from flask import Response
    from database import Article
    from datetime import datetime, timedelta
    import xml.etree.ElementTree as ET
    
    base_url = request.url_root.rstrip('/')
    days = 2  # Google News requirement: last 2 days
    
    # Calculate date threshold
    date_threshold = datetime.utcnow() - timedelta(days=days)
    
    # Create XML root
    root = ET.Element('urlset')
    root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    root.set('xmlns:news', 'http://www.google.com/schemas/sitemap-news/0.9')
    
    # Query articles from last 2 days
    articles = Article.query.filter_by(
        is_temp=False
    ).filter(
        Article.published_date >= date_threshold
    ).order_by(
        Article.published_date.desc()
    ).limit(1000).all()  # Google News limit: 1000 URLs per sitemap
    
    for article in articles:
        url_elem = ET.SubElement(root, 'url')
        
        # Loc: Sử dụng published_url, thay domain thành sermitsiaq.com
        if article.published_url:
            from urllib.parse import urlparse, urlunparse
            # Parse published_url để lấy path
            parsed = urlparse(article.published_url)
            # Tạo URL mới với domain sermitsiaq.com, giữ nguyên path
            loc = urlunparse((
                'https',
                'sermitsiaq.com',
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        else:
            # Fallback: tạo descriptive URL
            loc = f"{base_url}/{article.section}/{article.slug}/{article.id}"
        
        loc_elem = ET.SubElement(url_elem, 'loc')
        loc_elem.text = loc
        
        # News element
        news_elem = ET.SubElement(url_elem, 'news:news')
        
        # Publication
        publication_elem = ET.SubElement(news_elem, 'news:publication')
        publication_name_elem = ET.SubElement(publication_elem, 'news:name')
        publication_name_elem.text = 'Sermitsiaq'
        publication_lang_elem = ET.SubElement(publication_elem, 'news:language')
        publication_lang_elem.text = article.language or 'en'
        
        # Publication date
        if article.published_date:
            publication_date_elem = ET.SubElement(news_elem, 'news:publication_date')
            pub_date = article.published_date
            if isinstance(pub_date, datetime):
                publication_date_elem.text = pub_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            else:
                publication_date_elem.text = str(pub_date)
        
        # Title: Descriptive title
        title_elem = ET.SubElement(news_elem, 'news:title')
        title_elem.text = article.title
        
        # Keywords (optional)
        if article.section:
            keywords_elem = ET.SubElement(news_elem, 'news:keywords')
            keywords = [article.section]
            if article.category:
                keywords.append(article.category.name)
            keywords_elem.text = ', '.join(keywords)
        
        # Geo locations: Greenland
        geo_locations_elem = ET.SubElement(news_elem, 'news:geo_locations')
        geo_locations_elem.text = 'Greenland'
    
    # Create XML string
    ET.indent(root, space='  ')
    xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    
    return Response(xml_str, mimetype='application/xml')

# You can also define routes directly in app.py if preferred
# @app.route('/')
# def index():
#     return render_template('1.html')

# @app.route('/article')
# def article():
#     return render_template('1.html')

# Create tables on startup (only in development)
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)

