#!/usr/bin/env python3
"""
Script để kiểm tra một ArticleDetail cụ thể
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, ArticleDetail, Article
import json

def check_specific_article_detail(detail_id=None, article_id=None):
    with app.app_context():
        if detail_id:
            detail = ArticleDetail.query.get(detail_id)
        elif article_id:
            article = Article.query.get(article_id)
            if article:
                detail = ArticleDetail.query.filter_by(
                    published_url=article.published_url,
                    language=article.language
                ).first()
            else:
                print(f"Article ID {article_id} not found")
                return
        else:
            print("Please provide detail_id or article_id")
            return
        
        if not detail:
            print(f"ArticleDetail not found")
            return
        
        print(f"\n{'='*60}")
        print(f"ArticleDetail ID: {detail.id}")
        print(f"published_url: {detail.published_url}")
        print(f"language: {detail.language}")
        print(f"{'='*60}\n")
        
        content_blocks = detail.content_blocks
        if isinstance(content_blocks, str):
            try:
                content_blocks = json.loads(content_blocks)
            except:
                content_blocks = []
        
        if isinstance(content_blocks, list):
            image_blocks = [b for b in content_blocks if b.get('type') == 'image']
            print(f"Found {len(image_blocks)} image blocks:\n")
            
            for idx, block in enumerate(image_blocks, 1):
                image_sources = block.get('image_sources', {})
                if isinstance(image_sources, dict):
                    print(f"Image block #{idx}:")
                    for key, url in image_sources.items():
                        if isinstance(url, str):
                            if 'sermitsiaq.ag' in url:
                                print(f"  ⚠️  {key}: {url[:100]}... (DOMAIN .AG)")
                            elif 'sermitsiaq.com' in url:
                                print(f"  ✅ {key}: {url[:100]}... (DOMAIN .COM)")
                            else:
                                print(f"  ℹ️  {key}: {url[:100]}... (OTHER)")
                    print()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            check_specific_article_detail(detail_id=int(sys.argv[1]))
        else:
            print("Usage: python check_specific_article_detail.py <detail_id>")
    else:
        # Check ArticleDetail ID 3367 (from terminal output)
        check_specific_article_detail(detail_id=3367)

