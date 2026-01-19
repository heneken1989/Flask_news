"""
Migration script to change unique constraint on article_details table
- Remove unique constraint on published_url only
- Add composite unique constraint on (published_url, language)
- Add index on language if not exists

Run: python deploy/migrate_article_details_composite_unique.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from sqlalchemy import text, inspect

def migrate():
    """Update unique constraint on article_details table"""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            # Check if table exists
            if 'article_details' not in inspector.get_table_names():
                print("❌ Table 'article_details' does not exist")
                return
            
            print("🔄 Updating unique constraint on 'article_details' table...")
            
            # Get existing constraints
            constraints = inspector.get_unique_constraints('article_details')
            indexes = inspector.get_indexes('article_details')
            
            # Check if old unique constraint exists (on published_url only)
            old_unique_found = False
            constraint_name = None
            for constraint in constraints:
                if 'published_url' in constraint['column_names'] and len(constraint['column_names']) == 1:
                    old_unique_found = True
                    constraint_name = constraint['name']
                    print(f"   Found old unique constraint: {constraint_name} on published_url")
                    break
            
            # Also check for unique index on published_url (ix_article_details_published_url)
            old_unique_index_found = False
            unique_index_name = None
            for index in indexes:
                if index['name'] == 'ix_article_details_published_url' and index.get('unique', False):
                    old_unique_index_found = True
                    unique_index_name = index['name']
                    print(f"   Found old unique index: {unique_index_name} on published_url")
                    break
            
            # Check if new composite unique constraint already exists
            new_unique_exists = False
            for constraint in constraints:
                if 'published_url' in constraint['column_names'] and 'language' in constraint['column_names']:
                    new_unique_exists = True
                    print(f"   ✅ Composite unique constraint already exists: {constraint['name']}")
                    break
            
            # Drop old unique constraint if exists
            if old_unique_found and not new_unique_exists:
                try:
                    # PostgreSQL syntax
                    db.session.execute(text(f"ALTER TABLE article_details DROP CONSTRAINT IF EXISTS {constraint_name}"))
                    db.session.commit()
                    print(f"   ✅ Dropped old unique constraint: {constraint_name}")
                except Exception as e:
                    print(f"   ⚠️  Error dropping old constraint (might not exist): {e}")
                    db.session.rollback()
            
            # Drop old unique index if exists (ix_article_details_published_url)
            if old_unique_index_found:
                try:
                    # PostgreSQL syntax - drop index
                    db.session.execute(text(f"DROP INDEX IF EXISTS {unique_index_name}"))
                    db.session.commit()
                    print(f"   ✅ Dropped old unique index: {unique_index_name}")
                except Exception as e:
                    print(f"   ⚠️  Error dropping old unique index (might not exist): {e}")
                    db.session.rollback()
            
            # Recreate non-unique index on published_url if needed
            published_url_index_exists = False
            for index in indexes:
                if 'published_url' in index['column_names'] and not index.get('unique', False):
                    published_url_index_exists = True
                    break
            
            if not published_url_index_exists:
                try:
                    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_article_details_published_url ON article_details(published_url)"))
                    db.session.commit()
                    print("   ✅ Recreated non-unique index on published_url")
                except Exception as e:
                    print(f"   ⚠️  Error recreating index on published_url: {e}")
                    db.session.rollback()
            
            # Add new composite unique constraint if not exists
            if not new_unique_exists:
                try:
                    db.session.execute(text("""
                        ALTER TABLE article_details 
                        ADD CONSTRAINT uq_article_details_url_language 
                        UNIQUE (published_url, language)
                    """))
                    db.session.commit()
                    print("   ✅ Added composite unique constraint: (published_url, language)")
                except Exception as e:
                    print(f"   ⚠️  Error adding composite unique constraint: {e}")
                    db.session.rollback()
                    # Check if constraint already exists with different name
                    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                        print("   ℹ️  Constraint might already exist with different name")
            
            # Add index on language if not exists
            language_index_exists = False
            for index in indexes:
                if 'language' in index['column_names']:
                    language_index_exists = True
                    break
            
            if not language_index_exists:
                try:
                    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_article_details_language ON article_details(language)"))
                    db.session.commit()
                    print("   ✅ Added index on language column")
                except Exception as e:
                    print(f"   ⚠️  Error adding index on language: {e}")
                    db.session.rollback()
            else:
                print("   ℹ️  Index on language already exists")
            
            # Verify final state
            print("\n📋 Final constraints and indexes:")
            final_constraints = inspector.get_unique_constraints('article_details')
            final_indexes = inspector.get_indexes('article_details')
            
            for constraint in final_constraints:
                print(f"   Unique constraint: {constraint['name']} on {constraint['column_names']}")
            
            for index in final_indexes:
                if index['name'] not in ['ix_article_details_published_url', 'uq_article_details_url_language']:
                    print(f"   Index: {index['name']} on {index['column_names']}")
            
            print("\n✅ Migration completed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()

