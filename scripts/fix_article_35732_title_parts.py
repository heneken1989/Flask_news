"""
Script để fix article 35732: Đồng bộ title_parts với title field
Vấn đề: title_parts có "Pipaluk heather:" nhưng title field có "Pipaluk Lynge:"
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article
from sqlalchemy.orm.attributes import flag_modified
import re

def reconstruct_title_parts_from_title(title, original_title_parts):
    """
    Reconstruct title_parts từ title field, giữ nguyên color_class từ original
    """
    if not original_title_parts or not isinstance(original_title_parts, list):
        return [{'text': title, 'color_class': None}]
    
    # Tìm part đầu tiên có color_class (highlighted part)
    first_highlighted = None
    for part in original_title_parts:
        if isinstance(part, dict) and part.get('color_class'):
            first_highlighted = part
            break
    
    # Strategy: Split title theo ":" nếu có (thường highlighted part là phần trước ":")
    if ':' in title:
        parts = title.split(':', 1)
        if len(parts) == 2:
            # Part đầu tiên (trước ":") thường là highlighted
            color_class = first_highlighted.get('color_class') if first_highlighted else None
            return [
                {'text': parts[0] + ':', 'color_class': color_class},
                {'text': parts[1], 'color_class': None}
            ]
    
    # Nếu không có ":", giữ highlight cho toàn bộ hoặc part đầu tiên
    color_class = first_highlighted.get('color_class') if first_highlighted else None
    return [{'text': title, 'color_class': color_class}]

def fix_article_35732(dry_run=True):
    """
    Fix article 35732: Đồng bộ title_parts với title field
    """
    with app.app_context():
        article = Article.query.get(35732)
        if not article:
            print('❌ Article 35732 not found')
            return
        
        print('=' * 80)
        print(f'Fixing Article ID: {article.id}')
        print(f'Language: {article.language}')
        print('=' * 80)
        
        print(f'\n📝 Current Title field:')
        print(f'   "{article.title}"')
        
        if not article.layout_data or 'title_parts' not in article.layout_data:
            print('   ⚠️  No title_parts in layout_data')
            return
        
        current_title_parts = article.layout_data['title_parts']
        print(f'\n📋 Current title_parts:')
        for i, part in enumerate(current_title_parts):
            if isinstance(part, dict):
                print(f'   Part {i}: "{part.get("text", "")}" (color: {part.get("color_class")})')
        
        # Reconstruct title từ parts hiện tại
        reconstructed = ''.join([
            p.get('text', '') if isinstance(p, dict) else str(p) 
            for p in current_title_parts
        ])
        print(f'\n🔍 Reconstructed from current parts: "{reconstructed}"')
        
        if reconstructed.strip() == article.title.strip():
            print('   ✅ Title parts already match title field!')
            return
        
        print(f'\n⚠️  MISMATCH DETECTED!')
        print(f'   Title field: "{article.title}"')
        print(f'   Reconstructed: "{reconstructed}"')
        
        # Reconstruct title_parts từ title field
        new_title_parts = reconstruct_title_parts_from_title(article.title, current_title_parts)
        
        print(f'\n🔧 New title_parts:')
        for i, part in enumerate(new_title_parts):
            if isinstance(part, dict):
                print(f'   Part {i}: "{part.get("text", "")}" (color: {part.get("color_class")})')
        
        # Verify reconstruction
        new_reconstructed = ''.join([
            p.get('text', '') if isinstance(p, dict) else str(p) 
            for p in new_title_parts
        ])
        print(f'\n✅ New reconstructed: "{new_reconstructed}"')
        
        if new_reconstructed.strip() != article.title.strip():
            print(f'   ⚠️  Warning: New reconstruction does not match title field!')
            print(f'   Title: "{article.title}"')
            print(f'   Reconstructed: "{new_reconstructed}"')
            # Fallback: Tạo parts đơn giản
            if ':' in article.title:
                parts = article.title.split(':', 1)
                new_title_parts = [
                    {'text': parts[0] + ':', 'color_class': current_title_parts[0].get('color_class') if current_title_parts and isinstance(current_title_parts[0], dict) else None},
                    {'text': parts[1], 'color_class': None}
                ]
                print(f'\n   🔄 Using fallback split by ":"')
                print(f'   Part 0: "{new_title_parts[0]["text"]}"')
                print(f'   Part 1: "{new_title_parts[1]["text"]}"')
        
        if not dry_run:
            # Update layout_data
            article.layout_data['title_parts'] = new_title_parts
            flag_modified(article, 'layout_data')
            db.session.commit()
            print(f'\n✅ Fixed! Updated title_parts in layout_data')
        else:
            print(f'\n⚠️  DRY RUN - No changes made')
            print(f'   Run with dry_run=False to apply changes')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fix article 35732 title_parts')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    args = parser.parse_args()
    
    fix_article_35732(dry_run=not args.apply)
