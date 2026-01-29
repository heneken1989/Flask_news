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

def migrate_tags(limit=None, language=None, missing_only=False):
    """
    Migrate tags từ ArticleDetail.content_blocks sang Article.tags field
    
    Args:
        limit: Giới hạn số articles xử lý (None = tất cả)
        language: Chỉ migrate articles với language này (None = tất cả)
        missing_only: Chỉ migrate articles chưa có tags (tags is None or empty)
    """
    with app.app_context():
        print("=" * 60)
        print("🔄 Migrating tags from ArticleDetail to Article.tags field")
        if missing_only:
            print("   (Only updating articles with missing tags)")
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
                # Tìm TẤT CẢ articles có cùng published_url và language
                # Bao gồm cả section='home' và các section khác (sport, samfund, etc.)
                articles_to_update = Article.query.filter(
                    Article.published_url == detail.published_url,
                    Article.language == detail.language  # Language phải match
                ).all()
                
                # Nếu không tìm thấy articles nào
                if not articles_to_update:
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
                    continue
                
                # Update tags cho TẤT CẢ articles tìm thấy (NGOẠI TRỪ section='home')
                updated_in_batch = 0
                for article in articles_to_update:
                    # Skip nếu article có section='home'
                    if article.section == 'home':
                        continue
                    
                    # Skip nếu article đã được xử lý
                    if article.id in articles_processed:
                        continue
                    
                    # Kiểm tra xem article đã có tags trong field mới chưa
                    existing_tags = article.tags if article.tags else []
                    
                    # Nếu missing_only=True và article đã có tags → skip
                    if missing_only and existing_tags:
                        articles_processed.add(article.id)
                        continue
                    
                    if existing_tags == tags_list:
                        # Tags đã được migrate rồi
                        articles_processed.add(article.id)
                        continue
                    
                    # Migrate tags sang field mới
                    article.tags = tags_list
                    flag_modified(article, 'tags')
                    
                    migrated_count += 1
                    updated_in_batch += 1
                    articles_processed.add(article.id)
                
                if updated_in_batch == 0:
                    skipped_count += 1
                
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
    parser.add_argument('--missing-only', action='store_true', help='Only migrate articles with missing tags')
    
    args = parser.parse_args()
    
    migrate_tags(limit=args.limit, language=args.language, missing_only=args.missing_only)

