#!/usr/bin/env python3
"""
Script để migrate tags từ ArticleDetail.content_blocks sang Article.tags field
Chạy script này sau khi đã chạy migration migrate_add_tags.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article, ArticleDetail
import json
from sqlalchemy.orm.attributes import flag_modified

def migrate_tags(limit=None, language=None):
    """
    Migrate tags từ ArticleDetail.content_blocks sang Article.tags field
    
    Args:
        limit: Giới hạn số articles xử lý (None = tất cả)
        language: Chỉ migrate articles với language này (None = tất cả)
    """
    with app.app_context():
        print("=" * 60)
        print("🔄 Migrating tags from ArticleDetail to Article.tags field")
        print("=" * 60)
        print()
        
        # Query ArticleDetail records
        query = ArticleDetail.query
        
        if language:
            query = query.filter_by(language=language)
        
        if limit:
            details = query.limit(limit).all()
        else:
            details = query.all()
        
        print(f"📚 Found {len(details)} ArticleDetail records to check")
        print()
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        articles_processed = set()  # Track articles đã xử lý
        
        for idx, detail in enumerate(details, 1):
            try:
                # Tìm article tương ứng - chỉ tìm trong các section (trừ 'home' ra)
                # VÀ language phải match với ArticleDetail.language
                article = Article.query.filter(
                    Article.published_url == detail.published_url,
                    Article.section != 'home',  # Loại trừ section='home'
                    Article.language == detail.language  # Language phải match
                ).first()
                
                # Nếu không tìm thấy, có thể article có section='home' hoặc không có published_url match hoặc language không match
                if not article:
                    skipped_count += 1
                    continue
                
                # Skip nếu article đã được xử lý (có thể có nhiều ArticleDetail cho cùng 1 article)
                if article.id in articles_processed:
                    skipped_count += 1
                    continue
                
                # Parse content_blocks
                content_blocks = detail.content_blocks
                if isinstance(content_blocks, str):
                    try:
                        content_blocks = json.loads(content_blocks)
                    except:
                        content_blocks = []
                
                if not isinstance(content_blocks, list):
                    skipped_count += 1
                    continue
                
                # Tìm article_footer_tags block
                tags_list = []
                for block in content_blocks:
                    if block.get('type') == 'article_footer_tags':
                        tags_block = block
                        tags = tags_block.get('tags', [])
                        if tags and isinstance(tags, list):
                            # Extract tag texts
                            for tag_item in tags:
                                if isinstance(tag_item, dict):
                                    tag_text = tag_item.get('text', '').strip()
                                    if tag_text:
                                        tags_list.append(tag_text)
                                elif isinstance(tag_item, str):
                                    if tag_item.strip():
                                        tags_list.append(tag_item.strip())
                        break
                
                if not tags_list:
                    # Không có tags trong ArticleDetail
                    skipped_count += 1
                    articles_processed.add(article.id)
                    continue
                
                # Kiểm tra xem article đã có tags trong field mới chưa
                existing_tags = article.tags if article.tags else []
                
                if existing_tags == tags_list:
                    # Tags đã được migrate rồi
                    skipped_count += 1
                    articles_processed.add(article.id)
                    continue
                
                # Migrate tags sang field mới
                article.tags = tags_list
                flag_modified(article, 'tags')
                
                migrated_count += 1
                articles_processed.add(article.id)
                
                if idx % 100 == 0:
                    print(f"   Processed {idx}/{len(details)} ArticleDetail records... (migrated: {migrated_count}, skipped: {skipped_count})")
                    db.session.commit()
            
            except Exception as e:
                error_count += 1
                print(f"   ⚠️  Error processing ArticleDetail #{detail.id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Commit remaining changes
        db.session.commit()
        
        print()
        print("=" * 60)
        print("✅ Migration completed!")
        print(f"   Migrated: {migrated_count} articles")
        print(f"   Skipped: {skipped_count}")
        print(f"   Errors: {error_count}")
        print("=" * 60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate tags from layout_data to tags field')
    parser.add_argument('--limit', type=int, help='Limit number of articles to process')
    parser.add_argument('--language', choices=['da', 'kl', 'en'], help='Only migrate articles with this language')
    
    args = parser.parse_args()
    
    migrate_tags(limit=args.limit, language=args.language)

