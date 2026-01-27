#!/usr/bin/env python3
"""
Script để kiểm tra duplicate 5_articles containers với cùng display_order và language
"""
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, db

def check_duplicates():
    """Kiểm tra duplicate 5_articles containers"""
    with app.app_context():
        print("=" * 80)
        print(f"🔍 Checking for duplicate 5_articles containers")
        print("=" * 80)
        
        # Tìm tất cả 5_articles containers
        articles = Article.query.filter_by(
            layout_type='5_articles',
            section='home',
            is_home=True
        ).order_by(Article.display_order, Article.language, Article.created_at.desc()).all()
        
        print(f"\n📊 Found {len(articles)} 5_articles containers total")
        
        # Group by display_order and language
        groups = defaultdict(list)
        for article in articles:
            key = (article.display_order, article.language)
            groups[key].append(article)
        
        print(f"\n📊 Found {len(groups)} unique (display_order, language) combinations")
        
        # Check for duplicates
        duplicates_found = False
        for (display_order, language), article_list in groups.items():
            if len(article_list) > 1:
                duplicates_found = True
                print(f"\n⚠️  DUPLICATE: display_order={display_order}, language={language}: {len(article_list)} containers")
                for idx, article in enumerate(article_list, 1):
                    print(f"   [{idx}] ID: {article.id}")
                    print(f"       created_at: {article.created_at}")
                    print(f"       updated_at: {article.updated_at}")
                    print(f"       title: {article.title[:60]}...")
                    if article.layout_data and 'slider_articles' in article.layout_data:
                        print(f"       slider_articles count: {len(article.layout_data.get('slider_articles', []))}")
        
        if not duplicates_found:
            print("\n✅ No duplicates found - each (display_order, language) combination has only 1 container")
        else:
            print("\n" + "=" * 80)
            print("💡 Recommendation: Query should order by created_at DESC to get the latest container")
            print("=" * 80)

if __name__ == '__main__':
    check_duplicates()

