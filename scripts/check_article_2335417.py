#!/usr/bin/env python3
import sys
import os

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from app import app
from database import db
from models import Article
import json

def check_article():
    with app.app_context():
        # Tìm article DA
        da_article = Article.query.filter_by(
            published_url='https://www.sermitsiaq.ag/erhverv/naalakkersuisut-sagsbehandlingen-pa-rastofomradet-skal-smidiggores/2335417',
            language='da'
        ).first()
        
        if not da_article:
            print("❌ Không tìm thấy article DA")
            return
        
        print(f"✅ Tìm thấy article DA:")
        print(f"   ID: {da_article.id}")
        print(f"   Title: {da_article.title}")
        print(f"   Is home page: {da_article.is_home_page}")
        print(f"   Layout data: {json.dumps(da_article.layout_data, indent=2, ensure_ascii=False)}")
        
        # Tìm article EN
        en_article = Article.query.filter_by(
            published_url_en='https://www.sermitsiaq.ag/erhverv/naalakkersuisut-sagsbehandlingen-pa-rastofomradet-skal-smidiggores/2335417',
            language='en'
        ).first()
        
        if not en_article:
            print("\n❌ Không tìm thấy article EN")
            return
        
        print(f"\n✅ Tìm thấy article EN:")
        print(f"   ID: {en_article.id}")
        print(f"   Title: {en_article.title}")
        print(f"   Is home page: {en_article.is_home_page}")
        print(f"   Layout data: {json.dumps(en_article.layout_data, indent=2, ensure_ascii=False)}")
        
        # So sánh
        print("\n" + "="*60)
        print("SO SÁNH LAYOUT DATA:")
        print("="*60)
        
        da_content_classes = da_article.layout_data.get('content_classes', 'N/A') if da_article.layout_data else 'N/A'
        en_content_classes = en_article.layout_data.get('content_classes', 'N/A') if en_article.layout_data else 'N/A'
        
        print(f"\nDA content_classes: {da_content_classes}")
        print(f"EN content_classes: {en_content_classes}")
        
        da_kicker_classes = da_article.layout_data.get('kicker_floating_classes', 'N/A') if da_article.layout_data else 'N/A'
        en_kicker_classes = en_article.layout_data.get('kicker_floating_classes', 'N/A') if en_article.layout_data else 'N/A'
        
        print(f"\nDA kicker_floating_classes: {da_kicker_classes}")
        print(f"EN kicker_floating_classes: {en_kicker_classes}")
        
        if da_content_classes != en_content_classes or da_kicker_classes != en_kicker_classes:
            print("\n⚠️  LAYOUT DATA KHÔNG GIỐNG NHAU!")
            print("Cần chạy lại script link_home_articles.py để sync")
        else:
            print("\n✅ Layout data giống nhau")

if __name__ == '__main__':
    check_article()
