#!/usr/bin/env python3
"""
Migration script: Add multi-language support to articles table
Purpose: Hỗ trợ lưu trữ articles với 3 ngôn ngữ: DK, KL, EN
"""

import sys
import os

# Add parent directory to path để import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import db
from sqlalchemy import text

def upgrade():
    """Add language support columns to articles table"""
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='articles' AND column_name='language'
            """))
            
            if result.fetchone():
                print("⚠️  Language columns already exist. Skipping migration.")
                return
            
            # Add language column
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN language VARCHAR(2) NOT NULL DEFAULT 'da'
            """))
            
            # Add canonical_id column (nullable, will add foreign key later)
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN canonical_id INTEGER
            """))
            
            # Add original_language column
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN original_language VARCHAR(2) DEFAULT 'da'
            """))
            
            # Add foreign key constraint for canonical_id
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD CONSTRAINT fk_article_canonical 
                FOREIGN KEY (canonical_id) REFERENCES articles(id) ON DELETE SET NULL
            """))
            
            # Create indexes for faster querying
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_language 
                ON articles(language)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_canonical_language 
                ON articles(canonical_id, language)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_section_language 
                ON articles(section, language, display_order)
            """))
            
            db.session.commit()
            print("✅ Added language support columns to 'articles' table:")
            print("   - language (VARCHAR(2), default 'da')")
            print("   - canonical_id (INTEGER, FK to articles.id)")
            print("   - original_language (VARCHAR(2), default 'da')")
            print("✅ Created indexes:")
            print("   - idx_language")
            print("   - idx_canonical_language")
            print("   - idx_section_language")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding language columns: {e}")
            raise

def downgrade():
    """Remove language support columns from articles table"""
    with app.app_context():
        try:
            # Drop indexes first
            db.session.execute(text("""
                DROP INDEX IF EXISTS idx_section_language
            """))
            
            db.session.execute(text("""
                DROP INDEX IF EXISTS idx_canonical_language
            """))
            
            db.session.execute(text("""
                DROP INDEX IF EXISTS idx_language
            """))
            
            # Drop foreign key constraint
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP CONSTRAINT IF EXISTS fk_article_canonical
            """))
            
            # Drop columns
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP COLUMN IF EXISTS original_language
            """))
            
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP COLUMN IF EXISTS canonical_id
            """))
            
            db.session.execute(text("""
                ALTER TABLE articles 
                DROP COLUMN IF EXISTS language
            """))
            
            db.session.commit()
            print("✅ Dropped language support columns from 'articles' table.")
            print("✅ Dropped related indexes.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error dropping language columns: {e}")
            raise

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration: Add multi-language support to articles')
    parser.add_argument('--downgrade', action='store_true', help='Rollback migration')
    args = parser.parse_args()
    
    if args.downgrade:
        print("🔄 Rolling back migration: Remove language support...")
        downgrade()
    else:
        print("🔄 Running migration: Add language support...")
        upgrade()
    
    print("✅ Migration completed successfully.")
    return 0

if __name__ == '__main__':
    sys.exit(main())

