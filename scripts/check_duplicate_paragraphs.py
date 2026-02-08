"""
Script để kiểm tra và tìm các đoạn văn trùng lặp trong article details

Usage:
    python scripts/check_duplicate_paragraphs.py --url "https://www.sermitsiaq.ag/..."  # Kiểm tra 1 article cụ thể
    python scripts/check_duplicate_paragraphs.py --all  # Kiểm tra tất cả articles
    python scripts/check_duplicate_paragraphs.py --all --limit 100  # Giới hạn số lượng
"""
import sys
import os
import argparse
import re
from collections import defaultdict
from difflib import SequenceMatcher

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, ArticleDetail

def similarity(a, b):
    """Tính độ tương đồng giữa 2 chuỗi (0-1)"""
    return SequenceMatcher(None, a, b).ratio()

def normalize_text(text):
    """Chuẩn hóa text để so sánh (loại bỏ whitespace thừa, lowercase)"""
    if not text:
        return ""
    # Loại bỏ HTML tags nếu có
    text = re.sub(r'<[^>]+>', '', text)
    # Loại bỏ whitespace thừa
    text = re.sub(r'\s+', ' ', text)
    # Strip
    text = text.strip()
    return text.lower()

def find_duplicate_paragraphs_in_article(article_detail):
    """
    Tìm các đoạn văn trùng lặp trong một article detail
    
    Returns:
        list of dict: Danh sách các cặp đoạn văn trùng lặp
    """
    if not article_detail or not article_detail.content_blocks:
        return []
    
    duplicates = []
    text_blocks = []
    
    # Lấy tất cả text từ paragraph và intro blocks
    for idx, block in enumerate(article_detail.content_blocks):
        block_type = block.get('type', '')
        if block_type in ['paragraph', 'intro']:
            # Thử lấy text từ nhiều nguồn
            text = block.get('text', '') or block.get('content', '')
            
            # Nếu không có text, thử extract từ HTML
            if not text:
                html = block.get('html', '')
                if html:
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        text = soup.get_text(separator=' ', strip=True)
                    except:
                        pass
            
            if text:
                normalized = normalize_text(text)
                if len(normalized) > 50:  # Chỉ kiểm tra đoạn văn dài hơn 50 ký tự
                    text_blocks.append({
                        'index': idx,
                        'type': block_type,
                        'original': text,
                        'normalized': normalized
                    })
    
    # So sánh từng cặp
    for i in range(len(text_blocks)):
        for j in range(i + 1, len(text_blocks)):
            block1 = text_blocks[i]
            block2 = text_blocks[j]
            
            # Tính độ tương đồng
            sim = similarity(block1['normalized'], block2['normalized'])
            
            # Chỉ báo cáo nếu trùng lặp 100% (hoàn toàn giống nhau)
            if sim >= 1.0:
                duplicates.append({
                    'block1_index': block1['index'],
                    'block1_type': block1['type'],
                    'block1_text': block1['original'][:200] + '...' if len(block1['original']) > 200 else block1['original'],
                    'block2_index': block2['index'],
                    'block2_type': block2['type'],
                    'block2_text': block2['original'][:200] + '...' if len(block2['original']) > 200 else block2['original'],
                    'similarity': sim
                })
    
    return duplicates

def check_specific_article(url):
    """Kiểm tra một article cụ thể"""
    with app.app_context():
        # Tìm article detail
        article_detail = ArticleDetail.query.filter_by(published_url=url).first()
        
        if not article_detail:
            print(f"❌ Không tìm thấy article detail với URL: {url}")
            return
        
        print(f"\n🔍 Kiểm tra article detail:")
        print(f"   ID: {article_detail.id}")
        print(f"   Published URL: {article_detail.published_url}")
        print(f"   Language: {article_detail.language}")
        
        duplicates = find_duplicate_paragraphs_in_article(article_detail)
        
        if not duplicates:
            print(f"\n✅ Không có đoạn văn trùng lặp")
        else:
            print(f"\n⚠️  Tìm thấy {len(duplicates)} cặp đoạn văn trùng lặp:")
            for dup in duplicates:
                print(f"\n   📌 Cặp {duplicates.index(dup) + 1}:")
                print(f"      Block {dup['block1_index']} ({dup['block1_type']}):")
                print(f"         {dup['block1_text']}")
                print(f"      Block {dup['block2_index']} ({dup['block2_type']}):")
                print(f"         {dup['block2_text']}")
                print(f"      Độ tương đồng: {dup['similarity']:.2%}")

def check_all_articles(limit=None):
    """Kiểm tra tất cả articles"""
    with app.app_context():
        query = ArticleDetail.query.filter(
            ArticleDetail.content_blocks.isnot(None)
        )
        
        if limit:
            query = query.limit(limit)
        
        article_details = query.all()
        
        print(f"\n🔍 Kiểm tra {len(article_details)} article details...\n")
        
        articles_with_duplicates = []
        
        for article_detail in article_details:
            duplicates = find_duplicate_paragraphs_in_article(article_detail)
            if duplicates:
                articles_with_duplicates.append({
                    'article_detail': article_detail,
                    'duplicates': duplicates
                })
        
        if not articles_with_duplicates:
            print(f"✅ Không tìm thấy article nào có đoạn văn trùng lặp")
        else:
            print(f"\n⚠️  Tìm thấy {len(articles_with_duplicates)} articles có đoạn văn trùng lặp:\n")
            
            for item in articles_with_duplicates:
                article_detail = item['article_detail']
                duplicates = item['duplicates']
                
                print(f"\n{'='*80}")
                print(f"📰 Article Detail ID: {article_detail.id}")
                print(f"   Published URL: {article_detail.published_url}")
                print(f"   Language: {article_detail.language}")
                print(f"   Số cặp trùng lặp: {len(duplicates)}")
                
                for dup in duplicates:
                    print(f"\n   📌 Cặp {duplicates.index(dup) + 1} (tương đồng {dup['similarity']:.2%}):")
                    print(f"      Block {dup['block1_index']} ({dup['block1_type']}):")
                    print(f"         {dup['block1_text']}")
                    print(f"      Block {dup['block2_index']} ({dup['block2_type']}):")
                    print(f"         {dup['block2_text']}")
        
        print(f"\n{'='*80}")
        print(f"📊 Summary:")
        print(f"   - Total articles checked: {len(article_details)}")
        print(f"   - Articles with duplicates: {len(articles_with_duplicates)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Kiểm tra đoạn văn trùng lặp trong article details')
    parser.add_argument('--url', type=str, help='URL của article cần kiểm tra')
    parser.add_argument('--all', action='store_true', help='Kiểm tra tất cả articles')
    parser.add_argument('--limit', type=int, help='Giới hạn số lượng articles khi dùng --all')
    
    args = parser.parse_args()
    
    if args.url:
        check_specific_article(args.url)
    elif args.all:
        check_all_articles(limit=args.limit)
    else:
        parser.print_help()
        print("\n❌ Vui lòng chỉ định --url hoặc --all")
