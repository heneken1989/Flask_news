"""
Script để loại bỏ "PM" và "AM" trong dates của article details đã có trong database

Usage:
    python scripts/fix_pm_am_in_dates.py --dry-run  # Chỉ xem, không update
    python scripts/fix_pm_am_in_dates.py            # Thực sự update database
    python scripts/fix_pm_am_in_dates.py --limit 10  # Giới hạn số lượng
"""
import sys
import os
import argparse
import re
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, ArticleDetail

def fix_pm_am_in_dates(dry_run=True, limit=None):
    """
    Loại bỏ "PM" và "AM" trong dates của article details
    
    Args:
        dry_run: Nếu True, chỉ in ra những gì sẽ được fix, không update database
        limit: Giới hạn số lượng article details để fix (None = tất cả)
    """
    with app.app_context():
        # Lấy tất cả article details có language='en'
        query = ArticleDetail.query.filter_by(language='en')
        
        if limit:
            query = query.limit(limit)
        
        article_details = query.all()
        
        print(f"📋 Tìm thấy {len(article_details)} article details (language='en')")
        
        fixed_count = 0
        total_fixed_dates = 0
        
        for article_detail in article_details:
            if not article_detail.content_blocks:
                continue
            
            updated = False
            fixed_dates_in_this_article = 0
            updated_blocks = []
            
            # Duyệt qua content_blocks và tạo bản copy đã fix
            for block in article_detail.content_blocks:
                block_updated = False
                updated_block = block.copy()  # Tạo copy để có thể modify
                
                # Chỉ xử lý block có type='article_meta' và có dates
                if block.get('type') == 'article_meta' and block.get('dates'):
                    dates = updated_block.get('dates', {})
                    
                    # Xử lý dates.published
                    if dates.get('published'):
                        published = dates['published']
                        
                        # Fix title
                        if published.get('title'):
                            original_title = published['title']
                            # Loại bỏ " PM" hoặc " AM" ở cuối
                            fixed_title = re.sub(r'\s*(PM|AM)$', '', original_title, flags=re.IGNORECASE)
                            
                            if fixed_title != original_title:
                                if dry_run:
                                    print(f"   📝 Would fix title: '{original_title}' -> '{fixed_title}'")
                                else:
                                    published['title'] = fixed_title
                                updated = True
                                block_updated = True
                                fixed_dates_in_this_article += 1
                        
                        # Fix text
                        if published.get('text'):
                            original_text = published['text']
                            # Loại bỏ " PM" hoặc " AM" ở cuối
                            fixed_text = re.sub(r'\s*(PM|AM)$', '', original_text, flags=re.IGNORECASE)
                            
                            if fixed_text != original_text:
                                if dry_run:
                                    print(f"   📝 Would fix text: '{original_text}' -> '{fixed_text}'")
                                else:
                                    published['text'] = fixed_text
                                updated = True
                                block_updated = True
                                fixed_dates_in_this_article += 1
                
                # Thêm block vào list (đã được update nếu có)
                updated_blocks.append(updated_block)
            
            if updated:
                fixed_count += 1
                total_fixed_dates += fixed_dates_in_this_article
                
                if dry_run:
                    print(f"   ✅ Article Detail ID {article_detail.id} (published_url: {article_detail.published_url}): Would fix {fixed_dates_in_this_article} date(s)")
                else:
                    # Update content_blocks trong database với list mới đã fix
                    article_detail.content_blocks = updated_blocks
                    # SQLAlchemy doesn't auto-detect dict/list mutations in JSON fields
                    # Cần dùng flag_modified để đảm bảo SQLAlchemy detect được thay đổi
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(article_detail, 'content_blocks')
                    db.session.commit()
                    print(f"   ✅ Article Detail ID {article_detail.id} (published_url: {article_detail.published_url}): Fixed {fixed_dates_in_this_article} date(s)")
        
        print(f"\n📊 Summary:")
        print(f"   - Total article details checked: {len(article_details)}")
        print(f"   - Article details with fixes: {fixed_count}")
        print(f"   - Total dates fixed: {total_fixed_dates}")
        
        if dry_run:
            print(f"\n⚠️  DRY RUN MODE - No changes were made to database")
            print(f"   Run without --dry-run to actually update the database")
        else:
            print(f"\n✅ All fixes have been applied to database")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix PM/AM in dates of article details')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be fixed, do not update database')
    parser.add_argument('--limit', type=int, help='Limit number of article details to process')
    
    args = parser.parse_args()
    
    fix_pm_am_in_dates(dry_run=args.dry_run, limit=args.limit)
