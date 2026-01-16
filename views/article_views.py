from flask import Blueprint, render_template

article_view_bp = Blueprint('article_views', __name__)

@article_view_bp.route('/')
def index():
    """Home page - displays article list or main page"""
    return render_template('1.html')

@article_view_bp.route('/article')
@article_view_bp.route('/article/<int:article_id>')
def article(article_id=None):
    """Display article page"""
    return render_template('1.html', article_id=article_id)

