#!/usr/bin/env python3
"""
Script để debug route matching và tìm article

Usage:
    python scripts/debug_route_matching.py --path /samfund/hercules-fly-landede-i-nuuk-onsdag/2330773
"""
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
import argparse


def debug_route_matching(path: str):
    """
    Debug route matching với path cụ thể
    
    Args:
        path: Path từ URL (ví dụ: /samfund/article/123)
    """
    print(f"\n{'='*60}")
    print(f"🔍 Debug Route Matching")
    print(f"{'='*60}\n")
    print(f"📌 Testing path: {path}\n")
    
    # Normalize path (remove leading/trailing slashes nếu cần)
    path = path.strip()
    if not path.startswith('/'):
        path = '/' + path
    
    # Query tất cả articles có published_url
    all_articles = Article.query.filter(
        Article.published_url.isnot(None),
        Article.published_url != ''
    ).all()
    
    print(f"📊 Found {len(all_articles)} articles with published_url\n")
    
    # Tìm articles có path match
    matches = []
    for art in all_articles:
        if not art.published_url:
            continue
        
        art_parsed = urlparse(art.published_url)
        art_path = art_parsed.path
        
        if art_path == path:
            matches.append(art)
    
    if matches:
        print(f"✅ Found {len(matches)} matching article(s):\n")
        for art in matches:
            print(f"   Article ID: {art.id}")
            print(f"   Title: {art.title[:60]}...")
            print(f"   Language: {art.language}")
            print(f"   Published URL: {art.published_url}")
            print(f"   Path: {urlparse(art.published_url).path}")
            print()
            
            # Check ArticleDetail
            from services.article_detail_parser import ArticleDetailParser
            article_detail = ArticleDetailParser.get_article_detail_by_article(art, language=art.language)
            if article_detail:
                print(f"   ✅ ArticleDetail found: ID {article_detail.id}")
            else:
                print(f"   ❌ No ArticleDetail found")
            print()
    else:
        print(f"❌ No articles found with matching path\n")
        print(f"🔍 Showing similar paths (first 10):\n")
        
        # Show similar paths
        similar = []
        for art in all_articles[:50]:  # Check first 50
            if not art.published_url:
                continue
            art_parsed = urlparse(art.published_url)
            art_path = art_parsed.path
            
            # Check if path contains similar parts
            path_parts = path.split('/')
            art_path_parts = art_path.split('/')
            
            if len(path_parts) == len(art_path_parts):
                similar.append((art, art_path))
        
        if similar:
            for art, art_path in similar[:10]:
                print(f"   - {art_path} (Article #{art.id})")
        else:
            print(f"   No similar paths found")
            print(f"\n   Sample published_urls:")
            for art in all_articles[:10]:
                art_parsed = urlparse(art.published_url)
                print(f"      - {art_parsed.path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Debug route matching')
    parser.add_argument('--path', type=str, required=True,
                       help='URL path to test (e.g., /samfund/article/123)')
    
    args = parser.parse_args()
    
    with app.app_context():
        debug_route_matching(args.path)

