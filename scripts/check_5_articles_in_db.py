#!/usr/bin/env python3
"""
Script để kiểm tra 5_articles container có trong DB không
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, db

def check_5_articles():
    """Kiểm tra 5_articles containers trong DB"""
    with app.app_context():
        print("=" * 80)
        print(f"🔍 Checking for 5_articles containers in database")
        print("=" * 80)
        
        # Tìm tất cả articles với layout_type='5_articles'
        articles = Article.query.filter_by(
            layout_type='5_articles'
        ).all()
        
        print(f"\n📊 Found {len(articles)} articles with layout_type='5_articles':")
        
        if not articles:
            print("❌ No 5_articles containers found in database!")
            return
        
        for idx, article in enumerate(articles, 1):
            print(f"\n[{idx}] Article ID: {article.id}")
            print(f"   Language: {article.language}")
            print(f"   Section: {article.section}")
            print(f"   is_home: {article.is_home}")
            print(f"   display_order: {article.display_order}")
            print(f"   Title: {article.title[:80]}...")
            print(f"   published_url: {article.published_url[:80] if article.published_url else 'N/A'}...")
            
            # Check layout_data
            if article.layout_data:
                layout_data = article.layout_data
                print(f"   layout_data keys: {list(layout_data.keys())}")
                if 'slider_title' in layout_data:
                    print(f"   slider_title: {layout_data.get('slider_title')}")
                if 'slider_articles' in layout_data:
                    slider_articles = layout_data.get('slider_articles', [])
                    print(f"   slider_articles count: {len(slider_articles)}")
                    if slider_articles:
                        print(f"   First 3 slider articles:")
                        for i, item in enumerate(slider_articles[:3], 1):
                            print(f"      {i}. {item.get('title', 'N/A')[:50]}... (URL: {item.get('url', 'N/A')[:50]}...)")
                if 'items_per_view' in layout_data:
                    print(f"   items_per_view: {layout_data.get('items_per_view')}")
                if 'source_class' in layout_data:
                    print(f"   source_class: {layout_data.get('source_class')}")
            else:
                print(f"   ⚠️  No layout_data!")
        
        # Check specifically for 5_articles with section='home' and is_home=True
        print("\n" + "=" * 80)
        print("🔍 Checking for 5_articles with section='home' and is_home=True:")
        print("=" * 80)
        
        home_articles = Article.query.filter_by(
            layout_type='5_articles',
            section='home',
            is_home=True
        ).all()
        
        if home_articles:
            print(f"✅ Found {len(home_articles)} 5_articles container(s) with section='home' and is_home=True:")
            for article in home_articles:
                print(f"   - ID: {article.id}, Language: {article.language}, display_order: {article.display_order}")
        else:
            print("❌ No 5_articles container found with section='home' and is_home=True")
            
            # Check if there are 5_articles with other sections
            other_sections = Article.query.filter_by(
                layout_type='5_articles'
            ).filter(
                db.or_(Article.section != 'home', Article.is_home == False)
            ).all()
            
            if other_sections:
                print(f"\n⚠️  Found {len(other_sections)} 5_articles container(s) with other sections or is_home=False:")
                for article in other_sections:
                    print(f"   - ID: {article.id}, Section: {article.section}, is_home: {article.is_home}, Language: {article.language}")

if __name__ == '__main__':
    check_5_articles()

