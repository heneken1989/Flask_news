#!/usr/bin/env python3
"""
Script để xóa duplicate articles (cùng published_url + language)
Giữ lại article CŨ NHẤT (created_at nhỏ nhất), xóa các articles mới hơn
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import func

def remove_duplicate_articles(language='da', dry_run=True):
    """
    Xóa duplicate articles cho language cụ thể
    
    Args:
        language: Language code ('da', 'en', 'kl')
        dry_run: Nếu True, chỉ log không xóa
    """
    print(f"\n{'='*60}")
    print(f"🗑️  Removing duplicate articles for language: {language}")
    print(f"{'='*60}")
    print(f"   Dry run: {dry_run}")
    
    with app.app_context():
        # Find duplicate published_urls
        duplicates = db.session.query(
            Article.published_url,
            func.count(Article.id).label('count')
        ).filter(
            Article.language == language,
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).group_by(
            Article.published_url
        ).having(
            func.count(Article.id) > 1
        ).order_by(
            func.count(Article.id).desc()
        ).all()
        
        print(f"\n📊 Found {len(duplicates)} URLs with duplicate articles")
        
        if not duplicates:
            print(f"✅ No duplicates found!")
            return
        
        total_to_delete = 0
        total_to_keep = 0
        
        for url, count in duplicates:
            print(f"\n{'='*60}")
            print(f"🔍 Processing: {url[:80]}...")
            print(f"   Count: {count} articles")
            
            # Get all articles với URL này, sắp xếp theo created_at (cũ nhất trước)
            articles = Article.query.filter_by(
                published_url=url,
                language=language
            ).order_by(Article.created_at.asc()).all()
            
            # Giữ article ĐẦU TIÊN (cũ nhất), xóa các articles sau
            article_to_keep = articles[0]
            articles_to_delete = articles[1:]
            
            print(f"\n   ✅ KEEP (oldest):")
            print(f"      ID={article_to_keep.id}")
            print(f"      section={article_to_keep.section}")
            print(f"      is_home={article_to_keep.is_home}")
            print(f"      layout_type={article_to_keep.layout_type}")
            print(f"      created={article_to_keep.created_at}")
            
            print(f"\n   ❌ DELETE ({len(articles_to_delete)} articles):")
            for art in articles_to_delete:
                print(f"      ID={art.id}, section={art.section}, is_home={art.is_home}, layout_type={art.layout_type}, created={art.created_at}")
                
                if not dry_run:
                    db.session.delete(art)
                    total_to_delete += 1
                else:
                    total_to_delete += 1
            
            total_to_keep += 1
            
            if not dry_run:
                db.session.commit()
                print(f"      ✅ Deleted {len(articles_to_delete)} duplicate articles")
            else:
                print(f"      ⚠️  Would delete {len(articles_to_delete)} articles (dry run)")
        
        print(f"\n{'='*60}")
        print(f"✅ Duplicate removal completed")
        print(f"{'='*60}")
        print(f"   Articles to keep: {total_to_keep}")
        print(f"   Articles to delete: {total_to_delete}")
        
        if dry_run:
            print(f"\n⚠️  This was a DRY RUN. No articles were deleted.")
            print(f"   Run with --no-dry-run to actually delete duplicates")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove duplicate articles')
    parser.add_argument('--language', '-l', default='da', choices=['da', 'en', 'kl'],
                       help='Language code (default: da)')
    parser.add_argument('--no-dry-run', action='store_true',
                       help='Actually delete duplicates (default: dry run)')
    
    args = parser.parse_args()
    
    remove_duplicate_articles(
        language=args.language,
        dry_run=not args.no_dry_run
    )

