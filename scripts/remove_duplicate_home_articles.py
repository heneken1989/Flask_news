#!/usr/bin/env python3
"""
Script để xóa duplicate articles trong home page
Chỉ giữ lại 1 article (có display_order nhỏ nhất) cho mỗi published_url + language
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import func

def remove_duplicates():
    """Xóa duplicate articles trong home page"""
    with app.app_context():
        # Tìm duplicates: cùng published_url, section='home', is_home=True, cùng language
        duplicates = db.session.query(
            Article.published_url,
            Article.language,
            func.count(Article.id).label('count')
        ).filter(
            Article.section == 'home',
            Article.is_home == True
        ).group_by(
            Article.published_url,
            Article.language
        ).having(
            func.count(Article.id) > 1
        ).all()
        
        print(f"🔍 Found {len(duplicates)} duplicate groups in home page")
        print("="*80)
        
        total_deleted = 0
        
        for dup in duplicates:
            published_url, language, count = dup
            print(f"\n📰 Processing: {published_url[:80]}... (Language: {language}, Count: {count})")
            
            # Lấy tất cả articles duplicate này
            articles = Article.query.filter_by(
                published_url=published_url,
                section='home',
                is_home=True,
                language=language
            ).order_by(Article.display_order.asc(), Article.id.asc()).all()
            
            if len(articles) <= 1:
                continue
            
            # Giữ article đầu tiên (có display_order nhỏ nhất)
            keep_article = articles[0]
            delete_articles = articles[1:]
            
            print(f"   ✅ Keep article ID {keep_article.id} (display_order={keep_article.display_order})")
            print(f"   🗑️  Deleting {len(delete_articles)} duplicate articles: {[a.id for a in delete_articles]}")
            
            # Xóa duplicates
            for article in delete_articles:
                db.session.delete(article)
                total_deleted += 1
            
            db.session.commit()
            print(f"   ✅ Deleted {len(delete_articles)} duplicates")
        
        print("\n" + "="*80)
        print(f"✅ Removed {total_deleted} duplicate articles from home page")
        print("="*80)


if __name__ == '__main__':
    remove_duplicates()

