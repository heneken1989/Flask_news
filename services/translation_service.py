"""
Translation service để translate articles từ Danish sang English
"""
from deep_translator import GoogleTranslator
from database import Article, db
import time
from datetime import datetime


def translate_article(dk_article, target_language='en', delay=0.5):
    """
    Translate article từ Danish sang English
    
    Args:
        dk_article: Article object với language='da'
        target_language: Target language ('en')
        delay: Delay giữa các lần translate (giây) để tránh rate limit
    
    Returns:
        Article object với language='en' (chưa save vào database)
    """
    if dk_article.language != 'da':
        raise ValueError(f"Source article must be in Danish (da), got {dk_article.language}")
    
    if target_language != 'en':
        raise ValueError(f"Only English (en) translation is supported, got {target_language}")
    
    print(f"🌐 Translating article {dk_article.id}: '{dk_article.title[:50]}...'")
    
    try:
        translator = GoogleTranslator(source='da', target='en')
        
        # Translate title
        translated_title = translator.translate(dk_article.title)
        print(f"   ✅ Title translated")
        
        # Delay để tránh rate limit
        time.sleep(delay)
        
        # Translate content (nếu có)
        translated_content = None
        if dk_article.content:
            translated_content = translator.translate(dk_article.content)
            print(f"   ✅ Content translated ({len(translated_content)} chars)")
            time.sleep(delay)
        
        # Translate excerpt (nếu có)
        translated_excerpt = None
        if dk_article.excerpt:
            translated_excerpt = translator.translate(dk_article.excerpt)
            print(f"   ✅ Excerpt translated")
            time.sleep(delay)
        
        # Translate layout_data fields (nếu có)
        translated_layout_data = None
        if dk_article.layout_data:
            translated_layout_data = dk_article.layout_data.copy()
            
            # Translate kicker
            if 'kicker' in translated_layout_data and translated_layout_data['kicker']:
                translated_layout_data['kicker'] = translator.translate(translated_layout_data['kicker'])
                time.sleep(delay)
            
            # Translate kicker_floating
            if 'kicker_floating' in translated_layout_data and translated_layout_data['kicker_floating']:
                translated_layout_data['kicker_floating'] = translator.translate(translated_layout_data['kicker_floating'])
                time.sleep(delay)
            
            # Translate kicker_below
            if 'kicker_below' in translated_layout_data and translated_layout_data['kicker_below']:
                translated_layout_data['kicker_below'] = translator.translate(translated_layout_data['kicker_below'])
                time.sleep(delay)
            
            # Translate slider_title (quan trọng!)
            if 'slider_title' in translated_layout_data and translated_layout_data['slider_title']:
                translated_layout_data['slider_title'] = translator.translate(translated_layout_data['slider_title'])
                print(f"   ✅ Slider title translated: '{translated_layout_data['slider_title']}'")
                time.sleep(delay)
            
            # Translate slider_articles (các articles trong slider)
            if 'slider_articles' in translated_layout_data and isinstance(translated_layout_data['slider_articles'], list):
                print(f"   📰 Translating {len(translated_layout_data['slider_articles'])} slider articles...")
                for article_idx, article in enumerate(translated_layout_data['slider_articles']):
                    if isinstance(article, dict):
                        # Translate article title
                        if 'title' in article and article['title']:
                            article['title'] = translator.translate(article['title'])
                            time.sleep(delay)
                        
                        # Translate article kicker
                        if 'kicker' in article and article['kicker']:
                            article['kicker'] = translator.translate(article['kicker'])
                            time.sleep(delay)
                        
                        # Translate article excerpt nếu có
                        if 'excerpt' in article and article['excerpt']:
                            article['excerpt'] = translator.translate(article['excerpt'])
                            time.sleep(delay)
                print(f"   ✅ Slider articles translated")
            
            # Translate header_link text (cho JOB slider)
            if 'header_link' in translated_layout_data and isinstance(translated_layout_data['header_link'], dict):
                header_link = translated_layout_data['header_link']
                if 'text' in header_link and header_link['text']:
                    header_link['text'] = translator.translate(header_link['text'])
                    time.sleep(delay)
            
            # Translate list_title
            if 'list_title' in translated_layout_data and translated_layout_data['list_title']:
                translated_layout_data['list_title'] = translator.translate(translated_layout_data['list_title'])
                time.sleep(delay)
            
            # Translate list_items titles
            # ⚠️ QUAN TRỌNG: Tìm EN article tương ứng cho mỗi URL thay vì chỉ translate text
            if 'list_items' in translated_layout_data:
                from urllib.parse import urljoin, urlparse
                
                base_url = 'https://www.sermitsiaq.ag'
                translated_list_items = []
                
                for item in translated_layout_data['list_items']:
                    item_url = item.get('url', '')
                    da_title = item.get('title', '')
                    
                    if not item_url:
                        # Không có URL, giữ nguyên item
                        translated_list_items.append(item)
                        continue
                    
                    # Normalize URL: convert relative URL sang full URL để match
                    normalized_url = item_url
                    if item_url.startswith('/'):
                        normalized_url = urljoin(base_url, item_url)
                    
                    # Tìm EN article tương ứng trong DB
                    en_article = None
                    try:
                        # Tìm EN article có published_url = normalized_url (DA URL)
                        en_article = Article.query.filter_by(
                            published_url=normalized_url,
                            language='en'
                        ).first()
                        
                        # Nếu không tìm thấy, thử tìm bằng published_url_en
                        if not en_article:
                            en_article = Article.query.filter_by(
                                published_url_en=normalized_url,
                                language='en'
                            ).first()
                    except Exception as e:
                        print(f"      ⚠️  Error finding EN article for URL {item_url}: {e}")
                    
                    if en_article and en_article.title:
                        # Có EN article → dùng EN title
                        translated_item = {
                            'url': item_url,  # Giữ nguyên URL format
                            'title': en_article.title
                        }
                        translated_list_items.append(translated_item)
                        print(f"      ✅ Found EN article for list item: {en_article.title[:50]}...")
                    else:
                        # Không có EN article → translate text (fallback)
                        if da_title:
                            try:
                                translated_title = translator.translate(da_title)
                                translated_item = {
                                    'url': item_url,
                                    'title': translated_title
                                }
                                translated_list_items.append(translated_item)
                                print(f"      🌐 Translated list item (no EN article found): {translated_title[:50]}...")
                                time.sleep(delay)
                            except Exception as e:
                                print(f"      ⚠️  Error translating list item title: {e}")
                                # Fallback: giữ nguyên DA title
                                translated_list_items.append(item)
                        else:
                            # Không có title, giữ nguyên item
                            translated_list_items.append(item)
                
                # Update với list_items đã được translate
                translated_layout_data['list_items'] = translated_list_items
            
            # Translate title_parts nếu có (cho highlights)
            if 'title_parts' in translated_layout_data and isinstance(translated_layout_data['title_parts'], list):
                for part in translated_layout_data['title_parts']:
                    if isinstance(part, dict) and 'text' in part and part['text']:
                        part['text'] = translator.translate(part['text'])
                        time.sleep(delay)
        
        # Create translated article (lưu trực tiếp, không dùng temp)
        en_article = Article(
            title=translated_title,
            slug=dk_article.slug,  # Giữ nguyên slug
            content=translated_content,
            excerpt=translated_excerpt,
            language='en',
            canonical_id=dk_article.id,  # Link với DK version
            original_language='da',
            is_temp=False,  # Lưu trực tiếp, không dùng temp
            # Copy other fields
            element_guid=dk_article.element_guid,
            instance=dk_article.instance,
            site_alias=dk_article.site_alias,
            k5a_url=dk_article.k5a_url,  # Giữ nguyên URL
            published_url=dk_article.published_url,  # Giữ nguyên URL
            category_id=dk_article.category_id,
            section=dk_article.section,
            display_order=dk_article.display_order,
            is_featured=dk_article.is_featured,
            is_home=dk_article.is_home,
            article_type=dk_article.article_type,
            position=dk_article.position,
            grid_size=dk_article.grid_size,
            layout_type=dk_article.layout_type,
            layout_data=translated_layout_data or dk_article.layout_data,
            is_paywall=dk_article.is_paywall,
            paywall_class=dk_article.paywall_class,
            published_date=dk_article.published_date,
            image_data=dk_article.image_data,  # Giữ nguyên image
            crawl_metadata=dk_article.crawl_metadata
        )
        
        print(f"   ✅ Translation completed")
        return en_article
        
    except Exception as e:
        print(f"   ❌ Translation failed: {e}")
        raise


