"""
Script để kiểm tra article ID 35732 - so sánh title field vs title trong layout_data
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article

def check_article_35732():
    with app.app_context():
        article = Article.query.get(35732)
        if not article:
            print('❌ Article 35732 not found')
            return
        
        print('=' * 80)
        print(f'Article ID: {article.id}')
        print(f'Language: {article.language}')
        print(f'Published URL: {article.published_url}')
        print('=' * 80)
        
        print(f'\n📝 Title field:')
        print(f'   "{article.title}"')
        
        print(f'\n📋 Layout Data:')
        if article.layout_data:
            layout_data_str = json.dumps(article.layout_data, indent=2, ensure_ascii=False)
            print(layout_data_str)
            
            # Check for title in layout_data
            if 'title' in article.layout_data:
                print(f'\n⚠️  FOUND "title" in layout_data:')
                print(f'   "{article.layout_data["title"]}"')
                print(f'\n   Comparison:')
                print(f'   - Title field: "{article.title}"')
                print(f'   - Layout data title: "{article.layout_data["title"]}"')
                if article.title != article.layout_data['title']:
                    print(f'   ❌ MISMATCH DETECTED!')
                else:
                    print(f'   ✅ Titles match')
            
            # Check for title_parts
            if 'title_parts' in article.layout_data:
                print(f'\n📌 Title parts in layout_data:')
                title_parts = article.layout_data['title_parts']
                if isinstance(title_parts, list):
                    for i, part in enumerate(title_parts):
                        if isinstance(part, dict):
                            print(f'   Part {i}: {part}')
                        else:
                            print(f'   Part {i}: {part}')
            
            # Check for list_items (which might have titles)
            if 'list_items' in article.layout_data:
                print(f'\n📋 List items in layout_data:')
                list_items = article.layout_data['list_items']
                if isinstance(list_items, list):
                    for i, item in enumerate(list_items):
                        if isinstance(item, dict) and 'title' in item:
                            print(f'   Item {i} title: "{item["title"]}"')
        else:
            print('   (empty)')
        
        # Check if there's an EN version
        if article.language == 'da':
            en_article = Article.query.filter_by(
                canonical_id=article.id,
                language='en'
            ).first()
            if en_article:
                print(f'\n🌐 English version (ID: {en_article.id}):')
                print(f'   Title: "{en_article.title}"')
                if en_article.layout_data and 'title' in en_article.layout_data:
                    print(f'   Layout data title: "{en_article.layout_data["title"]}"')

if __name__ == '__main__':
    check_article_35732()
