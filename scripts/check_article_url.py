#!/usr/bin/env python3
"""Check article URL format"""
import sys
import os
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import Article

with app.app_context():
    # Tìm article với URL có chứa 'usas-fn-ambassador'
    article = Article.query.filter(
        Article.published_url.like('%usas-fn-ambassador%')
    ).first()
    
    if article:
        print(f'Article ID: {article.id}')
        print(f'Language: {article.language}')
        print(f'published_url: {article.published_url}')
        if article.published_url_en:
            print(f'published_url_en: {article.published_url_en}')
        
        # Parse URL
        parsed = urlparse(article.published_url)
        print(f'\nParsed published_url:')
        print(f'  scheme: {parsed.scheme}')
        print(f'  netloc: {parsed.netloc}')
        print(f'  path: {parsed.path}')
        
        # Check translations
        if article.canonical_id:
            canonical = Article.query.get(article.canonical_id)
            if canonical:
                translations = Article.query.filter(
                    (Article.id == canonical.id) | 
                    (Article.canonical_id == canonical.id)
                ).all()
                print(f'\nTranslations:')
                for trans in translations:
                    print(f'  - {trans.language}: published_url={trans.published_url}, published_url_en={trans.published_url_en}')
    else:
        print('Article not found')

