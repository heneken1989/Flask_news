#!/usr/bin/env python3
"""
Script để check status của home articles
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article

def check_home_articles():
    """Check status của home articles"""
    with app.app_context():
        # Tất cả articles với section='home'
        all_home_section = Article.query.filter_by(section='home').all()
        
        # Articles với section='home' và is_home=True
        correct_home = Article.query.filter_by(section='home', is_home=True).all()
        
        # Articles với section='home' nhưng is_home=False
        home_section_false = Article.query.filter_by(section='home', is_home=False).all()
        
        # Articles với is_home=True nhưng section != 'home'
        is_home_true_wrong_section = Article.query.filter(Article.is_home == True, Article.section != 'home').all()
        
        print("="*80)
        print("📊 Home Articles Status Report")
        print("="*80)
        print(f"\n1. Total articles with section='home': {len(all_home_section)}")
        print(f"2. Articles with section='home' AND is_home=True: {len(correct_home)}")
        print(f"3. Articles with section='home' BUT is_home=False: {len(home_section_false)}")
        print(f"4. Articles with is_home=True BUT section != 'home': {len(is_home_true_wrong_section)}")
        
        if home_section_false:
            print(f"\n⚠️  Found {len(home_section_false)} articles with section='home' but is_home=False:")
            for art in home_section_false[:10]:
                print(f"   - ID: {art.id}, title: {art.title[:50]}, section: {art.section}, is_home: {art.is_home}, language: {art.language}")
        
        if is_home_true_wrong_section:
            print(f"\n⚠️  Found {len(is_home_true_wrong_section)} articles with is_home=True but section != 'home':")
            for art in is_home_true_wrong_section[:10]:
                print(f"   - ID: {art.id}, title: {art.title[:50]}, section: {art.section}, is_home: {art.is_home}, language: {art.language}")
        
        # Check duplicates trong correct_home
        from collections import defaultdict
        url_counts = defaultdict(list)
        for art in correct_home:
            if art.published_url:
                url_counts[art.published_url].append(art)
        
        duplicates = {url: arts for url, arts in url_counts.items() if len(arts) > 1}
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} duplicate URLs in correct home articles:")
            for url, arts in list(duplicates.items())[:5]:
                print(f"   - URL: {url[:60]}... ({len(arts)} articles)")
                for art in arts:
                    print(f"     * ID: {art.id}, display_order: {art.display_order}, language: {art.language}")
        
        print("\n" + "="*80)


if __name__ == '__main__':
    check_home_articles()

