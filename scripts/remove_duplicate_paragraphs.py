"""
Script để tự động xóa các đoạn văn trùng lặp (100% giống nhau) trong article details

Usage:
    python flask/scripts/remove_duplicate_paragraphs.py --dry-run  # Chỉ xem, không xóa
    python flask/scripts/remove_duplicate_paragraphs.py            # Thực sự xóa
    python flask/scripts/remove_duplicate_paragraphs.py --limit 10  # Giới hạn số lượng
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

def find_duplicate_indices(article_detail):
    """
    Tìm các index của các đoạn văn trùng lặp (100% giống nhau)
    
    Returns:
        set: Set các index cần xóa (giữ lại index nhỏ hơn)
    """
    if not article_detail or not article_detail.content_blocks:
        return set()
    
    indices_to_remove = set()
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
                        'normalized': normalized
                    })
    
    # So sánh từng cặp
    for i in range(len(text_blocks)):
        for j in range(i + 1, len(text_blocks)):
            block1 = text_blocks[i]
            block2 = text_blocks[j]
            
            # Tính độ tương đồng
            sim = similarity(block1['normalized'], block2['normalized'])
            
            # Chỉ xóa nếu trùng lặp 100% (hoàn toàn giống nhau)
            if sim >= 1.0:
                # Giữ lại block có index nhỏ hơn, xóa block có index lớn hơn
                indices_to_remove.add(block2['index'])
    
    return indices_to_remove

def remove_duplicate_paragraphs(dry_run=True, limit=None, url=None):
    """
    Xóa các đoạn văn trùng lặp (100% giống nhau) trong article details
    
    Args:
        dry_run: Nếu True, chỉ in ra những gì sẽ được xóa, không xóa thực sự
        limit: Giới hạn số lượng article details để xử lý (None = tất cả)
        url: URL cụ thể của article cần xử lý (None = tất cả)
    """
    with app.app_context():
        # Nếu có URL cụ thể, chỉ xử lý article đó
        if url:
            article_detail = ArticleDetail.query.filter_by(published_url=url).first()
            if not article_detail:
                print(f"❌ Không tìm thấy article detail với URL: {url}")
                return
            article_details = [article_detail]
        else:
            # Lấy tất cả article details có content_blocks
            query = ArticleDetail.query.filter(
                ArticleDetail.content_blocks.isnot(None)
            )
            
            if limit:
                query = query.limit(limit)
            
            article_details = query.all()
        
        print(f"\n🔍 Kiểm tra {len(article_details)} article details để tìm duplicate paragraphs...\n")
        
        fixed_count = 0
        total_removed_blocks = 0
        articles_with_duplicates = []
        
        for article_detail in article_details:
            if not article_detail.content_blocks:
                continue
            
            # Tìm các index cần xóa
            indices_to_remove = find_duplicate_indices(article_detail)
            
            if not indices_to_remove:
                continue
            
            articles_with_duplicates.append({
                'article_detail': article_detail,
                'indices_to_remove': indices_to_remove
            })
        
        if not articles_with_duplicates:
            print(f"✅ Không tìm thấy article nào có duplicate paragraphs!")
            return
        
        print(f"⚠️  Tìm thấy {len(articles_with_duplicates)} articles có duplicate paragraphs:\n")
        
        for item in articles_with_duplicates:
            article_detail = item['article_detail']
            indices_to_remove = item['indices_to_remove']
            
            # Sắp xếp indices theo thứ tự giảm dần để xóa từ cuối lên (tránh ảnh hưởng đến index)
            sorted_indices = sorted(indices_to_remove, reverse=True)
            
            print(f"\n📰 Article Detail ID: {article_detail.id}")
            print(f"   Published URL: {article_detail.published_url}")
            print(f"   Language: {article_detail.language}")
            print(f"   Sẽ xóa {len(sorted_indices)} duplicate block(s) tại index: {sorted_indices}")
            
            # Hiển thị nội dung các blocks sẽ bị xóa
            for idx in sorted_indices:
                if idx < len(article_detail.content_blocks):
                    block = article_detail.content_blocks[idx]
                    block_type = block.get('type', 'unknown')
                    text = block.get('text', '') or block.get('html', '')
                    if text:
                        preview = text[:100] + '...' if len(text) > 100 else text
                        print(f"      - Block {idx} ({block_type}): {preview}")
            
            if dry_run:
                print(f"   ⚠️  DRY RUN: Sẽ xóa {len(sorted_indices)} block(s)")
            else:
                # Tạo list mới không chứa các blocks bị duplicate
                updated_blocks = []
                for idx, block in enumerate(article_detail.content_blocks):
                    if idx not in indices_to_remove:
                        updated_blocks.append(block)
                
                # Update content_blocks
                article_detail.content_blocks = updated_blocks
                # SQLAlchemy doesn't auto-detect dict/list mutations in JSON fields
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(article_detail, 'content_blocks')
                db.session.commit()
                
                fixed_count += 1
                total_removed_blocks += len(sorted_indices)
                print(f"   ✅ Đã xóa {len(sorted_indices)} duplicate block(s)")
        
        print(f"\n{'='*80}")
        print(f"📊 Summary:")
        print(f"   - Total article details checked: {len(article_details)}")
        print(f"   - Articles with duplicates: {len(articles_with_duplicates)}")
        
        if dry_run:
            total_blocks_to_remove = sum(len(item['indices_to_remove']) for item in articles_with_duplicates)
            print(f"   - Total blocks sẽ bị xóa: {total_blocks_to_remove}")
            print(f"\n⚠️  DRY RUN: Không có thay đổi nào được thực hiện")
            print(f"   Chạy lại script KHÔNG có --dry-run để thực sự xóa duplicate blocks")
        else:
            print(f"   - Articles fixed: {fixed_count}")
            print(f"   - Total blocks removed: {total_removed_blocks}")
            print(f"\n✅ Đã xóa tất cả duplicate paragraphs!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Xóa các đoạn văn trùng lặp trong article details')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Chỉ xem, không xóa (default: True - an toàn)')
    parser.add_argument('--no-dry-run', action='store_true',
                        help='Thực sự xóa (tắt dry-run mode)')
    parser.add_argument('--limit', type=int,
                        help='Giới hạn số lượng article details để xử lý')
    parser.add_argument('--url', type=str,
                        help='URL cụ thể của article cần xử lý')
    
    args = parser.parse_args()
    
    # Nếu có --no-dry-run, tắt dry-run
    dry_run = not args.no_dry_run if args.no_dry_run else args.dry_run
    
    remove_duplicate_paragraphs(dry_run=dry_run, limit=args.limit, url=args.url)
