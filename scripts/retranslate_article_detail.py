"""
Re-translate một article_detail để sửa lỗi khoảng trắng
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from scripts.crawl_article_details_batch import translate_content_blocks, create_en_article_detail_from_da
import json

def retranslate_article_detail(detail_id):
    """
    Re-translate một article_detail EN từ DA version
    """
    with app.app_context():
        # Get EN detail
        en_detail = ArticleDetail.query.get(detail_id)
        if not en_detail:
            print(f"❌ ArticleDetail {detail_id} not found")
            return
        
        if en_detail.language != 'en':
            print(f"❌ ArticleDetail {detail_id} is not EN (language: {en_detail.language})")
            return
        
        print(f"\n{'='*60}")
        print(f"Re-translating ArticleDetail ID: {en_detail.id}")
        print(f"Language: {en_detail.language}")
        print(f"URL: {en_detail.published_url}")
        print(f"{'='*60}\n")
        
        # Find corresponding DA detail
        da_detail = ArticleDetail.query.filter_by(
            published_url=en_detail.published_url,
            language='da'
        ).first()
        
        if not da_detail:
            print(f"❌ No DA version found for this URL")
            return
        
        print(f"Found DA version (ID: {da_detail.id})")
        print(f"Re-translating content blocks...\n")
        
        # Re-translate content blocks
        translated_blocks = translate_content_blocks(
            da_detail.content_blocks or [],
            source_lang='da',
            target_lang='en',
            delay=0.3
        )
        
        # Update EN detail
        en_detail.content_blocks = translated_blocks
        
        try:
            db.session.commit()
            print(f"✅ Successfully updated ArticleDetail {en_detail.id}")
            print(f"   Blocks: {len(translated_blocks)}")
            
            # Show subtitle block
            for block in translated_blocks:
                if block.get('type') == 'subtitle':
                    print(f"\nSubtitle block:")
                    print(f"  Text: {block.get('text')}")
                    print(f"  HTML: {block.get('html')}")
                    break
        except Exception as e:
            print(f"❌ Error updating: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-translate an article_detail')
    parser.add_argument('detail_id', type=int, help='ArticleDetail ID to re-translate')
    
    args = parser.parse_args()
    retranslate_article_detail(args.detail_id)

