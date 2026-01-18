from flask import Flask, render_template, jsonify, send_from_directory, request, session, redirect, url_for
from flask_babel import Babel, gettext as _, lazy_gettext as _l, format_date, format_time, format_datetime
from api.article_api import article_bp
from views.article_views import article_view_bp
from database import db
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Babel configuration for i18n
app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # English as default
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
    # Default to English
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

# Serve view-resources for local development
# On VPS, Nginx will handle this directly
@app.route('/view-resources/<path:filename>')
def serve_view_resources(filename):
    """Serve files from view-resources directory for local development"""
    view_resources_dir = os.path.join(app.root_path, 'view-resources')
    return send_from_directory(view_resources_dir, filename)

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

