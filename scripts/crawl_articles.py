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
    parser.add_argument('section', nargs='?', default='erhverv', 
                       help='Section to crawl (erhverv, samfund, kultur, sport, job)')
    parser.add_argument('--max-articles', type=int, default=50,
                       help='Maximum number of articles to crawl (default: 50)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                       help='Run browser in visible mode')
    parser.add_argument('--url', type=str, default=None,
                       help='Custom URL to crawl (overrides section)')
    
    args = parser.parse_args()
    
    # Section URLs
    section_urls = {
        'erhverv': 'https://www.sermitsiaq.ag/tag/erhverv',
        'samfund': 'https://www.sermitsiaq.ag/tag/samfund',
        'kultur': 'https://www.sermitsiaq.ag/tag/kultur',
        'sport': 'https://www.sermitsiaq.ag/tag/sport',
        'job': 'https://www.sermitsiaq.ag/tag/job',
    }
    
    # Determine URL
    if args.url:
        section_url = args.url
        section_name = args.section
    elif args.section in section_urls:
        section_url = section_urls[args.section]
        section_name = args.section
    else:
        print(f"❌ Unknown section: {args.section}")
        print(f"   Available sections: {', '.join(section_urls.keys())}")
        sys.exit(1)
    
    print("=" * 60)
    print("🕷️  Sermitsiaq Article Crawler")
    print("=" * 60)
    print(f"📰 Section: {section_name}")
    print(f"🔗 URL: {section_url}")
    print(f"📊 Max articles: {args.max_articles}")
    print(f"👁️  Headless: {args.headless}")
    print("=" * 60)
    print()
    
    # Run crawl
    crawler = SermitsiaqCrawler()
    
    try:
        result = crawler.crawl_section(
            section_url=section_url,
            section_name=section_name,
            max_articles=args.max_articles,
            headless=args.headless
        )
        
        print()
        print("=" * 60)
        print("📊 Crawl Results:")
        print("=" * 60)
        print(f"✅ Success: {result['success']}")
        print(f"📰 Articles crawled: {result['articles_crawled']}")
        print(f"➕ Articles created: {result['articles_created']}")
        print(f"🔄 Articles updated: {result['articles_updated']}")
        if result['errors']:
            print(f"⚠️  Errors: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
        print("=" * 60)
        
        if result['success']:
            sys.exit(0)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Crawl interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Crawl failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    with app.app_context():
        main()

