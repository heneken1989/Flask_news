#!/usr/bin/env python3
"""Recrawl article 2336887 with fixed parser"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, ArticleDetail
from scripts.crawl_article_details_batch import crawl_article_detail

url = 'https://www.sermitsiaq.ag/kultur/gronlands-svigerson-nar-kaerlighed-skaber-rodder-i-nord/2336887'

print(f"🔄 Recrawling article with FIXED parser...")
print(f"   URL: {url}")
print()

# Delete old versions
with app.app_context():
    old_details = ArticleDetail.query.filter_by(published_url=url).all()
    for detail in old_details:
        print(f"   🗑️  Deleting old ArticleDetail #{detail.id} (language: {detail.language})")
        db.session.delete(detail)
    db.session.commit()
    print()

# Recrawl
print("   📡 Crawling fresh content...")
result = crawl_article_detail(url, language='da', headless=True, download_images=False)

if result:
    print()
    print(f"✅ Recrawl successful!")
    print(f"   ArticleDetail ID: {result.id}")
    print(f"   Total blocks: {len(result.content_blocks)}")
    
    # Check for duplicates
    with app.app_context():
        blocks = result.content_blocks
        text_map = {}
        has_duplicate = False
        
        for i, block in enumerate(blocks):
            if block.get('text') and len(block.get('text', '').strip()) > 30:
                text = block['text'].strip()
                if text in text_map:
                    has_duplicate = True
                    print(f"   ❌ DUPLICATE at block #{i} (also at #{text_map[text]})")
                    break
                else:
                    text_map[text] = i
        
        if not has_duplicate:
            print(f"   ✅ No duplicates!")
else:
    print("   ❌ Recrawl failed")

