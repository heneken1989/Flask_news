from flask import Blueprint, jsonify

article_bp = Blueprint('article', __name__)

@article_bp.route('/articles', methods=['GET'])
def get_articles():
    """
    API endpoint to get articles
    TODO: Implement article fetching logic
    """
    return jsonify({'message': 'Article API - To be implemented'})

@article_bp.route('/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """
    API endpoint to get a specific article by ID
    TODO: Implement article fetching logic
    """
    return jsonify({'message': f'Article {article_id} API - To be implemented'})

