#!/usr/bin/env python3
"""
Script để kiểm tra article có trong DB không
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, db

def check_article(published_url):
    """Kiểm tra article trong DB"""
    with app.app_context():
        print("=" * 80)
        print(f"🔍 Checking article: {published_url}")
        print("=" * 80)
        
        # Tìm tất cả articles với published_url này
        articles = Article.query.filter_by(
            published_url=published_url
        ).all()
        
        print(f"\n📊 Found {len(articles)} articles with this URL:")
        
        if not articles:
            print("❌ Article not found in database!")
            return
        
        for idx, article in enumerate(articles, 1):
            print(f"\n[{idx}] Article ID: {article.id}")
            print(f"   Language: {article.language}")
            print(f"   Section: {article.section}")
            print(f"   is_home: {article.is_home}")
            print(f"   layout_type: {article.layout_type}")
            print(f"   display_order: {article.display_order}")
            print(f"   Title: {article.title[:80]}...")
            
            # Check layout_data
            if article.layout_data:
                layout_data = article.layout_data
                print(f"   layout_data keys: {list(layout_data.keys())}")
                if 'list_title' in layout_data:
                    print(f"   list_title: {layout_data.get('list_title')}")
                if 'list_items' in layout_data:
                    print(f"   list_items count: {len(layout_data.get('list_items', []))}")
        
        # Check specifically for 1_with_list_right with section='home'
        print("\n" + "=" * 80)
        print("🔍 Checking for 1_with_list_right with section='home':")
        print("=" * 80)
        
        home_articles = Article.query.filter_by(
            published_url=published_url,
            layout_type='1_with_list_right',
            section='home'
        ).all()
        
        if home_articles:
            print(f"✅ Found {len(home_articles)} article(s) with section='home':")
            for article in home_articles:
                print(f"   - ID: {article.id}, Language: {article.language}")
        else:
            print("❌ No article found with section='home'")
            
            # Check if there are articles with other sections
            other_sections = Article.query.filter_by(
                published_url=published_url,
                layout_type='1_with_list_right'
            ).all()
            
            if other_sections:
                print(f"\n⚠️  Found {len(other_sections)} article(s) with other sections:")
                for article in other_sections:
                    print(f"   - ID: {article.id}, Section: {article.section}, Language: {article.language}")

if __name__ == '__main__':
    url = "https://www.sermitsiaq.ag/sport/fire-langrendslobere-skal-til-junior-vm/2335195"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    check_article(url)

