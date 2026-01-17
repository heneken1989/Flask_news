"""
Migration script để thêm layout_type và layout_data vào bảng articles
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db
from sqlalchemy import text

def main():
    """Thêm layout_type và layout_data columns vào bảng articles"""
    with app.app_context():
        print("=" * 60)
        print("📝 Migration: Add layout_type and layout_data to articles")
        print("=" * 60)
        print()
        
        try:
            connection = db.engine.connect()
            
            # Check if columns already exist
            print("📋 Checking existing columns...")
            check_layout_type = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='articles' AND column_name='layout_type'
            """)
            result = connection.execute(check_layout_type)
            layout_type_exists = result.fetchone() is not None
            
            check_layout_data = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='articles' AND column_name='layout_data'
            """)
            result = connection.execute(check_layout_data)
            layout_data_exists = result.fetchone() is not None
            
            # Add layout_type column
            if not layout_type_exists:
                print("📝 Adding layout_type column...")
                add_layout_type = text("""
                    ALTER TABLE articles 
                    ADD COLUMN layout_type VARCHAR(50)
                """)
                connection.execute(add_layout_type)
                connection.commit()
                print("✅ Added layout_type column")
            else:
                print("ℹ️  layout_type column already exists")
            
            # Add layout_data column
            if not layout_data_exists:
                print("📝 Adding layout_data column...")
                # PostgreSQL uses JSONB for JSON columns
                add_layout_data = text("""
                    ALTER TABLE articles 
                    ADD COLUMN layout_data JSONB
                """)
                connection.execute(add_layout_data)
                connection.commit()
                print("✅ Added layout_data column")
            else:
                print("ℹ️  layout_data column already exists")
            
            connection.close()
            
            print()
            print("=" * 60)
            print("✅ Migration completed successfully!")
            print("=" * 60)
            print()
            print("📋 New columns:")
            print("   - layout_type: VARCHAR(50) - Layout type cho trang home")
            print("   - layout_data: JSONB - Additional data cho layout (kicker, list_items, etc.)")
            print()
            print("📝 Layout types:")
            print("   - '1_full': 1 article full width (t46)")
            print("   - '2_articles': 2 articles 1 row (t38)")
            print("   - '3_articles': 3 articles 1 row (t24)")
            print("   - '1_special_bg': 1 article với special background (bg-black)")
            print("   - '1_with_list_left': 1 article + list bên trái")
            print("   - '1_with_list_right': 1 article + list bên phải")
            print()
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

