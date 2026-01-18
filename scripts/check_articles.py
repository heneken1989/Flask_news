#!/usr/bin/env python3
"""Quick script to check article counts by language"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import Article

with app.app_context():
    dk = Article.query.filter_by(language='da', is_home=True).count()
    kl = Article.query.filter_by(language='kl', is_home=True).count()
    en = Article.query.filter_by(language='en', is_home=True).count()
    print(f"📊 Current articles in database:")
    print(f"   - Danish (DK): {dk}")
    print(f"   - Greenlandic (KL): {kl}")
    print(f"   - English (EN): {en}")
    print(f"   - Total: {dk + kl + en}")

