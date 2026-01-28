#!/usr/bin/env python3
"""Check ArticleDetail ID 3367"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, ArticleDetail
import json

with app.app_context():
    detail = ArticleDetail.query.get(3367)
    if detail:
        print(f'ArticleDetail ID: {detail.id}')
        print(f'published_url: {detail.published_url}')
        print(f'language: {detail.language}')
        print(f'created_at: {detail.created_at}')
        print()
        
        content_blocks = detail.content_blocks
        if isinstance(content_blocks, str):
            try:
                content_blocks = json.loads(content_blocks)
            except:
                content_blocks = []
        
        if isinstance(content_blocks, list):
            image_blocks = [b for b in content_blocks if b.get('type') == 'image']
            print(f'Found {len(image_blocks)} image blocks:\n')
            
            for idx, block in enumerate(image_blocks, 1):
                image_sources = block.get('image_sources', {})
                if isinstance(image_sources, dict):
                    print(f'Image block #{idx}:')
                    for key, url in image_sources.items():
                        if isinstance(url, str):
                            if 'sermitsiaq.ag' in url:
                                print(f'  ⚠️  {key}: {url[:100]}... (DOMAIN .AG)')
                            elif 'sermitsiaq.com' in url:
                                print(f'  ✅ {key}: {url[:100]}... (DOMAIN .COM)')
                            else:
                                print(f'  ℹ️  {key}: {url[:100]}... (OTHER)')
                    print()
    else:
        print('ArticleDetail ID 3367 not found')

