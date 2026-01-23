#!/usr/bin/env python3
"""
Script để khởi tạo database tables
Usage: python3 init_database.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from database import Article, Category, CrawlLog, User

def init_database():
    """Tạo tất cả tables trong database"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Tạo một số categories mẫu
        categories = [
            {'name': 'Erhverv', 'slug': 'erhverv'},
            {'name': 'Samfund', 'slug': 'samfund'},
            {'name': 'Kultur', 'slug': 'kultur'},
            {'name': 'Sport', 'slug': 'sport'},
            {'name': 'Job', 'slug': 'job'},
        ]
        
        print("\nCreating default categories...")
        for cat_data in categories:
            existing = Category.query.filter_by(slug=cat_data['slug']).first()
            if not existing:
                category = Category(**cat_data)
                db.session.add(category)
                print(f"  ✅ Created category: {cat_data['name']}")
            else:
                print(f"  ⏭️  Category already exists: {cat_data['name']}")
        
        db.session.commit()
        print("\n✅ Database initialization completed!")

if __name__ == '__main__':
    init_database()

