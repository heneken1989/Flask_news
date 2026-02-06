"""
Script để kiểm tra xem còn PM/AM trong dates của article details không

Usage:
    python scripts/check_pm_am_in_dates.py
    python scripts/check_pm_am_in_dates.py --limit 10
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

def check_pm_am_in_dates(limit=None):
    """
    Kiểm tra xem còn PM/AM trong dates của article details không
    
    Args:
        limit: Giới hạn số lượng article details để kiểm tra (None = tất cả)
    """
    with app.app_context():
        # Lấy tất cả article details có language='en'
        query = ArticleDetail.query.filter_by(language='en')
        
        if limit:
            query = query.limit(limit)
        
        article_details = query.all()
        
        print(f"📋 Đang kiểm tra {len(article_details)} article details (language='en')...\n")
        
        found_count = 0
        total_found_dates = 0
        examples = []
        
        for article_detail in article_details:
            if not article_detail.content_blocks:
                continue
            
            found_in_this_article = []
            
            # Duyệt qua content_blocks
            for block in article_detail.content_blocks:
                # Chỉ xử lý block có type='article_meta' và có dates
                if block.get('type') == 'article_meta' and block.get('dates'):
                    dates = block.get('dates', {})
                    
                    # Xử lý dates.published
                    if dates.get('published'):
                        published = dates['published']
                        
                        # Check title
                        if published.get('title'):
                            title = published['title']
                            if re.search(r'\s*(PM|AM)$', title, flags=re.IGNORECASE):
                                found_in_this_article.append({
                                    'type': 'title',
                                    'text': title,
                                    'published_url': article_detail.published_url
                                })
                                total_found_dates += 1
                        
                        # Check text
                        if published.get('text'):
                            text = published['text']
                            if re.search(r'\s*(PM|AM)$', text, flags=re.IGNORECASE):
                                found_in_this_article.append({
                                    'type': 'text',
                                    'text': text,
                                    'published_url': article_detail.published_url
                                })
                                total_found_dates += 1
            
            if found_in_this_article:
                found_count += 1
                print(f"   ⚠️  Article Detail ID {article_detail.id}")
                print(f"      Published URL: {article_detail.published_url}")
                for item in found_in_this_article:
                    print(f"      - {item['type']}: '{item['text']}'")
                    if len(examples) < 5:
                        examples.append({
                            'id': article_detail.id,
                            'published_url': article_detail.published_url,
                            **item
                        })
                print()
        
        print(f"\n📊 Summary:")
        print(f"   - Total article details checked: {len(article_details)}")
        print(f"   - Article details with PM/AM: {found_count}")
        print(f"   - Total dates with PM/AM: {total_found_dates}")
        
        if found_count > 0:
            print(f"\n⚠️  Vẫn còn {found_count} article details có PM/AM trong dates!")
            print(f"   Chạy script fix_pm_am_in_dates.py để loại bỏ:")
            print(f"   python scripts/fix_pm_am_in_dates.py")
        else:
            print(f"\n✅ Không tìm thấy PM/AM trong dates!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check PM/AM in dates of article details')
    parser.add_argument('--limit', type=int, help='Limit number of article details to check')
    
    args = parser.parse_args()
    
    check_pm_am_in_dates(limit=args.limit)
