#!/usr/bin/env python3
"""
Script để check duplicate articles trong home page
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import func

def check_duplicates():
    """Check duplicate articles trong home page"""
    with app.app_context():
        # Tìm duplicates: cùng published_url, section='home', is_home=True, cùng language
        duplicates = db.session.query(
            Article.published_url,
            Article.section,
            Article.is_home,
            Article.language,
            func.count(Article.id).label('count')
        ).filter(
            Article.section == 'home',
            Article.is_home == True
        ).group_by(
            Article.published_url,
            Article.section,
            Article.is_home,
            Article.language
        ).having(
            func.count(Article.id) > 1
        ).all()
        
        print(f"🔍 Found {len(duplicates)} duplicate groups in home page:")
        print("="*80)
        
        for dup in duplicates:
            published_url, section, is_home, language, count = dup
            print(f"\n📰 URL: {published_url[:80]}...")
            print(f"   Section: {section}, is_home: {is_home}, Language: {language}, Count: {count}")
            
            # Lấy tất cả articles duplicate này
            articles = Article.query.filter_by(
                published_url=published_url,
                section=section,
                is_home=is_home,
                language=language
            ).all()
            
            print(f"   Article IDs: {[a.id for a in articles]}")
            print(f"   Display orders: {[a.display_order for a in articles]}")
            print(f"   Layout types: {[a.layout_type for a in articles]}")
            
            # Đề xuất: giữ article có display_order nhỏ nhất (mới nhất)
            if articles:
                articles_sorted = sorted(articles, key=lambda x: x.display_order)
                keep_article = articles_sorted[0]
                delete_articles = articles_sorted[1:]
                
                print(f"   💡 Keep article ID {keep_article.id} (display_order={keep_article.display_order})")
                print(f"   🗑️  Should delete: {[a.id for a in delete_articles]}")
        
        print("\n" + "="*80)
        print(f"📊 Total duplicate groups: {len(duplicates)}")
        
        # Đếm tổng số articles duplicate
        total_duplicate_articles = sum(count - 1 for _, _, _, _, count in duplicates)
        print(f"📊 Total duplicate articles to remove: {total_duplicate_articles}")


if __name__ == '__main__':
    check_duplicates()

