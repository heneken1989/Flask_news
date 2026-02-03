#!/usr/bin/env python3
"""
Test search page translations
Verify that search page texts are properly translated to EN
"""

import sys
import os

# Add flask directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'flask'))

from app import app
from flask import session

def test_translations():
    """Test that search page translations work"""
    with app.app_context():
        with app.test_client() as client:
            print(f"\n{'='*80}")
            print(f"🌐 Testing Search Page Translations")
            print(f"{'='*80}\n")
            
            # Test Danish (default)
            print("📝 Testing Danish (DA):")
            with client.session_transaction() as sess:
                sess['language'] = 'da'
            response = client.get('/search?q=test')
            html = response.data.decode('utf-8')
            
            da_checks = [
                ('Søg i vores arkiver', 'Search header'),
                ('Skriv søgeord', 'Search placeholder'),
                ('Søg</button>', 'Search button'),
            ]
            
            for text, desc in da_checks:
                if text in html:
                    print(f"   ✅ {desc}: '{text}' found")
                else:
                    print(f"   ❌ {desc}: '{text}' NOT found")
            
            print("")
            
            # Test English
            print("📝 Testing English (EN):")
            with client.session_transaction() as sess:
                sess['language'] = 'en'
            response = client.get('/search?q=test&lang=en')
            html = response.data.decode('utf-8')
            
            en_checks = [
                ('Search our archives', 'Search header'),
                ('Enter search term', 'Search placeholder'),
                ('Search</button>', 'Search button'),
                ('Show more', 'Load more button (if results exist)'),
            ]
            
            for text, desc in en_checks:
                if text in html:
                    print(f"   ✅ {desc}: '{text}' found")
                else:
                    # Show more might not appear if no results
                    if 'Show more' in text and 'no results' in html.lower():
                        print(f"   ⚠️  {desc}: Not shown (no search results)")
                    else:
                        print(f"   ❌ {desc}: '{text}' NOT found")
            
            print("")
            
            # Test Kalaallisut
            print("📝 Testing Kalaallisut (KL):")
            with client.session_transaction() as sess:
                sess['language'] = 'kl'
            response = client.get('/search?q=test&lang=kl')
            html = response.data.decode('utf-8')
            
            kl_checks = [
                ('Søg i vores arkiver', 'Search header (should show DA if KL not translated)'),
                ('Skriv søgeord', 'Search placeholder'),
            ]
            
            for text, desc in kl_checks:
                if text in html:
                    print(f"   ✅ {desc}: '{text}' found")
                else:
                    print(f"   ⚠️  {desc}: '{text}' NOT found (may need KL translation)")
            
            print(f"\n{'='*80}\n")

if __name__ == '__main__':
    test_translations()
