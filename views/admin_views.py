"""
Admin views để quản lý Article Detail
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database import db, ArticleDetail, Article
from datetime import datetime
from urllib.parse import urlparse
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/article-details')
def list_article_details():
    """
    List tất cả article details với pagination và search
    """
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    language = request.args.get('language', '').strip()
    
    # Build query
    query = ArticleDetail.query
    
    # Filter by search
    if search:
        # Check if search is a number (could be article ID or article_detail ID)
        if search.isdigit():
            search_id = int(search)
            # Try to find by article_detail ID first
            detail_by_id = ArticleDetail.query.get(search_id)
            if detail_by_id:
                # If found by ID, return only that one (with language filter if specified)
                if language and detail_by_id.language != language:
                    # Language doesn't match, return empty
                    return render_template('admin/article_details_list.html',
                        article_details=[],
                        pagination=None,
                        search=search,
                        language=language,
                        current_page=1,
                        is_single_result=False
                    )
                article = Article.query.filter_by(published_url=detail_by_id.published_url).first()
                return render_template('admin/article_details_list.html',
                    article_details=[{'detail': detail_by_id, 'article': article}],
                    pagination=None,  # No pagination for single result
                    search=search,
                    language=language,
                    current_page=1,
                    is_single_result=True
                )
            else:
                # Try to find by article ID
                article = Article.query.get(search_id)
                if article and article.published_url:
                    # Find all article_details by published_url (can have multiple languages)
                    query = ArticleDetail.query.filter_by(published_url=article.published_url)
                else:
                    # No results
                    return render_template('admin/article_details_list.html',
                        article_details=[],
                        pagination=None,
                        search=search,
                        language=language,
                        current_page=1,
                        is_single_result=False
                    )
        else:
            # Check if search is a URL (contains http:// or https://)
            search_path = None
            if search.startswith('http://') or search.startswith('https://'):
                # Parse URL and extract path
                parsed = urlparse(search)
                search_path = parsed.path
                # Remove leading slash if present
                if search_path.startswith('/'):
                    search_path = search_path[1:]
            elif search.startswith('/'):
                # Already a path, remove leading slash
                search_path = search[1:]
            else:
                # Check if it looks like a path (contains /)
                if '/' in search:
                    search_path = search.lstrip('/')
            
            if search_path:
                # Normalize search_path: ensure it starts with /
                if not search_path.startswith('/'):
                    search_path = '/' + search_path
                
                # Search by path in Article.published_url and Article.published_url_en
                # Find all articles that match the path
                matching_articles = []
                
                # Search in published_url (DA)
                articles_by_published_url = Article.query.filter(
                    Article.published_url.isnot(None),
                    Article.published_url != ''
                ).all()
                
                for art in articles_by_published_url:
                    # Check published_url (DA)
                    if art.published_url:
                        art_parsed = urlparse(art.published_url)
                        art_path = art_parsed.path
                        # Match exact path
                        if art_path == search_path:
                            matching_articles.append(art)
                            continue
                    
                    # Check published_url_en (EN)
                    if art.published_url_en:
                        art_en_parsed = urlparse(art.published_url_en)
                        art_en_path = art_en_parsed.path
                        # Match exact path
                        if art_en_path == search_path:
                            matching_articles.append(art)
                
                if matching_articles:
                    # Get all published_urls from matching articles
                    published_urls = []
                    for art in matching_articles:
                        if art.published_url:
                            published_urls.append(art.published_url)
                        if art.published_url_en:
                            published_urls.append(art.published_url_en)
                    
                    # Find all article_details with these published_urls
                    query = query.filter(ArticleDetail.published_url.in_(published_urls))
                else:
                    # No matching articles found
                    return render_template('admin/article_details_list.html',
                        article_details=[],
                        pagination=None,
                        search=search,
                        language=language,
                        current_page=1,
                        is_single_result=False
                    )
            else:
                # Search in published_url (original behavior - text search)
                query = query.filter(ArticleDetail.published_url.ilike(f'%{search}%'))
    
    # Filter by language
    if language:
        query = query.filter(ArticleDetail.language == language)
    
    # Order by updated_at desc
    query = query.order_by(ArticleDetail.updated_at.desc())
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    article_details = pagination.items
    
    # Get article info for each detail
    details_with_articles = []
    for detail in article_details:
        article = Article.query.filter_by(published_url=detail.published_url).first()
        details_with_articles.append({
            'detail': detail,
            'article': article
        })
    
    return render_template('admin/article_details_list.html',
        article_details=details_with_articles,
        pagination=pagination,
        search=search,
        language=language,
        current_page=page,
        is_single_result=False
    )


@admin_bp.route('/article-detail/<int:detail_id>')
def view_article_detail(detail_id):
    """
    View article detail (read-only)
    """
    article_detail = ArticleDetail.query.get_or_404(detail_id)
    article = Article.query.filter_by(published_url=article_detail.published_url).first()
    
    return render_template('admin/article_detail_view.html',
        article_detail=article_detail,
        article=article
    )


@admin_bp.route('/article-detail/<int:detail_id>/edit')
def edit_article_detail(detail_id):
    """
    Edit article detail form (JSON editor)
    """
    article_detail = ArticleDetail.query.get_or_404(detail_id)
    article = Article.query.filter_by(published_url=article_detail.published_url).first()
    
    # Format content_blocks as JSON string for editing
    content_blocks_json = json.dumps(article_detail.content_blocks, indent=2, ensure_ascii=False) if article_detail.content_blocks else '[]'
    
    return render_template('admin/article_detail_edit.html',
        article_detail=article_detail,
        article=article,
        content_blocks_json=content_blocks_json
    )


@admin_bp.route('/article-detail/<int:detail_id>/edit-visual')
def edit_article_detail_visual(detail_id):
    """
    Edit article detail with visual editor (like article_detail view)
    """
    article_detail = ArticleDetail.query.get_or_404(detail_id)
    article = Article.query.filter_by(published_url=article_detail.published_url).first()
    
    return render_template('admin/article_detail_edit_visual.html',
        article_detail=article_detail,
        article=article
    )


@admin_bp.route('/article-detail/<int:detail_id>/update', methods=['POST'])
def update_article_detail(detail_id):
    """
    Update article detail
    """
    article_detail = ArticleDetail.query.get_or_404(detail_id)
    
    try:
        # Debug: log request data
        print(f"🔍 Update request for article_detail {detail_id}")
        print(f"   Form keys: {list(request.form.keys())}")
        print(f"   Content-Type: {request.content_type}")
        
        # Get JSON data from form
        content_blocks_json = request.form.get('content_blocks', '[]')
        print(f"   Content blocks JSON length: {len(content_blocks_json)}")
        
        if not content_blocks_json or content_blocks_json == '[]':
            flash('No content blocks data received', 'error')
            if request.form.get('from_visual_editor') == 'true':
                return redirect(url_for('admin.edit_article_detail_visual', detail_id=detail_id))
            return redirect(url_for('admin.edit_article_detail', detail_id=detail_id))
        
        # Check if request is from visual editor
        is_visual_editor = request.form.get('from_visual_editor', 'false') == 'true'
        print(f"   From visual editor: {is_visual_editor}")
        
        # Parse JSON
        try:
            content_blocks = json.loads(content_blocks_json)
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error: {str(e)}")
            print(f"   JSON preview: {content_blocks_json[:200]}...")
            flash(f'Invalid JSON: {str(e)}', 'error')
            if is_visual_editor:
                return redirect(url_for('admin.edit_article_detail_visual', detail_id=detail_id))
            return redirect(url_for('admin.edit_article_detail', detail_id=detail_id))
        
        # Validate: must be a list
        if not isinstance(content_blocks, list):
            print(f"   ❌ Content blocks is not a list: {type(content_blocks)}")
            flash('Content blocks must be a JSON array', 'error')
            if is_visual_editor:
                return redirect(url_for('admin.edit_article_detail_visual', detail_id=detail_id))
            return redirect(url_for('admin.edit_article_detail', detail_id=detail_id))
        
        print(f"   ✅ Parsed {len(content_blocks)} blocks")
        
        # Update article detail
        article_detail.content_blocks = content_blocks
        article_detail.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        print(f"   ✅ Successfully updated article_detail {detail_id}")
        flash('Article detail updated successfully!', 'success')
        if is_visual_editor:
            return redirect(url_for('admin.edit_article_detail_visual', detail_id=detail_id))
        return redirect(url_for('admin.view_article_detail', detail_id=detail_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error updating article detail: {str(e)}', 'error')
        if request.form.get('from_visual_editor') == 'true':
            return redirect(url_for('admin.edit_article_detail_visual', detail_id=detail_id))
        return redirect(url_for('admin.edit_article_detail', detail_id=detail_id))


@admin_bp.route('/article-detail/search')
def search_article_detail():
    """
    Search article detail by URL (AJAX endpoint)
    """
    url = request.args.get('url', '').strip()
    language = request.args.get('language', '').strip()
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Build query
    query = ArticleDetail.query.filter_by(published_url=url)
    
    if language:
        query = query.filter_by(language=language)
    
    article_detail = query.first()
    
    if not article_detail:
        return jsonify({'error': 'Article detail not found'}), 404
    
    return jsonify({
        'id': article_detail.id,
        'published_url': article_detail.published_url,
        'language': article_detail.language,
        'edit_url': url_for('admin.edit_article_detail', detail_id=article_detail.id)
    })

