#!/usr/bin/env python3
"""
Script để re-translate các EN articles đã có để update layout_data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article, ArticleDetail
from services.translation_service import translate_article
from deep_translator import GoogleTranslator
from datetime import datetime
import re
import time

def convert_da_url_to_en_url(da_url: str) -> str:
    """
    Convert URL từ DA sang EN
    Ví dụ: https://www.sermitsiaq.ag/... -> https://www.sermitsiaq.ag/... (giữ nguyên)
    Hoặc: https://kl.sermitsiaq.ag/... -> https://www.sermitsiaq.ag/...
    """
    en_url = da_url.replace('kl.sermitsiaq.ag', 'www.sermitsiaq.ag')
    en_url = re.sub(r'https?://kl\.', 'https://www.', en_url)
    return en_url


def translate_article_detail_content_blocks(content_blocks: list, delay=0.3) -> list:
    """
    Dịch content_blocks từ DA sang EN sử dụng GoogleTranslator
    
    Args:
        content_blocks: List of content blocks
        delay: Delay giữa các lần translate
        
    Returns:
        Translated content blocks
    """
    if not content_blocks:
        return []
    
    translator = GoogleTranslator(source='da', target='en')
    translated_blocks = []
    
    for block in content_blocks:
        translated_block = block.copy()
        
        # Chỉ dịch các block có text content
        if block.get('type') in ['paragraph', 'heading', 'intro', 'subtitle', 'title']:
            # Dịch text
            if block.get('text'):
                try:
                    translated_text = translator.translate(block['text'])
                    translated_block['text'] = translated_text
                    time.sleep(delay)
                except Exception as e:
                    print(f"      ⚠️  Translation error for text: {e}")
                    translated_block['text'] = block['text']
            
            # Dịch HTML content (chỉ dịch text trong tags, giữ nguyên tags)
            if block.get('html'):
                try:
                    html = block['html']
                    # Tìm tất cả text nodes và dịch
                    def translate_html_text(match):
                        text = match.group(1)
                        if text.strip():
                            try:
                                translated = translator.translate(text)
                                time.sleep(delay)
                                return f'>{translated}<'
                            except:
                                return match.group(0)
                        return match.group(0)
                    
                    # Dịch text giữa các tags
                    translated_html = re.sub(r'>([^<]+)<', translate_html_text, html)
                    translated_block['html'] = translated_html
                except Exception as e:
                    print(f"      ⚠️  Translation error for HTML: {e}")
                    translated_block['html'] = block['html']
        
        # Giữ nguyên các block khác (images, ads, paywall_offers, etc.)
        translated_blocks.append(translated_block)
    
    return translated_blocks


def retranslate_en_article_detail(da_article_detail: ArticleDetail, delay=0.3) -> ArticleDetail:
    """
    Dịch article_detail từ DA sang EN
    
    Args:
        da_article_detail: ArticleDetail object với language='da'
        delay: Delay giữa các lần translate
        
    Returns:
        ArticleDetail object với language='en'
    """
    if da_article_detail.language != 'da':
        raise ValueError(f"Source article_detail must be in Danish (da), got {da_article_detail.language}")
    
    # Convert URL từ DA sang EN
    en_url = convert_da_url_to_en_url(da_article_detail.published_url)
    
    # Kiểm tra xem đã có EN version chưa
    existing_en_detail = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
    
    print(f"   🌐 Translating article_detail content blocks...")
    translated_blocks = translate_article_detail_content_blocks(
        da_article_detail.content_blocks or [],
        delay=delay
    )
    
    if existing_en_detail:
        # Update existing EN article_detail
        existing_en_detail.content_blocks = translated_blocks
        existing_en_detail.updated_at = datetime.utcnow()
        db.session.commit()
        print(f"      ✅ Updated existing EN article_detail (ID: {existing_en_detail.id})")
        return existing_en_detail
    else:
        # Tạo ArticleDetail mới với language='en'
        en_article_detail = ArticleDetail(
            published_url=en_url,
            content_blocks=translated_blocks,
            language='en',
            element_guid=da_article_detail.element_guid
        )
        db.session.add(en_article_detail)
        db.session.commit()
        print(f"      ✅ Created new EN article_detail (ID: {en_article_detail.id})")
        return en_article_detail


def retranslate_en_articles():
    """Re-translate tất cả EN articles từ DK articles"""
    with app.app_context():
        # Get all EN articles
        en_articles = Article.query.filter_by(
            language='en',
            is_home=True
        ).all()
        
        print(f"📊 Found {len(en_articles)} EN articles to re-translate")
        
        if not en_articles:
            print("⚠️  No EN articles found")
            return
        
        updated_count = 0
        errors = []
        
        for idx, en_article in enumerate(en_articles, 1):
            try:
                # Get DK source article
                if en_article.canonical_id:
                    dk_article = Article.query.get(en_article.canonical_id)
                else:
                    # Try to find DK article by element_guid
                    dk_article = Article.query.filter_by(
                        element_guid=en_article.element_guid,
                        language='da',
                        is_home=True
                    ).first()
                
                if not dk_article:
                    print(f"   [{idx}/{len(en_articles)}] ⚠️  No DK source found for EN article {en_article.id}")
                    continue
                
                print(f"\n[{idx}/{len(en_articles)}] Re-translating article {en_article.id} from DK {dk_article.id}...")
                
                # Re-translate
                new_en_article = translate_article(dk_article, target_language='en', delay=0.3)
                
                # Update existing EN article
                en_article.title = new_en_article.title
                en_article.content = new_en_article.content
                en_article.excerpt = new_en_article.excerpt
                en_article.layout_data = new_en_article.layout_data
                
                db.session.commit()
                updated_count += 1
                print(f"   ✅ Updated article {en_article.id}")
                
            except Exception as e:
                error_msg = f"Failed to re-translate article {en_article.id}: {e}"
                print(f"   ❌ {error_msg}")
                errors.append({
                    'article_id': en_article.id,
                    'error': str(e)
                })
                db.session.rollback()
                continue
        
        print(f"\n✅ Re-translation completed:")
        print(f"   - Updated: {updated_count}/{len(en_articles)}")
        print(f"   - Errors: {len(errors)}")
        
        if errors:
            print(f"\n❌ Errors:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   - Article {error['article_id']}: {error['error']}")


def retranslate_en_article_details():
    """Re-translate tất cả EN article_details từ DA article_details"""
    with app.app_context():
        # Get all DA article_details (không phải kl.sermitsiaq.ag)
        da_details = ArticleDetail.query.filter(
            ArticleDetail.language == 'da',
            ~ArticleDetail.published_url.contains('kl.sermitsiaq.ag')
        ).all()
        
        print(f"\n📊 Found {len(da_details)} DA article_details to translate")
        
        if not da_details:
            print("⚠️  No DA article_details found")
            return
        
        updated_count = 0
        created_count = 0
        skipped_count = 0
        errors = []
        
        for idx, da_detail in enumerate(da_details, 1):
            try:
                # Convert URL sang EN
                en_url = convert_da_url_to_en_url(da_detail.published_url)
                
                # Kiểm tra xem đã có EN version chưa
                existing_en = ArticleDetail.query.filter_by(
                    published_url=en_url,
                    language='en'
                ).first()
                
                if existing_en:
                    print(f"\n[{idx}/{len(da_details)}] Updating EN article_detail for {en_url[:70]}...")
                    print(f"   (Existing EN detail ID: {existing_en.id})")
                else:
                    print(f"\n[{idx}/{len(da_details)}] Creating EN article_detail for {en_url[:70]}...")
                
                # Translate
                en_detail = retranslate_en_article_detail(da_detail, delay=0.3)
                
                if existing_en:
                    updated_count += 1
                else:
                    created_count += 1
                
            except Exception as e:
                error_msg = f"Failed to translate article_detail {da_detail.id}: {e}"
                print(f"   ❌ {error_msg}")
                errors.append({
                    'article_detail_id': da_detail.id,
                    'error': str(e)
                })
                db.session.rollback()
                continue
        
        print(f"\n✅ Re-translation of article_details completed:")
        print(f"   - Updated: {updated_count}/{len(da_details)}")
        print(f"   - Created: {created_count}/{len(da_details)}")
        print(f"   - Errors: {len(errors)}")
        
        if errors:
            print(f"\n❌ Errors:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   - ArticleDetail {error['article_detail_id']}: {error['error']}")


def main():
    """Main function với options"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-translate EN articles and article_details')
    parser.add_argument('--articles-only', action='store_true',
                       help='Chỉ dịch articles, không dịch article_details')
    parser.add_argument('--article-details-only', action='store_true',
                       help='Chỉ dịch article_details, không dịch articles')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.article_details_only:
            retranslate_en_article_details()
        elif args.articles_only:
            retranslate_en_articles()
        else:
            # Dịch cả hai
            print("="*60)
            print("🔄 Re-translating Articles...")
            print("="*60)
            retranslate_en_articles()
            
            print("\n" + "="*60)
            print("🔄 Re-translating Article Details...")
            print("="*60)
            retranslate_en_article_details()


if __name__ == '__main__':
    main()

