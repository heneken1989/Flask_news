#!/usr/bin/env python3
"""
Script để kiểm tra data trong database
Usage: python3 scripts/check_database.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, Category, CrawlLog, db
from sqlalchemy import func


def main():
    with app.app_context():
        print("=" * 60)
        print("📊 Database Check")
        print("=" * 60)
        print()
        
        # Check Categories
        print("📁 Categories:")
        categories = Category.query.all()
        print(f"   Total: {len(categories)}")
        for cat in categories[:10]:  # Show first 10
            print(f"   - {cat.name} (slug: {cat.slug})")
        if len(categories) > 10:
            print(f"   ... and {len(categories) - 10} more")
        print()
        
        # Check Articles
        print("📰 Articles:")
        total_articles = Article.query.count()
        print(f"   Total: {total_articles}")
        print()
        
        if total_articles > 0:
            # Articles by section
            print("   By Section:")
            sections = db.session.query(Article.section, func.count(Article.id)).group_by(Article.section).all()
            for section, count in sections:
                print(f"   - {section or 'None'}: {count} articles")
            print()
            
            # Recent articles
            print("   Recent Articles (first 10):")
            recent_articles = Article.query.order_by(Article.display_order.asc()).limit(10).all()
            for idx, article in enumerate(recent_articles, 1):
                print(f"   {idx}. [{article.display_order}] {article.title[:60]}")
                print(f"      GUID: {article.element_guid}")
                print(f"      Section: {article.section}")
                print(f"      URL: {article.published_url}")
                print(f"      Paywall: {article.is_paywall}")
                if article.published_date:
                    print(f"      Published: {article.published_date}")
                
                # Show image data
                if article.image_data:
                    print(f"      Images:")
                    if article.image_data.get('desktop_webp'):
                        print(f"        Desktop WebP: {article.image_data['desktop_webp'][:80]}...")
                    if article.image_data.get('desktop_jpeg'):
                        print(f"        Desktop JPEG: {article.image_data['desktop_jpeg'][:80]}...")
                    if article.image_data.get('mobile_webp'):
                        print(f"        Mobile WebP: {article.image_data['mobile_webp'][:80]}...")
                    if article.image_data.get('mobile_jpeg'):
                        print(f"        Mobile JPEG: {article.image_data['mobile_jpeg'][:80]}...")
                    if article.image_data.get('fallback'):
                        print(f"        Fallback: {article.image_data['fallback'][:80]}...")
                else:
                    print(f"      Images: No image data")
                print()
            
            if total_articles > 10:
                print(f"   ... and {total_articles - 10} more articles")
            print()
        
        # Check Crawl Logs
        print("🕷️  Crawl Logs:")
        crawl_logs = CrawlLog.query.order_by(CrawlLog.started_at.desc()).limit(5).all()
        print(f"   Recent crawls: {len(crawl_logs)}")
        for log in crawl_logs:
            print(f"   - {log.section} ({log.crawl_type}): {log.status}")
            print(f"     Crawled: {log.articles_crawled}, Created: {log.articles_created}, Updated: {log.articles_updated}")
            print(f"     Started: {log.started_at}")
            if log.completed_at:
                duration = (log.completed_at - log.started_at).total_seconds()
                print(f"     Duration: {duration:.1f}s")
            print()
        
        print("=" * 60)


if __name__ == '__main__':
    main()

