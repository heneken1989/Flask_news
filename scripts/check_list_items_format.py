#!/usr/bin/env python3
"""
Script để kiểm tra format list_items của các articles có layout_type 1_with_list_left/right
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article

def check_list_items_format():
    with app.app_context():
        print("="*80)
        print("🔍 Checking list_items format in database...")
        print("="*80)
        
        # Tìm tất cả articles có layout_type 1_with_list_left hoặc 1_with_list_right
        articles = Article.query.filter(
            Article.layout_type.in_(['1_with_list_left', '1_with_list_right'])
        ).all()
        
        print(f"\n📊 Found {len(articles)} articles with layout_type 1_with_list_left/right")
        
        if not articles:
            print("   ⚠️  No articles found!")
            return
        
        # Phân loại theo language
        articles_by_lang = {}
        for article in articles:
            lang = article.language
            if lang not in articles_by_lang:
                articles_by_lang[lang] = []
            articles_by_lang[lang].append(article)
        
        print(f"\n📊 Articles by language:")
        for lang, arts in articles_by_lang.items():
            print(f"   - {lang}: {len(arts)} articles")
        
        # Kiểm tra chi tiết
        print(f"\n{'='*80}")
        print("📋 Detailed check:")
        print("="*80)
        
        total_checked = 0
        total_with_list_items = 0
        total_without_list_items = 0
        total_invalid_format = 0
        
        for article in articles:
            total_checked += 1
            layout_data = article.layout_data or {}
            list_items = layout_data.get('list_items', [])
            list_title = layout_data.get('list_title', '')
            
            print(f"\n[{total_checked}/{len(articles)}] Article ID: {article.id}")
            print(f"   Language: {article.language}")
            print(f"   Layout type: {article.layout_type}")
            print(f"   Title: {article.title[:60]}...")
            print(f"   Display order: {article.display_order}")
            print(f"   List title: {list_title if list_title else '(empty)'}")
            print(f"   List items count: {len(list_items)}")
            
            if not list_items:
                total_without_list_items += 1
                print(f"   ❌ No list_items found!")
                print(f"      layout_data keys: {list(layout_data.keys())}")
            else:
                total_with_list_items += 1
                print(f"   ✅ Has {len(list_items)} list items")
                
                # Kiểm tra format của từng item
                invalid_items = []
                for idx, item in enumerate(list_items[:5], 1):  # Check first 5
                    print(f"      Item {idx}:")
                    
                    # Check format
                    if not isinstance(item, dict):
                        print(f"         ❌ Not a dict: {type(item)}")
                        invalid_items.append(idx)
                        continue
                    
                    has_title = 'title' in item
                    has_url = 'url' in item
                    
                    print(f"         - title: {item.get('title', '(missing)')[:50] if has_title else '(missing)'}")
                    print(f"         - url: {item.get('url', '(missing)')[:60] if has_url else '(missing)'}")
                    
                    if not has_title or not has_url:
                        print(f"         ⚠️  Missing required fields!")
                        invalid_items.append(idx)
                    elif not item.get('title') or not item.get('url'):
                        print(f"         ⚠️  Empty title or url!")
                        invalid_items.append(idx)
                
                if invalid_items:
                    total_invalid_format += 1
                    print(f"   ⚠️  Found {len(invalid_items)} invalid items")
                else:
                    print(f"   ✅ All items have correct format (title, url)")
                
                if len(list_items) > 5:
                    print(f"      ... and {len(list_items) - 5} more items")
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 Summary:")
        print("="*80)
        print(f"   Total articles checked: {total_checked}")
        print(f"   Articles with list_items: {total_with_list_items}")
        print(f"   Articles without list_items: {total_without_list_items}")
        print(f"   Articles with invalid format: {total_invalid_format}")
        print(f"   Articles with valid format: {total_with_list_items - total_invalid_format}")
        
        # Check by language
        print(f"\n{'='*80}")
        print("📊 Summary by language:")
        print("="*80)
        
        for lang, arts in articles_by_lang.items():
            with_items = 0
            without_items = 0
            invalid = 0
            
            for article in arts:
                layout_data = article.layout_data or {}
                list_items = layout_data.get('list_items', [])
                
                if not list_items:
                    without_items += 1
                else:
                    with_items += 1
                    # Check if all items have correct format
                    for item in list_items:
                        if not isinstance(item, dict) or not item.get('title') or not item.get('url'):
                            invalid += 1
                            break
            
            print(f"\n   {lang.upper()}:")
            print(f"      Total: {len(arts)}")
            print(f"      With list_items: {with_items}")
            print(f"      Without list_items: {without_items}")
            print(f"      Invalid format: {invalid}")
            print(f"      Valid format: {with_items - invalid}")


if __name__ == '__main__':
    check_list_items_format()

