#!/usr/bin/env python3
"""
Migration script: Add is_temp field to articles table
Purpose: Đánh dấu articles đang trong quá trình translate (temp) để tránh duplicate
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import db
from sqlalchemy import text

def upgrade():
    """Add is_temp column to articles table"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='articles' AND column_name='is_temp'
            """))
            
            if result.fetchone():
                print("⚠️  Column 'is_temp' already exists. Skipping migration.")
                return
            
            # Add is_temp column
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN is_temp BOOLEAN DEFAULT FALSE
            """))
            
            # Create index for faster querying
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_is_temp 
                ON articles(is_temp, language)
            """))
            
            db.session.commit()
            print("✅ Added 'is_temp' column to 'articles' table.")
            print("✅ Created index 'idx_is_temp' for faster querying.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding 'is_temp' column: {e}")
            raise

def downgrade():
    """Remove is_temp column from articles table"""
    with app.app_context():
        try:
            # Drop index first
            db.session.execute(text("""
                DROP INDEX IF EXISTS idx_is_temp
            """))
            
            # Drop column
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP COLUMN IF EXISTS is_temp
            """))
            
            db.session.commit()
            print("✅ Dropped 'is_temp' column from 'articles' table.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error dropping 'is_temp' column: {e}")
            raise

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Migration: Add is_temp field to articles')
    parser.add_argument('--downgrade', action='store_true', help='Rollback migration')
    args = parser.parse_args()
    
    if args.downgrade:
        print("🔄 Rolling back migration: Remove is_temp field...")
        downgrade()
    else:
        print("🔄 Running migration: Add is_temp field...")
        upgrade()
    
    print("✅ Migration completed successfully.")
    return 0

if __name__ == '__main__':
    sys.exit(main())

