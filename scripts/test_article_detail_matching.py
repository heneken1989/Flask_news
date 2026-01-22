#!/usr/bin/env python3
"""
Script để test xem ArticleDetail có match với URL mới không

Usage:
    python scripts/test_article_detail_matching.py
    python scripts/test_article_detail_matching.py --url-path /erhverv/gronlandsudvalget-inviteret-til-avannaata-qimussersua/2329146
"""
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from services.article_detail_parser import ArticleDetailParser
import argparse


def test_article_detail_matching(url_path: str = None):
    """
    Test xem ArticleDetail có match với URL mới không
    
    Args:
        url_path: Path từ URL (ví dụ: /erhverv/article/123)
    """
    print(f"\n{'='*60}")
    print(f"🔍 Testing ArticleDetail Matching")
    print(f"{'='*60}\n")
    
    if url_path:
        # Test với URL path cụ thể
        print(f"📌 Testing URL path: {url_path}\n")
        
        # Tìm Article bằng path
        all_articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).all()
        
        article = None
        for art in all_articles:
            if not art.published_url:
                continue
            
            art_parsed = urlparse(art.published_url)
            art_path = art_parsed.path
            
            if art_path == url_path:
                article = art
                break
        
        if not article:
            print(f"❌ No article found with path: {url_path}")
            return
        
        print(f"✅ Found Article:")
        print(f"   ID: {article.id}")
        print(f"   Title: {article.title[:60]}...")
        print(f"   Language: {article.language}")
        print(f"   Published URL: {article.published_url}")
        print()
        
        # Test tìm ArticleDetail
        print(f"🔍 Looking for ArticleDetail...")
        article_detail = ArticleDetailParser.get_article_detail_by_article(article, language=article.language)
        
        if article_detail:
            print(f"✅ Found ArticleDetail:")
            print(f"   ID: {article_detail.id}")
            print(f"   Published URL: {article_detail.published_url}")
            print(f"   Language: {article_detail.language}")
            print(f"   Content blocks: {len(article_detail.content_blocks) if article_detail.content_blocks else 0}")
        else:
            print(f"❌ No ArticleDetail found for this article")
            print(f"   Trying to find by published_url directly...")
            
            # Thử tìm trực tiếp
            direct_detail = ArticleDetail.query.filter_by(
                published_url=article.published_url,
                language=article.language
            ).first()
            
            if direct_detail:
                print(f"   ✅ Found by direct query: ID {direct_detail.id}")
            else:
                print(f"   ❌ Not found even by direct query")
                print(f"   Checking all ArticleDetails with similar path...")
                
                # Tìm tất cả ArticleDetails có path tương tự
                all_details = ArticleDetail.query.filter(
                    ArticleDetail.published_url.like(f'%{url_path}%')
                ).all()
                
                if all_details:
                    print(f"   Found {len(all_details)} ArticleDetail(s) with similar path:")
                    for detail in all_details:
                        print(f"      - ID {detail.id}: {detail.published_url[:80]}... (lang: {detail.language})")
                else:
                    print(f"   ❌ No ArticleDetails found with similar path")
    else:
        # Test tổng quát
        print("📊 Testing all articles with published_url...\n")
        
        articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).limit(10).all()
        
        print(f"Found {len(articles)} articles to test\n")
        
        matched = 0
        not_matched = 0
        
        for article in articles:
            article_detail = ArticleDetailParser.get_article_detail_by_article(article, language=article.language)
            
            if article_detail:
                matched += 1
                print(f"✅ Article #{article.id}: {article.title[:50]}...")
                print(f"   Published URL: {article.published_url[:70]}...")
                print(f"   ArticleDetail: {article_detail.published_url[:70]}...")
            else:
                not_matched += 1
                print(f"❌ Article #{article.id}: {article.title[:50]}...")
                print(f"   Published URL: {article.published_url[:70]}...")
                print(f"   No ArticleDetail found")
            print()
        
        print(f"{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"   Total tested: {len(articles)}")
        print(f"   Matched: {matched}")
        print(f"   Not matched: {not_matched}")
        print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test ArticleDetail matching with new URLs')
    parser.add_argument('--url-path', type=str, default=None,
                       help='URL path to test (e.g., /erhverv/article/123)')
    
    args = parser.parse_args()
    
    with app.app_context():
        test_article_detail_matching(url_path=args.url_path)

