#!/usr/bin/env python3
"""
Script để crawl và translate articles từ các sections (tags) và home page cho cả 3 ngôn ngữ

Workflow cho mỗi section:
1. Crawl DK từ https://www.sermitsiaq.ag/tag/{section} (hoặc /podcasti cho podcasti)
2. Crawl KL từ https://kl.sermitsiaq.ag/tag/{section} (hoặc /podcasti cho podcasti)
3. Match articles giữa DK và KL
4. Translate DK articles sang EN

Workflow cho home:
1. Crawl DK từ https://www.sermitsiaq.ag/
2. Crawl KL từ https://kl.sermitsiaq.ag/
3. Match articles giữa DK và KL
4. Translate DK articles sang EN

Sections: erhverv, samfund, kultur, sport, podcasti, home
Note: podcasti sử dụng URL /podcasti thay vì /tag/podcasti
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
from scripts.translate_article_urls import translate_url
import argparse
import time

# Section URLs mapping
SECTION_URLS = {
    'erhverv': {
        'da': 'https://www.sermitsiaq.ag/tag/erhverv',
        'kl': 'https://kl.sermitsiaq.ag/tag/erhverv'
    },
    'samfund': {
        'da': 'https://www.sermitsiaq.ag/tag/samfund',
        'kl': 'https://kl.sermitsiaq.ag/tag/samfund'
    },
    'kultur': {
        'da': 'https://www.sermitsiaq.ag/tag/kultur',
        'kl': 'https://kl.sermitsiaq.ag/tag/kultur'
    },
    'sport': {
        'da': 'https://www.sermitsiaq.ag/tag/sport',
        'kl': 'https://kl.sermitsiaq.ag/tag/sport'
    },
    'podcasti': {
        'da': 'https://www.sermitsiaq.ag/podcasti',
        'kl': 'https://kl.sermitsiaq.ag/podcasti'
    }
}


def crawl_danish_section(section_name, max_articles=0):
    """Crawl Danish section"""
    print("\n" + "="*60)
    print(f"🇩🇰 Crawling Danish (DK) section: {section_name}")
    print("="*60)
    
    if section_name not in SECTION_URLS:
        print(f"❌ Invalid section: {section_name}")
        return 0
    
    crawler = SermitsiaqCrawler(
        base_url='https://www.sermitsiaq.ag',
        language='da'
    )
    
    result = crawler.crawl_section(
        section_url=SECTION_URLS[section_name]['da'],
        section_name=section_name,
        max_articles=max_articles,
        headless=True,
        language='da'
    )
    
    if result['success']:
        print(f"✅ Danish crawl completed: {result['articles_created']} articles")
        return result['articles_created']
    else:
        print(f"❌ Danish crawl failed: {result['errors']}")
        return 0


def crawl_greenlandic_section(section_name, max_articles=0):
    """Crawl Greenlandic section"""
    print("\n" + "="*60)
    print(f"🇬🇱 Crawling Greenlandic (KL) section: {section_name}")
    print("="*60)
    
    if section_name not in SECTION_URLS:
        print(f"❌ Invalid section: {section_name}")
        return 0
    
    crawler = SermitsiaqCrawler(
        base_url='https://kl.sermitsiaq.ag',
        language='kl'
    )
    
    result = crawler.crawl_section(
        section_url=SECTION_URLS[section_name]['kl'],
        section_name=section_name,
        max_articles=max_articles,
        headless=True,
        language='kl'
    )
    
    if result['success']:
        print(f"✅ Greenlandic crawl completed: {result['articles_created']} articles")
        return result['articles_created']
    else:
        print(f"❌ Greenlandic crawl failed: {result['errors']}")
        return 0


def match_dk_kl_section_articles(section_name):
    """Match DK và KL articles trong section"""
    print("\n" + "="*60)
    print(f"🔗 Matching DK and KL articles in section: {section_name}")
    print("="*60)
    
    # Get DK articles
    dk_articles = Article.query.filter_by(
        language='da',
        section=section_name,
        is_home=False  # Section articles, not home
    ).all()
    
    # Get KL articles
    kl_articles = Article.query.filter_by(
        language='kl',
        section=section_name,
        is_home=False
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


def translate_dk_section_to_en(section_name):
    """Translate DK section articles to EN"""
    print("\n" + "="*60)
    print(f"🌐 Translating DK section '{section_name}' to EN...")
    print("="*60)
    
    # Get ALL DK articles in section (sẽ tạo temp EN articles)
    dk_articles = Article.query.filter_by(
        language='da',
        section=section_name,
        is_home=False
    ).all()
    
    print(f"   Found {len(dk_articles)} DK articles to translate")
    
    if not dk_articles:
        print("⚠️  No articles to translate")
        return
    
    # Translate articles (skip nếu đã có)
    translated, errors, stats = translate_articles_batch(
        dk_articles,
        target_language='en',
        save_to_db=True,
        delay=0.5
    )
    
    print(f"✅ Translation completed for section: {section_name}")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred during translation")
    
    # Translate URLs cho EN articles mới (skip nếu đã có published_url_en)
    print("\n" + "="*60)
    print(f"🌐 Translating URLs for EN articles in section: {section_name}")
    print("="*60)
    
    en_articles = Article.query.filter_by(
        language='en',
        section=section_name,
        is_home=False
    ).all()
    
    url_translated_count = 0
    url_skipped_count = 0
    url_error_count = 0
    
    for article in en_articles:
        # Skip nếu đã có published_url_en
        if article.published_url_en and article.published_url_en.strip():
            url_skipped_count += 1
            continue
        
        # Skip nếu không có published_url
        if not article.published_url or not article.published_url.strip():
            continue
        
        try:
            # Translate URL
            en_url = translate_url(article.published_url, delay=0.3)
            if en_url:
                article.published_url_en = en_url
                db.session.commit()
                url_translated_count += 1
                if url_translated_count % 10 == 0:
                    print(f"   ✅ Translated {url_translated_count} URLs...")
            else:
                url_error_count += 1
        except Exception as e:
            print(f"   ⚠️  Error translating URL for article {article.id}: {e}")
            url_error_count += 1
            db.session.rollback()
            continue
    
    print(f"✅ URL translation completed:")
    print(f"   - Translated: {url_translated_count}")
    print(f"   - Skipped (already translated): {url_skipped_count}")
    if url_error_count > 0:
        print(f"   - Errors: {url_error_count}")
    
    return translated, errors


def crawl_danish_home(max_articles=0):
    """Crawl Danish home page"""
    print("\n" + "="*60)
    print(f"🇩🇰 Crawling Danish (DK) home page...")
    print("="*60)
    
    crawler = SermitsiaqCrawler(
        base_url='https://www.sermitsiaq.ag',
        language='da'
    )
    
    result = crawler.crawl_home(
        home_url='https://www.sermitsiaq.ag',
        max_articles=max_articles,  # 0 = crawl all articles (no limit)
        headless=True
    )
    
    if result['success']:
        print(f"✅ Danish home crawl completed: {result['articles_created']} articles")
        return result['articles_created']
    else:
        print(f"❌ Danish home crawl failed: {result['errors']}")
        return 0


def crawl_greenlandic_home(max_articles=0):
    """Crawl Greenlandic home page"""
    print("\n" + "="*60)
    print(f"🇬🇱 Crawling Greenlandic (KL) home page...")
    print("="*60)
    
    crawler = SermitsiaqCrawler(
        base_url='https://kl.sermitsiaq.ag',
        language='kl'
    )
    
    result = crawler.crawl_home(
        home_url='https://kl.sermitsiaq.ag',
        max_articles=max_articles,  # 0 = crawl all articles (no limit)
        headless=True
    )
    
    if result['success']:
        print(f"✅ Greenlandic home crawl completed: {result['articles_created']} articles")
        return result['articles_created']
    else:
        print(f"❌ Greenlandic home crawl failed: {result['errors']}")
        return 0


def match_dk_kl_home_articles():
    """Match DK và KL articles trong home"""
    print("\n" + "="*60)
    print(f"🔗 Matching DK and KL home articles")
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


def translate_dk_home_to_en():
    """Translate DK home articles to EN"""
    print("\n" + "="*60)
    print(f"🌐 Translating DK home articles to EN...")
    print("="*60)
    
    # Get ALL DK home articles (sẽ tạo temp EN articles)
    dk_articles = Article.query.filter_by(
        language='da',
        is_home=True
    ).all()
    
    print(f"   Found {len(dk_articles)} DK articles to translate")
    
    if not dk_articles:
        print("⚠️  No articles to translate")
        return
    
    # Translate articles (skip nếu đã có)
    translated, errors, stats = translate_articles_batch(
        dk_articles,
        target_language='en',
        save_to_db=True,
        delay=0.5
    )
    
    print(f"✅ Translation completed for home articles")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred during translation")
    
    # Translate URLs cho EN home articles mới (skip nếu đã có published_url_en)
    print("\n" + "="*60)
    print(f"🌐 Translating URLs for EN home articles")
    print("="*60)
    
    en_articles = Article.query.filter_by(
        language='en',
        is_home=True
    ).all()
    
    url_translated_count = 0
    url_skipped_count = 0
    url_error_count = 0
    
    for article in en_articles:
        # Skip nếu đã có published_url_en
        if article.published_url_en and article.published_url_en.strip():
            url_skipped_count += 1
            continue
        
        # Skip nếu không có published_url
        if not article.published_url or not article.published_url.strip():
            continue
        
        try:
            # Translate URL
            en_url = translate_url(article.published_url, delay=0.3)
            if en_url:
                article.published_url_en = en_url
                db.session.commit()
                url_translated_count += 1
                if url_translated_count % 10 == 0:
                    print(f"   ✅ Translated {url_translated_count} URLs...")
            else:
                url_error_count += 1
        except Exception as e:
            print(f"   ⚠️  Error translating URL for article {article.id}: {e}")
            url_error_count += 1
            db.session.rollback()
            continue
    
    print(f"✅ URL translation completed:")
    print(f"   - Translated: {url_translated_count}")
    print(f"   - Skipped (already translated): {url_skipped_count}")
    if url_error_count > 0:
        print(f"   - Errors: {url_error_count}")
    
    return translated, errors


def process_home(max_articles=0, skip_crawl=False):
    """Process home page: crawl, match, translate"""
    print("\n" + "="*80)
    print(f"🏠 PROCESSING HOME PAGE")
    print("="*80)
    
    if not skip_crawl:
        crawl_danish_home(max_articles)
        crawl_greenlandic_home(max_articles)
    
    match_dk_kl_home_articles()
    translate_dk_home_to_en()
    
    # Print summary
    dk_count = Article.query.filter_by(language='da', is_home=True).count()
    kl_count = Article.query.filter_by(language='kl', is_home=True).count()
    en_count = Article.query.filter_by(language='en', is_home=True).count()
    
    print(f"\n📊 Summary for home:")
    print(f"   - Danish (DK): {dk_count} articles")
    print(f"   - Greenlandic (KL): {kl_count} articles")
    print(f"   - English (EN): {en_count} articles")


def process_section(section_name, max_articles=0, skip_crawl=False):
    """Process một section: crawl, match, translate"""
    print("\n" + "="*80)
    print(f"📰 PROCESSING SECTION: {section_name.upper()}")
    print("="*80)
    
    if not skip_crawl:
        crawl_danish_section(section_name, max_articles)
        crawl_greenlandic_section(section_name, max_articles)
    
    match_dk_kl_section_articles(section_name)
    translate_dk_section_to_en(section_name)
    
    # Print summary
    dk_count = Article.query.filter_by(language='da', section=section_name, is_home=False).count()
    kl_count = Article.query.filter_by(language='kl', section=section_name, is_home=False).count()
    en_count = Article.query.filter_by(language='en', section=section_name, is_home=False).count()
    
    print(f"\n📊 Summary for {section_name}:")
    print(f"   - Danish (DK): {dk_count} articles")
    print(f"   - Greenlandic (KL): {kl_count} articles")
    print(f"   - English (EN): {en_count} articles")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Crawl and translate sections and home for multi-language')
    parser.add_argument('--section', choices=['erhverv', 'samfund', 'kultur', 'sport', 'podcasti', 'home', 'all'],
                       default='all', help='Section to process (default: all). Use "home" for home page.')
    parser.add_argument('--max-articles', type=int, default=0,
                       help='Maximum articles per section (default: 0 = crawl all). Use 0 to crawl all articles without limit.')
    parser.add_argument('--skip-crawl', action='store_true',
                       help='Skip crawling, only match and translate')
    args = parser.parse_args()
    
    with app.app_context():
        # Handle home separately
        if args.section == 'home':
            try:
                process_home(max_articles=args.max_articles, skip_crawl=args.skip_crawl)
            except Exception as e:
                print(f"❌ Error processing home: {e}")
                import traceback
                traceback.print_exc()
        elif args.section == 'all':
            # Process all sections first
            sections = ['erhverv', 'samfund', 'kultur', 'sport', 'podcasti']
            for section in sections:
                try:
                    process_section(section, max_articles=args.max_articles, skip_crawl=args.skip_crawl)
                except Exception as e:
                    print(f"❌ Error processing section {section}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Then process home last
            try:
                process_home(max_articles=args.max_articles, skip_crawl=args.skip_crawl)
            except Exception as e:
                print(f"❌ Error processing home: {e}")
                import traceback
                traceback.print_exc()
        else:
            # Process single section
            sections = [args.section]
            for section in sections:
                try:
                    process_section(section, max_articles=args.max_articles, skip_crawl=args.skip_crawl)
                except Exception as e:
                    print(f"❌ Error processing section {section}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        print("\n" + "="*80)
        print("✅ All processing completed!")
        print("="*80)
        
        # Print overall summary
        print(f"\n📊 Overall Summary:")
        
        # Home summary
        dk_home = Article.query.filter_by(language='da', is_home=True).count()
        kl_home = Article.query.filter_by(language='kl', is_home=True).count()
        en_home = Article.query.filter_by(language='en', is_home=True).count()
        print(f"   HOME: DK={dk_home}, KL={kl_home}, EN={en_home}")
        
        # Sections summary
        sections = ['erhverv', 'samfund', 'kultur', 'sport', 'podcasti']
        for section in sections:
            dk = Article.query.filter_by(language='da', section=section, is_home=False).count()
            kl = Article.query.filter_by(language='kl', section=section, is_home=False).count()
            en = Article.query.filter_by(language='en', section=section, is_home=False).count()
            print(f"   {section.upper()}: DK={dk}, KL={kl}, EN={en}")


if __name__ == '__main__':
    main()

