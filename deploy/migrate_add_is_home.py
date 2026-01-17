#!/usr/bin/env python3
"""
Migration script: Add is_home field to articles table
Purpose: Đánh dấu articles nào thuộc về trang home
"""

import sys
import os

# Add parent directory to path để import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import db
from sqlalchemy import text

def upgrade():
    """Add is_home column to articles table"""
    with app.app_context():
        try:
            # Kiểm tra xem column đã tồn tại chưa
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='articles' AND column_name='is_home'
            """))
            
            if result.fetchone():
                print("⚠️  Column 'is_home' already exists. Skipping migration.")
                return
            
            # Add is_home column
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN is_home BOOLEAN DEFAULT FALSE
            """))
            
            # Create index for faster querying
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_is_home 
                ON articles(is_home, display_order)
            """))
            
            db.session.commit()
            print("✅ Added 'is_home' column to 'articles' table.")
            print("✅ Created index 'idx_is_home' for faster querying.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding 'is_home' column: {e}")
            raise

def downgrade():
    """Remove is_home column from articles table"""
    with app.app_context():
        try:
            # Drop index first
            db.session.execute(text("""
                DROP INDEX IF EXISTS idx_is_home
            """))
            
            # Drop column
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP COLUMN IF EXISTS is_home
            """))
            
            db.session.commit()
            print("✅ Dropped 'is_home' column from 'articles' table.")
            print("✅ Dropped index 'idx_is_home'.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error dropping 'is_home' column: {e}")
            raise

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration: Add is_home field to articles')
    parser.add_argument('--downgrade', action='store_true', help='Rollback migration')
    args = parser.parse_args()
    
    if args.downgrade:
        print("🔄 Rolling back migration: Remove is_home field...")
        downgrade()
    else:
        print("🔄 Running migration: Add is_home field...")
        upgrade()
    
    print("✅ Migration completed successfully.")
    return 0

if __name__ == '__main__':
    sys.exit(main())

