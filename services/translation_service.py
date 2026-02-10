"""
Translation service để translate articles từ Danish sang English
"""
from deep_translator import GoogleTranslator
from database import Article, db
import time
from datetime import datetime
from contextlib import contextmanager
from seleniumbase import SB
import os
from pathlib import Path

# User data directory riêng cho Google Translate Web
USER_DATA_DIR_TRANSLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data_translate')


def get_chrome_options_for_headless():
    """
    Trả về Chrome options cần thiết cho Linux headless server
    """
    return "no-sandbox,disable-dev-shm-usage,disable-gpu"


@contextmanager
def start_browser_for_translate(headless=True):
    """
    Start browser để sử dụng Google Translate Web cho title/title_parts
    
    Args:
        headless: Run browser in headless mode
    
    Yields:
        SB instance
    """
    chrome_opts = get_chrome_options_for_headless()
    os.makedirs(USER_DATA_DIR_TRANSLATE, exist_ok=True)
    os.chmod(USER_DATA_DIR_TRANSLATE, 0o755)
    
    sb_context = SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR_TRANSLATE, chromium_arg=chrome_opts)
    sb = sb_context.__enter__()
    
    try:
        yield sb
    finally:
        sb_context.__exit__(None, None, None)


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
        
        # ⚠️ QUAN TRỌNG: Dùng Google Translate Web cho title để tránh dịch sai tên riêng
        # Translate title bằng Google Translate Web
        print(f"   🌐 Translating title using Google Translate Web...")
        from scripts.google_translate_web_helper import translate_text_with_google_web
        
        translated_title = None
        try:
            with start_browser_for_translate(headless=True) as sb_web:
                translated_title = translate_text_with_google_web(
                    sb_web,
                    dk_article.title,
                    source_lang='da',
                    target_lang='en'
                )
        except Exception as e:
            print(f"   ⚠️  Error translating title with Google Translate Web: {e}")
            # Fallback: dùng deep_translator
            print(f"   🔄 Falling back to deep_translator for title...")
        translated_title = translator.translate(dk_article.title)
        
        if translated_title:
            print(f"   ✅ Title translated: '{dk_article.title[:50]}...' → '{translated_title[:50]}...'")
        else:
            print(f"   ⚠️  Title translation failed, using original")
            translated_title = dk_article.title
        
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
            # ⚠️ QUAN TRỌNG: Dùng Google Translate Web cho titles
            if 'slider_articles' in translated_layout_data and isinstance(translated_layout_data['slider_articles'], list):
                print(f"   📰 Translating {len(translated_layout_data['slider_articles'])} slider articles...")
                
                # Tạo browser instance để dịch titles bằng Google Translate Web
                from scripts.google_translate_web_helper import translate_text_with_google_web
                try:
                    with start_browser_for_translate(headless=True) as sb_web:
                for article_idx, article in enumerate(translated_layout_data['slider_articles']):
                    if isinstance(article, dict):
                                # Translate article title bằng Google Translate Web
                        if 'title' in article and article['title']:
                                    translated_title = translate_text_with_google_web(
                                        sb_web,
                                        article['title'],
                                        source_lang='da',
                                        target_lang='en'
                                    )
                                    if translated_title:
                                        article['title'] = translated_title
                                        time.sleep(delay)
                                    else:
                                        # Fallback: dùng deep_translator
                            article['title'] = translator.translate(article['title'])
                            time.sleep(delay)
                        
                                # Translate article kicker - dùng deep_translator (không phải title)
                        if 'kicker' in article and article['kicker']:
                            article['kicker'] = translator.translate(article['kicker'])
                            time.sleep(delay)
                        
                                # Translate article excerpt nếu có - dùng deep_translator (không phải title)
                                if 'excerpt' in article and article['excerpt']:
                                    article['excerpt'] = translator.translate(article['excerpt'])
                                    time.sleep(delay)
                    print(f"   ✅ Slider articles translated (titles via Google Translate Web)")
                except Exception as e:
                    print(f"   ⚠️  Error translating slider articles with Google Translate Web: {e}")
                    # Fallback: dùng deep_translator cho tất cả
                    print(f"   🔄 Falling back to deep_translator for slider articles...")
                    for article_idx, article in enumerate(translated_layout_data['slider_articles']):
                        if isinstance(article, dict):
                            if 'title' in article and article['title']:
                                article['title'] = translator.translate(article['title'])
                                time.sleep(delay)
                            if 'kicker' in article and article['kicker']:
                                article['kicker'] = translator.translate(article['kicker'])
                                time.sleep(delay)
                        if 'excerpt' in article and article['excerpt']:
                            article['excerpt'] = translator.translate(article['excerpt'])
                            time.sleep(delay)
                    print(f"   ✅ Slider articles translated (fallback)")
            
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
                        # Không có EN article → translate text bằng Google Translate Web (fallback)
                        if da_title:
                            try:
                                # ⚠️ QUAN TRỌNG: Dùng Google Translate Web cho list item titles
                                from scripts.google_translate_web_helper import translate_text_with_google_web
                                translated_title = None
                                try:
                                    with start_browser_for_translate(headless=True) as sb_web:
                                        translated_title = translate_text_with_google_web(
                                            sb_web,
                                            da_title,
                                            source_lang='da',
                                            target_lang='en'
                                        )
                                except Exception as e:
                                    print(f"      ⚠️  Error translating list item title with Google Translate Web: {e}")
                                    # Fallback: dùng deep_translator
                                translated_title = translator.translate(da_title)
                                
                                if translated_title:
                                translated_item = {
                                    'url': item_url,
                                    'title': translated_title
                                }
                                translated_list_items.append(translated_item)
                                    print(f"      🌐 Translated list item (Google Translate Web): {translated_title[:50]}...")
                                time.sleep(delay)
                                else:
                                    # Fallback: giữ nguyên DA title
                                    translated_list_items.append(item)
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
            # ⚠️ QUAN TRỌNG: Thay vì dịch từng part riêng lẻ (có thể dịch sai tên riêng),
            # ta sẽ dùng translated_title đã dịch để reconstruct title_parts
            if 'title_parts' in translated_layout_data and isinstance(translated_layout_data['title_parts'], list):
                original_title_parts = translated_layout_data['title_parts']
                
                # Reconstruct title_parts từ translated_title để đảm bảo consistency
                # Giữ nguyên color_class từ original parts
                if translated_title and original_title_parts:
                    # Tìm các phần được highlight (có color_class)
                    highlighted_parts = [p for p in original_title_parts if isinstance(p, dict) and p.get('color_class')]
                    
                    if highlighted_parts:
                        # Có highlighted parts - cần tìm text tương ứng trong translated_title
                        # Strategy: Tìm text được highlight trong original, map sang translated_title
                        new_title_parts = []
                        remaining_title = translated_title
                        
                        for i, original_part in enumerate(original_title_parts):
                            if isinstance(original_part, dict) and original_part.get('color_class'):
                                # Đây là highlighted part
                                original_text = original_part.get('text', '').strip()
                                
                                # Tìm text tương ứng trong translated_title
                                # Nếu original_text là tên riêng, có thể đã bị dịch sai
                                # Nên ta sẽ tìm text ở vị trí tương ứng trong translated_title
                                
                                # Fallback: Nếu không tìm thấy, dịch original_text
                                if original_text in remaining_title:
                                    # Tìm thấy exact match
                                    pos = remaining_title.find(original_text)
                                    if pos > 0:
                                        # Text trước highlighted part
                                        before_text = remaining_title[:pos]
                                        if before_text.strip():
                                            new_title_parts.append({
                                                'text': before_text,
                                                'color_class': None
                                            })
                                    
                                    # Highlighted part
                                    highlighted_text = remaining_title[pos:pos + len(original_text)]
                                    new_title_parts.append({
                                        'text': highlighted_text,
                                        'color_class': original_part.get('color_class')
                                    })
                                    
                                    remaining_title = remaining_title[pos + len(original_text):]
                                else:
                                    # Không tìm thấy - có thể là tên riêng bị dịch sai
                                    # Dịch original_text bằng Google Translate Web để lấy bản dịch chính xác hơn
                                    try:
                                        from scripts.google_translate_web_helper import translate_text_with_google_web
                                        # Dùng browser instance đã có nếu có, nếu không tạo mới
                                        # Note: Trong trường hợp này, chúng ta đang trong context của translate_article
                                        # nên có thể tạo browser instance riêng cho title_parts
                                        with start_browser_for_translate(headless=True) as sb_web:
                                            translated_part = translate_text_with_google_web(
                                                sb_web,
                                                original_text,
                                                source_lang='da',
                                                target_lang='en'
                                            )
                                        if not translated_part:
                                            # Fallback: dùng deep_translator
                                            translated_part = translator.translate(original_text)
                                        time.sleep(delay)
                                        
                                        # Tìm translated_part trong remaining_title
                                        if translated_part in remaining_title:
                                            pos = remaining_title.find(translated_part)
                                            if pos > 0:
                                                before_text = remaining_title[:pos]
                                                if before_text.strip():
                                                    new_title_parts.append({
                                                        'text': before_text,
                                                        'color_class': None
                                                    })
                                            
                                            new_title_parts.append({
                                                'text': translated_part,
                                                'color_class': original_part.get('color_class')
                                            })
                                            remaining_title = remaining_title[pos + len(translated_part):] if pos >= 0 else remaining_title
                                        else:
                                            # Không tìm thấy trong translated_title - có thể đã bị dịch khác
                                            # Dùng translated_part trực tiếp
                                            new_title_parts.append({
                                                'text': translated_part,
                                                'color_class': original_part.get('color_class')
                                            })
                                    except:
                                        # Lỗi dịch - giữ nguyên original text
                                        new_title_parts.append({
                                            'text': original_text,
                                            'color_class': original_part.get('color_class')
                                        })
                            else:
                                # Non-highlighted part - bỏ qua vì sẽ được thêm vào cuối
                                pass
                        
                        # Thêm phần còn lại
                        if remaining_title.strip():
                            new_title_parts.append({
                                'text': remaining_title,
                                'color_class': None
                            })
                        
                        # Nếu không tạo được parts hợp lý, fallback: split translated_title dựa trên structure của original
                        if not new_title_parts or ''.join([p.get('text', '') for p in new_title_parts]).strip() != translated_title.strip():
                            # Fallback: Tạo parts đơn giản từ translated_title
                            # Giữ highlight cho part đầu tiên nếu có
                            if ':' in translated_title:
                                parts = translated_title.split(':', 1)
                                new_title_parts = [
                                    {'text': parts[0] + ':', 'color_class': original_title_parts[0].get('color_class') if original_title_parts and isinstance(original_title_parts[0], dict) else None},
                                    {'text': parts[1], 'color_class': None}
                                ]
                            else:
                                new_title_parts = [{'text': translated_title, 'color_class': original_title_parts[0].get('color_class') if original_title_parts and isinstance(original_title_parts[0], dict) else None}]
                        
                        translated_layout_data['title_parts'] = new_title_parts
                        print(f"   ✅ Title parts reconstructed from translated title")
                    else:
                        # Không có highlighted parts - tạo parts đơn giản
                        translated_layout_data['title_parts'] = [{'text': translated_title, 'color_class': None}]
                else:
                    # Fallback: Dịch từng part như cũ (nếu không có translated_title)
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
            section='home' if dk_article.is_home else dk_article.section,  # ⚠️ Home articles luôn có section='home'
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
            # ⚠️ QUAN TRỌNG: Với home articles, chỉ check theo published_url + language
            # vì section có thể khác nhau (detect từ URL: 'samfund', 'sport', etc.)
            existing = None
            
            if dk_article.published_url:
                if dk_article.is_home:
                    # Home articles: chỉ check theo published_url + language
                    # (không check section vì có thể khác nhau)
                    existing = Article.query.filter_by(
                        published_url=dk_article.published_url,
                        language='en'
                    ).first()
                else:
                    # Section articles: check theo published_url + language + section
                    existing = Article.query.filter_by(
                        published_url=dk_article.published_url,
                        language='en',
                        section=dk_article.section
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

