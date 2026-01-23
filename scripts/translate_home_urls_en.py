#!/usr/bin/env python3
"""
Script để chỉ translate URLs cho EN home articles
Chỉ chạy bước "Translating URLs for EN home articles" mà không chạy các bước khác
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from scripts.translate_article_urls import translate_url
import argparse


def translate_home_urls_en(force=False, delay=0.3):
    """
    Translate URLs cho EN home articles
    
    Args:
        force: Nếu True, dịch lại cả các articles đã có published_url_en
        delay: Delay giữa các lần translate (giây)
    """
    with app.app_context():
        print("\n" + "="*60)
        print(f"🌐 Translating URLs for EN home articles")
        print("="*60)
        
        # Query EN home articles
        query = Article.query.filter_by(
            language='en',
            is_home=True
        )
        
        # Nếu không force, chỉ lấy articles chưa có published_url_en
        if not force:
            query = query.filter(
                (Article.published_url_en.is_(None) | (Article.published_url_en == ''))
            )
        
        en_articles = query.all()
        
        if not en_articles:
            if force:
                print("✅ Không có articles nào để dịch lại!")
            else:
                print("✅ Không có articles nào cần dịch URL!")
            return
        
        print(f"   Found {len(en_articles)} EN home articles to translate URLs")
        
        url_translated_count = 0
        url_skipped_count = 0
        url_error_count = 0
        
        for idx, article in enumerate(en_articles, 1):
            # Skip nếu không có published_url
            if not article.published_url or not article.published_url.strip():
                url_skipped_count += 1
                continue
            
            # Skip nếu đã có published_url_en (chỉ khi không force)
            if not force and article.published_url_en and article.published_url_en.strip():
                url_skipped_count += 1
                continue
            
            try:
                print(f"   [{idx}/{len(en_articles)}] Translating URL for article {article.id}...")
                print(f"      DA URL: {article.published_url}")
                
                # Translate URL
                en_url = translate_url(article.published_url, delay=delay)
                
                if en_url:
                    article.published_url_en = en_url
                    db.session.commit()
                    url_translated_count += 1
                    print(f"      ✅ EN URL: {en_url}")
                    
                    if url_translated_count % 10 == 0:
                        print(f"   ✅ Translated {url_translated_count} URLs...")
                else:
                    url_error_count += 1
                    print(f"      ⚠️  Could not translate URL")
                    
            except Exception as e:
                print(f"      ⚠️  Error translating URL for article {article.id}: {e}")
                url_error_count += 1
                db.session.rollback()
                continue
        
        print(f"\n✅ URL translation completed:")
        print(f"   - Translated: {url_translated_count}")
        print(f"   - Skipped: {url_skipped_count}")
        if url_error_count > 0:
            print(f"   - Errors: {url_error_count}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Translate URLs for EN home articles')
    parser.add_argument('--force', action='store_true', help='Force translate even if published_url_en already exists')
    parser.add_argument('--delay', type=float, default=0.3, help='Delay between translations (seconds)')
    
    args = parser.parse_args()
    
    translate_home_urls_en(force=args.force, delay=args.delay)


