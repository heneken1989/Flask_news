from flask import Flask, render_template, jsonify
from api.article_api import article_bp
from views.article_views import article_view_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(article_bp, url_prefix='/api')
app.register_blueprint(article_view_bp)  # Register views blueprint

# You can also define routes directly in app.py if preferred
# @app.route('/')
# def index():
#     return render_template('1.html')

# @app.route('/article')
# def article():
#     return render_template('1.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

