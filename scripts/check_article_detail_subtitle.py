#!/usr/bin/env python3
"""
Script để kiểm tra subtitle trong ArticleDetail.content_blocks
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

def check_subtitle_in_article_detail(published_url=None, article_id=None, instance=None):
    """Kiểm tra subtitle trong ArticleDetail.content_blocks"""
    with app.app_context():
        # Tìm article
        if article_id:
            article = Article.query.get(article_id)
        elif instance:
            article = Article.query.filter_by(instance=instance).first()
        elif published_url:
            article = Article.query.filter_by(published_url=published_url).first()
        else:
            print("❌ Cần cung cấp article_id, instance, hoặc published_url")
            return
        
        if not article:
            print(f"❌ Không tìm thấy article")
            return
        
        print(f"\n{'='*80}")
        print(f"📰 Article ID: {article.id}")
        print(f"   Title: {article.title}")
        print(f"   Published URL: {article.published_url}")
        print(f"   Instance: {article.instance}")
        print(f"{'='*80}")
        
        # Kiểm tra Article.excerpt
        print(f"\n📝 Article.excerpt:")
        if article.excerpt:
            print(f"   ✅ Có excerpt ({len(article.excerpt)} chars):")
            print(f"   {article.excerpt[:200]}...")
        else:
            print(f"   ❌ KHÔNG có excerpt")
        
        # Kiểm tra ArticleDetail.content_blocks
        print(f"\n📚 ArticleDetail.content_blocks:")
        article_details = ArticleDetail.query.filter_by(published_url=article.published_url).all()
        
        if not article_details:
            print(f"   ❌ KHÔNG có ArticleDetail")
            return
        
        for detail in article_details:
            print(f"\n   🌍 Language: {detail.language}")
            print(f"   📦 Total blocks: {len(detail.content_blocks) if detail.content_blocks else 0}")
            
            if not detail.content_blocks:
                print(f"   ❌ content_blocks là NULL hoặc empty")
                continue
            
            # Tìm subtitle block
            subtitle_block = None
            intro_block = None
            first_paragraph = None
            
            for block in detail.content_blocks:
                block_type = block.get('type', '')
                
                if block_type == 'subtitle':
                    subtitle_block = block
                elif block_type == 'intro' and not intro_block:
                    intro_block = block
                elif block_type == 'paragraph' and not first_paragraph:
                    first_paragraph = block
            
            # Hiển thị subtitle block
            if subtitle_block:
                print(f"\n   ✅ TÌM THẤY subtitle block:")
                print(f"      Type: {subtitle_block.get('type')}")
                print(f"      Order: {subtitle_block.get('order')}")
                print(f"      Text: {subtitle_block.get('text', '')[:200]}...")
                print(f"      HTML: {subtitle_block.get('html', '')[:200]}...")
                print(f"      Classes: {subtitle_block.get('classes', [])}")
            else:
                print(f"\n   ❌ KHÔNG có subtitle block trong content_blocks")
            
            # Hiển thị intro block (fallback)
            if intro_block:
                print(f"\n   📄 Intro block (fallback option):")
                print(f"      Type: {intro_block.get('type')}")
                print(f"      Text: {intro_block.get('text', '')[:200]}...")
            
            # Hiển thị first paragraph (fallback option)
            if first_paragraph:
                print(f"\n   📄 First paragraph (fallback option):")
                print(f"      Type: {first_paragraph.get('type')}")
                text = first_paragraph.get('text', '')
                if not text:
                    # Try to extract from HTML
                    html = first_paragraph.get('html', '')
                    if html:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        text = soup.get_text(strip=True)
                print(f"      Text: {text[:200] if text else 'N/A'}...")
            
            # Hiển thị tất cả block types để debug
            print(f"\n   📋 All block types:")
            block_types = {}
            for block in detail.content_blocks:
                block_type = block.get('type', 'unknown')
                block_types[block_type] = block_types.get(block_type, 0) + 1
            for block_type, count in sorted(block_types.items()):
                print(f"      - {block_type}: {count} block(s)")
            
            # So sánh với text trong URL (nếu có)
            url_text = "Over en årrække har væksten i Færøernes økonomi har været blandt de højeste i Europa. Nu er der tegn på, at tempoet er taget lidt af på arbejdsmarkedet efter nogle år med høj vækst, mener Nationalbanken."
            
            if url_text in (article.published_url or ''):
                print(f"\n   🔍 So sánh với text trong URL:")
                if subtitle_block and url_text in subtitle_block.get('text', ''):
                    print(f"      ✅ Text CÓ trong subtitle block")
                elif intro_block and url_text in intro_block.get('text', ''):
                    print(f"      ✅ Text CÓ trong intro block")
                elif first_paragraph and url_text in (first_paragraph.get('text', '') or ''):
                    print(f"      ✅ Text CÓ trong first paragraph")
                else:
                    print(f"      ❌ Text KHÔNG có trong content_blocks")
                    print(f"      → Text chỉ có trong URL (lỗi crawl)")

if __name__ == '__main__':
    # Test với instance 2334183
    check_subtitle_in_article_detail(instance='2334183')
    
    # Hoặc với published_url
    # published_url = 'https://www.sermitsiaq.ag/erhverv/nationalbanken-udsigt-til-lavere-vaekst-i-faeroernes-okonomi-samt-hoj-usikkerhed-om-fremtiden/2334183'
    # check_subtitle_in_article_detail(published_url=published_url)
