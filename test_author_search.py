#!/usr/bin/env python3
"""
Test script for author search functionality
"""

from app import app
from database import db, Article, ArticleDetail
import json

print("=" * 70)
print("🔍 TESTING AUTHOR SEARCH FUNCTIONALITY")
print("=" * 70)

with app.app_context():
    # Test 1: Find articles with author info
    print("\n1️⃣ Finding articles with author info...")
    print("-" * 70)
    
    articles_with_authors = db.session.query(Article).join(
        ArticleDetail,
        db.and_(
            Article.published_url == ArticleDetail.published_url,
            Article.language == ArticleDetail.language
        )
    ).filter(
        ArticleDetail.content_blocks.isnot(None)
    ).limit(5).all()
    
    print(f"Found {len(articles_with_authors)} articles with ArticleDetail")
    
    for article in articles_with_authors:
        # Get detail
        detail = ArticleDetail.query.filter_by(
            published_url=article.published_url,
            language=article.language
        ).first()
        
        if detail and detail.content_blocks:
            # Find article_meta block
            for block in detail.content_blocks:
                if block.get('type') == 'article_meta' and 'bylines' in block:
                    bylines = block.get('bylines', [])
                    if bylines:
                        print(f"\n📰 Article: {article.title[:60]}...")
                        for byline in bylines:
                            print(f"   👤 Author: {byline.get('fullname', 'N/A')}")
                            print(f"      Title: {byline.get('description', 'N/A')}")
                    break
    
    # Test 2: Search for specific author
    print("\n\n2️⃣ Testing author search...")
    print("-" * 70)
    
    test_authors = ["Jette", "Arne", "Redaktør", "Tusagassiortoq"]
    
    for search_term in test_authors:
        print(f"\n🔍 Searching for: '{search_term}'")
        
        # Simulate search query
        search_pattern = f"%{search_term}%"
        
        results = db.session.query(Article).outerjoin(
            ArticleDetail,
            db.and_(
                Article.published_url == ArticleDetail.published_url,
                Article.language == ArticleDetail.language
            )
        ).filter(
            Article.language == 'da',
            Article.is_temp == False,
            db.func.lower(db.func.cast(ArticleDetail.content_blocks, db.String)).contains(search_term.lower())
        ).limit(3).all()
        
        print(f"   Found {len(results)} results")
        
        for article in results:
            print(f"   - {article.title[:50]}...")
    
    # Test 3: Verify search includes author alongside other fields
    print("\n\n3️⃣ Testing combined search (author + title + content)...")
    print("-" * 70)
    
    search_term = "USA"  # Could be in title, content, or author name
    search_pattern = f"%{search_term}%"
    
    from sqlalchemy import or_, func
    
    results = db.session.query(Article).outerjoin(
        ArticleDetail,
        db.and_(
            Article.published_url == ArticleDetail.published_url,
            Article.language == ArticleDetail.language
        )
    ).filter(
        Article.language == 'da',
        Article.is_temp == False,
        or_(
            Article.title.ilike(search_pattern),
            Article.content.ilike(search_pattern),
            func.lower(func.cast(ArticleDetail.content_blocks, db.String)).contains(search_term.lower())
        )
    ).limit(5).all()
    
    print(f"\n🔍 Search: '{search_term}'")
    print(f"   Found {len(results)} results")
    
    for article in results:
        # Determine which field matched
        matches = []
        if search_term.upper() in article.title.upper():
            matches.append("title")
        if article.content and search_term.upper() in article.content.upper():
            matches.append("content")
        
        # Check author match
        detail = ArticleDetail.query.filter_by(
            published_url=article.published_url,
            language=article.language
        ).first()
        
        if detail and detail.content_blocks:
            content_str = json.dumps(detail.content_blocks).lower()
            if search_term.lower() in content_str:
                matches.append("author")
        
        print(f"   - {article.title[:50]}... [Matched in: {', '.join(matches)}]")
    
    # Test 4: Performance check
    print("\n\n4️⃣ Performance check...")
    print("-" * 70)
    
    import time
    
    search_term = "Grønland"
    search_pattern = f"%{search_term}%"
    
    start_time = time.time()
    
    count = db.session.query(Article).outerjoin(
        ArticleDetail,
        db.and_(
            Article.published_url == ArticleDetail.published_url,
            Article.language == ArticleDetail.language
        )
    ).filter(
        Article.language == 'da',
        Article.is_temp == False,
        or_(
            Article.title.ilike(search_pattern),
            Article.excerpt.ilike(search_pattern),
            Article.content.ilike(search_pattern),
            func.lower(func.cast(Article.tags, db.String)).contains(search_term.lower()),
            func.lower(func.cast(ArticleDetail.content_blocks, db.String)).contains(search_term.lower())
        )
    ).count()
    
    elapsed = time.time() - start_time
    
    print(f"   Search term: '{search_term}'")
    print(f"   Total results: {count}")
    print(f"   Query time: {elapsed:.3f} seconds")
    
    if elapsed > 1.0:
        print("   ⚠️  Query is slow (>1s). Consider adding indexes.")
    else:
        print("   ✅ Query performance is acceptable.")

print("\n" + "=" * 70)
print("✅ TESTING COMPLETED")
print("=" * 70)