def translate_articles_batch(dk_articles, target_language='en', save_to_db=True, delay=0.5):
    """
    Translate multiple articles từ Danish sang English
    
    Args:
        dk_articles: List of Article objects với language='da'
        target_language: Target language ('en')
        save_to_db: Whether to save translated articles to database
        delay: Delay giữa các lần translate (giây)
    
    Returns:
        tuple: (translated_articles, errors, stats) where stats is dict with 'new_count' and 'skipped_count'
    """
    translated_articles = []
    errors = []
    new_count = 0
    skipped_count = 0
    
    for idx, dk_article in enumerate(dk_articles, 1):
        try:
            print(f"\n[{idx}/{len(dk_articles)}] Translating article {dk_article.id}...")
            
            # Check if translation already exists bằng published_url + language='en'
            # Đảm bảo không tạo duplicate EN articles
            existing = None
            
            if dk_article.published_url:
                existing = Article.query.filter_by(
                    published_url=dk_article.published_url,
                    language='en',
                    section=dk_article.section,
                    is_home=dk_article.is_home
                ).first()
            
            if existing:
                # Nếu article đã tồn tại, chỉ set is_temp=False nếu cần và skip
                if existing.is_temp:
                    # Chỉ set is_temp=False, không re-translate
                    existing.is_temp = False
                    db.session.commit()
                    print(f"   ✅ Set is_temp=False for existing article (ID: {existing.id})")
                
                # Đảm bảo canonical_id được set đúng (nếu chưa có)
                if not existing.canonical_id:
                    existing.canonical_id = dk_article.id
                    db.session.commit()
                    print(f"   ✅ Set canonical_id={dk_article.id} for existing article (ID: {existing.id})")
                
                print(f"   ⏭️  Translation already exists (ID: {existing.id}, published_url: {existing.published_url[:60] if existing.published_url else 'N/A'}...). Skipping...")
                translated_articles.append(existing)  # Add existing to list để đếm
                skipped_count += 1
                continue
            
            # Translate và lưu trực tiếp (không dùng temp)
            en_article = translate_article(dk_article, target_language, delay)
            
            if save_to_db:
                db.session.add(en_article)
                db.session.commit()
                print(f"   ✅ Saved translation to database (ID: {en_article.id})")
            
            translated_articles.append(en_article)
            new_count += 1
            
        except Exception as e:
            error_msg = f"Failed to translate article {dk_article.id}: {e}"
            print(f"   ❌ {error_msg}")
            errors.append({
                'article_id': dk_article.id,
                'error': str(e)
            })
            db.session.rollback()
            continue
    
    print(f"\n✅ Translation batch completed:")
    print(f"   - New translations: {new_count}")
    print(f"   - Skipped (already translated): {skipped_count}")
    print(f"   - Errors: {len(errors)}")
    
    if errors:
        print(f"\n❌ Errors:")
        for error in errors:
            print(f"   - Article {error['article_id']}: {error['error']}")
    
    stats = {
        'new_count': new_count,
        'skipped_count': skipped_count
    }
    
    return translated_articles, errors, stats

