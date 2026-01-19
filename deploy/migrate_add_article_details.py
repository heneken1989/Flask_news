"""
Migration script to add article_details table
Run: python deploy/migrate_add_article_details.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, ArticleDetail
from sqlalchemy import text

def migrate():
    """Add article_details table"""
    with app.app_context():
        try:
            # Check if table already exists
            inspector = db.inspect(db.engine)
            if 'article_details' in inspector.get_table_names():
                print("✅ Table 'article_details' already exists")
                return
            
            # Create table
            print("Creating table 'article_details'...")
            db.create_all()
            
            # Verify table was created
            if 'article_details' in inspector.get_table_names():
                print("✅ Table 'article_details' created successfully")
                
                # Create index on published_url if not exists
                try:
                    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_article_details_published_url ON article_details(published_url)"))
                    db.session.commit()
                    print("✅ Index on published_url created")
                except Exception as e:
                    print(f"⚠️  Index creation warning: {e}")
            else:
                print("❌ Failed to create table 'article_details'")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            raise

if __name__ == '__main__':
    migrate()

