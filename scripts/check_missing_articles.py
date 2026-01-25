#!/usr/bin/env python3
"""
Script để kiểm tra các articles có thật sự không có trong DB không
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article

# URLs từ terminal output
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

def check_articles():
    with app.app_context():
        print("="*80)
        print("🔍 Checking articles in database...")
        print("="*80)
        
        found_count = 0
        not_found_count = 0
        
        for url in urls_to_check:
            # Tìm exact match
            exact_match = Article.query.filter_by(published_url=url).first()
            
            # Tìm partial match (URL bắt đầu với)
            partial_matches = Article.query.filter(
                Article.published_url.like(f"{url}%")
            ).all()
            
            if exact_match:
                print(f"\n✅ FOUND (exact): {url[:60]}...")
                print(f"   ID: {exact_match.id}, Language: {exact_match.language}, Section: {exact_match.section}, is_home: {exact_match.is_home}")
                found_count += 1
            elif partial_matches:
                print(f"\n✅ FOUND (partial): {url[:60]}...")
                for match in partial_matches:
                    print(f"   ID: {match.id}, Language: {match.language}, Section: {match.section}, is_home: {match.is_home}")
                    print(f"   Full URL: {match.published_url}")
                found_count += 1
            else:
                # Tìm bằng slug hoặc title
                slug = url.split('/')[-1] if '/' in url else url
                slug_matches = Article.query.filter(
                    Article.published_url.like(f"%{slug}%")
                ).all()
                
                if slug_matches:
                    print(f"\n⚠️  FOUND (by slug): {url[:60]}...")
                    for match in slug_matches:
                        print(f"   ID: {match.id}, Language: {match.language}, Section: {match.section}, is_home: {match.is_home}")
                        print(f"   Full URL: {match.published_url}")
                    found_count += 1
                else:
                    print(f"\n❌ NOT FOUND: {url[:60]}...")
                    not_found_count += 1
        
        print("\n" + "="*80)
        print(f"📊 Summary:")
        print(f"   - Found: {found_count}")
        print(f"   - Not found: {not_found_count}")
        print("="*80)
        
        # Kiểm tra thêm: Có bao nhiêu articles trong SAMFUND section
        print("\n" + "="*80)
        print("📊 SAMFUND Section Statistics:")
        print("="*80)
        
        da_count = Article.query.filter_by(language='da', section='samfund', is_home=False).count()
        kl_count = Article.query.filter_by(language='kl', section='samfund', is_home=False).count()
        en_count = Article.query.filter_by(language='en', section='samfund', is_home=False).count()
        
        print(f"   - Danish (DA): {da_count}")
        print(f"   - Greenlandic (KL): {kl_count}")
        print(f"   - English (EN): {en_count}")
        
        # Kiểm tra duplicate EN articles
        print("\n" + "="*80)
        print("🔍 Checking for duplicate EN articles in SAMFUND:")
        print("="*80)
        
        en_articles = Article.query.filter_by(
            language='en',
            section='samfund',
            is_home=False
        ).all()
        
        # Group by published_url
        url_to_articles = {}
        for article in en_articles:
            if article.published_url:
                if article.published_url not in url_to_articles:
                    url_to_articles[article.published_url] = []
                url_to_articles[article.published_url].append(article)
        
        duplicates = {url: articles for url, articles in url_to_articles.items() if len(articles) > 1}
        
        if duplicates:
            print(f"   ⚠️  Found {len(duplicates)} duplicate URLs:")
            for url, articles in duplicates.items():
                print(f"\n   URL: {url[:60]}... ({len(articles)} articles)")
                for article in sorted(articles, key=lambda x: x.id):
                    print(f"      - ID: {article.id}, created_at: {article.created_at}")
        else:
            print("   ✅ No duplicate EN articles found")
        
        # Kiểm tra EN articles không có DK version
        print("\n" + "="*80)
        print("🔍 Checking EN articles without DK version in SAMFUND:")
        print("="*80)
        
        en_without_dk = []
        en_from_kl = []
        en_orphan = []
        
        for en_article in en_articles:
            if en_article.published_url:
                dk_version = Article.query.filter_by(
                    published_url=en_article.published_url,
                    language='da',
                    section='samfund',
                    is_home=False
                ).first()
                
                if not dk_version:
                    en_without_dk.append(en_article)
                    
                    # Kiểm tra xem có KL version không
                    kl_version = Article.query.filter_by(
                        published_url=en_article.published_url,
                        language='kl',
                        section='samfund',
                        is_home=False
                    ).first()
                    
                    if kl_version:
                        en_from_kl.append((en_article, kl_version))
                    else:
                        en_orphan.append(en_article)
        
        if en_without_dk:
            print(f"   ⚠️  Found {len(en_without_dk)} EN articles without DK version:")
            print(f"      - From KL: {len(en_from_kl)}")
            print(f"      - Orphan (no DK, no KL): {len(en_orphan)}")
            
            if en_from_kl:
                print(f"\n   📋 EN articles created from KL (first 5):")
                for en_article, kl_article in en_from_kl[:5]:
                    print(f"      - EN ID: {en_article.id}, KL ID: {kl_article.id}")
                    print(f"        URL: {en_article.published_url[:60]}...")
            
            if en_orphan:
                print(f"\n   ⚠️  Orphan EN articles (no DK, no KL) (first 10):")
                for article in en_orphan[:10]:
                    canonical_article = None
                    if article.canonical_id:
                        canonical_article = Article.query.get(article.canonical_id)
                    
                    print(f"      - EN ID: {article.id}, URL: {article.published_url}")
                    print(f"        Created: {article.created_at}, Canonical ID: {article.canonical_id}")
                    if canonical_article:
                        print(f"        Canonical article: ID={canonical_article.id}, Language={canonical_article.language}, Section={canonical_article.section}, is_home={canonical_article.is_home}")
                        print(f"        Canonical URL: {canonical_article.published_url}")
                        
                        # So sánh chi tiết
                        if canonical_article.published_url != article.published_url:
                            print(f"        ⚠️  URL mismatch!")
                            print(f"           EN:  '{article.published_url}'")
                            print(f"           DA:  '{canonical_article.published_url}'")
                        else:
                            print(f"        ✅ URLs match exactly")
                            
                            # Kiểm tra tại sao query không tìm thấy
                            dk_found = Article.query.filter_by(
                                published_url=article.published_url,
                                language='da',
                                section='samfund',
                                is_home=False
                            ).first()
                            
                            if dk_found:
                                print(f"        ✅ Query FOUND DA article: ID={dk_found.id}")
                            else:
                                print(f"        ❌ Query NOT FOUND DA article with same URL!")
                                # Thử query không filter section
                                dk_any = Article.query.filter_by(
                                    published_url=article.published_url,
                                    language='da'
                                ).first()
                                if dk_any:
                                    print(f"        ⚠️  But found DA article with different section: section={dk_any.section}, is_home={dk_any.is_home}")
                    else:
                        print(f"        ❌ Canonical article not found (ID {article.canonical_id} does not exist)")
        else:
            print("   ✅ All EN articles have DK versions")
        
        # Kiểm tra xem có EN articles nào được tạo từ KL nhưng không có DK tương ứng
        print("\n" + "="*80)
        print("🔍 Checking if EN articles match KL articles (but not DK):")
        print("="*80)
        
        kl_articles = Article.query.filter_by(
            language='kl',
            section='samfund',
            is_home=False
        ).all()
        
        kl_with_en_but_no_dk = []
        for kl_article in kl_articles:
            if kl_article.published_url:
                # Check if has EN version
                en_version = Article.query.filter_by(
                    published_url=kl_article.published_url,
                    language='en',
                    section='samfund',
                    is_home=False
                ).first()
                
                # Check if has DK version
                dk_version = Article.query.filter_by(
                    published_url=kl_article.published_url,
                    language='da',
                    section='samfund',
                    is_home=False
                ).first()
                
                if en_version and not dk_version:
                    kl_with_en_but_no_dk.append((kl_article, en_version))
        
        if kl_with_en_but_no_dk:
            print(f"   ⚠️  Found {len(kl_with_en_but_no_dk)} KL articles with EN version but no DK version:")
            for kl_article, en_article in kl_with_en_but_no_dk[:5]:
                print(f"      - KL ID: {kl_article.id}, EN ID: {en_article.id}")
                print(f"        URL: {kl_article.published_url[:60]}...")
        else:
            print("   ✅ All KL articles with EN version also have DK version")


if __name__ == '__main__':
    check_articles()

