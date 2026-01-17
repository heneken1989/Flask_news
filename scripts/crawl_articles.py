#!/usr/bin/env python3
"""
Script để crawl articles từ sermitsiaq.ag
Usage: python3 scripts/crawl_articles.py [section] [--max-articles N] [--headless]
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from services.crawl_service import SermitsiaqCrawler, crawl_erhverv_section
import argparse


def main():
    parser = argparse.ArgumentParser(description='Crawl articles from sermitsiaq.ag')
    parser.add_argument('section', nargs='?', default='all', 
                       help='Section to crawl (erhverv, samfund, kultur, sport, job, home, all). Default: all')
    parser.add_argument('--max-articles', type=int, default=50,
                       help='Maximum number of articles to crawl per section (default: 50). Use 0 or >= 1000 to crawl all articles (for home page)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                       help='Run browser in visible mode')
    parser.add_argument('--url', type=str, default=None,
                       help='Custom URL to crawl (overrides section)')
    parser.add_argument('--delay', type=int, default=5,
                       help='Delay between sections when crawling all (seconds, default: 5)')
    
    args = parser.parse_args()
    
    # Section URLs
    section_urls = {
        'erhverv': 'https://www.sermitsiaq.ag/tag/erhverv',
        'samfund': 'https://www.sermitsiaq.ag/tag/samfund',
        'kultur': 'https://www.sermitsiaq.ag/tag/kultur',
        'sport': 'https://www.sermitsiaq.ag/tag/sport',
        'job': 'https://www.sermitsiaq.ag/tag/job',
        'home': 'https://www.sermitsiaq.ag',  # Home page
    }
    
    # Determine sections to crawl
    if args.url:
        # Custom URL - crawl single section
        sections_to_crawl = [(args.section, args.url)]
    elif args.section == 'all':
        # Crawl all sections (including home)
        sections_to_crawl = [(name, url) for name, url in section_urls.items()]
    elif args.section == 'home':
        # Crawl home page only
        sections_to_crawl = [('home', section_urls['home'])]
    elif args.section in section_urls:
        # Single section
        sections_to_crawl = [(args.section, section_urls[args.section])]
    else:
        print(f"❌ Unknown section: {args.section}")
        print(f"   Available sections: {', '.join(section_urls.keys())}, all")
        sys.exit(1)
    
    print("=" * 60)
    print("🕷️  Sermitsiaq Article Crawler")
    print("=" * 60)
    print(f"📰 Sections to crawl: {len(sections_to_crawl)}")
    if len(sections_to_crawl) > 1:
        print(f"   Sections: {', '.join([s[0] for s in sections_to_crawl])}")
    else:
        print(f"   Section: {sections_to_crawl[0][0]}")
    
    # Default: home page crawl tất cả articles
    if len(sections_to_crawl) == 1 and sections_to_crawl[0][0] == 'home':
        print(f"📊 Max articles: ALL (default for home page)")
    else:
        print(f"📊 Max articles per section: {args.max_articles}")
    
    print(f"👁️  Headless: {args.headless}")
    if len(sections_to_crawl) > 1:
        print(f"⏱️  Delay between sections: {args.delay}s")
    print("=" * 60)
    print()
    
    # Run crawl
    crawler = SermitsiaqCrawler()
    
    all_results = []
    total_articles_crawled = 0
    total_articles_created = 0
    total_articles_updated = 0
    all_errors = []
    
    try:
        for idx, (section_name, section_url) in enumerate(sections_to_crawl, 1):
            if len(sections_to_crawl) > 1:
                print(f"\n{'=' * 60}")
                print(f"📰 Crawling section {idx}/{len(sections_to_crawl)}: {section_name}")
                print(f"{'=' * 60}")
            
            # Use crawl_home for home page, crawl_section for others
            if section_name == 'home':
                # Default: crawl tất cả articles từ home (max_articles = 0)
                # Chỉ dùng max_articles từ args nếu user chỉ định rõ ràng (không phải default 50)
                # Kiểm tra xem có phải default value không bằng cách check sys.argv
                import sys
                user_specified_max = '--max-articles' in ' '.join(sys.argv)
                
                if user_specified_max:
                    # User đã chỉ định max-articles
                    home_max_articles = args.max_articles if args.max_articles > 0 else 0
                    if home_max_articles == 0:
                        print(f"📰 Crawling ALL articles from home page (no limit)")
                    else:
                        print(f"📰 Crawling up to {home_max_articles} articles from home page")
                else:
                    # Default: crawl tất cả
                    home_max_articles = 0
                    print(f"📰 Crawling ALL articles from home page (default: no limit)")
                
                result = crawler.crawl_home(
                    home_url=section_url,
                    max_articles=home_max_articles,
                    headless=args.headless
                )
            else:
                result = crawler.crawl_section(
                    section_url=section_url,
                    section_name=section_name,
                    max_articles=args.max_articles,
                    headless=args.headless
                )
            
            all_results.append({
                'section': section_name,
                'result': result
            })
            
            total_articles_crawled += result['articles_crawled']
            total_articles_created += result['articles_created']
            total_articles_updated += result['articles_updated']
            all_errors.extend(result['errors'])
            
            # Print section result
            print(f"\n✅ Section '{section_name}' completed:")
            print(f"   📰 Articles crawled: {result['articles_crawled']}")
            print(f"   ➕ Articles created: {result['articles_created']}")
            print(f"   🔄 Articles updated: {result['articles_updated']}")
            if result['errors']:
                print(f"   ⚠️  Errors: {len(result['errors'])}")
            
            # Delay between sections (except for last one)
            if idx < len(sections_to_crawl) and args.delay > 0:
                print(f"\n⏱️  Waiting {args.delay}s before next section...")
                import time
                time.sleep(args.delay)
        
        # Print summary
        print()
        print("=" * 60)
        print("📊 Crawl Summary:")
        print("=" * 60)
        print(f"📰 Total sections crawled: {len(sections_to_crawl)}")
        print(f"📰 Total articles crawled: {total_articles_crawled}")
        print(f"➕ Total articles created: {total_articles_created}")
        print(f"🔄 Total articles updated: {total_articles_updated}")
        
        if all_errors:
            print(f"⚠️  Total errors: {len(all_errors)}")
            print("\n   First 10 errors:")
            for error in all_errors[:10]:
                print(f"   - {error}")
        
        print("\n📋 Results by section:")
        for item in all_results:
            section = item['section']
            result = item['result']
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {section}: {result['articles_created']} created, {result['articles_updated']} updated")
        
        print("=" * 60)
        
        # Exit with success if at least one section succeeded
        if any(r['result']['success'] for r in all_results):
            sys.exit(0)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Crawl interrupted by user")
        print(f"   Completed {len(all_results)}/{len(sections_to_crawl)} sections")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Crawl failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    with app.app_context():
        main()

