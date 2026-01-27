#!/usr/bin/env python3
"""
Script để verify không còn duplicate articles sau khi fix crawler
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import func


def check_duplicate_articles(language='da', section=None):
    """
    Check duplicate articles theo language và section
    
    Args:
        language: 'da', 'kl', hoặc 'en'
        section: Section name ('home', 'kultur', 'sport', etc.) hoặc None (check tất cả)
    
    Returns:
        dict: Statistics về duplicates
    """
    print("\n" + "="*60)
    if section:
        print(f"🔍 Checking duplicate {language.upper()} articles in section: {section}")
    else:
        print(f"🔍 Checking duplicate {language.upper()} articles (all sections)")
    print("="*60)
    
    # Query để tìm published_url xuất hiện nhiều lần trong cùng section + language
    if section:
        duplicate_urls_query = db.session.query(
            Article.published_url,
            func.count(Article.id).label('count')
        ).filter(
            Article.language == language,
            Article.section == section,
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).group_by(
            Article.published_url
        ).having(
            func.count(Article.id) > 1
        ).all()
    else:
        duplicate_urls_query = db.session.query(
            Article.published_url,
            func.count(Article.id).label('count')
        ).filter(
            Article.language == language,
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).group_by(
            Article.published_url
        ).having(
            func.count(Article.id) > 1
        ).all()
    
    total_duplicates = 0
    duplicate_groups = []
    
    for url, count in duplicate_urls_query:
        # Get all articles with this URL
        if section:
            articles = Article.query.filter_by(
                published_url=url,
                language=language,
                section=section
            ).all()
        else:
            articles = Article.query.filter_by(
                published_url=url,
                language=language
            ).all()
        
        total_duplicates += (count - 1)  # Số duplicates = total - 1
        
        duplicate_groups.append({
            'url': url,
            'count': count,
            'articles': articles
        })
    
    # Print results
    if duplicate_groups:
        print(f"\n⚠️  Found {len(duplicate_urls_query)} URLs with duplicates:")
        print(f"   Total duplicate articles: {total_duplicates}")
        print()
        
        for group in duplicate_groups[:20]:  # Show first 20
            url = group['url']
            count = group['count']
            articles = group['articles']
            
            print(f"   📄 URL: {url[:80]}...")
            print(f"      Count: {count} articles")
            
            for article in articles:
                print(f"      - ID: {article.id}, Section: {article.section}, is_home: {article.is_home}, created: {article.created_at}")
            print()
        
        if len(duplicate_groups) > 20:
            print(f"   ... and {len(duplicate_groups) - 20} more duplicate groups")
    else:
        print(f"\n✅ No duplicate articles found!")
    
    return {
        'duplicate_groups': len(duplicate_urls_query),
        'total_duplicates': total_duplicates,
        'groups': duplicate_groups
    }


def check_all_sections_duplicates(language='da'):
    """Check duplicates trong tất cả sections"""
    print("\n" + "="*80)
    print(f"🔍 Checking duplicates in ALL sections for {language.upper()}")
    print("="*80)
    
    sections = ['home', 'erhverv', 'samfund', 'kultur', 'sport', 'podcasti']
    
    total_stats = {
        'total_duplicate_groups': 0,
        'total_duplicates': 0
    }
    
    for section in sections:
        stats = check_duplicate_articles(language=language, section=section)
        total_stats['total_duplicate_groups'] += stats['duplicate_groups']
        total_stats['total_duplicates'] += stats['total_duplicates']
    
    print("\n" + "="*80)
    print(f"📊 Summary for {language.upper()}")
    print("="*80)
    print(f"   Total duplicate groups: {total_stats['total_duplicate_groups']}")
    print(f"   Total duplicate articles: {total_stats['total_duplicates']}")
    
    return total_stats


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify no duplicate articles')
    parser.add_argument('--language', '-l', choices=['da', 'kl', 'en', 'all'], default='all',
                       help='Language to check (default: all)')
    parser.add_argument('--section', '-s',
                       help='Section to check (default: all sections)')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.language == 'all':
            # Check all languages
            languages = ['da', 'kl', 'en']
            for lang in languages:
                if args.section:
                    check_duplicate_articles(language=lang, section=args.section)
                else:
                    check_all_sections_duplicates(language=lang)
        else:
            # Check single language
            if args.section:
                check_duplicate_articles(language=args.language, section=args.section)
            else:
                check_all_sections_duplicates(language=args.language)


if __name__ == '__main__':
    main()

