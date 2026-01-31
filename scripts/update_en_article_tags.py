#!/usr/bin/env python3
"""
Script để extract và update tags cho EN articles từ ArticleDetail.content_blocks

Usage:
    python scripts/update_en_article_tags.py [--limit N] [--dry-run]
"""

import sys
import os
import argparse

# Add parent directory to path để import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from sqlalchemy import or_, cast
from sqlalchemy.dialects.postgresql import JSONB
import json

def extract_tags_from_content_blocks(content_blocks):
    """
    Extract tags từ content_blocks
    
    Args:
        content_blocks: List of content block dicts
        
    Returns:
        List of tag strings hoặc None nếu không tìm thấy
    """
    if isinstance(content_blocks, str):
        try:
            content_blocks = json.loads(content_blocks)
        except:
            return None
    
    if not isinstance(content_blocks, list):
        return None
    
    # Tìm article_footer_tags block
    for block in content_blocks:
        if block.get('type') == 'article_footer_tags':
            tags = block.get('tags', [])
            if tags:
                # Extract tag texts
                tags_list = []
                for tag_item in tags:
                    if isinstance(tag_item, dict):
                        tag_text = tag_item.get('text', '').strip()
                        if tag_text:
                            tags_list.append(tag_text)
                return tags_list if tags_list else None
    
    return None


def update_en_article_tags(limit=None, dry_run=False):
    """
    Update tags cho tất cả EN articles chưa có tags
    
    Args:
        limit: Giới hạn số lượng articles để update
        dry_run: Nếu True, chỉ show changes mà không save
    """
    print("=" * 80)
    print("UPDATE EN ARTICLE TAGS FROM ARTICLEDETAIL.CONTENT_BLOCKS")
    print("=" * 80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be saved\n")
    
    # Query EN articles chưa có tags (tags = NULL hoặc tags = [])
    query = Article.query.filter(
        Article.language == 'en',
        or_(
            Article.tags.is_(None),
            Article.tags == cast([], JSONB)
        )
    )
    
    if limit:
        query = query.limit(limit)
    
    articles = query.all()
    
    if not articles:
        print("✅ No EN articles found without tags!\n")
        return
    
    print(f"📊 Found {len(articles)} EN articles without tags\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] Processing article ID: {article.id}")
        print(f"   URL: {article.published_url[:70]}...")
        print(f"   Title: {article.title[:60] if article.title else 'N/A'}...")
        
        try:
            # Tìm ArticleDetail tương ứng
            article_detail = ArticleDetail.query.filter_by(
                published_url=article.published_url,
                language='en'
            ).first()
            
            if not article_detail:
                print(f"   ⚠️  No ArticleDetail found")
                skip_count += 1
                continue
            
            # Extract tags từ content_blocks
            tags_list = extract_tags_from_content_blocks(article_detail.content_blocks)
            
            if not tags_list:
                print(f"   ℹ️  No tags found in ArticleDetail.content_blocks")
                skip_count += 1
                continue
            
            print(f"   🏷️  Found {len(tags_list)} tags: {', '.join(tags_list[:5])}{'...' if len(tags_list) > 5 else ''}")
            
            if not dry_run:
                # Update Article.tags
                article.tags = tags_list
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(article, 'tags')
                db.session.commit()
                print(f"   ✅ Updated Article.tags")
                success_count += 1
            else:
                print(f"   💡 Would update Article.tags (dry-run)")
                success_count += 1
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
            if not dry_run:
                try:
                    db.session.rollback()
                except:
                    pass
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Success: {success_count}/{len(articles)}")
    print(f"⏭️  Skipped: {skip_count}/{len(articles)}")
    print(f"❌ Failed: {fail_count}/{len(articles)}")
    print("=" * 80 + "\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Update tags cho EN articles từ ArticleDetail.content_blocks'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Giới hạn số lượng articles để update'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Chỉ show changes mà không save vào database'
    )
    
    args = parser.parse_args()
    
    # Use Flask app context
    with app.app_context():
        update_en_article_tags(limit=args.limit, dry_run=args.dry_run)


if __name__ == '__main__':
    main()

