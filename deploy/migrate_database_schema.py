#!/usr/bin/env python3
"""
Script để migrate database schema:
- Bỏ unique constraint trên element_guid
- Dùng ID (primary key) làm unique identifier thay vì element_guid
- Cho phép cùng element_guid xuất hiện ở nhiều sections với ID khác nhau
Usage: python3 deploy/migrate_database_schema.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db
from sqlalchemy import text


def main():
    with app.app_context():
        print("=" * 60)
        print("🔄 Migrate Database Schema")
        print("=" * 60)
        print()
        print("Changes:")
        print("  1. Remove unique constraint on element_guid")
        print("  2. Use ID (primary key) as unique identifier")
        print("  3. Allow same element_guid in different sections (different IDs)")
        print()
        
        confirm = input("⚠️  This will modify database schema. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Migration cancelled")
            return
        
        try:
            # Get database connection
            connection = db.engine.connect()
            trans = connection.begin()
            
            try:
                # Drop old unique constraint on element_guid (if exists)
                print("📝 Dropping old unique constraint on element_guid...")
                try:
                    # Try different constraint names
                    constraint_names = [
                        'articles_element_guid_key',
                        'articles_pkey',  # This is primary key, don't drop
                        'uq_article_guid_section'  # Composite constraint if exists
                    ]
                    
                    for constraint_name in constraint_names:
                        if constraint_name == 'articles_pkey':
                            continue  # Don't drop primary key
                        try:
                            drop_sql = text(f"ALTER TABLE articles DROP CONSTRAINT IF EXISTS {constraint_name}")
                            connection.execute(drop_sql)
                            print(f"✅ Dropped constraint: {constraint_name}")
                        except Exception as e:
                            pass  # Constraint may not exist
                    
                except Exception as e:
                    print(f"⚠️  Could not drop old constraint (may not exist): {e}")
                
                # Make element_guid nullable (if not already)
                print("📝 Making element_guid nullable...")
                try:
                    alter_null = text("ALTER TABLE articles ALTER COLUMN element_guid DROP NOT NULL")
                    connection.execute(alter_null)
                    print("✅ Made element_guid nullable")
                except Exception as e:
                    print(f"⚠️  Could not alter column (may already be nullable): {e}")
                
                # Add index on element_guid for faster queries (not unique)
                print("📝 Adding index on element_guid...")
                try:
                    add_index = text("CREATE INDEX IF NOT EXISTS idx_element_guid ON articles(element_guid)")
                    connection.execute(add_index)
                    print("✅ Added index on element_guid")
                except Exception as e:
                    print(f"⚠️  Could not add index (may already exist): {e}")
                
                trans.commit()
                connection.close()
                
                print()
                print("=" * 60)
                print("✅ Migration completed!")
                print("=" * 60)
                print()
                print("📝 Schema changes:")
                print("  - element_guid: No longer unique (can have duplicates)")
                print("  - ID (primary key): Used as unique identifier")
                print("  - Same element_guid can appear in different sections with different IDs")
                print()
                print("📝 Next steps:")
                print("  1. Re-crawl sections to create articles for each section")
                print("  2. Each section will have articles with unique IDs")
                print("  3. Articles with same element_guid but different sections = different IDs")
                print()
                
            except Exception as e:
                trans.rollback()
                raise e
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return


if __name__ == '__main__':
    main()

