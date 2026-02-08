"""
Script để debug nguyên nhân trùng lặp đoạn văn
Kiểm tra HTML structure của article để tìm nguyên nhân
"""
import sys
import os
import argparse
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, ArticleDetail

def debug_article_html_structure(url):
    """Debug HTML structure của một article"""
    with app.app_context():
        article_detail = ArticleDetail.query.filter_by(published_url=url).first()
        
        if not article_detail:
            print(f"❌ Không tìm thấy article detail với URL: {url}")
            return
        
        print(f"\n🔍 Debug HTML structure cho article:")
        print(f"   ID: {article_detail.id}")
        print(f"   Published URL: {article_detail.published_url}")
        print(f"   Language: {article_detail.language}")
        
        # Kiểm tra content_blocks để tìm duplicate
        if not article_detail.content_blocks:
            print(f"\n❌ Không có content_blocks")
            return
        
        # Tìm các paragraph blocks
        paragraph_blocks = []
        for idx, block in enumerate(article_detail.content_blocks):
            if block.get('type') == 'paragraph':
                text = block.get('text', '') or block.get('html', '')
                if text:
                    # Normalize để so sánh
                    normalized = ' '.join(text.split())
                    paragraph_blocks.append({
                        'index': idx,
                        'text': normalized[:200] + '...' if len(normalized) > 200 else normalized,
                        'full_text': normalized
                    })
        
        # Tìm duplicate
        print(f"\n📝 Tìm thấy {len(paragraph_blocks)} paragraph blocks:")
        for i, p1 in enumerate(paragraph_blocks):
            for j, p2 in enumerate(paragraph_blocks[i+1:], i+1):
                if p1['full_text'] == p2['full_text']:
                    print(f"\n   ⚠️  DUPLICATE FOUND:")
                    print(f"      Block {p1['index']}: {p1['text']}")
                    print(f"      Block {p2['index']}: {p2['text']}")
        
        # Giải thích cấu trúc
        print(f"\n📊 Content blocks structure:")
        for idx, block in enumerate(article_detail.content_blocks):
            block_type = block.get('type', 'unknown')
            order = block.get('order', idx)
            print(f"   [{order}] {block_type}: ", end='')
            
            if block_type == 'paragraph':
                text = block.get('text', '')[:100]
                print(f"{text}...")
            elif block_type in ['title', 'subtitle', 'heading']:
                text = block.get('text', '')[:100]
                print(f"{text}...")
            else:
                print(f"(no text)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Debug HTML structure để tìm nguyên nhân duplicate')
    parser.add_argument('--url', type=str, required=True, help='URL của article cần debug')
    
    args = parser.parse_args()
    debug_article_html_structure(args.url)
