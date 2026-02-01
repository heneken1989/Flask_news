#!/usr/bin/env python3
"""Retranslate article 2336218 with cross-boundary duplicate fix"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from scripts.crawl_article_details_batch import create_en_article_detail_from_da

da_url = 'https://www.sermitsiaq.ag/erhverv/trump-oger-interessen-for-gronland/2336218'

print(f"🔄 Retranslating article with CROSS-BOUNDARY duplicate fix...")
print(f"   DA URL: {da_url}")
print()

with app.app_context():
    # Find DA ArticleDetail
    da_detail = ArticleDetail.query.filter_by(published_url=da_url, language='da').first()
    
    if not da_detail:
        print(f"❌ DA ArticleDetail not found")
        sys.exit(1)
    
    print(f"✅ Found DA ArticleDetail #{da_detail.id}")
    
    # Delete old EN ArticleDetail
    en_detail = ArticleDetail.query.filter_by(published_url=da_url, language='en').first()
    if en_detail:
        print(f"🗑️  Deleting old EN ArticleDetail #{en_detail.id}")
        db.session.delete(en_detail)
        db.session.commit()
        print()
    
    # Retranslate
    print("🌐 Translating DA → EN with cross-boundary fix...")
    result = create_en_article_detail_from_da(da_detail, delay=0.3)
    
    if result:
        print()
        print(f"✅ Translation successful!")
        print(f"   EN ArticleDetail ID: {result.id}")
        print(f"   Total blocks: {len(result.content_blocks)}")
        
        # Check for "recent recent"
        has_duplicate = False
        for i, block in enumerate(result.content_blocks):
            if block.get('text') and 'recent recent' in block.get('text', '').lower():
                has_duplicate = True
                print(f"   ❌ Still has 'recent recent' in block #{i}")
                print(f"      Text: {block['text'][:200]}...")
                break
            
            # Also check HTML
            if block.get('html') and 'recent' in block.get('html', '').lower():
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(block['html'], 'html.parser')
                text = soup.get_text()
                if 'recent recent' in text.lower():
                    has_duplicate = True
                    print(f"   ❌ Still has 'recent recent' in block #{i} HTML")
                    print(f"      Text: {text[:200]}...")
                    break
        
        if not has_duplicate:
            print(f"   ✅ No 'recent recent' duplicates!")
            
            # Show block 5 for verification
            if len(result.content_blocks) > 5:
                block5 = result.content_blocks[5]
                print()
                print("Block #5 preview:")
                print(f"  Text: {block5.get('text', '')[:200]}...")
    else:
        print("   ❌ Translation failed")

