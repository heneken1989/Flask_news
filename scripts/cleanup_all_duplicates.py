#!/usr/bin/env python3
"""
Script để cleanup tất cả duplicate articles (cả home và sections)
- Xóa temp articles cũ (is_temp=True nhưng không có canonical_id mới)
- Xóa duplicate articles (cùng canonical_id, giữ lại mới nhất)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from sqlalchemy import func

def cleanup_temp_articles():
    """Xóa temp articles cũ (orphaned temp articles)"""
    with app.app_context():
        # Temp articles không có canonical_id (orphaned)
        orphaned_temp = Article.query.filter_by(
            is_temp=True
        ).filter(Article.canonical_id.is_(None)).all()
        
        count = len(orphaned_temp)
        print(f"📊 Found {count} orphaned temp articles")
        
        if count > 0:
            for article in orphaned_temp:
                db.session.delete(article)
            db.session.commit()
            print(f"✅ Deleted {count} orphaned temp articles")
        
        return count


def cleanup_duplicate_articles():
    """Xóa duplicate articles (cùng canonical_id, giữ lại mới nhất)"""
    with app.app_context():
        # Tìm các canonical_id có nhiều hơn 1 article (cùng language)
        duplicates = db.session.query(
            Article.canonical_id,
            Article.language,
            func.count(Article.id).label('count')
        ).filter(
            Article.canonical_id.isnot(None)
        ).group_by(Article.canonical_id, Article.language)\
         .having(func.count(Article.id) > 1).all()
        
        print(f"📊 Found {len(duplicates)} canonical_id+language combinations with duplicates")
        
        total_deleted = 0
        
        for canonical_id, language, count in duplicates:
            # Lấy tất cả articles với canonical_id và language này
            articles = Article.query.filter_by(
                canonical_id=canonical_id,
                language=language
            ).order_by(Article.id.desc()).all()  # Mới nhất trước
            
            # Giữ lại article đầu tiên (mới nhất), xóa các article còn lại
            keep_article = articles[0]
            articles_to_delete = articles[1:]
            
            print(f"   Canonical ID {canonical_id} ({language}): {count} articles, keeping ID {keep_article.id}, deleting {len(articles_to_delete)} duplicates")
            
            for article in articles_to_delete:
                db.session.delete(article)
                total_deleted += 1
        
        db.session.commit()
        print(f"\n✅ Deleted {total_deleted} duplicate articles")
        return total_deleted


def cleanup_old_temp_articles():
    """Xóa temp articles cũ (is_temp=True) nếu đã có non-temp version"""
    with app.app_context():
        # Tìm temp articles có canonical_id, và đã có non-temp version
        temp_articles = Article.query.filter_by(is_temp=True).all()
        
        deleted_count = 0
        for temp_article in temp_articles:
            if temp_article.canonical_id:
                # Check xem đã có non-temp version chưa
                non_temp = Article.query.filter_by(
                    canonical_id=temp_article.canonical_id,
                    language=temp_article.language,
                    is_temp=False
                ).first()
                
                if non_temp:
                    # Đã có non-temp version, xóa temp
                    print(f"   Deleting temp article {temp_article.id} (has non-temp version {non_temp.id})")
                    db.session.delete(temp_article)
                    deleted_count += 1
        
        db.session.commit()
        print(f"✅ Deleted {deleted_count} old temp articles (have non-temp versions)")
        return deleted_count


def show_statistics():
    """Hiển thị thống kê articles"""
    with app.app_context():
        print("\n📊 Article Statistics:")
        
        # By language
        for lang in ['da', 'kl', 'en']:
            total = Article.query.filter_by(language=lang).count()
            temp = Article.query.filter_by(language=lang, is_temp=True).count()
            non_temp = Article.query.filter_by(language=lang, is_temp=False).count()
            home = Article.query.filter_by(language=lang, is_home=True).count()
            sections = Article.query.filter_by(language=lang, is_home=False).count()
            
            print(f"\n   {lang.upper()}:")
            print(f"      Total: {total}")
            print(f"      Temp: {temp}, Non-temp: {non_temp}")
            print(f"      Home: {home}, Sections: {sections}")
        
        # Duplicates
        duplicates = db.session.query(
            Article.canonical_id,
            Article.language,
            func.count(Article.id).label('count')
        ).filter(
            Article.canonical_id.isnot(None)
        ).group_by(Article.canonical_id, Article.language)\
         .having(func.count(Article.id) > 1).count()
        
        print(f"\n   Duplicates: {duplicates} canonical_id+language combinations")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Cleanup duplicate and temp articles')
    parser.add_argument('--action', choices=['stats', 'cleanup-all', 'cleanup-temp', 'cleanup-duplicates', 'cleanup-old-temp'],
                       default='stats', help='Action to perform')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    args = parser.parse_args()
    
    with app.app_context():
        if args.action == 'stats':
            show_statistics()
        elif args.action == 'cleanup-all':
            show_statistics()
            if not args.yes:
                response = input("\n⚠️  Do you want to cleanup all duplicates and temp articles? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Cancelled")
                    return
            cleanup_temp_articles()
            cleanup_duplicate_articles()
            cleanup_old_temp_articles()
            print("\n" + "="*60)
            show_statistics()
        elif args.action == 'cleanup-temp':
            show_statistics()
            if not args.yes:
                response = input("\n⚠️  Do you want to cleanup orphaned temp articles? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Cancelled")
                    return
            cleanup_temp_articles()
            show_statistics()
        elif args.action == 'cleanup-duplicates':
            show_statistics()
            if not args.yes:
                response = input("\n⚠️  Do you want to cleanup duplicate articles? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Cancelled")
                    return
            cleanup_duplicate_articles()
            show_statistics()
        elif args.action == 'cleanup-old-temp':
            show_statistics()
            if not args.yes:
                response = input("\n⚠️  Do you want to cleanup old temp articles? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Cancelled")
                    return
            cleanup_old_temp_articles()
            show_statistics()


if __name__ == '__main__':
    main()

