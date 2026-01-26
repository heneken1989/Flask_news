#!/usr/bin/env python3
"""
Script để kiểm tra article và xem tại sao section='home'
"""

import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article

def check_article():
    """Kiểm tra article"""
    with app.app_context():
        url = "https://www.sermitsiaq.ag/samfund/se-billeder-flager-for-solidaritet-og-sammenhold/2329979"
        
        print("="*80)
        print(f"🔍 Checking article: {url}")
        print("="*80)
        
        # Tìm article trong database
        articles = Article.query.filter(
            Article.published_url.like(f"%{url.split('/')[-1]}%")
        ).all()
        
        print(f"\n📊 Found {len(articles)} articles matching URL pattern")
        
        for article in articles:
            print(f"\n   Article ID: {article.id}")
            print(f"   Language: {article.language}")
            print(f"   Section: {article.section}")
            print(f"   Layout Type: {article.layout_type}")
            print(f"   published_url: {article.published_url}")
            print(f"   is_home: {article.is_home}")
            print(f"   created_at: {article.created_at}")
            print(f"   title: {article.title[:80]}...")
            
            # Test extract_section_from_url
            print(f"\n   🔍 Testing extract_section_from_url:")
            if article.published_url:
                parsed = urlparse(article.published_url)
                path = parsed.path.strip('/')
                path_parts = path.split('/')
                print(f"      Path: {path}")
                print(f"      Path parts: {path_parts}")
                print(f"      First part: {path_parts[0] if path_parts else 'N/A'}")
                
                valid_sections = ['kultur', 'samfund', 'erhverv', 'sport', 'podcasti']
                if path_parts and path_parts[0] in valid_sections:
                    expected_section = path_parts[0]
                    print(f"      ✅ Expected section: {expected_section}")
                else:
                    print(f"      ❌ First part not in valid_sections: {valid_sections}")
            
            # Check layout type
            print(f"\n   🔍 Checking layout_type logic:")
            article_layout_types = ['1_full', '1_article', '2_articles', '3_articles', '1_special_bg']
            if article.layout_type in article_layout_types:
                print(f"      ✅ layout_type '{article.layout_type}' is in article_layout_types")
                print(f"      → Should detect section from URL")
            else:
                print(f"      ❌ layout_type '{article.layout_type}' is NOT in article_layout_types")
                print(f"      → Will use section='home'")
                print(f"      article_layout_types: {article_layout_types}")

if __name__ == '__main__':
    check_article()

