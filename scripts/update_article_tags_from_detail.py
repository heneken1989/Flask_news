#!/usr/bin/env python3
"""
Script để update tags cho các articles từ ArticleDetail.content_blocks
Chạy script này để sync tags từ ArticleDetail vào Article.layout_data['tags']
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article, ArticleDetail
import json

def update_article_tags_from_detail(limit=None, language=None):
    """
    Update tags cho articles từ ArticleDetail.content_blocks
    
    Args:
        limit: Giới hạn số lượng articles để update (None = tất cả)
        language: Filter theo language (None = tất cả)
    """
    with app.app_context():
        # Query articles
        query = Article.query
        
        if language:
            query = query.filter_by(language=language)
        
        if limit:
            articles = query.limit(limit).all()
        else:
            articles = query.all()
        
        print(f"\n{'='*60}")
        print(f"🔄 Updating tags for {len(articles)} articles")
        print(f"{'='*60}\n")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for article in articles:
            try:
                # Tìm ArticleDetail tương ứng
                article_detail = ArticleDetail.query.filter_by(
                    published_url=article.published_url,
                    language=article.language
                ).first()
                
                if not article_detail:
                    skipped_count += 1
                    if skipped_count % 100 == 0:
                        print(f"  ⏭️  Skipped {skipped_count} articles (no detail)...")
                    continue
                
                # Extract tags từ content_blocks
                content_blocks = article_detail.content_blocks
                if isinstance(content_blocks, str):
                    try:
                        content_blocks = json.loads(content_blocks)
                    except:
                        content_blocks = []
                
                if not isinstance(content_blocks, list):
                    skipped_count += 1
                    continue
                
                # Tìm article_footer_tags block
                tags_block = None
                for block in content_blocks:
                    if block.get('type') == 'article_footer_tags':
                        tags_block = block
                        break
                
                if not tags_block or not tags_block.get('tags'):
                    skipped_count += 1
                    continue
                
                # Extract tag texts
                tags_list = []
                for tag_item in tags_block.get('tags', []):
                    if isinstance(tag_item, dict):
                        tag_text = tag_item.get('text', '').strip()
                        if tag_text:
                            tags_list.append(tag_text)
                
                if not tags_list:
                    skipped_count += 1
                    continue
                
                # Update layout_data với tags
                if not article.layout_data:
                    article.layout_data = {}
                elif isinstance(article.layout_data, str):
                    try:
                        article.layout_data = json.loads(article.layout_data)
                    except:
                        article.layout_data = {}
                
                if not isinstance(article.layout_data, dict):
                    article.layout_data = {}
                
                # Check xem tags đã có chưa
                existing_tags = article.layout_data.get('tags', [])
                if existing_tags == tags_list:
                    skipped_count += 1
                    continue
                
                # Update tags
                article.layout_data['tags'] = tags_list
                updated_count += 1
                
                if updated_count % 10 == 0:
                    print(f"  ✅ Updated {updated_count} articles... (latest: {article.id} - {', '.join(tags_list[:3])}...)")
                    db.session.commit()
            
            except Exception as e:
                error_count += 1
                print(f"  ⚠️  Error updating article {article.id}: {e}")
                db.session.rollback()
                continue
        
        # Final commit
        db.session.commit()
        
        print(f"\n{'='*60}")
        print(f"📊 Summary:")
        print(f"  - Updated: {updated_count}")
        print(f"  - Skipped: {skipped_count}")
        print(f"  - Errors: {error_count}")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Update article tags from ArticleDetail')
    parser.add_argument('--limit', type=int, help='Limit number of articles to update')
    parser.add_argument('--language', type=str, choices=['da', 'kl', 'en'], help='Filter by language')
    
    args = parser.parse_args()
    
    update_article_tags_from_detail(limit=args.limit, language=args.language)

