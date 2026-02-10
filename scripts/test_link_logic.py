#!/usr/bin/env python3
"""
Script để test logic link và chọn article trong link_home_articles.py
Test với articles có cùng article ID nhưng khác URL (liveblog case)
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import or_

# Test URLs
URL1 = 'https://www.sermitsiaq.ag/samfund/macron-i-et-interview-krisen-om-gronland-er-ikke-slut/2326415'
URL2 = 'https://www.sermitsiaq.ag/samfund/amerikanere-modes-med-udvalg-kl-11/2326415'
ARTICLE_ID = 2326415
LANGUAGE = 'da'

def test_link_logic():
    with app.app_context():
        print('='*80)
        print('Testing Link Logic for Liveblog Articles')
        print('='*80)
        
        # Step 1: Find all articles with these URLs or article ID
        print(f'\n📰 Step 1: Finding articles with article ID {ARTICLE_ID}...')
        all_articles = Article.query.filter(
            or_(
                Article.published_url.like(f'%/{ARTICLE_ID}'),
                Article.published_url_en.like(f'%/{ARTICLE_ID}')
            ),
            Article.language == LANGUAGE,
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).order_by(Article.created_at.desc()).all()
        
        print(f'   Found {len(all_articles)} articles:')
        for idx, article in enumerate(all_articles, 1):
            print(f'\n   {idx}. DB ID: {article.id}')
            print(f'      published_url: {article.published_url[:70] if article.published_url else "N/A"}...')
            print(f'      is_home: {article.is_home}')
            print(f'      created_at: {article.created_at}')
            print(f'      updated_at: {article.updated_at}')
            print(f'      section: {article.section}')
            print(f'      layout_type: {article.layout_type}')
            print(f'      display_order: {article.display_order}')
        
        if not all_articles:
            print('   ❌ No articles found!')
            return
        
        # Step 2: Simulate articles_map creation
        print(f'\n📋 Step 2: Simulating articles_map creation...')
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
        
        # Step 3: Test matching logic for URL1 (newest URL in layout)
        print(f'\n🔍 Step 3: Testing matching logic for URL1 (from layout)...')
        print(f'   URL: {URL1}')
        
        published_url = URL1
        language = LANGUAGE
        require_home_section = False
        
        matched_article = None
        
        # Test logic: Match by URL first
        if published_url in articles_map:
            print(f'   ✅ URL found in articles_map')
            candidates = []
            for article in articles_map[published_url]:
                if article.language == language:
                    if require_home_section:
                        if article.section == 'home':
                            candidates.append(article)
                    else:
                        candidates.append(article)
            
            if candidates:
                print(f'   Found {len(candidates)} candidates:')
                for idx, candidate in enumerate(candidates, 1):
                    print(f'      {idx}. DB ID: {candidate.id}, is_home: {candidate.is_home}, created_at: {candidate.created_at}')
                
                # Sort: 1) created_at mới nhất, 2) is_home=True
                candidates.sort(key=lambda a: (
                    -(a.created_at.timestamp() if a.created_at else 0),  # Mới nhất ở đầu
                    not a.is_home  # is_home=True sẽ ở đầu nếu cùng created_at
                ))
                matched_article = candidates[0]
                print(f'\n   ✅ Selected article (after sorting):')
                print(f'      DB ID: {matched_article.id}')
                print(f'      URL: {matched_article.published_url[:70] if matched_article.published_url else "N/A"}...')
                print(f'      is_home: {matched_article.is_home}')
                print(f'      created_at: {matched_article.created_at}')
            else:
                print(f'   ❌ No candidates found for language={language}')
        else:
            print(f'   ❌ URL NOT found in articles_map')
            print(f'   → Will try to find by article ID...')
            
            # Test logic: Match by article ID (fallback)
            try:
                article_id_match = re.search(r'/(\d+)$', published_url)
                if article_id_match:
                    article_id_from_url = int(article_id_match.group(1))
                    print(f'   Extracted article ID: {article_id_from_url}')
                    
                    candidates_by_id = Article.query.filter(
                        or_(
                            Article.published_url.like(f'%/{article_id_from_url}'),
                            Article.published_url_en.like(f'%/{article_id_from_url}')
                        ),
                        Article.language == language,
                        or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                    )
                    
                    if require_home_section:
                        candidates_by_id = candidates_by_id.filter_by(section='home')
                    
                    candidates_by_id = candidates_by_id.all()
                    
                    if candidates_by_id:
                        print(f'   Found {len(candidates_by_id)} candidates by ID:')
                        for idx, candidate in enumerate(candidates_by_id, 1):
                            print(f'      {idx}. DB ID: {candidate.id}, is_home: {candidate.is_home}, created_at: {candidate.created_at}')
                        
                        # Sort: 1) created_at mới nhất, 2) is_home=True
                        candidates_by_id.sort(key=lambda a: (
                            -(a.created_at.timestamp() if a.created_at else 0),  # Mới nhất ở đầu
                            not a.is_home  # is_home=True sẽ ở đầu nếu cùng created_at
                        ))
                        matched_article = candidates_by_id[0]
                        print(f'\n   ✅ Selected article (by ID, after sorting):')
                        print(f'      DB ID: {matched_article.id}')
                        print(f'      URL: {matched_article.published_url[:70] if matched_article.published_url else "N/A"}...')
                        print(f'      is_home: {matched_article.is_home}')
                        print(f'      created_at: {matched_article.created_at}')
            except Exception as e:
                print(f'   ❌ Error finding by article ID: {e}')
        
        # Step 4: Verify selection
        print(f'\n✅ Step 4: Verification...')
        if matched_article:
            # Check if it's the newest article
            newest_article = max(all_articles, key=lambda a: a.created_at if a.created_at else datetime.min)
            
            print(f'   Selected article: DB ID {matched_article.id}')
            print(f'   Newest article: DB ID {newest_article.id}')
            
            if matched_article.id == newest_article.id:
                print(f'   ✅ CORRECT: Selected article is the newest one!')
            else:
                print(f'   ❌ ERROR: Selected article is NOT the newest one!')
                print(f'      Selected created_at: {matched_article.created_at}')
                print(f'      Newest created_at: {newest_article.created_at}')
            
            # Check if newest article should have is_home=True
            if newest_article.is_home:
                print(f'   ✅ Newest article already has is_home=True')
            else:
                print(f'   ⚠️  Newest article does NOT have is_home=True (should be set)')
            
            # Check older articles
            matched_created_at = matched_article.created_at.timestamp() if matched_article.created_at else 0
            older_articles = [
                a for a in all_articles 
                if a.id != matched_article.id 
                and (a.created_at.timestamp() if a.created_at else 0) < matched_created_at
            ]
            
            print(f'\n   Older articles (should have is_home=False): {len(older_articles)}')
            for old_article in older_articles:
                if old_article.is_home:
                    print(f'      ⚠️  DB ID {old_article.id}: is_home=True (should be False)')
                else:
                    print(f'      ✅ DB ID {old_article.id}: is_home=False (correct)')
        else:
            print(f'   ❌ No article matched!')
        
        # Step 5: Summary
        print(f'\n📊 Step 5: Summary...')
        print(f'   Total articles with article ID {ARTICLE_ID}: {len(all_articles)}')
        print(f'   Articles with is_home=True: {sum(1 for a in all_articles if a.is_home)}')
        print(f'   Articles with is_home=False: {sum(1 for a in all_articles if not a.is_home)}')
        
        # Find newest article
        if all_articles:
            newest = max(all_articles, key=lambda a: a.created_at if a.created_at else datetime.min)
            print(f'\n   Newest article:')
            print(f'      DB ID: {newest.id}')
            print(f'      URL: {newest.published_url[:70] if newest.published_url else "N/A"}...')
            print(f'      is_home: {newest.is_home}')
            print(f'      created_at: {newest.created_at}')
            
            if newest.is_home:
                print(f'      ✅ Newest article has is_home=True (correct)')
            else:
                print(f'      ❌ Newest article does NOT have is_home=True (should be fixed)')
            
            # Check if older articles have is_home=False
            newest_created_at = newest.created_at.timestamp() if newest.created_at else 0
            older_articles = [
                a for a in all_articles 
                if a.id != newest.id 
                and (a.created_at.timestamp() if a.created_at else 0) < newest_created_at
            ]
            
            if older_articles:
                print(f'\n   Older articles: {len(older_articles)}')
                all_older_correct = True
                for old_article in older_articles:
                    if old_article.is_home:
                        print(f'      ❌ DB ID {old_article.id}: is_home=True (should be False)')
                        all_older_correct = False
                    else:
                        print(f'      ✅ DB ID {old_article.id}: is_home=False (correct)')
                
                if all_older_correct:
                    print(f'      ✅ All older articles have is_home=False (correct)')
                else:
                    print(f'      ❌ Some older articles still have is_home=True (should be fixed)')

if __name__ == '__main__':
    test_link_logic()
