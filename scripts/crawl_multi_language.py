#!/usr/bin/env python3
"""
Script để crawl articles từ cả 2 ngôn ngữ (DK và KL) và translate DK -> EN

Workflow:
1. Crawl DK từ https://www.sermitsiaq.ag/
2. Crawl KL từ https://kl.sermitsiaq.ag/
3. Match articles giữa DK và KL
4. Translate DK articles sang EN
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from services.crawl_service import SermitsiaqCrawler
from services.article_matcher import match_and_link_articles
from services.translation_service import translate_articles_batch
import argparse


def crawl_danish_home():
    """Crawl Danish home page"""
    print("\n" + "="*60)
    print("🇩🇰 STEP 1: Crawling Danish (DK) home page...")
    print("="*60)
    
    crawler = SermitsiaqCrawler(
        base_url='https://www.sermitsiaq.ag',
        language='da'
    )
    
    result = crawler.crawl_home(
        home_url='https://www.sermitsiaq.ag',
        max_articles=0,  # 0 = crawl all articles (no limit)
        headless=True
    )
    
    if result['success']:
        print(f"✅ Danish crawl completed: {result['articles_created']} articles")
        return result['articles_created']
    else:
        print(f"❌ Danish crawl failed: {result['errors']}")
        return 0


def crawl_greenlandic_home():
    """Crawl Greenlandic home page"""
    print("\n" + "="*60)
    print("🇬🇱 STEP 2: Crawling Greenlandic (KL) home page...")
    print("="*60)
    
    crawler = SermitsiaqCrawler(
        base_url='https://kl.sermitsiaq.ag',
        language='kl'
    )
    
    result = crawler.crawl_home(
        home_url='https://kl.sermitsiaq.ag',
        max_articles=0,  # 0 = crawl all articles (no limit)
        headless=True
    )
    
    if result['success']:
        print(f"✅ Greenlandic crawl completed: {result['articles_created']} articles")
        return result['articles_created']
    else:
        print(f"❌ Greenlandic crawl failed: {result['errors']}")
        return 0


def match_dk_kl_articles():
    """Match DK và KL articles"""
    print("\n" + "="*60)
    print("🔗 STEP 3: Matching DK and KL articles...")
    print("="*60)
    
    # Get DK articles
    dk_articles = Article.query.filter_by(
        language='da',
        is_home=True
    ).all()
    
    # Get KL articles
    kl_articles = Article.query.filter_by(
        language='kl',
        is_home=True
    ).all()
    
    print(f"   Found {len(dk_articles)} DK articles")
    print(f"   Found {len(kl_articles)} KL articles")
    
    if not dk_articles or not kl_articles:
        print("⚠️  No articles to match")
        return
    
    # Match and link
    stats = match_and_link_articles(dk_articles, kl_articles)
    
    print(f"✅ Matching completed: {stats['matched_count']} articles matched")
    return stats


def translate_dk_to_en():
    """Translate DK articles to EN"""
    print("\n" + "="*60)
    print("🌐 STEP 4: Translating DK articles to EN...")
    print("="*60)
    
    # Get ALL DK articles (sẽ tạo temp EN articles, sau đó replace old ones)
    dk_articles = Article.query.filter_by(
        language='da',
        is_home=True
    ).all()
    
    print(f"   Found {len(dk_articles)} DK articles to translate")
    
    if not dk_articles:
        print("⚠️  No articles to translate")
        return
    
    # Translate (tạo temp articles với is_temp=True)
    translated, errors, stats = translate_articles_batch(
        dk_articles,
        target_language='en',
        save_to_db=True,
        delay=0.5  # Delay 0.5s giữa các lần translate để tránh rate limit
    )
    
    print(f"✅ Translation completed: {len(translated)} articles translated (temp)")
    
    # Sau khi translate xong, thay thế old EN articles bằng temp articles
    print("\n" + "="*60)
    print("🔄 Replacing old EN articles with new translations...")
    print("="*60)
    
    # Đếm old EN articles (không phải temp)
    old_en_count = Article.query.filter_by(
        language='en',
        is_home=True,
        is_temp=False
    ).count()
    
    print(f"   Found {old_en_count} old EN articles to remove")
    
    # Xóa old EN articles (không phải temp)
    if old_en_count > 0:
        deleted = Article.query.filter_by(
            language='en',
            is_home=True,
            is_temp=False
        ).delete()
        db.session.commit()
        print(f"   ✅ Deleted {deleted} old EN articles")
    
    # Đổi temp articles thành bình thường (is_temp=False)
    temp_count = Article.query.filter_by(
        language='en',
        is_home=True,
        is_temp=True
    ).count()
    
    if temp_count > 0:
        updated = Article.query.filter_by(
            language='en',
            is_home=True,
            is_temp=True
        ).update({'is_temp': False})
        db.session.commit()
        print(f"   ✅ Activated {updated} new EN articles (removed temp flag)")
    
    print(f"\n✅ Replacement completed!")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred during translation")
    
    return translated, errors


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Crawl multi-language articles')
    parser.add_argument('--step', choices=['1', '2', '3', '4', 'all'], default='all',
                       help='Which step to run (1=DK crawl, 2=KL crawl, 3=Match, 4=Translate, all=all steps)')
    parser.add_argument('--skip-crawl', action='store_true', help='Skip crawling, only match and translate')
    args = parser.parse_args()
    
    with app.app_context():
        if args.step == 'all':
            if not args.skip_crawl:
                crawl_danish_home()
                crawl_greenlandic_home()
            match_dk_kl_articles()
            translate_dk_to_en()
        elif args.step == '1':
            crawl_danish_home()
        elif args.step == '2':
            crawl_greenlandic_home()
        elif args.step == '3':
            match_dk_kl_articles()
        elif args.step == '4':
            translate_dk_to_en()
        
        print("\n" + "="*60)
        print("✅ Multi-language crawl workflow completed!")
        print("="*60)
        
        # Print summary
        dk_count = Article.query.filter_by(language='da', is_home=True).count()
        kl_count = Article.query.filter_by(language='kl', is_home=True).count()
        en_count = Article.query.filter_by(language='en', is_home=True).count()
        
        print(f"\n📊 Summary:")
        print(f"   - Danish (DK): {dk_count} articles")
        print(f"   - Greenlandic (KL): {kl_count} articles")
        print(f"   - English (EN): {en_count} articles")


if __name__ == '__main__':
    main()

