from flask import Flask, render_template, jsonify, send_from_directory
from api.article_api import article_bp
from views.article_views import article_view_bp
import os

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)

