#!/usr/bin/env python3
"""
Script để kiểm tra image URLs trong ArticleDetail.content_blocks
Xem có URLs với domain .ag hay không
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, ArticleDetail
import json

def check_article_detail_images():
    print("\n" + "="*60)
    print("🔍 Checking image URLs in ArticleDetail.content_blocks")
    print("="*60)

    with app.app_context():
        # Lấy một vài ArticleDetail để kiểm tra
        article_details = ArticleDetail.query.limit(10).all()

        print(f"Found {len(article_details)} article details to check\n")

        ag_domain_count = 0
        com_domain_count = 0
        total_image_blocks = 0

        for detail in article_details:
            print(f"ArticleDetail ID: {detail.id}")
            print(f"  published_url: {detail.published_url[:80] if detail.published_url else 'N/A'}...")
            print(f"  language: {detail.language}")
            
            content_blocks = detail.content_blocks
            if isinstance(content_blocks, str):
                try:
                    content_blocks = json.loads(content_blocks)
                except:
                    content_blocks = []
            
            if isinstance(content_blocks, list):
                image_blocks = [b for b in content_blocks if b.get('type') == 'image']
                total_image_blocks += len(image_blocks)
                
                if image_blocks:
                    print(f"  Found {len(image_blocks)} image blocks:")
                    for idx, block in enumerate(image_blocks, 1):
                        image_sources = block.get('image_sources', {})
                        if isinstance(image_sources, dict):
                            print(f"    Image block #{idx}:")
                            has_ag = False
                            has_com = False
                            
                            for key, url in image_sources.items():
                                if isinstance(url, str):
                                    if 'sermitsiaq.ag' in url:
                                        print(f"      ⚠️  {key}: {url[:100]}... (DOMAIN .AG)")
                                        has_ag = True
                                    elif 'sermitsiaq.com' in url:
                                        print(f"      ✅ {key}: {url[:100]}... (DOMAIN .COM)")
                                        has_com = True
                            
                            if has_ag:
                                ag_domain_count += 1
                                print(f"      → Block này CÓ URLs với domain .ag")
                            elif has_com:
                                com_domain_count += 1
                                print(f"      → Block này CÓ URLs với domain .com")
                else:
                    print(f"  No image blocks found")
            else:
                print(f"  ⚠️  content_blocks is not a list")
            
            print()

        print("="*60)
        print("📊 Summary:")
        print(f"  - Total image blocks checked: {total_image_blocks}")
        print(f"  - Blocks with .ag domain: {ag_domain_count}")
        print(f"  - Blocks with .com domain: {com_domain_count}")
        print("="*60)

if __name__ == '__main__':
    check_article_detail_images()

