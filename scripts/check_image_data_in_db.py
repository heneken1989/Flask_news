#!/usr/bin/env python3
"""
Script để kiểm tra image_data trong database
Xem có URLs với domain .com hay không
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
import json

def check_image_data():
    """Kiểm tra image_data trong database"""
    with app.app_context():
        # Lấy một số articles có image_data
        # PostgreSQL JSON không thể so sánh với string, chỉ cần check IS NOT NULL
        articles = Article.query.filter(
            Article.image_data.isnot(None)
        ).limit(20).all()
        
        print(f"\n{'='*60}")
        print(f"🔍 Checking image_data in database")
        print(f"{'='*60}")
        print(f"Found {len(articles)} articles with image_data\n")
        
        com_count = 0
        ag_count = 0
        other_count = 0
        
        for article in articles:
            img_data = article.image_data
            
            # Parse JSON nếu là string
            if isinstance(img_data, str):
                try:
                    img_data = json.loads(img_data)
                except:
                    print(f"⚠️  Article #{article.id}: Cannot parse image_data as JSON")
                    continue
            
            if not isinstance(img_data, dict):
                print(f"⚠️  Article #{article.id}: image_data is not a dict")
                continue
            
            print(f"\nArticle #{article.id} (lang: {article.language}):")
            print(f"  Title: {article.title[:60]}...")
            
            # Check từng image URL
            image_keys = ['desktop_jpeg', 'desktop_webp', 'fallback', 'mobile_jpeg', 'mobile_webp']
            has_com = False
            has_ag = False
            
            for key in image_keys:
                url = img_data.get(key)
                if url:
                    if 'sermitsiaq.com' in url:
                        print(f"  ✅ {key}: {url[:80]}... (DOMAIN .COM)")
                        has_com = True
                        com_count += 1
                    elif 'sermitsiaq.ag' in url:
                        print(f"  ⚠️  {key}: {url[:80]}... (DOMAIN .AG)")
                        has_ag = True
                        ag_count += 1
                    else:
                        print(f"  ℹ️  {key}: {url[:80]}... (OTHER)")
                        other_count += 1
            
            if has_com:
                print(f"  → Article này CÓ image với domain .com")
            elif has_ag:
                print(f"  → Article này CHỈ có image với domain .ag")
            else:
                print(f"  → Article này có image nhưng không rõ domain")
        
        print(f"\n{'='*60}")
        print(f"📊 Summary:")
        print(f"  - Images with .com domain: {com_count}")
        print(f"  - Images with .ag domain: {ag_count}")
        print(f"  - Images with other domain: {other_count}")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    check_image_data()

