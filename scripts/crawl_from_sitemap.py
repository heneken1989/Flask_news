#!/usr/bin/env python3
"""
Script để crawl articles từ sitemap.xml của sermitsiaq.ag
Theo yêu cầu khách hàng: bắt đầu từ sitemap.xml thay vì crawl thủ công

Usage:
    python scripts/crawl_from_sitemap.py
    python scripts/crawl_from_sitemap.py --sitemap-url https://www.sermitsiaq.ag/sitemap.xml
    python scripts/crawl_from_sitemap.py --language da
    python scripts/crawl_from_sitemap.py --limit 100
"""
import sys
import os
import argparse
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
from datetime import datetime
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from services.article_detail_parser import ArticleDetailParser
from services.crawl_service import SermitsiaqCrawler
import time


def parse_sitemap(sitemap_url: str) -> list:
    """
    Parse sitemap.xml và trả về danh sách URLs
    
    Args:
        sitemap_url: URL của sitemap.xml
    
    Returns:
        list: Danh sách URLs từ sitemap
    """
    print(f"📄 Fetching sitemap: {sitemap_url}")
    
    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Namespace cho sitemap
        namespaces = {
            'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }
        
        urls = []
        
        # Tìm tất cả <url> elements
        for url_elem in root.findall('.//sitemap:url', namespaces):
            loc_elem = url_elem.find('sitemap:loc', namespaces)
            if loc_elem is not None:
                url = loc_elem.text.strip()
                
                # Lấy lastmod nếu có
                lastmod_elem = url_elem.find('sitemap:lastmod', namespaces)
                lastmod = None
                if lastmod_elem is not None and lastmod_elem.text:
                    try:
                        lastmod = datetime.fromisoformat(lastmod_elem.text.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Lấy changefreq nếu có
                changefreq_elem = url_elem.find('sitemap:changefreq', namespaces)
                changefreq = changefreq_elem.text if changefreq_elem is not None else None
                
                # Lấy priority nếu có
                priority_elem = url_elem.find('sitemap:priority', namespaces)
                priority = float(priority_elem.text) if priority_elem is not None and priority_elem.text else None
                
                urls.append({
                    'url': url,
                    'lastmod': lastmod,
                    'changefreq': changefreq,
                    'priority': priority
                })
        
        # Nếu là sitemap index (chứa nhiều sitemaps), parse từng sitemap
        sitemapindex = root.findall('.//sitemap:sitemap', namespaces)
        if sitemapindex:
            print(f"📋 Found sitemap index with {len(sitemapindex)} sitemaps")
            all_urls = []
            for sitemap_elem in sitemapindex:
                sitemap_loc = sitemap_elem.find('sitemap:loc', namespaces)
                if sitemap_loc is not None:
                    sub_sitemap_url = sitemap_loc.text.strip()
                    print(f"   📄 Parsing sub-sitemap: {sub_sitemap_url}")
                    sub_urls = parse_sitemap(sub_sitemap_url)
                    all_urls.extend(sub_urls)
            return all_urls
        
        print(f"✅ Found {len(urls)} URLs in sitemap")
        return urls
        
    except Exception as e:
        print(f"❌ Error parsing sitemap: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_section_from_url(url: str) -> str:
    """
    Extract section từ URL
    Ví dụ: https://www.sermitsiaq.ag/samfund/article-title/1234567 -> 'samfund'
    """
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Sections có thể có
        sections = ['erhverv', 'samfund', 'kultur', 'sport', 'job', 'podcasti', 'nuuk']
        
        for part in path_parts:
            if part in sections:
                return part
        
        # Nếu không tìm thấy, trả về 'home'
        return 'home'
    except:
        return 'home'


def crawl_urls_from_sitemap(sitemap_url: str, language: str = 'da', limit: int = None, headless: bool = True):
    """
    Crawl articles từ URLs trong sitemap.xml
    
    Args:
        sitemap_url: URL của sitemap.xml
        language: Language code ('da', 'kl', 'en')
        limit: Giới hạn số lượng URLs để crawl (None = không giới hạn)
        headless: Run browser in headless mode
    """
    print(f"\n{'='*60}")
    print(f"🗺️  Crawling from Sitemap")
    print(f"{'='*60}")
    print(f"   Sitemap URL: {sitemap_url}")
    print(f"   Language: {language}")
    print(f"   Limit: {limit if limit else 'No limit'}")
    print(f"{'='*60}\n")
    
    # Parse sitemap
    urls = parse_sitemap(sitemap_url)
    
    if not urls:
        print("❌ No URLs found in sitemap")
        return
    
    # Filter URLs nếu cần
    if language == 'da':
        urls = [u for u in urls if 'www.sermitsiaq.ag' in u['url'] and 'kl.sermitsiaq.ag' not in u['url']]
    elif language == 'kl':
        urls = [u for u in urls if 'kl.sermitsiaq.ag' in u['url']]
    
    # Limit nếu có
    if limit:
        urls = urls[:limit]
    
    print(f"📊 Filtered to {len(urls)} URLs for language '{language}'")
    
    # Khởi tạo crawler
    crawler = SermitsiaqCrawler(
        base_url='https://www.sermitsiaq.ag' if language == 'da' else 'https://kl.sermitsiaq.ag',
        language=language
    )
    
    try:
        crawler.start_browser(headless=headless)
        
        articles_created = 0
        articles_updated = 0
        errors = []
        
        for idx, url_data in enumerate(urls, 1):
            url = url_data['url']
            
            print(f"\n[{idx}/{len(urls)}] Processing: {url[:70]}...")
            
            try:
                # Extract section từ URL
                section = extract_section_from_url(url)
                
                # Crawl article detail
                result = ArticleDetailParser.crawl_and_save_article_detail(
                    url=url,
                    language=language,
                    crawler_instance=crawler
                )
                
                if result and result.get('success'):
                    # Tìm hoặc tạo Article record
                    article = Article.query.filter_by(published_url=url, language=language).first()
                    
                    if not article:
                        # Tạo Article mới từ article_detail
                        article_detail = result.get('article_detail')
                        if article_detail:
                            # Extract title từ content_blocks
                            title = url.split('/')[-2] if '/' in url else url.split('/')[-1]
                            if article_detail.content_blocks:
                                for block in article_detail.content_blocks:
                                    if block.get('type') == 'heading' and block.get('level') == 1:
                                        title = block.get('text', title)
                                        break
                            
                            # Extract slug từ URL
                            slug = url.split('/')[-2] if '/' in url else url.split('/')[-1]
                            
                            article = Article(
                                title=title,
                                slug=slug,
                                published_url=url,
                                section=section,
                                language=language,
                                element_guid=article_detail.element_guid,
                                published_date=url_data.get('lastmod')
                            )
                            db.session.add(article)
                            db.session.commit()
                            articles_created += 1
                            print(f"   ✅ Created article: {title[:50]}...")
                        else:
                            print(f"   ⚠️  No article_detail returned")
                    else:
                        # Update article nếu cần
                        if url_data.get('lastmod') and article.published_date != url_data['lastmod']:
                            article.published_date = url_data['lastmod']
                            db.session.commit()
                            articles_updated += 1
                            print(f"   ✅ Updated article")
                        else:
                            print(f"   ⏭️  Article already exists")
                else:
                    error_msg = result.get('error', 'Unknown error') if result else 'No result'
                    errors.append({'url': url, 'error': error_msg})
                    print(f"   ❌ Error: {error_msg}")
                
                # Delay giữa các requests
                time.sleep(2)
                
            except Exception as e:
                error_msg = str(e)
                errors.append({'url': url, 'error': error_msg})
                print(f"   ❌ Error: {error_msg}")
                import traceback
                traceback.print_exc()
                continue
        
        # Tổng kết
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"   Total URLs processed: {len(urls)}")
        print(f"   Articles created: {articles_created}")
        print(f"   Articles updated: {articles_updated}")
        print(f"   Errors: {len(errors)}")
        if errors:
            print(f"\n   Error details:")
            for err in errors[:10]:  # Show first 10 errors
                print(f"      - {err['url'][:60]}...: {err['error']}")
        print(f"{'='*60}")
        
    finally:
        crawler.close_browser()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Crawl articles from sitemap.xml')
    parser.add_argument('--sitemap-url', type=str, 
                       default='https://www.sermitsiaq.ag/sitemap.xml',
                       help='URL of sitemap.xml (default: https://www.sermitsiaq.ag/sitemap.xml)')
    parser.add_argument('--language', type=str, default='da', choices=['da', 'kl', 'en'],
                       help='Language to crawl (default: da)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of URLs to crawl (default: no limit)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                       help='Run browser in visible mode')
    
    args = parser.parse_args()
    
    with app.app_context():
        crawl_urls_from_sitemap(
            sitemap_url=args.sitemap_url,
            language=args.language,
            limit=args.limit,
            headless=args.headless
        )

