"""
Test script để debug parser
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.article_detail_parser import ArticleDetailParser
from database import ArticleDetail

with app.app_context():
    # Test với article mới (không có paywall)
    article_detail = ArticleDetail.query.filter_by(
        published_url='https://www.sermitsiaq.ag/samfund/nuummiut-gar-pa-gaden-for-at-kaempe-for-gronland/2331847'
    ).first()
    
    if not article_detail:
        # Fallback to old article
        article_detail = ArticleDetail.query.filter_by(
            published_url='https://www.sermitsiaq.ag/kultur/siiva-fleischer-udgiver-en-sang-vi-er-meget-bekymrede-over-usas-pres-pa-vores-land/2331296'
        ).first()
    
    if article_detail:
        print(f"Article Detail ID: {article_detail.id}")
        print(f"Content blocks: {len(article_detail.content_blocks)}")
        print("\nBlocks:")
        for i, block in enumerate(article_detail.content_blocks):
            print(f"\n{i+1}. Type: {block.get('type')}, Order: {block.get('order')}")
            if block.get('type') == 'paragraph':
                print(f"   Text: {block.get('text', '')[:100]}...")
            elif block.get('type') == 'image':
                print(f"   Element GUID: {block.get('element_guid')}")
                print(f"   Image sources keys: {list(block.get('image_sources', {}).keys())}")
            elif block.get('type') == 'paywall_offer':
                print(f"   Offers: {len(block.get('offers', []))}")
    else:
        print("Article detail not found")

