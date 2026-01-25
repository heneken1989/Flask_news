#!/usr/bin/env python3
"""
Script để kiểm tra tại sao các articles từ home layout không tìm thấy trong DB
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article

# URLs từ terminal output (bị truncate, cần tìm full URL)
urls_to_check = [
    "https://www.sermitsiaq.ag/samfund/kaere-trump/2327059",
    "https://www.sermitsiaq.ag/samfund/forsker-frygter-konsekvens",
    "https://www.sermitsiaq.ag/samfund/medie-heftig-diskussion-pa",
    "https://www.sermitsiaq.ag/samfund/trump-radgiver-ingen-vil-k",
    "https://www.sermitsiaq.ag/samfund/lettet-vivian-mit-storste-",
    "https://www.sermitsiaq.ag/samfund/senatorer-i-usa-venter-at-",
    "https://www.sermitsiaq.ag/samfund/pipaluk-lynge-kritiserer-f",
    "https://www.sermitsiaq.ag/samfund/professor-trump-drommer-om",
    "https://www.sermitsiaq.ag/samfund/arbejdstilsynet-far-ny-kre",
    "https://www.sermitsiaq.ag/samfund/ordre-palaegger-danske-sol",
]

def normalize_url(url):
    """Normalize URL: remove trailing slash, lowercase, etc."""
    if not url:
        return url
    url = url.strip().lower()
    if url.endswith('/'):
        url = url[:-1]
    return url

def check_articles():
    with app.app_context():
        print("="*80)
        print("🔍 Checking missing home articles in database...")
        print("="*80)
        
        found_count = 0
        not_found_count = 0
        partial_found_count = 0
        
        for url in urls_to_check:
            print(f"\n{'='*80}")
            print(f"Checking: {url}")
            print(f"{'='*80}")
            
            # 1. Tìm exact match
            exact_match = Article.query.filter_by(published_url=url).first()
            
            # 2. Tìm bằng normalized URL
            normalized_url = normalize_url(url)
            normalized_matches = Article.query.filter(
                db.func.lower(db.func.rtrim(Article.published_url, '/')) == normalized_url
            ).all()
            
            # 3. Tìm bằng slug (phần cuối của URL)
            url_parts = url.rstrip('/').split('/')
            slug = url_parts[-1] if url_parts else ''
            slug_matches = []
            if slug:
                slug_matches = Article.query.filter(
                    Article.published_url.like(f"%{slug}%")
                ).all()
            
            # 4. Tìm bằng path (bỏ domain)
            path = '/'.join(url_parts[-2:]) if len(url_parts) >= 2 else ''
            path_matches = []
            if path:
                path_matches = Article.query.filter(
                    Article.published_url.like(f"%{path}%")
                ).all()
            
            if exact_match:
                print(f"✅ FOUND (exact match):")
                print(f"   ID: {exact_match.id}, Language: {exact_match.language}")
                print(f"   Section: {exact_match.section}, is_home: {exact_match.is_home}")
                print(f"   URL: {exact_match.published_url}")
                found_count += 1
            elif normalized_matches:
                print(f"✅ FOUND (normalized match): {len(normalized_matches)} articles")
                for match in normalized_matches:
                    print(f"   ID: {match.id}, Language: {match.language}, Section: {match.section}")
                    print(f"   URL: {match.published_url}")
                found_count += 1
            elif slug_matches:
                print(f"⚠️  FOUND (by slug): {len(slug_matches)} articles")
                for match in slug_matches[:5]:  # Show first 5
                    print(f"   ID: {match.id}, Language: {match.language}, Section: {match.section}")
                    print(f"   URL: {match.published_url}")
                if len(slug_matches) > 5:
                    print(f"   ... and {len(slug_matches) - 5} more")
                partial_found_count += 1
            elif path_matches:
                print(f"⚠️  FOUND (by path): {len(path_matches)} articles")
                for match in path_matches[:5]:  # Show first 5
                    print(f"   ID: {match.id}, Language: {match.language}, Section: {match.section}")
                    print(f"   URL: {match.published_url}")
                if len(path_matches) > 5:
                    print(f"   ... and {len(path_matches) - 5} more")
                partial_found_count += 1
            else:
                print(f"❌ NOT FOUND")
                not_found_count += 1
                
                # Kiểm tra xem có articles nào trong section 'samfund' không
                samfund_count = Article.query.filter_by(
                    section='samfund',
                    language='da'
                ).count()
                print(f"   ℹ️  Total DA articles in 'samfund' section: {samfund_count}")
                
                # Kiểm tra xem URL có format đúng không
                parsed = urlparse(url)
                print(f"   ℹ️  URL parts: path={parsed.path}, slug={slug}")
        
        print(f"\n{'='*80}")
        print(f"📊 Summary:")
        print(f"   - Found (exact/normalized): {found_count}")
        print(f"   - Found (partial): {partial_found_count}")
        print(f"   - Not found: {not_found_count}")
        print(f"{'='*80}")
        
        # Kiểm tra tổng số articles trong DB
        print(f"\n{'='*80}")
        print(f"📊 Database Statistics:")
        print(f"{'='*80}")
        
        total_da = Article.query.filter_by(language='da').count()
        total_da_samfund = Article.query.filter_by(language='da', section='samfund').count()
        total_da_home = Article.query.filter_by(language='da', is_home=True).count()
        
        print(f"   - Total DA articles: {total_da}")
        print(f"   - DA articles in 'samfund': {total_da_samfund}")
        print(f"   - DA articles with is_home=True: {total_da_home}")
        
        # Kiểm tra xem có articles nào có URL pattern tương tự không
        print(f"\n{'='*80}")
        print(f"🔍 Checking for similar URLs in 'samfund' section:")
        print(f"{'='*80}")
        
        samfund_articles = Article.query.filter_by(
            language='da',
            section='samfund'
        ).limit(20).all()
        
        if samfund_articles:
            print(f"   Sample DA articles in 'samfund' section:")
            for article in samfund_articles[:10]:
                print(f"      - ID: {article.id}, URL: {article.published_url[:80] if article.published_url else 'N/A'}")
        else:
            print(f"   ⚠️  No DA articles found in 'samfund' section!")


if __name__ == '__main__':
    check_articles()

