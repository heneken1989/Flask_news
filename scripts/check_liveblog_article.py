#!/usr/bin/env python3
"""
Script để kiểm tra vấn đề với liveblog article không được set is_home=True
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import or_
import json

# URLs cần kiểm tra
URL1 = 'https://www.sermitsiaq.ag/samfund/macron-i-et-interview-krisen-om-gronland-er-ikke-slut/2326415'
URL2 = 'https://www.sermitsiaq.ag/samfund/amerikanere-modes-med-udvalg-kl-11/2326415'
ARTICLE_ID = 2326415

def check_articles():
    with app.app_context():
        print('='*80)
        print('Checking articles in database...')
        print('='*80)
        
        # Check URL 1
        print(f'\n📰 Checking URL 1: {URL1}')
        articles1 = Article.query.filter(
            (Article.published_url == URL1) | (Article.published_url_en == URL1)
        ).all()
        
        print(f'   Found {len(articles1)} articles:')
        for article in articles1:
            print(f'   - DB ID: {article.id}, Lang: {article.language}')
            print(f'     published_url: {article.published_url[:70] if article.published_url else "N/A"}...')
            print(f'     published_url_en: {article.published_url_en[:70] if article.published_url_en else "N/A"}...')
            print(f'     is_home: {article.is_home}, layout_type: {article.layout_type}, display_order: {article.display_order}')
            print(f'     section: {article.section}, is_deleted: {article.is_deleted}')
            print(f'     title: {article.title[:60] if article.title else "N/A"}...')
            print()
        
        # Check URL 2
        print(f'\n📰 Checking URL 2: {URL2}')
        articles2 = Article.query.filter(
            (Article.published_url == URL2) | (Article.published_url_en == URL2)
        ).all()
        
        print(f'   Found {len(articles2)} articles:')
        for article in articles2:
            print(f'   - DB ID: {article.id}, Lang: {article.language}')
            print(f'     published_url: {article.published_url[:70] if article.published_url else "N/A"}...')
            print(f'     published_url_en: {article.published_url_en[:70] if article.published_url_en else "N/A"}...')
            print(f'     is_home: {article.is_home}, layout_type: {article.layout_type}, display_order: {article.display_order}')
            print(f'     section: {article.section}, is_deleted: {article.is_deleted}')
            print(f'     title: {article.title[:60] if article.title else "N/A"}...')
            print()
        
        # Check articles với cùng article ID (2326415)
        print(f'\n📰 Checking articles with article ID {ARTICLE_ID} (all URLs):')
        articles3 = Article.query.filter(
            or_(
                Article.published_url.like(f'%/{ARTICLE_ID}'),
                Article.published_url_en.like(f'%/{ARTICLE_ID}')
            )
        ).order_by(Article.language, Article.id).all()
        
        print(f'   Found {len(articles3)} articles:')
        for article in articles3:
            print(f'   - DB ID: {article.id}, Lang: {article.language}')
            print(f'     published_url: {article.published_url[:70] if article.published_url else "N/A"}...')
            print(f'     published_url_en: {article.published_url_en[:70] if article.published_url_en else "N/A"}...')
            print(f'     is_home: {article.is_home}, layout_type: {article.layout_type}, display_order: {article.display_order}')
            print(f'     section: {article.section}, is_deleted: {article.is_deleted}')
            print(f'     title: {article.title[:60] if article.title else "N/A"}...')
            print()
        
        # Check layout files
        print('\n' + '='*80)
        print('Checking layout files...')
        print('='*80)
        
        layouts_dir = Path(__file__).parent.parent / 'home_layouts'
        if layouts_dir.exists():
            # Tìm file layout mới nhất
            layout_files = sorted(layouts_dir.glob('home_layout_da_*.json'), reverse=True)
            if layout_files:
                latest_layout = layout_files[0]
                print(f'\n📄 Loading latest layout: {latest_layout.name}')
                
                with open(latest_layout, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                
                layout_items = layout_data.get('layout_items', [])
                print(f'   Total layout items: {len(layout_items)}')
                
                # Tìm URL1 trong layout
                found_url1 = False
                found_url2 = False
                for idx, item in enumerate(layout_items):
                    item_url = item.get('published_url', '')
                    if URL1 in item_url or item_url.endswith(f'/{ARTICLE_ID}'):
                        found_url1 = True
                        print(f'\n   ✅ Found URL1 in layout at index {idx}:')
                        print(f'      published_url: {item_url[:70]}...')
                        print(f'      layout_type: {item.get("layout_type")}')
                        print(f'      display_order: {item.get("display_order")}')
                        print(f'      title: {item.get("title", "")[:60]}...')
                    elif URL2 in item_url:
                        found_url2 = True
                        print(f'\n   ✅ Found URL2 in layout at index {idx}:')
                        print(f'      published_url: {item_url[:70]}...')
                        print(f'      layout_type: {item.get("layout_type")}')
                        print(f'      display_order: {item.get("display_order")}')
                        print(f'      title: {item.get("title", "")[:60]}...')
                
                if not found_url1:
                    print(f'\n   ❌ URL1 NOT FOUND in layout!')
                if not found_url2:
                    print(f'\n   ❌ URL2 NOT FOUND in layout!')
            else:
                print('   ⚠️  No layout files found')
        else:
            print('   ⚠️  Layouts directory not found')
        
        # Check articles_map logic
        print('\n' + '='*80)
        print('Checking articles_map logic...')
        print('='*80)
        
        # Simulate articles_map creation
        all_articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != '',
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).all()
        
        articles_map = {}
        for article in all_articles:
            if article.published_url:
                if article.published_url not in articles_map:
                    articles_map[article.published_url] = []
                articles_map[article.published_url].append(article)
        
        print(f'\n   Total unique URLs in articles_map: {len(articles_map)}')
        
        # Check URL1 in articles_map
        if URL1 in articles_map:
            print(f'\n   ✅ URL1 found in articles_map: {len(articles_map[URL1])} articles')
            for article in articles_map[URL1]:
                print(f'      - DB ID: {article.id}, Lang: {article.language}, is_home: {article.is_home}')
        else:
            print(f'\n   ❌ URL1 NOT FOUND in articles_map!')
        
        # Check URL2 in articles_map
        if URL2 in articles_map:
            print(f'\n   ✅ URL2 found in articles_map: {len(articles_map[URL2])} articles')
            for article in articles_map[URL2]:
                print(f'      - DB ID: {article.id}, Lang: {article.language}, is_home: {article.is_home}')
        else:
            print(f'\n   ❌ URL2 NOT FOUND in articles_map!')
        
        # Check for duplicate URLs with same article ID
        print('\n' + '='*80)
        print('Checking for duplicate URLs with same article ID...')
        print('='*80)
        
        # Find all articles with same article ID
        all_articles_with_id = Article.query.filter(
            or_(
                Article.published_url.like(f'%/{ARTICLE_ID}'),
                Article.published_url_en.like(f'%/{ARTICLE_ID}')
            )
        ).all()
        
        # Group by language
        by_language = {}
        for article in all_articles_with_id:
            lang = article.language
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(article)
        
        print(f'\n   Articles grouped by language:')
        for lang, articles in by_language.items():
            print(f'   - {lang.upper()}: {len(articles)} articles')
            for article in articles:
                print(f'     * DB ID: {article.id}, published_url: {article.published_url[:60] if article.published_url else "N/A"}...')
                print(f'       is_home: {article.is_home}, section: {article.section}')
                
                # Check if there are multiple articles with same published_url
                if article.published_url:
                    duplicates = Article.query.filter_by(
                        published_url=article.published_url,
                        language=lang
                    ).filter(
                        or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                    ).all()
                    if len(duplicates) > 1:
                        print(f'       ⚠️  WARNING: {len(duplicates)} articles with same published_url!')
                        for dup in duplicates:
                            print(f'          - DB ID: {dup.id}, is_home: {dup.is_home}, section: {dup.section}')

if __name__ == '__main__':
    check_articles()
