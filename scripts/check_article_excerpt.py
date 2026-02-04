#!/usr/bin/env python3
"""
Script để kiểm tra excerpt và content của article theo published_url
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from database import db, Article, ArticleDetail
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/hrai')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def check_article(published_url):
    """Kiểm tra article theo published_url"""
    with app.app_context():
        # Tìm article
        article = Article.query.filter_by(published_url=published_url).first()
        
        if not article:
            print(f"❌ Không tìm thấy article với published_url:")
            print(f"   {published_url}")
            return
        
        print(f"\n{'='*80}")
        print(f"📰 Article ID: {article.id}")
        print(f"{'='*80}")
        print(f"\n📋 Thông tin cơ bản:")
        print(f"   Title: {article.title}")
        print(f"   Section: {article.section}")
        print(f"   Language: {article.language}")
        print(f"   Published URL: {article.published_url}")
        print(f"   Published Date: {article.published_date}")
        
        print(f"\n📝 EXCERPT:")
        if article.excerpt:
            print(f"   ✅ Có excerpt ({len(article.excerpt)} chars):")
            print(f"   {article.excerpt[:200]}...")
        else:
            print(f"   ❌ KHÔNG có excerpt (NULL hoặc empty)")
        
        print(f"\n📄 CONTENT:")
        if article.content:
            content_preview = article.content[:300].replace('\n', ' ')
            print(f"   ✅ Có content ({len(article.content)} chars):")
            print(f"   {content_preview}...")
        else:
            print(f"   ❌ KHÔNG có content (NULL hoặc empty)")
        
        # Kiểm tra ArticleDetail
        print(f"\n📚 ARTICLE DETAIL:")
        article_details = ArticleDetail.query.filter_by(published_url=article.published_url).all()
        if article_details:
            for detail in article_details:
                print(f"   Language: {detail.language}")
                print(f"   Content blocks: {len(detail.content_blocks) if detail.content_blocks else 0} blocks")
                if detail.content_blocks:
                    # Tìm intro block
                    for block in detail.content_blocks:
                        if block.get('type') == 'intro' or block.get('type') == 'paragraph':
                            text = block.get('text', '')
                            if text:
                                print(f"   First block text: {text[:200]}...")
                                break
        else:
            print(f"   ❌ KHÔNG có ArticleDetail")
        
        # Kiểm tra text trong URL
        print(f"\n🔍 PHÂN TÍCH URL:")
        url_text = "Over en årrække har væksten i Færøernes økonomi har været blandt de højeste i Europa. Nu er der tegn på, at tempoet er taget lidt af på arbejdsmarkedet efter nogle år med høj vækst, mener Nationalbanken."
        
        if url_text in article.published_url:
            print(f"   ⚠️  PHÁT HIỆN: Text trong URL!")
            print(f"   Text: {url_text}")
            print(f"   → Đây là LỖI - text không nên có trong URL")
            print(f"   → URL đúng nên là: .../nationalbanken-udsigt-til-lavere-vaekst-i-faeroernes-okonomi-samt-hoj-usikkerhed-om-fremtiden/2334183")
        
        # So sánh với excerpt/content
        print(f"\n🔗 SO SÁNH:")
        if article.excerpt and url_text in article.excerpt:
            print(f"   ✅ Text này CÓ trong excerpt")
        elif article.content and url_text in article.content:
            print(f"   ✅ Text này CÓ trong content")
        else:
            print(f"   ❌ Text này KHÔNG có trong excerpt hoặc content")
            print(f"   → Text chỉ có trong URL (lỗi crawl?)")

if __name__ == '__main__':
    # URL từ user query
    published_url = 'https://www.sermitsiaq.ag/erhverv/nationalbanken-udsigt-til-lavere-vaekst-i-faeroernes-okonomi-samt-hoj-usikkerhed-om-Over en årrække har væksten i Færøernes økonomi har været blandt de højeste i Europa. Nu er der tegn på, at tempoet er taget lidt af på arbejdsmarkedet efter nogle år med høj vækst, mener Nationalbanken.fremtiden/2334183'
    
    check_article(published_url)
