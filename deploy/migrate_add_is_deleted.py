#!/usr/bin/env python3
"""
Migration script: Add is_deleted field to articles table
Đặc biệt cho 1_with_list_left/right articles để tạo mới mỗi lần update
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

from app import app
from database import db
from sqlalchemy import text


def check_column_exists():
    """Check if is_deleted column already exists"""
    with app.app_context():
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'articles' 
            AND column_name = 'is_deleted'
        """))
        return result.fetchone() is not None


def migrate():
    """Add is_deleted column to articles table"""
    print("\n" + "="*60)
    print("📦 Migration: Add is_deleted field to articles table")
    print("="*60)
    
    with app.app_context():
        # Check if column already exists
        if check_column_exists():
            print("   ✅ Column 'is_deleted' already exists, skipping migration")
            return
        
        try:
            print("   🔄 Adding is_deleted column...")
            
            # Add is_deleted column
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE
            """))
            
            print("   🔄 Creating index on is_deleted...")
            
            # Create index for is_deleted (for faster queries)
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_articles_is_deleted 
                ON articles (is_deleted)
            """))
            
            # Commit changes
            db.session.commit()
            
            print("   ✅ Migration completed successfully!")
            print("\n" + "="*60)
            print("📊 Summary:")
            print("="*60)
            print("   ✅ Added is_deleted column (BOOLEAN, default FALSE)")
            print("   ✅ Created index ix_articles_is_deleted")
            print("   ℹ️  Purpose: Soft delete for 1_with_list_left/right articles")
            print("   ℹ️  Usage: Mark old articles before creating new ones")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Migration failed: {e}")
            raise


def rollback():
    """Remove is_deleted column from articles table"""
    print("\n" + "="*60)
    print("🔄 Rollback: Remove is_deleted field from articles table")
    print("="*60)
    
    with app.app_context():
        if not check_column_exists():
            print("   ℹ️  Column 'is_deleted' does not exist, nothing to rollback")
            return
        
        try:
            print("   🔄 Removing index...")
            db.session.execute(text("""
                DROP INDEX IF EXISTS ix_articles_is_deleted
            """))
            
            print("   🔄 Removing is_deleted column...")
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP COLUMN IF EXISTS is_deleted
            """))
            
            db.session.commit()
            print("   ✅ Rollback completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Rollback failed: {e}")
            raise


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate is_deleted field')
    parser.add_argument('--rollback', action='store_true', 
                       help='Rollback migration (remove is_deleted field)')
    args = parser.parse_args()
    
    if args.rollback:
        rollback()
    else:
        migrate()

