#!/usr/bin/env python3
"""
Script để fix section cho articles đã crawl
Kiểm tra và phân loại lại articles theo section từ URL hoặc data-section attribute
Usage: python3 scripts/fix_sections.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, db
from urllib.parse import urlparse


def extract_section_from_url(url):
    """Extract section từ URL"""
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        parts = path.split('/')
        
        # URL format: /erhverv/article-slug/123456
        if len(parts) >= 1:
            section = parts[0]
            valid_sections = ['samfund', 'erhverv', 'kultur', 'sport', 'job']
            if section in valid_sections:
                return section
        return None
    except:
        return None


def main():
    with app.app_context():
        print("=" * 60)
        print("🔧 Fix Sections for Articles")
        print("=" * 60)
        print()
        
        # Lấy tất cả articles
        articles = Article.query.all()
        print(f"📰 Total articles: {len(articles)}")
        print()
        
        fixed_count = 0
        unchanged_count = 0
        
        for article in articles:
            # Extract section từ URL
            section_from_url = extract_section_from_url(article.published_url)
            
            if section_from_url and section_from_url != article.section:
                old_section = article.section or 'None'
                article.section = section_from_url
                fixed_count += 1
                print(f"✅ Fixed: {article.title[:50]}")
                print(f"   Old section: {old_section} → New section: {section_from_url}")
            else:
                unchanged_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            print()
            print(f"✅ Fixed {fixed_count} articles")
            print(f"⏭️  Unchanged: {unchanged_count} articles")
        else:
            print("✅ All articles already have correct sections")
        
        print()
        print("=" * 60)
        print()
        
        # Show summary by section
        print("📊 Articles by Section (after fix):")
        from sqlalchemy import func
        sections = db.session.query(
            Article.section,
            func.count(Article.id).label('count')
        ).group_by(Article.section).all()
        
        for section, count in sections:
            print(f"   - {section or 'None'}: {count} articles")
        print()


if __name__ == '__main__':
    main()

