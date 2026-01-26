#!/usr/bin/env python3
"""
Script để xóa các articles sai của slider
Chỉ giữ lại slider containers (published_url='')
Xóa các articles có layout_type='slider' hoặc 'job_slider' nhưng có published_url
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article


def cleanup_slider_articles(dry_run=True):
    """
    Xóa các articles sai của slider
    
    Args:
        dry_run: Nếu True, chỉ log không xóa
    """
    print("="*80)
    print("🧹 CLEANUP SLIDER ARTICLES")
    print("="*80)
    print(f"   Dry run: {dry_run}")
    print()
    
    with app.app_context():
        # 1. Kiểm tra slider containers (đúng - cần giữ)
        slider_containers = Article.query.filter(
            Article.layout_type.in_(['slider', 'job_slider']),
            Article.published_url == ''
        ).all()
        
        print(f"✅ Slider Containers (giữ lại): {len(slider_containers)}")
        print()
        
        # 2. Tìm articles sai (có layout_type='slider' hoặc 'job_slider' nhưng có published_url)
        slider_articles_with_url = Article.query.filter(
            Article.layout_type.in_(['slider', 'job_slider']),
            Article.published_url != '',
            Article.published_url.isnot(None)
        ).all()
        
        print(f"❌ Articles sai (cần xóa): {len(slider_articles_with_url)}")
        print()
        
        if len(slider_articles_with_url) == 0:
            print("✅ Không có articles sai cần xóa")
            return
        
        # Hiển thị danh sách articles sẽ xóa
        print("📋 Danh sách articles sẽ xóa:")
        for idx, article in enumerate(slider_articles_with_url, 1):
            print(f"   {idx}. ID: {article.id}, published_url: {article.published_url[:60]}..., language: {article.language}, is_home: {article.is_home}")
        print()
        
        if dry_run:
            print("⚠️  DRY RUN: Không xóa articles (chạy với --execute để xóa thật)")
        else:
            # Xóa articles
            deleted_count = 0
            for article in slider_articles_with_url:
                print(f"   🗑️  Deleting article ID: {article.id} ({article.published_url[:60]}...)")
                db.session.delete(article)
                deleted_count += 1
            
            db.session.commit()
            print()
            print(f"✅ Đã xóa {deleted_count} articles sai")
        
        print()
        print("="*80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup slider articles')
    parser.add_argument('--execute', action='store_true', help='Thực sự xóa articles (mặc định: dry run)')
    
    args = parser.parse_args()
    
    cleanup_slider_articles(dry_run=not args.execute)

