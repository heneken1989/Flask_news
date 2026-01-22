"""
Migration script để thêm cột published_url_en vào bảng articles

Usage:
    python deploy/migrate_add_published_url_en_article.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from sqlalchemy import text

def migrate():
    """Thêm cột published_url_en vào bảng articles"""
    with app.app_context():
        try:
            print("🔄 Starting migration: Add published_url_en column to articles...")
            
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'articles' 
                AND column_name = 'published_url_en'
            """))
            
            if result.fetchone():
                print("   ℹ️  Column published_url_en already exists, skipping...")
                return
            
            # Add column
            print("   ➕ Adding published_url_en column...")
            db.session.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN published_url_en VARCHAR(500)
            """))
            
            # Add index
            print("   ➕ Adding index on published_url_en...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_articles_published_url_en 
                ON articles(published_url_en)
            """))
            
            db.session.commit()
            print("   ✅ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    migrate()

