#!/usr/bin/env python3
"""
Script để kiểm tra categories và articles theo section
Usage: python3 scripts/check_categories.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, Category, db
from sqlalchemy import func


def main():
    with app.app_context():
        print("=" * 60)
        print("📊 Check Categories & Articles by Section")
        print("=" * 60)
        print()
        
        # Check Categories
        print("📁 Categories in Database:")
        categories = Category.query.all()
        print(f"   Total categories: {len(categories)}")
        for cat in categories:
            article_count = Article.query.filter_by(category_id=cat.id).count()
            print(f"   - {cat.name} (slug: {cat.slug}): {article_count} articles")
        print()
        
        # Check Articles by Section
        print("📰 Articles by Section:")
        sections = db.session.query(
            Article.section,
            func.count(Article.id).label('count')
        ).group_by(Article.section).all()
        
        if not sections:
            print("   ❌ No articles found in database!")
            print()
            print("💡 Tip: Run crawl script to get articles:")
            print("   python3 scripts/crawl_articles.py erhverv")
            print("   python3 scripts/crawl_articles.py samfund")
            print("   python3 scripts/crawl_articles.py kultur")
            print("   python3 scripts/crawl_articles.py sport")
        else:
            total = 0
            for section, count in sections:
                print(f"   - {section or 'None'}: {count} articles")
                total += count
            
            print()
            print(f"   Total articles: {total}")
            print()
            
            # Show sample articles from each section
            print("📋 Sample Articles by Section:")
            for section, count in sections:
                if section:
                    print(f"\n   Section: {section} ({count} articles)")
                    sample_articles = Article.query.filter_by(section=section)\
                                                   .order_by(Article.display_order.asc())\
                                                   .limit(3).all()
                    for idx, article in enumerate(sample_articles, 1):
                        print(f"     {idx}. [{article.display_order}] {article.title[:60]}")
                        print(f"        GUID: {article.element_guid}")
                        print(f"        Published: {article.published_date}")
        
        print()
        print("=" * 60)
        print()
        
        # Recommendations
        print("💡 Recommendations:")
        sections_to_crawl = ['samfund', 'erhverv', 'kultur', 'sport']
        existing_sections = [s[0] for s in sections if s[0]]
        
        missing_sections = [s for s in sections_to_crawl if s not in existing_sections]
        if missing_sections:
            print(f"   ⚠️  Missing sections: {', '.join(missing_sections)}")
            print("   Run crawl for missing sections:")
            for section in missing_sections:
                print(f"     python3 scripts/crawl_articles.py {section}")
        else:
            print("   ✅ All main sections have articles!")
        
        print()


if __name__ == '__main__':
    main()

