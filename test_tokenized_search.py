#!/usr/bin/env python3
"""
Test tokenized search functionality
Tests that search works like the original website with word tokenization
"""

import sys
import os

# Add flask directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'flask'))

from app import app
from database import db, Article, ArticleDetail
from sqlalchemy import func, or_, case
from sqlalchemy.sql import text
import re

def test_tokenized_search(query, language='da', limit=5):
    """Test tokenized search logic"""
    with app.app_context():
        print(f"\n{'='*80}")
        print(f"🔍 Testing Tokenized Search")
        print(f"{'='*80}")
        print(f"Query: '{query}'")
        print(f"Language: {language}")
        print(f"")
        
        # Tokenize search query
        words = [w.strip() for w in re.split(r'\s+', query) if len(w.strip()) >= 2]
        
        if not words:
            words = [query]
        
        print(f"🔤 Tokenized into words: {words}")
        print(f"")
        
        # Build OR conditions for each word
        word_conditions = []
        for word in words:
            word_pattern = f"%{word}%"
            word_conditions.append(
                or_(
                    Article.title.ilike(word_pattern),
                    Article.excerpt.ilike(word_pattern),
                    Article.content.ilike(word_pattern),
                    func.lower(func.cast(Article.tags, db.String)).contains(word.lower()),
                    func.lower(func.cast(ArticleDetail.content_blocks, db.String)).contains(word.lower())
                )
            )
        
        combined_word_conditions = or_(*word_conditions)
        
        # Calculate relevance score
        relevance_expressions = []
        for word in words:
            word_pattern = f"%{word}%"
            relevance_expressions.append(
                case(
                    (Article.title.ilike(word_pattern), 3),
                    else_=0
                )
            )
            relevance_expressions.append(
                case(
                    (Article.excerpt.ilike(word_pattern), 2),
                    else_=0
                )
            )
            relevance_expressions.append(
                case(
                    (Article.content.ilike(word_pattern), 1),
                    else_=0
                )
            )
        
        from sqlalchemy import literal_column
        relevance_score = sum(relevance_expressions) if relevance_expressions else literal_column('0')
        
        # Subquery for deduplication
        subquery = db.session.query(
            func.max(Article.id).label('max_id'),
            func.regexp_replace(
                Article.published_url,
                '.*/([0-9]+)$',
                '\\1'
            ).label('url_id')
        ).outerjoin(
            ArticleDetail,
            db.and_(
                Article.published_url == ArticleDetail.published_url,
                Article.language == ArticleDetail.language
            )
        ).filter(
            Article.language == language,
            Article.is_temp == False,
            combined_word_conditions
        ).group_by(
            'url_id'
        ).subquery()
        
        # Main query with relevance scoring
        results = db.session.query(
            Article,
            relevance_score.label('relevance')
        ).outerjoin(
            ArticleDetail,
            db.and_(
                Article.published_url == ArticleDetail.published_url,
                Article.language == ArticleDetail.language
            )
        ).filter(
            Article.id.in_(
                db.session.query(subquery.c.max_id)
            )
        ).order_by(
            text('relevance DESC'),
            Article.created_at.desc()
        ).limit(limit).all()
        
        print(f"📊 Found {len(results)} results (showing top {limit})")
        print(f"")
        
        if results:
            for idx, (article, relevance) in enumerate(results, 1):
                print(f"#{idx} - Relevance Score: {relevance}")
                print(f"   Title: {article.title[:80]}...")
                print(f"   URL: {article.published_url}")
                
                # Show which words matched
                matched_words = []
                for word in words:
                    if word.lower() in article.title.lower():
                        matched_words.append(f"{word}(title)")
                    elif word.lower() in (article.excerpt or '').lower():
                        matched_words.append(f"{word}(excerpt)")
                    elif word.lower() in (article.content or '').lower():
                        matched_words.append(f"{word}(content)")
                
                print(f"   Matched words: {', '.join(matched_words) if matched_words else 'None visible'}")
                print(f"")
        else:
            print("❌ No results found")
        
        print(f"{'='*80}\n")

if __name__ == '__main__':
    # Test 1: Multi-word phrase search
    test_tokenized_search("Donald Trump har sendt", language='da')
    
    # Test 2: Single word search
    test_tokenized_search("Grønland", language='da')
    
    # Test 3: Author name search
    test_tokenized_search("Jens Frederik Nielsen", language='da')
    
    # Test 4: Two word search
    test_tokenized_search("USA Grønland", language='da')
