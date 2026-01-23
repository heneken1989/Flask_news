#!/usr/bin/env python3
"""
Script to check login configuration for production
Helps debug login issues
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Check configuration
print("=" * 60)
print("LOGIN CONFIGURATION CHECK")
print("=" * 60)

# 1. Check SECRET_KEY
secret_key = app.config.get('SECRET_KEY')
print(f"\n1. SECRET_KEY:")
print(f"   Set: {bool(secret_key)}")
print(f"   Length: {len(secret_key) if secret_key else 0}")
print(f"   Value: {secret_key[:20]}... (first 20 chars)" if secret_key and len(secret_key) > 20 else f"   Value: {secret_key}")
if not secret_key or secret_key == 'dev-secret-key-change-in-production':
    print("   ⚠️  WARNING: Using default SECRET_KEY! Change this in production!")

# 2. Check environment
flask_env = os.environ.get('FLASK_ENV', 'development')
environment = os.environ.get('ENVIRONMENT', 'development')
is_production = flask_env == 'production' or environment == 'production'
print(f"\n2. Environment:")
print(f"   FLASK_ENV: {flask_env}")
print(f"   ENVIRONMENT: {environment}")
print(f"   Is Production: {is_production}")

# 3. Check session configuration
print(f"\n3. Session Configuration:")
print(f"   SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE', 'Not set')}")
print(f"   SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY', 'Not set')}")
print(f"   SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE', 'Not set')}")

# 4. Check database connection
print(f"\n4. Database Connection:")
db_url = os.environ.get('DATABASE_URL')
if db_url:
    # Hide password in output
    if '@' in db_url:
        parts = db_url.split('@')
        if '://' in parts[0]:
            user_pass = parts[0].split('://')[1]
            if ':' in user_pass:
                user = user_pass.split(':')[0]
                db_url_display = db_url.replace(f':{user_pass.split(":")[1]}', ':****')
            else:
                db_url_display = db_url
        else:
            db_url_display = db_url
    else:
        db_url_display = db_url
    print(f"   DATABASE_URL: {db_url_display}")
    
    # Try to connect
    try:
        from database import db
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            # Try to query users table
            from database import User
            user_count = User.query.count()
            print(f"   ✅ Connection successful")
            print(f"   Users in database: {user_count}")
            
            # Check for active users
            active_users = User.query.filter_by(is_active=True).count()
            print(f"   Active users: {active_users}")
            
            # List first 3 users (email only, no password)
            users = User.query.limit(3).all()
            if users:
                print(f"   Sample users:")
                for u in users:
                    print(f"      - ID: {u.id}, Email: {u.email}, Subscriber: {u.subscriber_number}, Active: {u.is_active}")
    except Exception as e:
        print(f"   ❌ Connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("   ⚠️  DATABASE_URL not set")

# 5. Check .env file
print(f"\n5. Environment File:")
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    print(f"   ✅ .env file exists: {env_file}")
    # Check if readable
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()
            print(f"   Lines in .env: {len(lines)}")
            # Check for SECRET_KEY
            has_secret = any('SECRET_KEY' in line for line in lines)
            print(f"   Contains SECRET_KEY: {has_secret}")
    except Exception as e:
        print(f"   ⚠️  Cannot read .env file: {str(e)}")
else:
    print(f"   ⚠️  .env file not found: {env_file}")

# 6. Recommendations
print(f"\n6. Recommendations:")
if not secret_key or secret_key == 'dev-secret-key-change-in-production':
    print("   ❌ Set a strong SECRET_KEY in .env file or environment variable")
if not is_production:
    print("   ℹ️  Set FLASK_ENV=production or ENVIRONMENT=production for production")
if is_production and not app.config.get('SESSION_COOKIE_SECURE'):
    print("   ⚠️  SESSION_COOKIE_SECURE should be True in production")
if not db_url:
    print("   ❌ Set DATABASE_URL in .env file or environment variable")

print("\n" + "=" * 60)
print("Check complete!")
print("=" * 60)

