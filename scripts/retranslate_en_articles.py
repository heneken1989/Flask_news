#!/usr/bin/env python3
"""
Script để re-translate các EN articles đã có để update layout_data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from services.translation_service import translate_article

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

if __name__ == '__main__':
    retranslate_en_articles()

