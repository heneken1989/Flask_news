#!/usr/bin/env python3
"""
Script để kiểm tra articles thuộc section='home' và layout_type có '1article' hoặc 'right'
và xem tại sao chưa được dịch
"""

import sys
import os
from pathlib import Path

# Add flask directory to path
flask_dir = Path(__file__).parent.parent
sys.path.insert(0, str(flask_dir.parent))

os.chdir(flask_dir.parent)

from flask.app import app
from flask.database import db, Article
from sqlalchemy import or_

def check_home_articles():
    """Kiểm tra articles home chưa dịch"""
    
    with app.app_context():
        # Tìm articles DA với section='home' và layout_type có '1article' hoặc 'right'
        articles = Article.query.filter(
            Article.section == 'home',
            Article.language == 'da',
            or_(
                Article.layout_type.like('%1article%'),
                Article.layout_type.like('%right%'),
                Article.layout_type.like('%1_article%')
            )
        ).order_by(Article.created_at.desc()).limit(20).all()
        
        print(f"🔍 Tìm thấy {len(articles)} articles DA với section='home' và layout_type có '1article' hoặc 'right'\n")
        
        for article in articles:
            print(f"\n{'='*80}")
            print(f"Article ID: {article.id}")
            print(f"Title: {article.title[:80]}...")
            print(f"Section: {article.section}")
            print(f"Language: {article.language}")
            print(f"Layout Type: {article.layout_type}")
            print(f"Published URL: {article.published_url}")
            print(f"Published URL EN: {article.published_url_en}")
            print(f"Canonical ID: {article.canonical_id}")
            print(f"Is Temp: {article.is_temp}")
            print(f"Is Home: {article.is_home}")
            print(f"Created At: {article.created_at}")
            
            # Kiểm tra xem có translation EN chưa
            if article.canonical_id:
                # Article này là translation, tìm canonical
                canonical = Article.query.get(article.canonical_id)
                if canonical:
                    print(f"   ⚠️  Article này là translation của article #{canonical.id}")
                    # Tìm tất cả translations của canonical
                    translations = Article.query.filter(
                        (Article.id == canonical.id) | 
                        (Article.canonical_id == canonical.id)
                    ).all()
                    print(f"   Translations: {[f'#{t.id} ({t.language})' for t in translations]}")
            else:
                # Article này là canonical, tìm translations
                translations = Article.query.filter(
                    Article.canonical_id == article.id
                ).all()
                
                if translations:
                    print(f"   ✅ Có {len(translations)} translations:")
                    for trans in translations:
                        print(f"      - #{trans.id} ({trans.language}) - is_temp: {trans.is_temp}")
                else:
                    print(f"   ❌ CHƯA CÓ TRANSLATION")
                    
                    # Kiểm tra xem có article EN nào với cùng published_url không
                    if article.published_url:
                        en_articles = Article.query.filter(
                            Article.published_url == article.published_url,
                            Article.language == 'en'
                        ).all()
                        
                        if en_articles:
                            print(f"   ⚠️  Tìm thấy {len(en_articles)} article(s) EN với cùng published_url:")
                            for en_art in en_articles:
                                print(f"      - Article #{en_art.id}: canonical_id={en_art.canonical_id}, is_temp={en_art.is_temp}")
                        else:
                            print(f"   ℹ️  Không có article EN nào với cùng published_url")
            
            # Kiểm tra ArticleDetail
            from database import ArticleDetail
            details = ArticleDetail.query.filter_by(
                article_id=article.id
            ).all()
            
            if details:
                print(f"   ArticleDetail: {len(details)} record(s)")
                for detail in details:
                    print(f"      - ID: {detail.id}, Language: {detail.language}, Published URL: {detail.published_url}")
            else:
                print(f"   ⚠️  Không có ArticleDetail")

if __name__ == '__main__':
    check_home_articles()

