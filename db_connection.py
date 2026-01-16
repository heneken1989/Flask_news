"""
Database connection helper
Dùng cho cả Flask app và crawl scripts
"""

import os
from pathlib import Path

def get_database_url():
    """
    Lấy DATABASE_URL từ environment variable hoặc .env file
    Có thể dùng cho cả Flask app và crawl scripts
    """
    # Thử lấy từ environment variable trước
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        return db_url
    
    # Nếu không có, thử đọc từ .env file
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    db_url = line.split('=', 1)[1].strip()
                    # Remove quotes if present
                    db_url = db_url.strip('"').strip("'")
                    return db_url
    
    # Nếu vẫn không có, thử đọc từ connection info file (trên VPS)
    conn_info_file = Path('/tmp/flask_db_connection.txt')
    if conn_info_file.exists():
        with open(conn_info_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL=') and not line.startswith('#'):
                    db_url = line.split('=', 1)[1].strip()
                    return db_url
    
    # Default fallback (development)
    return 'postgresql://flask_user:your_password@localhost/flask_news'


def setup_database_url():
    """
    Setup DATABASE_URL trong environment
    Dùng cho crawl scripts
    """
    db_url = get_database_url()
    os.environ['DATABASE_URL'] = db_url
    return db_url


# Example usage for crawl scripts:
if __name__ == '__main__':
    # Setup database URL
    db_url = setup_database_url()
    print(f"✅ DATABASE_URL set: {db_url[:50]}...")
    
    # Test connection
    try:
        from app import app, db
        with app.app_context():
            db.engine.connect()
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

