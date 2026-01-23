"""
Script để tạo test user cho login system
Usage: python create_test_user.py
"""
import sys
import os
import hashlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, User
from datetime import datetime

def create_test_user():
    """Tạo test user mẫu"""
    with app.app_context():
        # Đảm bảo tất cả tables đã được tạo (bao gồm users table)
        print("Creating database tables if not exists...")
        db.create_all()
        print("✅ Database tables ready!")
        
        # Check if user already exists
        existing = User.query.filter_by(email='test@sermitsiaq.com').first()
        if existing:
            print(f"⚠️  User {existing.email} đã tồn tại!")
            return
        
        # Create password hash (SHA256 - đơn giản, nên upgrade sau với werkzeug)
        password = 'test123'
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create user
        user = User(
            email='test@sermitsiaq.com',
            subscriber_number='12345',
            password_hash=password_hash,
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ Đã tạo test user:")
        print(f"   Email: {user.email}")
        print(f"   Subscriber Number: {user.subscriber_number}")
        print(f"   Password: {password}")
        print(f"\nBạn có thể login với email hoặc subscriber number!")

if __name__ == '__main__':
    create_test_user()

