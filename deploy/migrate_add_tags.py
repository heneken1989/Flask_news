"""
Migration script để thêm cột tags vào bảng articles

Usage:
    python deploy/migrate_add_tags.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from sqlalchemy import text

def migrate():
    """Thêm cột tags vào bảng articles"""
    with app.app_context():
        try:
            print("🔄 Starting migration: Add tags column to articles...")
            
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'articles' 
                AND column_name = 'tags'
            """))
            
            if result.fetchone():
                print("   ℹ️  Column tags already exists, skipping...")
                return
            
            # Add column (JSON type for PostgreSQL)
            print("   ➕ Adding tags column (JSON type)...")
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN tags JSONB
            """))
            
            # Add GIN index for faster JSON queries
            print("   ➕ Adding GIN index on tags...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_articles_tags_gin 
                ON articles USING GIN (tags)
            """))
            
            db.session.commit()
            print("   ✅ Migration completed successfully!")
            print("   ℹ️  Note: Tags will be populated when articles are crawled/updated")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    migrate()

