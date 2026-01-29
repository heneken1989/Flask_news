#!/usr/bin/env python3
"""
Check why there are many 5_articles records in home section
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import db, Article

def check_5_articles():
    with app.app_context():
        print("="*80)
        print("🔍 Checking 5_articles records in home section")
        print("="*80)
        print()
        
        # Count total
        total = Article.query.filter_by(
            section='home',
            layout_type='5_articles'
        ).count()
        
        print(f"📊 Total 5_articles in home section: {total}")
        print()
        
        # Group by language and is_deleted
        print("📈 Breakdown by language and is_deleted:")
        print("-"*80)
        
        for language in ['da', 'kl', 'en']:
            count_active = Article.query.filter_by(
                section='home',
                layout_type='5_articles',
                language=language,
                is_deleted=False
            ).count()
            
            count_deleted = Article.query.filter_by(
                section='home',
                layout_type='5_articles',
                language=language,
                is_deleted=True
            ).count()
            
            count_null = Article.query.filter_by(
                section='home',
                layout_type='5_articles',
                language=language
            ).filter(Article.is_deleted.is_(None)).count()
            
            print(f"{language.upper():3} | Active: {count_active:4} | Deleted: {count_deleted:4} | Null: {count_null:4} | Total: {count_active + count_deleted + count_null}")
        
        print()
        print("="*80)
        print("🔍 Sample records (latest 10):")
        print("-"*80)
        
        samples = Article.query.filter_by(
            section='home',
            layout_type='5_articles'
        ).order_by(Article.created_at.desc()).limit(10).all()
        
        for art in samples:
            print(f"ID: {art.id:6} | Lang: {art.language} | is_deleted: {art.is_deleted} | created: {art.created_at}")
            print(f"  Title: {art.title[:70]}...")
            print()
        
        print("="*80)

if __name__ == '__main__':
    check_5_articles()

