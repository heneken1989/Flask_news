from flask import Flask, render_template, jsonify, send_from_directory
from api.article_api import article_bp
from views.article_views import article_view_bp
import os

app = Flask(__name__)

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

