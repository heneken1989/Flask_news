#!/usr/bin/env python3
"""
Script để kiểm tra articles với article ID 2326415
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import or_
from datetime import datetime

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
            Article.published_url == URL1
        ).all()
        
        print(f'   Found {len(articles1)} articles:')
        for article in articles1:
            print(f'   - DB ID: {article.id}, Lang: {article.language}')
            print(f'     published_url: {article.published_url}')
            print(f'     published_url_en: {article.published_url_en}')
            print(f'     is_home: {article.is_home}')
            print(f'     layout_type: {article.layout_type}')
            print(f'     display_order: {article.display_order}')
            print(f'     section: {article.section}')
            print(f'     is_deleted: {article.is_deleted}')
            print(f'     created_at: {article.created_at}')
            print(f'     updated_at: {article.updated_at}')
            print(f'     title: {article.title[:60] if article.title else "N/A"}...')
            print()
        
        # Check URL 2
        print(f'\n📰 Checking URL 2: {URL2}')
        articles2 = Article.query.filter(
            Article.published_url == URL2
        ).all()
        
        print(f'   Found {len(articles2)} articles:')
        for article in articles2:
            print(f'   - DB ID: {article.id}, Lang: {article.language}')
            print(f'     published_url: {article.published_url}')
            print(f'     published_url_en: {article.published_url_en}')
            print(f'     is_home: {article.is_home}')
            print(f'     layout_type: {article.layout_type}')
            print(f'     display_order: {article.display_order}')
            print(f'     section: {article.section}')
            print(f'     is_deleted: {article.is_deleted}')
            print(f'     created_at: {article.created_at}')
            print(f'     updated_at: {article.updated_at}')
            print(f'     title: {article.title[:60] if article.title else "N/A"}...')
            print()
        
        # Check all articles with article ID 2326415
        print(f'\n📰 Checking ALL articles with article ID {ARTICLE_ID}:')
        all_articles = Article.query.filter(
            or_(
                Article.published_url.like(f'%/{ARTICLE_ID}'),
                Article.published_url_en.like(f'%/{ARTICLE_ID}')
            )
        ).order_by(Article.language, Article.created_at.desc()).all()
        
        print(f'   Found {len(all_articles)} articles:')
        for article in all_articles:
            print(f'   - DB ID: {article.id}, Lang: {article.language}')
            print(f'     published_url: {article.published_url[:70] if article.published_url else "N/A"}...')
            print(f'     published_url_en: {article.published_url_en[:70] if article.published_url_en else "N/A"}...')
            print(f'     is_home: {article.is_home}')
            print(f'     layout_type: {article.layout_type}')
            print(f'     display_order: {article.display_order}')
            print(f'     section: {article.section}')
            print(f'     is_deleted: {article.is_deleted}')
            print(f'     created_at: {article.created_at}')
            print(f'     updated_at: {article.updated_at}')
            print(f'     title: {article.title[:60] if article.title else "N/A"}...')
            print()
        
        # Group by language and find newest
        print(f'\n📊 Analysis by language:')
        by_language = {}
        for article in all_articles:
            lang = article.language
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(article)
        
        for lang, articles in by_language.items():
            print(f'\n   {lang.upper()}: {len(articles)} articles')
            # Sort by created_at descending
            articles_sorted = sorted(articles, key=lambda a: a.created_at if a.created_at else datetime.min, reverse=True)
            
            for idx, article in enumerate(articles_sorted):
                marker = "⭐ NEWEST" if idx == 0 else ""
                print(f'     {idx+1}. DB ID: {article.id} {marker}')
                print(f'        URL: {article.published_url[:60] if article.published_url else "N/A"}...')
                print(f'        is_home: {article.is_home}')
                print(f'        created_at: {article.created_at}')
                if idx == 0 and not article.is_home:
                    print(f'        ⚠️  PROBLEM: Newest article is NOT set is_home=True!')
        
        # Check if articles are in articles_map
        print(f'\n📋 Checking articles_map logic:')
        all_articles_for_map = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != '',
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).all()
        
        articles_map = {}
        for article in all_articles_for_map:
            if article.published_url:
                if article.published_url not in articles_map:
                    articles_map[article.published_url] = []
                articles_map[article.published_url].append(article)
        
        print(f'   Total unique URLs in articles_map: {len(articles_map)}')
        
        if URL1 in articles_map:
            print(f'\n   ✅ URL1 in articles_map: {len(articles_map[URL1])} articles')
            for article in articles_map[URL1]:
                print(f'      - DB ID: {article.id}, Lang: {article.language}, is_home: {article.is_home}')
        else:
            print(f'\n   ❌ URL1 NOT in articles_map')
        
        if URL2 in articles_map:
            print(f'\n   ✅ URL2 in articles_map: {len(articles_map[URL2])} articles')
            for article in articles_map[URL2]:
                print(f'      - DB ID: {article.id}, Lang: {article.language}, is_home: {article.is_home}')
        else:
            print(f'\n   ❌ URL2 NOT in articles_map')

if __name__ == '__main__':
    check_articles()
