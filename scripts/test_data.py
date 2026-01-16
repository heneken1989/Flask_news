#!/usr/bin/env python3
"""
Script để test xem data có được lấy đúng không
Usage: python3 scripts/test_data.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article, db
from utils import apply_grid_size_pattern


def main():
    with app.app_context():
        print("=" * 60)
        print("🧪 Test Data từ Database")
        print("=" * 60)
        print()
        
        # Query articles
        articles = Article.query.order_by(Article.display_order.asc()).limit(10).all()
        print(f"📰 Found {len(articles)} articles")
        print()
        
        if not articles:
            print("❌ No articles found in database!")
            return
        
        # Convert to dict
        articles_dict = [article.to_dict() for article in articles]
        
        # Apply grid_size pattern
        articles_dict = apply_grid_size_pattern(articles_dict)
        
        # Display first 5 articles
        print("📋 First 5 Articles:")
        print()
        for idx, article in enumerate(articles_dict[:5], 1):
            print(f"{idx}. {article['title'][:60]}")
            print(f"   Display Order: {article.get('display_order', 'N/A')}")
            print(f"   Grid Size: {article.get('grid_size', 'N/A')}")
            print(f"   Section: {article.get('section', 'N/A')}")
            print(f"   URL: {article.get('url', 'N/A')[:60]}...")
            print(f"   Paywall: {article.get('is_paywall', False)}")
            
            # Check image
            image = article.get('image', {})
            if image:
                print(f"   Image:")
                if image.get('desktop_webp'):
                    print(f"     ✅ Desktop WebP: {image['desktop_webp'][:60]}...")
                if image.get('desktop_jpeg'):
                    print(f"     ✅ Desktop JPEG: {image['desktop_jpeg'][:60]}...")
                if image.get('mobile_webp'):
                    print(f"     ✅ Mobile WebP: {image['mobile_webp'][:60]}...")
                if image.get('fallback'):
                    print(f"     ✅ Fallback: {image['fallback'][:60]}...")
            else:
                print(f"   Image: ❌ No image data")
            print()
        
        print("=" * 60)
        print("✅ Data structure looks good!")
        print()
        print("🚀 Next step: Start Flask app to view in browser:")
        print("   python3 app.py")
        print("   Then visit: http://localhost:5000/")


if __name__ == '__main__':
    main()

