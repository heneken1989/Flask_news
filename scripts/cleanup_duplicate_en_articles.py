#!/usr/bin/env python3
"""
Script để xóa các EN articles duplicate
- Xóa các EN articles có cùng canonical_id (giữ lại bản mới nhất)
- Hoặc xóa tất cả EN articles để re-translate lại
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import func
import argparse


def remove_duplicate_en_articles():
    """Xóa các EN articles duplicate (giữ lại bản mới nhất cho mỗi canonical_id)"""
    with app.app_context():
        # Tìm các canonical_id có nhiều hơn 1 EN article
        duplicates = db.session.query(
            Article.canonical_id,
            func.count(Article.id).label('count')
        ).filter(
            Article.language == 'en',
            Article.is_home == True,
            Article.canonical_id.isnot(None)
        ).group_by(Article.canonical_id).having(func.count(Article.id) > 1).all()
        
        print(f"📊 Found {len(duplicates)} canonical_ids with duplicate EN articles")
        
        total_deleted = 0
        
        for canonical_id, count in duplicates:
            # Lấy tất cả EN articles với canonical_id này
            en_articles = Article.query.filter_by(
                language='en',
                is_home=True,
                canonical_id=canonical_id
            ).order_by(Article.id.desc()).all()  # Sắp xếp theo ID desc (mới nhất trước)
            
            # Giữ lại article đầu tiên (mới nhất), xóa các article còn lại
            keep_article = en_articles[0]
            articles_to_delete = en_articles[1:]
            
            print(f"   Canonical ID {canonical_id}: {count} articles, keeping ID {keep_article.id}, deleting {len(articles_to_delete)} duplicates")
            
            for article in articles_to_delete:
                db.session.delete(article)
                total_deleted += 1
        
        db.session.commit()
        print(f"\n✅ Deleted {total_deleted} duplicate EN articles")
        return total_deleted


def remove_all_en_articles():
    """Xóa tất cả EN articles (để re-translate lại từ đầu)"""
    with app.app_context():
        en_articles = Article.query.filter_by(
            language='en',
            is_home=True
        ).all()
        
        count = len(en_articles)
        print(f"📊 Found {count} EN articles to delete")
        
        if count > 0:
            for article in en_articles:
                db.session.delete(article)
            
            db.session.commit()
            print(f"✅ Deleted all {count} EN articles")
        
        return count


def show_en_articles_stats():
    """Hiển thị thống kê EN articles"""
    with app.app_context():
        # Tổng số EN articles
        total = Article.query.filter_by(language='en', is_home=True).count()
        
        # Số EN articles có canonical_id
        with_canonical = Article.query.filter_by(
            language='en',
            is_home=True
        ).filter(Article.canonical_id.isnot(None)).count()
        
        # Số EN articles không có canonical_id (orphaned)
        orphaned = Article.query.filter_by(
            language='en',
            is_home=True
        ).filter(Article.canonical_id.is_(None)).count()
        
        # Số canonical_id có duplicate
        duplicates = db.session.query(
            Article.canonical_id,
            func.count(Article.id).label('count')
        ).filter(
            Article.language == 'en',
            Article.is_home == True,
            Article.canonical_id.isnot(None)
        ).group_by(Article.canonical_id).having(func.count(Article.id) > 1).count()
        
        print(f"\n📊 EN Articles Statistics:")
        print(f"   - Total EN articles: {total}")
        print(f"   - With canonical_id: {with_canonical}")
        print(f"   - Orphaned (no canonical_id): {orphaned}")
        print(f"   - Canonical IDs with duplicates: {duplicates}")
        
        # Show some duplicate examples
        if duplicates > 0:
            print(f"\n   Examples of duplicates:")
            duplicate_examples = db.session.query(
                Article.canonical_id,
                func.count(Article.id).label('count')
            ).filter(
                Article.language == 'en',
                Article.is_home == True,
                Article.canonical_id.isnot(None)
            ).group_by(Article.canonical_id).having(func.count(Article.id) > 1).limit(5).all()
            
            for canonical_id, count in duplicate_examples:
                print(f"      - Canonical ID {canonical_id}: {count} EN articles")


def remove_orphaned_en_articles():
    """Xóa các EN articles không có canonical_id (orphaned)"""
    with app.app_context():
        orphaned = Article.query.filter_by(
            language='en',
            is_home=True
        ).filter(Article.canonical_id.is_(None)).all()
        
        count = len(orphaned)
        print(f"📊 Found {count} orphaned EN articles (no canonical_id)")
        
        if count > 0:
            for article in orphaned:
                db.session.delete(article)
            
            db.session.commit()
            print(f"✅ Deleted {count} orphaned EN articles")
        
        return count


def main():
    parser = argparse.ArgumentParser(description='Cleanup duplicate EN articles')
    parser.add_argument('--action', choices=['stats', 'remove-duplicates', 'remove-orphaned', 'remove-all'], 
                       default='stats', help='Action to perform')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    with app.app_context():
        if args.action == 'stats':
            show_en_articles_stats()
        elif args.action == 'remove-duplicates':
            show_en_articles_stats()
            print("\n" + "="*60)
            response = input("⚠️  Do you want to remove duplicate EN articles? (yes/no): ")
            if response.lower() == 'yes':
                remove_duplicate_en_articles()
                print("\n" + "="*60)
                show_en_articles_stats()
            else:
                print("❌ Cancelled")
        elif args.action == 'remove-orphaned':
            show_en_articles_stats()
            if not args.yes:
                print("\n" + "="*60)
                response = input("⚠️  Do you want to remove orphaned EN articles (no canonical_id)? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Cancelled")
                    return
            remove_orphaned_en_articles()
            print("\n" + "="*60)
            show_en_articles_stats()
        elif args.action == 'remove-all':
            show_en_articles_stats()
            if not args.yes:
                print("\n" + "="*60)
                response = input("⚠️  WARNING: This will delete ALL EN articles! Continue? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Cancelled")
                    return
            remove_all_en_articles()
            print("\n" + "="*60)
            show_en_articles_stats()


if __name__ == '__main__':
    main()

