"""
Script để crawl article detail pages theo batch
- List tất cả articles với published_url và ID
- Check xem ArticleDetail đã tồn tại chưa (dựa vào published_url)
- Chỉ crawl những article detail chưa có

Usage:
    # List tất cả articles cần crawl
    python scripts/crawl_article_details_batch.py --list
    
    # Crawl tất cả articles chưa có detail
    python scripts/crawl_article_details_batch.py --crawl-all
    
    # Crawl theo language
    python scripts/crawl_article_details_batch.py --crawl-all --language en
    
    # Crawl theo section
    python scripts/crawl_article_details_batch.py --crawl-all --section samfund
    
    # Crawl giới hạn số lượng
    python scripts/crawl_article_details_batch.py --crawl-all --limit 10
    
    # Crawl với headless mode (default)
    python scripts/crawl_article_details_batch.py --crawl-all --headless
    
    # Crawl với no-headless mode (để debug)
    python scripts/crawl_article_details_batch.py --crawl-all --no-headless
"""
import sys
import os
import argparse
from datetime import datetime
import time
from contextlib import contextmanager
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from services.article_detail_parser import ArticleDetailParser
from services.image_downloader import download_and_update_image_data
from seleniumbase import SB
from deep_translator import GoogleTranslator
import re
import json

# User data directory để lưu session login
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')
LOGIN_URL = "https://www.sermitsiaq.ag/login"
LOGIN_EMAIL = "aluu@greenland.org"
LOGIN_PASSWORD = "LEn924924jfkjfk"


def get_chrome_options_for_headless():
    """
    Trả về Chrome options cần thiết cho Linux headless server
    Cần thiết khi chạy với root hoặc không có display
    """
    # --no-sandbox: Bỏ qua sandbox (cần thiết khi chạy với root)
    # --disable-dev-shm-usage: Tránh lỗi shared memory trên VPS
    # --disable-gpu: Tắt GPU (không cần trên server)
    return "no-sandbox,disable-dev-shm-usage,disable-gpu"


def kill_chrome_processes():
    """
    Kill tất cả Chrome/Chromium processes đang chạy để tránh conflict
    """
    import subprocess
    try:
        # Tìm tất cả Chrome processes
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        chrome_pids = []
        for line in result.stdout.split('\n'):
            if any(keyword in line.lower() for keyword in ['chrome', 'chromium', 'chromedriver']):
                # Tránh kill chính script này
                if 'check_chrome_status.py' not in line and 'python' not in line.lower()[:50]:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            chrome_pids.append(pid)
                        except:
                            pass
        
        if chrome_pids:
            print(f"   🔪 Killing {len(chrome_pids)} Chrome/Chromium processes: {chrome_pids[:5]}{'...' if len(chrome_pids) > 5 else ''}")
            for pid in chrome_pids:
                try:
                    os.kill(pid, 9)  # SIGKILL
                except ProcessLookupError:
                    # Process đã chết
                    pass
                except Exception as e:
                    print(f"   ⚠️  Error killing process {pid}: {e}")
            
            # Đợi một chút để processes được kill
            time.sleep(2)
            print(f"   ✅ Killed Chrome processes")
            return len(chrome_pids)
        else:
            return 0
            
    except Exception as e:
        print(f"   ⚠️  Error killing Chrome processes: {e}")
        return 0


def cleanup_user_data_dir():
    """
    Xóa user_data_dir cũ nếu tồn tại để tránh conflict
    """
    if os.path.exists(USER_DATA_DIR):
        try:
            print(f"   🗑️  Removing old user_data_dir: {USER_DATA_DIR}")
            shutil.rmtree(USER_DATA_DIR)
            print(f"   ✅ Removed old user_data_dir")
        except Exception as e:
            print(f"   ⚠️  Error removing user_data_dir: {e}")
            # Thử xóa từng file nếu không xóa được cả thư mục
            try:
                for root, dirs, files in os.walk(USER_DATA_DIR):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                        except:
                            pass
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root, d))
                        except:
                            pass
                os.rmdir(USER_DATA_DIR)
                print(f"   ✅ Removed user_data_dir (file by file)")
            except:
                pass


def create_fresh_user_data_dir():
    """
    Tạo user_data_dir mới với permissions đúng
    """
    cleanup_user_data_dir()
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    os.chmod(USER_DATA_DIR, 0o755)  # rwxr-xr-x
    print(f"   ✅ Created fresh user_data_dir: {USER_DATA_DIR}")


@contextmanager
def start_browser_with_retry(headless=True, max_retries=2):
    """
    Start browser với retry logic: nếu không start được, xóa user_data_dir và thử lại
    
    Args:
        headless: Run browser in headless mode
        max_retries: Số lần retry tối đa
    
    Yields:
        SB instance
    """
    chrome_opts = get_chrome_options_for_headless()
    sb_context = None
    sb = None
    sb_entered = False
    
    for attempt in range(max_retries + 1):
        try:
            # Kill Chrome processes trước khi start (tránh conflict)
            if attempt == 0:
                # Lần đầu: kill Chrome processes nếu có
                killed = kill_chrome_processes()
                if killed > 0:
                    print(f"   ⏳ Waiting 3 seconds for processes to fully terminate...")
                    time.sleep(3)
            else:
                # Các lần retry: kill lại và tạo lại user_data_dir mới
                print(f"   🔄 Retry attempt {attempt}/{max_retries}: Killing Chrome processes and creating fresh user_data_dir...")
                kill_chrome_processes()
                time.sleep(2)
                create_fresh_user_data_dir()
            
            # Tạo user_data_dir nếu chưa tồn tại
            if attempt == 0:
                # Lần đầu: thử với user_data_dir hiện tại (nếu có)
                os.makedirs(USER_DATA_DIR, exist_ok=True)
                os.chmod(USER_DATA_DIR, 0o755)
            
            # Thử start browser - sử dụng context manager đúng cách
            sb_context = SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR, chromium_arg=chrome_opts)
            sb = sb_context.__enter__()  # Start browser và lấy SB instance
            sb_entered = True
            print(f"   ✅ Browser started successfully (attempt {attempt + 1}/{max_retries + 1})")
            try:
                yield sb
            finally:
                # Cleanup khi exit context
                if sb_entered and sb_context:
                    try:
                        sb_context.__exit__(None, None, None)
                    except Exception as cleanup_error:
                        print(f"   ⚠️  Error during browser cleanup: {cleanup_error}")
            return
            
        except Exception as e:
            error_msg = str(e)
            error_type = str(type(e))
            
            # Cleanup nếu browser đã được start nhưng có lỗi
            if sb_entered and sb_context:
                try:
                    sb_context.__exit__(None, None, None)
                except:
                    pass
                sb_entered = False
                sb_context = None
                sb = None
            
            # Kiểm tra xem có phải lỗi browser start không
            is_browser_start_error = (
                'SessionNotCreatedException' in error_type or 
                'cannot connect to chrome' in error_msg.lower() or 
                'chrome not reachable' in error_msg.lower() or
                'session not created' in error_msg.lower()
            )
            
            if is_browser_start_error:
                if attempt < max_retries:
                    print(f"   ⚠️  Browser start failed (attempt {attempt + 1}/{max_retries + 1}): {error_msg[:150]}")
                    print(f"   🔄 Will retry with fresh user_data_dir...")
                    sb = None
                    continue
                else:
                    print(f"   ❌ Browser start failed after {max_retries + 1} attempts")
                    print(f"   ❌ Last error: {error_msg[:200]}")
                    raise
            else:
                # Lỗi khác, không retry - re-raise ngay
                print(f"   ❌ Browser start failed with unexpected error: {error_msg[:200]}")
                raise


def get_articles_to_crawl(language=None, section=None, limit=None):
    """
    Lấy danh sách articles cần crawl (chưa có ArticleDetail)
    
    Args:
        language: Filter theo language (da, kl, en)
        section: Filter theo section (samfund, sport, kultur, etc.)
        limit: Giới hạn số lượng articles
    
    Returns:
        List of Article objects
    """
    query = Article.query.filter(
        Article.published_url.isnot(None),
        Article.published_url != ''
    )
    
    # Loại bỏ www.sjob.gl
    query = query.filter(~Article.published_url.contains('www.sjob.gl'))
    
    # Loại bỏ articles có language='en' (được dịch từ DK, không phải articles gốc)
    query = query.filter(Article.language != 'en')
    
    # Filter theo language
    if language:
        query = query.filter_by(language=language)
    
    # Filter theo section
    if section:
        query = query.filter_by(section=section)
    
    # Order by published_date desc
    query = query.order_by(Article.published_date.desc().nullslast())
    
    # Limit
    if limit:
        query = query.limit(limit)
    
    articles = query.all()
    
    # Filter: chỉ lấy những articles chưa có ArticleDetail
    articles_to_crawl = []
    for article in articles:
        # Double check: loại bỏ www.sjob.gl (nếu có)
        if 'www.sjob.gl' in article.published_url:
            continue
        
        # Double check: loại bỏ articles có language='en' (được dịch từ DK)
        if article.language == 'en':
            continue
        
        existing_detail = ArticleDetail.query.filter_by(
            published_url=article.published_url
        ).first()
        
        if not existing_detail:
            articles_to_crawl.append(article)
    
    return articles_to_crawl


def convert_da_url_to_en_url(da_url: str) -> str:
    """
    Convert URL từ DA sang EN
    Ví dụ: https://www.sermitsiaq.ag/... -> https://www.sermitsiaq.ag/... (giữ nguyên)
    Hoặc: https://kl.sermitsiaq.ag/... -> https://www.sermitsiaq.ag/...
    
    Args:
        da_url: URL tiếng Đan Mạch
        
    Returns:
        URL tiếng Anh tương ứng
    """
    # Loại bỏ kl. prefix nếu có
    en_url = da_url.replace('kl.sermitsiaq.ag', 'www.sermitsiaq.ag')
    # Đảm bảo là www.sermitsiaq.ag (không phải kl.)
    en_url = re.sub(r'https?://kl\.', 'https://www.', en_url)
    return en_url


def translate_content_blocks(content_blocks: list, source_lang: str = 'da', target_lang: str = 'en', delay: float = 0.3) -> list:
    """
    Dịch content_blocks từ source_lang sang target_lang
    Sử dụng GoogleTranslator từ deep_translator (giống translation_service)
    
    Args:
        content_blocks: List of content blocks
        source_lang: Source language code ('da')
        target_lang: Target language code ('en')
        delay: Delay giữa các lần translate (giây) để tránh rate limit
        
    Returns:
        Translated content blocks
    """
    if not content_blocks:
        return []
    
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    translated_blocks = []
    
    for block in content_blocks:
        translated_block = block.copy()
        
        # Chỉ dịch các block có text content
        if block.get('type') in ['paragraph', 'heading', 'intro', 'subtitle', 'title']:
            # Dịch text
            if block.get('text'):
                try:
                    original_text = block['text']
                    translated_text = translator.translate(original_text)
                    
                    # Viết hoa chữ đầu câu nếu chưa viết hoa
                    # Chỉ viết hoa nếu chữ đầu là chữ thường
                    if translated_text and translated_text[0].islower():
                        translated_text = translated_text[0].upper() + translated_text[1:]
                    
                    translated_block['text'] = translated_text
                    time.sleep(delay)  # Delay để tránh rate limit
                except Exception as e:
                    print(f"      ⚠️  Translation error for text: {e}")
                    # Giữ nguyên text nếu dịch lỗi
                    translated_block['text'] = block['text']
            
            # Dịch HTML content (chỉ dịch text trong tags, giữ nguyên tags)
            if block.get('html'):
                try:
                    html = block['html']
                    
                    # BƯỚC 1: Sửa lỗi thiếu khoảng trắng TRƯỚC KHI dịch
                    # Thêm khoảng trắng trước tag nếu word kết thúc bằng chữ cái và tag bắt đầu bằng chữ cái
                    # Ví dụ: "candies<span" -> "candies <span"
                    html = re.sub(r'([a-zA-Z])(<[a-zA-Z/])', r'\1 \2', html)
                    
                    # BƯỚC 1.5: Đảm bảo có khoảng trắng sau dấu phẩy và trước chữ cái (nếu thiếu)
                    # Ví dụ: ",KNQK" -> ", KNQK" hoặc "</span>KNQK" -> "</span> KNQK"
                    # Nhưng không sửa nếu đã có khoảng trắng hoặc tag
                    html = re.sub(r'(,)([A-Za-z])', r'\1 \2', html)  # Dấu phẩy trước chữ cái
                    html = re.sub(r'(</[^>]+>)([A-Za-z])', r'\1 \2', html)  # Closing tag trước chữ cái
                    
                    # Tìm tất cả text nodes và dịch
                    first_text_node = True  # Flag để biết text node đầu tiên
                    def translate_html_text(match):
                        nonlocal first_text_node
                        text = match.group(1)
                        if text.strip():
                            try:
                                translated = translator.translate(text)
                                
                                # Viết hoa chữ đầu của text node đầu tiên trong block
                                # (thường là đầu câu/đoạn)
                                if first_text_node and translated:
                                    # Tìm chữ cái đầu tiên và viết hoa
                                    for i, char in enumerate(translated):
                                        if char.isalpha():
                                            translated = translated[:i] + char.upper() + translated[i+1:]
                                            break
                                    first_text_node = False
                                
                                time.sleep(delay)
                                return f'>{translated}<'
                            except:
                                return match.group(0)
                        return match.group(0)
                    
                    # Dịch text giữa các tags
                    translated_html = re.sub(r'>([^<]+)<', translate_html_text, html)
                    
                    # BƯỚC 2: Sửa lại sau khi dịch (đảm bảo không có lỗi mới)
                    # Thêm khoảng trắng nếu vẫn còn pattern "word<tag" sau khi dịch
                    translated_html = re.sub(r'([a-zA-Z])(<[a-zA-Z/])', r'\1 \2', translated_html)
                    
                    # Đảm bảo có khoảng trắng sau dấu phẩy (sau khi dịch có thể bị mất)
                    translated_html = re.sub(r'(,)([A-Za-z])', r'\1 \2', translated_html)
                    translated_html = re.sub(r'(</[^>]+>)([A-Za-z])', r'\1 \2', translated_html)
                    
                    # Sửa lỗi "candiesis" -> "candies is" nếu có
                    translated_html = re.sub(r'candiesis', 'candies is', translated_html, flags=re.IGNORECASE)
                    
                    translated_block['html'] = translated_html
                    
                    # Cập nhật text field từ HTML sau khi dịch (để đảm bảo text và HTML đồng bộ)
                    # Extract text từ HTML để có text chính xác
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(translated_html, 'html.parser')
                        extracted_text = soup.get_text(separator=' ', strip=True)
                        # Normalize khoảng trắng (đảm bảo có khoảng sau dấu phẩy)
                        extracted_text = re.sub(r'(,)([A-Za-z])', r'\1 \2', extracted_text)
                        # Chỉ cập nhật nếu text field đã được dịch (tránh ghi đè text gốc)
                        if block.get('text') and translated_block.get('text'):
                            translated_block['text'] = extracted_text
                    except:
                        # Nếu không extract được, giữ nguyên text đã dịch
                        pass
                except Exception as e:
                    print(f"      ⚠️  Translation error for HTML: {e}")
                    # Giữ nguyên HTML nếu dịch lỗi
                    translated_block['html'] = block['html']
        
        # Dịch header_image_caption block
        if block.get('type') == 'header_image_caption':
            # Dịch caption nếu có
            if block.get('caption'):
                try:
                    translated_caption = translator.translate(block['caption'])
                    translated_block['caption'] = translated_caption
                    time.sleep(delay)
                except Exception as e:
                    print(f"      ⚠️  Translation error for header_image_caption caption: {e}")
                    translated_block['caption'] = block['caption']
            
            # Author không cần dịch (tên người)
            # Nhưng có thể cần xử lý prefix "Foto: " / "Assi: "
            if block.get('author'):
                # Author đã được xử lý prefix trong parser, chỉ giữ nguyên
                translated_block['author'] = block['author']
        
        # Dịch article_meta block (bylines descriptions và dates)
        if block.get('type') == 'article_meta':
            if block.get('bylines'):
                translated_bylines = []
                for byline in block.get('bylines', []):
                    translated_byline = byline.copy()
                    # Dịch description nếu có
                    if byline.get('description'):
                        try:
                            translated_desc = translator.translate(byline['description'])
                            translated_byline['description'] = translated_desc
                            time.sleep(delay)
                        except Exception as e:
                            print(f"      ⚠️  Translation error for byline description: {e}")
                            # Giữ nguyên nếu dịch lỗi
                            translated_byline['description'] = byline['description']
                    translated_bylines.append(translated_byline)
                translated_block['bylines'] = translated_bylines
            
            # Dịch dates
            if block.get('dates'):
                translated_dates = {}
                for date_type, date_info in block.get('dates', {}).items():
                    translated_date_info = date_info.copy()
                    
                    # Dịch label (ví dụ: "Offentliggjort" -> "Published")
                    if date_info.get('label'):
                        try:
                            translated_label = translator.translate(date_info['label'])
                            translated_date_info['label'] = translated_label
                            time.sleep(delay)
                        except Exception as e:
                            print(f"      ⚠️  Translation error for date label: {e}")
                            translated_date_info['label'] = date_info['label']
                    
                    # Dịch title (ví dụ: "Offentliggjort mandag 19. jan 2026 06:04" -> "Published Monday 19. Jan 2026 06:04")
                    if date_info.get('title'):
                        try:
                            translated_title = translator.translate(date_info['title'])
                            translated_date_info['title'] = translated_title
                            time.sleep(delay)
                        except Exception as e:
                            print(f"      ⚠️  Translation error for date title: {e}")
                            translated_date_info['title'] = date_info['title']
                    
                    # Dịch text (ví dụ: "mandag 19. jan 2026 06:04" -> "Monday 19. Jan 2026 06:04")
                    if date_info.get('text'):
                        try:
                            translated_text = translator.translate(date_info['text'])
                            translated_date_info['text'] = translated_text
                            time.sleep(delay)
                        except Exception as e:
                            print(f"      ⚠️  Translation error for date text: {e}")
                            translated_date_info['text'] = date_info['text']
                    
                    # datetime giữ nguyên (ISO format)
                    if date_info.get('datetime'):
                        translated_date_info['datetime'] = date_info['datetime']
                    
                    translated_dates[date_type] = translated_date_info
                
                translated_block['dates'] = translated_dates
        
        # Dịch article_footer_tags block (tags text)
        if block.get('type') == 'article_footer_tags':
            if block.get('tags'):
                translated_tags = []
                for tag in block.get('tags', []):
                    translated_tag = tag.copy()
                    # Dịch tag text nếu có
                    if tag.get('text'):
                        try:
                            translated_text = translator.translate(tag['text'])
                            translated_tag['text'] = translated_text
                            time.sleep(delay)
                        except Exception as e:
                            print(f"      ⚠️  Translation error for tag text: {e}")
                            # Giữ nguyên nếu dịch lỗi
                            translated_tag['text'] = tag['text']
                    translated_tags.append(translated_tag)
                translated_block['tags'] = translated_tags
        
        # Dịch image block (caption và author)
        if block.get('type') == 'image':
            # Dịch caption nếu có
            if block.get('caption'):
                try:
                    translated_caption = translator.translate(block['caption'])
                    translated_block['caption'] = translated_caption
                    time.sleep(delay)
                except Exception as e:
                    print(f"      ⚠️  Translation error for image caption: {e}")
                    # Giữ nguyên nếu dịch lỗi
                    translated_block['caption'] = block['caption']
            
            # Dịch author nếu có
            if block.get('author'):
                try:
                    translated_author = translator.translate(block['author'])
                    translated_block['author'] = translated_author
                    time.sleep(delay)
                except Exception as e:
                    print(f"      ⚠️  Translation error for image author: {e}")
                    # Giữ nguyên nếu dịch lỗi
                    translated_block['author'] = block['author']
        
        # Giữ nguyên các block khác (ads, paywall_offers, etc.)
        translated_blocks.append(translated_block)
    
    return translated_blocks


def create_en_article_detail_from_da(da_article_detail: ArticleDetail, delay: float = 0.3) -> ArticleDetail:
    """
    Tạo article_detail EN từ article_detail DA
    
    Args:
        da_article_detail: ArticleDetail object với language='da'
        delay: Delay giữa các lần translate (giây) để tránh rate limit
        
    Returns:
        ArticleDetail object với language='en' hoặc existing nếu đã tồn tại
    """
    if da_article_detail.language != 'da':
        raise ValueError(f"Source article_detail must be in Danish (da), got {da_article_detail.language}")
    
    # Convert URL từ DA sang EN
    en_url = convert_da_url_to_en_url(da_article_detail.published_url)
    
    # CHỈ kiểm tra xem đã có EN version chưa (không check DA version)
    # Vì unique constraint là (published_url, language), nên có thể có cả DA và EN với cùng URL
    existing_en_detail = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
    
    if existing_en_detail:
        # Đã có EN version → skip
        print(f"   ℹ️  EN version already exists (ID: {existing_en_detail.id}), skipping translation")
        return existing_en_detail
    
    # Dịch content_blocks
    print(f"   🌐 Translating content blocks from DA to EN...")
    translated_blocks = translate_content_blocks(
        da_article_detail.content_blocks or [],
        source_lang='da',
        target_lang='en',
        delay=delay
    )
    
    # Tạo ArticleDetail mới với language='en'
    en_article_detail = ArticleDetail(
        published_url=en_url,
        content_blocks=translated_blocks,
        language='en',
        element_guid=da_article_detail.element_guid
    )
    
    try:
        db.session.add(en_article_detail)
        db.session.commit()
        print(f"   ✅ Created EN article_detail (ID: {en_article_detail.id}, Blocks: {len(translated_blocks)})")
        return en_article_detail
    except Exception as e:
        # Rollback nếu lỗi (đặc biệt là IntegrityError)
        db.session.rollback()
        
        # Kiểm tra xem có phải do duplicate không (nếu migration chưa chạy, vẫn có thể bị lỗi unique)
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError) or 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            # Kiểm tra lại xem đã có EN version chưa
            existing_en = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
            if existing_en:
                print(f"   ℹ️  EN version already exists (ID: {existing_en.id}), skipping translation")
                return existing_en
            else:
                print(f"   ⚠️  Unique constraint error - might need to run migration script")
                print(f"   ⚠️  Run: python deploy/migrate_article_details_composite_unique.py")
        
        print(f"   ❌ Error creating EN article_detail: {e}")
        raise


def translate_da_article_details_to_en(limit=None):
    """
    Dịch tất cả article_detail từ DA sang EN
    
    Args:
        limit: Giới hạn số lượng articles để dịch
    """
    # Lấy tất cả article_detail có language='da' và published_url không phải kl.sermitsiaq.ag
    query = ArticleDetail.query.filter(
        ArticleDetail.language == 'da',
        ~ArticleDetail.published_url.contains('kl.sermitsiaq.ag')
    )
    
    if limit:
        query = query.limit(limit)
    
    da_details = query.all()
    
    if not da_details:
        print("\n✅ Không có article_detail DA nào cần dịch!")
        return
    
    print(f"\n🌐 Bắt đầu dịch {len(da_details)} article_detail từ DA sang EN...\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, da_detail in enumerate(da_details, 1):
        print(f"\n[{i}/{len(da_details)}] Processing: {da_detail.published_url[:70]}...")
        
        try:
            # Convert URL sang EN
            en_url = convert_da_url_to_en_url(da_detail.published_url)
            
            # CHỈ kiểm tra xem đã có EN version chưa (không check DA version)
            existing_en = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
            if existing_en:
                print(f"   ⏭️  Skipped - EN version already exists (ID: {existing_en.id})")
                skip_count += 1
                continue
            
            # Tạo EN version
            en_detail = create_en_article_detail_from_da(da_detail)
            if en_detail:
                success_count += 1
            else:
                skip_count += 1  # Không phải lỗi, chỉ là skip
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            # Rollback session nếu có lỗi
            try:
                db.session.rollback()
            except:
                pass
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Hoàn thành dịch!")
    print(f"   Success: {success_count}/{len(da_details)}")
    print(f"   Skipped: {skip_count}/{len(da_details)}")
    print(f"   Failed: {fail_count}/{len(da_details)}")
    print(f"{'='*60}\n")


def list_articles_to_crawl(language=None, section=None, limit=None):
    """
    List tất cả articles cần crawl
    """
    articles = get_articles_to_crawl(language=language, section=section, limit=limit)
    
    print(f"\n📋 Articles cần crawl:")
    print(f"   Total: {len(articles)} articles")
    
    if language:
        print(f"   Language: {language}")
    if section:
        print(f"   Section: {section}")
    if limit:
        print(f"   Limit: {limit}")
    
    print(f"\n   Articles:")
    for i, article in enumerate(articles, 1):
        print(f"   {i}. ID: {article.id:6d} | {article.language:2s} | {article.section:12s} | {article.published_url[:70]}...")
    
    return articles


def handle_cookie_popup(sb):
    """
    Xử lý cookie consent popup nếu có xuất hiện
    
    Args:
        sb: SeleniumBase instance
    """
    try:
        # Kiểm tra xem có popup không
        sb.sleep(1)  # Đợi popup xuất hiện
        
        # Tìm và click button "ACCEPTER ALLE" (Accept All)
        # Sử dụng JavaScript để tìm button có text chứa "ACCEPTER" hoặc "Accept"
        buttons = sb.execute_script("""
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || buttons[i].innerText;
                if (text.includes('ACCEPTER') || text.includes('Accepter') || 
                    text.includes('ACCEPT') || text.includes('Accept')) {
                    return buttons[i];
                }
            }
            return null;
        """)
        
        if buttons:
            sb.execute_script("arguments[0].click();", buttons)
            print("   ✅ Accepted cookie consent popup")
            sb.sleep(3)  # Wait for popup to close and page to stabilize
            
            # Kiểm tra xem popup đã đóng chưa
            try:
                # Đợi popup biến mất
                sb.wait_for_element_not_visible('button:contains("ACCEPTER")', timeout=5)
            except:
                pass
            
            # Đảm bảo đang ở đúng trang login sau khi accept cookie
            current_url = sb.get_current_url()
            if 'login' not in current_url.lower():
                print("   🔄 Reloading login page after cookie acceptance...")
                sb.open(LOGIN_URL)
                sb.sleep(3)  # Wait for page to load
            
            return True
        
        # Fallback: Tìm bằng text content
        try:
            page_source = sb.get_page_source()
            if 'Du bestemmer over dine data' in page_source or 'cookie' in page_source.lower():
                # Tìm button bằng xpath
                try:
                    accept_btn = sb.find_element('//button[contains(text(), "ACCEPTER") or contains(text(), "Accepter")]', timeout=3)
                    if accept_btn:
                        sb.click(accept_btn)
                        print("   ✅ Accepted cookie consent popup (via XPath)")
                        sb.sleep(3)  # Wait for popup to close
                        
                        # Đảm bảo đang ở đúng trang login
                        current_url = sb.get_current_url()
                        if 'login' not in current_url.lower():
                            print("   🔄 Reloading login page after cookie acceptance...")
                            sb.open(LOGIN_URL)
                            sb.sleep(3)
                        
                        return True
                except:
                    pass
        except:
            pass
        
        # Nếu không tìm thấy popup, có thể đã được accept hoặc không có
        return False
    except Exception as e:
        # Không có popup hoặc đã được xử lý
        return False


def ensure_login(sb):
    """
    Đảm bảo đã login vào sermitsiaq.ag
    Kiểm tra bằng cách mở trang login và xem có nút "Log ud" không
    Nếu đã login, trang login sẽ hiển thị "Du er allerede logget ind: Log ud"
    
    Args:
        sb: SeleniumBase instance
    """
    print("🔐 Checking login status...")
    
    # Mở trang login để kiểm tra
    try:
        sb.open(LOGIN_URL)
        sb.sleep(2)  # Wait for page to load
        
        # Xử lý cookie popup trước khi kiểm tra login
        handle_cookie_popup(sb)
        sb.sleep(1)  # Wait a bit after handling popup
        
        # Kiểm tra xem có nút "Log ud" (Logout) hoặc text "Du er allerede logget ind" không
        # CHỈ kiểm tra nếu thực sự đã login (nút logout chỉ xuất hiện khi đã login)
        try:
            # Tìm nút logout
            logout_button = sb.find_element('button.logout', timeout=3)
            if logout_button:
                print("   ✅ Already logged in (found Log ud button)")
                # Chụp màn hình để xác nhận
                screenshot_path = os.path.join(USER_DATA_DIR, 'login_check_logged_in.png')
                sb.save_screenshot(screenshot_path)
                print(f"   📸 Screenshot saved: {screenshot_path}")
                return True
        except:
            pass
        
        # Kiểm tra text "Du er allerede logget ind" trong page source
        try:
            page_source = sb.get_page_source()
            if 'Du er allerede logget ind' in page_source:
                # Tìm nút logout trong page source
                if 'button.logout' in page_source or 'class="logout"' in page_source:
                    print("   ✅ Already logged in (found login status message with logout button)")
                    # Chụp màn hình để xác nhận
                    screenshot_path = os.path.join(USER_DATA_DIR, 'login_check_logged_in.png')
                    sb.save_screenshot(screenshot_path)
                    print(f"   📸 Screenshot saved: {screenshot_path}")
                    return True
        except:
            pass
        
        # Nếu không tìm thấy logout button hoặc message, chưa login
        print("   ⚠️  Not logged in (no Log ud button found), attempting login...")
        needs_login = True
        
    except Exception as e:
        print(f"   ⚠️  Error checking login status: {e}, attempting login...")
        needs_login = True
    
    if needs_login:
        try:
            # Đảm bảo đang ở trang login (có thể đã mở ở trên)
            current_url = sb.get_current_url()
            if 'login' not in current_url.lower():
                print(f"   🔑 Navigating to {LOGIN_URL}...")
                sb.open(LOGIN_URL)
                sb.sleep(3)  # Wait for page to load
            
            # Xử lý cookie popup trước khi login
            handle_cookie_popup(sb)
            
            # Đảm bảo đang ở trang login và đợi form load
            current_url = sb.get_current_url()
            if 'login' not in current_url.lower():
                print(f"   🔄 Navigating to {LOGIN_URL}...")
                sb.open(LOGIN_URL)
                sb.sleep(3)
            
            # Kiểm tra lại xem có đã login chưa (có thể đã login trong lúc chờ)
            try:
                logout_button = sb.find_element('button.logout', timeout=2)
                if logout_button:
                    print("   ✅ Already logged in (found Log ud button after navigation)")
                    # Chụp màn hình để xác nhận
                    screenshot_path = os.path.join(USER_DATA_DIR, 'login_check_after_nav.png')
                    sb.save_screenshot(screenshot_path)
                    print(f"   📸 Screenshot saved: {screenshot_path}")
                    return True
            except:
                pass
            
            print(f"   🔑 Logging in...")
            
            # Chụp màn hình trước khi login để debug
            screenshot_path = os.path.join(USER_DATA_DIR, 'before_login.png')
            sb.save_screenshot(screenshot_path)
            print(f"   📸 Screenshot before login: {screenshot_path}")
            
            # Form login nằm trong iframe 0, cần switch vào iframe trước
            print("   🔄 Switching to iframe containing login form...")
            try:
                # Đợi iframe load
                sb.sleep(2)
                # Switch vào iframe 0 (iframe đầu tiên chứa form login)
                sb.switch_to_frame(0)
                sb.sleep(2)  # Đợi iframe content load
                print("   ✅ Switched to iframe")
            except Exception as e:
                print(f"   ⚠️  Could not switch to iframe: {e}")
                # Thử reload và switch lại
                sb.switch_to_default_content()
                sb.open(LOGIN_URL)
                sb.sleep(3)
                handle_cookie_popup(sb)
                sb.sleep(2)
                sb.switch_to_frame(0)
                sb.sleep(2)
            
            # Đợi form login xuất hiện trong iframe
            try:
                sb.wait_for_element('#id_subscriber', timeout=10)
            except:
                print("   ⚠️  Login form not found in iframe, trying to reload...")
                sb.switch_to_default_content()
                sb.open(LOGIN_URL)
                sb.sleep(3)
                handle_cookie_popup(sb)
                sb.sleep(2)
                sb.switch_to_frame(0)
                sb.sleep(2)
                sb.wait_for_element('#id_subscriber', timeout=10)
            
            # Fill in email/subscriber field
            subscriber_input = sb.find_element('#id_subscriber', timeout=10)
            if subscriber_input:
                sb.type('#id_subscriber', LOGIN_EMAIL)
                print(f"   ✅ Filled subscriber field")
            else:
                print("   ❌ Could not find subscriber input field")
                return False
            
            # Fill in password field
            password_input = sb.find_element('#id_password', timeout=10)
            if password_input:
                sb.type('#id_password', LOGIN_PASSWORD)
                print(f"   ✅ Filled password field")
            else:
                print("   ❌ Could not find password input field")
                return False
            
            # Click login button
            login_button = sb.find_element('button[type="submit"]', timeout=10)
            if login_button:
                sb.click('button[type="submit"]')
                print(f"   ✅ Clicked login button")
                sb.sleep(5)  # Wait for login to complete
                
                # Switch về default content để kiểm tra login status
                sb.switch_to_default_content()
                sb.sleep(2)
                
                # Kiểm tra xem đã login thành công chưa bằng cách tìm nút "Log ud"
                try:
                    logout_button = sb.find_element('button.logout', timeout=3)
                    if logout_button:
                        print("   ✅ Login successful! (found Log ud button)")
                        # Chụp màn hình để xác nhận
                        screenshot_path = os.path.join(USER_DATA_DIR, 'login_success.png')
                        sb.save_screenshot(screenshot_path)
                        print(f"   📸 Screenshot saved: {screenshot_path}")
                        return True
                except:
                    pass
                
                # Fallback: kiểm tra page source
                try:
                    page_source = sb.get_page_source()
                    if 'Du er allerede logget ind' in page_source or 'Log ud' in page_source:
                        print("   ✅ Login successful! (found login status message)")
                        # Chụp màn hình để xác nhận
                        screenshot_path = os.path.join(USER_DATA_DIR, 'login_success.png')
                        sb.save_screenshot(screenshot_path)
                        print(f"   📸 Screenshot saved: {screenshot_path}")
                        return True
                except:
                    pass
                
                # Fallback: kiểm tra URL
                current_url = sb.get_current_url()
                if 'login' not in current_url.lower():
                    print("   ✅ Login successful! (redirected away from login page)")
                    # Chụp màn hình để xác nhận
                    screenshot_path = os.path.join(USER_DATA_DIR, 'login_success_redirect.png')
                    sb.save_screenshot(screenshot_path)
                    print(f"   📸 Screenshot saved: {screenshot_path}")
                    return True
                else:
                    print("   ❌ Login failed - still on login page")
                    # Chụp màn hình để debug
                    screenshot_path = os.path.join(USER_DATA_DIR, 'login_failed.png')
                    sb.save_screenshot(screenshot_path)
                    print(f"   📸 Screenshot saved: {screenshot_path}")
                    return False
            else:
                print("   ❌ Could not find login button")
                return False
                
        except Exception as e:
            print(f"   ❌ Error during login: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


def crawl_article_detail(url: str, language: str = 'da', headless: bool = True, download_images: bool = True):
    """
    Crawl article detail page và lưu vào database
    
    Args:
        url: URL của article detail page
        language: Language code ('da', 'kl', 'en')
        headless: Run browser in headless mode
        download_images: Download images về .com domain nếu True
    
    Returns:
        ArticleDetail object or None
    """
    print(f"🔍 Crawling: {url[:70]}...")
    
    # Start browser với retry logic (tự động xóa và tạo lại user_data_dir nếu cần)
    with start_browser_with_retry(headless=headless) as sb:
        # Đảm bảo đã login trước khi crawl (chỉ login 1 lần cho batch)
        # Note: Login sẽ được thực hiện ở batch_crawl_articles, không cần login lại mỗi article
        try:
            # Navigate to URL
            sb.open(url)
            sb.sleep(2)  # Wait for page to load
            
            # Kiểm tra xem có phải liveblog không (có .livefeed)
            is_liveblog = False
            try:
                livefeed_elem = sb.find_element('.livefeed', timeout=3)
                if livefeed_elem:
                    is_liveblog = True
                    print(f"   📺 Detected liveblog format")
            except:
                pass
            
            # Wait for content (bodytext hoặc livefeed)
            if is_liveblog:
                try:
                    sb.wait_for_element('.livefeed', timeout=10)
                except:
                    print(f"   ⚠️  Timeout waiting for .livefeed")
                    return None
            else:
                try:
                    sb.wait_for_element('.bodytext', timeout=10)
                except:
                    print(f"   ⚠️  Timeout waiting for .bodytext")
                    return None
            
            # Get article title
            title = None
            try:
                title_elem = sb.find_element('h1.headline.mainTitle', timeout=5)
                if title_elem:
                    title = title_elem.text
            except:
                pass
            
            # Get excerpt
            excerpt = None
            try:
                excerpt_elem = sb.find_element('h2.subtitle', timeout=5)
                if excerpt_elem:
                    excerpt = excerpt_elem.text
            except:
                pass
            
            # Get articleHeader HTML (chứa subtitle và meta) - để parser có thể parse subtitle
            article_header_html = None
            meta_html = None
            try:
                # Try to find articleHeader
                article_header = sb.find_element('.articleHeader', timeout=5)
                if article_header:
                    article_header_html = article_header.get_attribute('outerHTML')
                    print(f"   ✅ Found articleHeader via Selenium ({len(article_header_html)} chars)")
                    
                    # Extract meta từ articleHeader
                    try:
                        meta_elem = article_header.find_element('.meta', timeout=3)
                        if meta_elem:
                            meta_html = meta_elem.get_attribute('outerHTML')
                    except:
                        pass
            except:
                # Fallback: parse from page source
                try:
                    from bs4 import BeautifulSoup
                    page_source = sb.get_page_source()
                    soup = BeautifulSoup(page_source, 'html.parser')
                    article_header = soup.find('div', class_='articleHeader')
                    if article_header:
                        article_header_html = str(article_header)
                        print(f"   ✅ Found articleHeader from page source ({len(article_header_html)} chars)")
                        
                        meta_div = article_header.find('div', class_='meta')
                        if meta_div:
                            meta_html = str(meta_div)
                except:
                    pass
            
            # Get content HTML (bodytext hoặc livefeed)
            bodytext_html = None
            livefeed_html = None
            
            try:
                page_source = sb.get_page_source()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')
                
                if is_liveblog:
                    # Tìm livefeed container
                    livefeed_div = soup.find('div', class_='livefeed')
                    if not livefeed_div:
                        # Try by ID pattern
                        livefeed_div = soup.find('div', id=lambda x: x and 'livefeed' in str(x))
                    
                    if livefeed_div:
                        livefeed_html = str(livefeed_div)
                        print(f"   ✅ Found livefeed HTML ({len(livefeed_html)} chars)")
                    else:
                        # Fallback: try Selenium element
                        try:
                            livefeed_elem = sb.find_element('.livefeed', timeout=5)
                            if livefeed_elem:
                                livefeed_html = livefeed_elem.get_attribute('outerHTML')
                                print(f"   ✅ Found livefeed via Selenium ({len(livefeed_html)} chars)")
                        except:
                            pass
                else:
                    # Tìm bodytext như bình thường
                    bodytext_div = soup.find('div', class_='bodytext', attrs={'data-element-guid': True})
                    if bodytext_div:
                        bodytext_html = str(bodytext_div)
                    else:
                        # Fallback: try Selenium element
                        try:
                            bodytext_elem = sb.find_element('div.bodytext.large-12', timeout=5)
                            if bodytext_elem:
                                bodytext_html = bodytext_elem.get_attribute('outerHTML')
                        except:
                            pass
            except Exception as e:
                print(f"   ⚠️  Error parsing content: {e}")
                return None
            
            # Get paywall offers section
            offers_html = None
            try:
                offers_elem = sb.find_element('.iteras-offers', timeout=5)
                if offers_elem:
                    offers_html = offers_elem.get_attribute('outerHTML')
            except:
                pass
            
            # Get article footer tags section
            footer_html = None
            try:
                footer_elem = sb.find_element('.articleFooter', timeout=5)
                if footer_elem:
                    footer_html = footer_elem.get_attribute('outerHTML')
            except:
                # Fallback: parse from page source
                try:
                    from bs4 import BeautifulSoup
                    page_source = sb.get_page_source()
                    soup = BeautifulSoup(page_source, 'html.parser')
                    footer_div = soup.find('div', class_='articleFooter')
                    if footer_div:
                        footer_html = str(footer_div)
                except:
                    pass
            
            # Combine HTML - articleHeader (chứa subtitle) nên đặt đầu tiên, sau đó meta, rồi bodytext/livefeed
            full_html = ''
            if article_header_html:
                # Sử dụng articleHeader HTML để parser có thể parse subtitle
                full_html = article_header_html
                print(f"   ✅ Added articleHeader to HTML ({len(article_header_html)} chars)")
            elif meta_html:
                # Fallback: chỉ có meta nếu không có articleHeader
                full_html = meta_html
            
            # Thêm livefeed hoặc bodytext
            if livefeed_html:
                full_html += livefeed_html
                print(f"   ✅ Added livefeed to HTML ({len(livefeed_html)} chars)")
            elif bodytext_html:
                full_html += bodytext_html
                print(f"   ✅ Added bodytext to HTML ({len(bodytext_html)} chars)")
            
            if offers_html:
                full_html += offers_html
            if footer_html:
                full_html += footer_html
            
            if not full_html:
                print(f"   ❌ Could not find content")
                return None
            
            # Get element_guid from bodytext hoặc livefeed
            element_guid = None
            if livefeed_html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(livefeed_html, 'html.parser')
                # Tìm element_guid từ livefeed container
                livefeed_div = soup.find('div', class_='livefeed')
                if livefeed_div:
                    element_guid = livefeed_div.get('id', '').replace('livefeed_', '')
            elif bodytext_html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(bodytext_html, 'html.parser')
                bodytext_div = soup.find('div', class_='bodytext')
                if bodytext_div:
                    element_guid = bodytext_div.get('data-element-guid', '')
            
            # Parse and save to database
            article_detail = ArticleDetailParser.save_article_detail(
                published_url=url,
                html_content=full_html,
                language=language,
                element_guid=element_guid
            )
            
            print(f"   ✅ Saved (Detail ID: {article_detail.id}, Blocks: {len(article_detail.content_blocks)})")
            
            # Update article if exists
            article = Article.query.filter_by(published_url=url).first()
            if article:
                if title and not article.title:
                    article.title = title
                if excerpt and not article.excerpt:
                    article.excerpt = excerpt
                
                # Download và cập nhật images từ article.image_data (header image)
                # Function download_and_update_image_data sẽ tự kiểm tra từng URL và chỉ download những URL chưa có .com
                if download_images and article.image_data:
                    try:
                        # Parse image_data (có thể là dict hoặc JSON string)
                        img_data = article.image_data
                        if isinstance(img_data, str):
                            try:
                                img_data = json.loads(img_data)
                            except:
                                img_data = {}
                        
                        # Luôn gọi download_and_update_image_data để kiểm tra và download từng URL
                        if isinstance(img_data, dict) and len(img_data) > 0:
                            print(f"   📥 Processing header image for article (ID: {article.id})...")
                            try:
                                updated_image_data = download_and_update_image_data(
                                    img_data,
                                    base_url='https://www.sermitsiaq.com',
                                    download_all_formats=True  # Download tất cả formats cho article detail
                                )
                                # Update image_data trong Article
                                article.image_data = updated_image_data
                                print(f"   ✅ Updated header image_data")
                            except Exception as e:
                                print(f"   ⚠️  Error downloading header images: {e}")
                                # Giữ nguyên image_data gốc nếu lỗi
                        else:
                            print(f"   ℹ️  No header image_data to process")
                    except Exception as e:
                        print(f"   ⚠️  Error processing header image_data: {e}")
                
                # Download và cập nhật images từ article_detail.content_blocks (images trong nội dung)
                if download_images and article_detail.content_blocks:
                    try:
                        content_blocks = article_detail.content_blocks
                        if isinstance(content_blocks, str):
                            try:
                                content_blocks = json.loads(content_blocks)
                            except:
                                content_blocks = []
                        
                        if isinstance(content_blocks, list):
                            image_blocks_count = 0
                            updated_blocks_count = 0
                            
                            # Tạo list mới để SQLAlchemy detect được thay đổi
                            updated_content_blocks = []
                            
                            for block in content_blocks:
                                # Tìm các image blocks
                                if block.get('type') == 'image' and block.get('image_sources'):
                                    image_blocks_count += 1
                                    image_sources = block.get('image_sources', {})
                                    
                                    if isinstance(image_sources, dict) and len(image_sources) > 0:
                                        print(f"   📥 Processing image block #{image_blocks_count}...")
                                        try:
                                            # Download và cập nhật image_sources
                                            updated_image_sources = download_and_update_image_data(
                                                image_sources,
                                                base_url='https://www.sermitsiaq.com',
                                                download_all_formats=True  # Download tất cả formats
                                            )
                                            # Tạo block mới với image_sources đã update
                                            updated_block = block.copy()
                                            updated_block['image_sources'] = updated_image_sources
                                            updated_content_blocks.append(updated_block)
                                            updated_blocks_count += 1
                                            print(f"      ✅ Updated image block #{image_blocks_count}")
                                        except Exception as e:
                                            print(f"      ⚠️  Error downloading image block #{image_blocks_count}: {e}")
                                            # Giữ nguyên block nếu lỗi
                                            updated_content_blocks.append(block)
                                    else:
                                        # Không có image_sources, giữ nguyên block
                                        updated_content_blocks.append(block)
                                else:
                                    # Không phải image block, giữ nguyên
                                    updated_content_blocks.append(block)
                            
                            if image_blocks_count > 0:
                                # Update content_blocks trong ArticleDetail với list mới
                                article_detail.content_blocks = updated_content_blocks
                                # Force mark as modified để đảm bảo SQLAlchemy detect thay đổi
                                from sqlalchemy.orm.attributes import flag_modified
                                flag_modified(article_detail, 'content_blocks')
                                print(f"   ✅ Updated {updated_blocks_count}/{image_blocks_count} image blocks in content")
                            else:
                                print(f"   ℹ️  No image blocks found in content")
                    except Exception as e:
                        print(f"   ⚠️  Error processing content image blocks: {e}")
                
                db.session.commit()
            
            # Nếu là article_detail DA (không phải kl.sermitsiaq.ag), tự động tạo EN version
            if language == 'da' and 'kl.sermitsiaq.ag' not in url:
                try:
                    en_url = convert_da_url_to_en_url(url)
                    existing_en = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
                    if not existing_en:
                        print(f"   🌐 Auto-creating EN version...")
                        create_en_article_detail_from_da(article_detail)
                except Exception as e:
                    print(f"   ⚠️  Error creating EN version: {e}")
            
            return article_detail
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None


def update_is_temp_flag():
    """
    Update is_temp=False cho tất cả articles có is_temp=True và đã có ArticleDetail
    Function này luôn được gọi ở cuối crawl_all() để đảm bảo articles đã có detail được set is_temp=False
    """
    print(f"\n{'='*60}")
    print(f"🔄 Updating is_temp=False for articles with details crawled")
    print(f"{'='*60}")
    
    try:
        # Tìm tất cả articles có is_temp=True và đã có ArticleDetail
        temp_articles = Article.query.filter_by(is_temp=True).all()
        updated_count = 0
        
        for article in temp_articles:
            # Check xem đã có ArticleDetail chưa
            if article.published_url:
                existing_detail = ArticleDetail.query.filter_by(
                    published_url=article.published_url
                ).first()
                
                if existing_detail:
                    # Đã có detail → set is_temp=False
                    article.is_temp = False
                    updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"   ✅ Updated {updated_count} articles: is_temp=True → is_temp=False")
        else:
            print(f"   ℹ️  No articles to update (all temp articles still missing details)")
        
        # Đếm số articles vẫn còn is_temp=True
        remaining_temp = Article.query.filter_by(is_temp=True).count()
        if remaining_temp > 0:
            print(f"   ⚠️  {remaining_temp} articles still have is_temp=True (details not crawled yet)")
        
    except Exception as e:
        print(f"   ❌ Error updating is_temp: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()


def crawl_all(language=None, section=None, limit=None, headless=True, delay=2, auto_translate=True, translate_delay=0.3, download_images=True):
    """
    Crawl tất cả articles chưa có detail
    
    Args:
        language: Filter theo language
        section: Filter theo section
        limit: Giới hạn số lượng
        headless: Run browser in headless mode
        delay: Delay giữa các requests (seconds)
        auto_translate: Tự động translate article_detail DA sang EN sau khi crawl xong
        translate_delay: Delay giữa các lần translate (seconds)
        download_images: Download images về .com domain nếu True
    """
    articles = get_articles_to_crawl(language=language, section=section, limit=limit)
    
    if not articles:
        print("\n✅ Không có articles nào cần crawl!")
        # Nếu auto_translate=True, vẫn chạy translate cho các article_detail DA đã có
        if auto_translate:
            print("\n🌐 Không có articles cần crawl, nhưng sẽ kiểm tra và translate các article_detail DA đã có...")
            translate_da_article_details_to_en(limit=None)
        
        # ⚠️ QUAN TRỌNG: Vẫn phải update is_temp=False cho articles đã có detail
        update_is_temp_flag()
        return
    
    print(f"\n🚀 Bắt đầu crawl {len(articles)} articles...")
    if language:
        print(f"   Language: {language}")
    if section:
        print(f"   Section: {section}")
    if limit:
        print(f"   Limit: {limit}")
    print(f"   Headless: {headless}")
    print(f"   Delay: {delay}s giữa các requests")
    print(f"   Auto-translate: {auto_translate}")
    if auto_translate:
        print(f"   Translate delay: {translate_delay}s")
    print(f"   Download images: {download_images}\n")
    
    # Login một lần trước khi bắt đầu crawl (sử dụng user_data_dir để lưu session)
    print("🔐 Initializing browser session with login...")
    # Start browser với retry logic (tự động xóa và tạo lại user_data_dir nếu cần)
    with start_browser_with_retry(headless=headless) as sb:
        if not ensure_login(sb):
            print("❌ Failed to login, cannot proceed with crawling")
            return
    
    # Sau khi login xong, session đã được lưu trong user_data_dir
    # Các lần crawl tiếp theo sẽ tự động sử dụng session đã lưu
    print("✅ Login session saved, starting to crawl articles...\n")
    
    success_count = 0
    fail_count = 0
    crawled_da_details = []  # Lưu các article_detail DA đã crawl để translate sau
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] Article ID: {article.id}")
        
        result = crawl_article_detail(
            url=article.published_url,
            language=article.language,
            headless=headless,
            download_images=download_images
        )
        
        if result:
            success_count += 1
            # Lưu lại article_detail DA để translate sau (chỉ DA, không phải kl.sermitsiaq.ag)
            if result.language == 'da' and 'kl.sermitsiaq.ag' not in result.published_url:
                crawled_da_details.append(result)
        else:
            fail_count += 1
        
        # Delay giữa các requests
        if i < len(articles):
            time.sleep(delay)
    
    print(f"\n{'='*60}")
    print(f"✅ Crawl hoàn thành!")
    print(f"   Success: {success_count}/{len(articles)}")
    print(f"   Failed: {fail_count}/{len(articles)}")
    print(f"{'='*60}\n")
    
    # Tự động translate article_detail DA sang EN sau khi crawl xong
    if auto_translate and crawled_da_details:
        print(f"\n{'='*60}")
        print(f"🌐 Bắt đầu translate {len(crawled_da_details)} article_detail từ DA sang EN...")
        print(f"{'='*60}\n")
        
        translate_success = 0
        translate_skip = 0
        translate_fail = 0
        
        for idx, da_detail in enumerate(crawled_da_details, 1):
            try:
                print(f"\n[{idx}/{len(crawled_da_details)}] Translating article_detail ID: {da_detail.id}")
                print(f"   URL: {da_detail.published_url[:70]}...")
                
                # CHỈ kiểm tra xem đã có EN version chưa (không check DA version)
                en_url = convert_da_url_to_en_url(da_detail.published_url)
                existing_en = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
                
                if existing_en:
                    print(f"   ⏭️  Skipped - EN version already exists (ID: {existing_en.id})")
                    translate_skip += 1
                    continue
                
                # Chỉ translate nếu chưa có ArticleDetail với URL này
                en_detail = create_en_article_detail_from_da(da_detail, delay=translate_delay)
                
                if en_detail:
                    translate_success += 1
                else:
                    translate_skip += 1  # Không phải lỗi, chỉ là skip
                    
            except Exception as e:
                print(f"   ❌ Error translating: {e}")
                import traceback
                traceback.print_exc()
                # Rollback session nếu có lỗi
                try:
                    db.session.rollback()
                except:
                    pass
                translate_fail += 1
                continue
        
        print(f"\n{'='*60}")
        print(f"✅ Translation hoàn thành!")
        print(f"   Success: {translate_success}/{len(crawled_da_details)}")
        print(f"   Skipped: {translate_skip}/{len(crawled_da_details)}")
        print(f"   Failed: {translate_fail}/{len(crawled_da_details)}")
        print(f"{'='*60}\n")
    elif auto_translate and not crawled_da_details:
        print("\nℹ️  Không có article_detail DA nào để translate (tất cả đều là KL hoặc không crawl được)\n")
    
    # ⚠️ QUAN TRỌNG: Luôn update is_temp=False ở cuối (bất kể có crawl hay không)
    # Để đảm bảo articles đã có ArticleDetail được set is_temp=False
    update_is_temp_flag()


def main():
    parser = argparse.ArgumentParser(
        description='Crawl article detail pages theo batch',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mặc định: Crawl và translate tất cả articles chưa có detail
  python scripts/crawl_article_details_batch.py
  
  # List tất cả articles cần crawl
  python scripts/crawl_article_details_batch.py --list
  
  # Crawl tất cả articles chưa có detail (tương đương với không có flag)
  python scripts/crawl_article_details_batch.py --crawl-all
  
  # Crawl theo language
  python scripts/crawl_article_details_batch.py --language en
  
  # Crawl theo section
  python scripts/crawl_article_details_batch.py --section samfund
  
  # Crawl giới hạn số lượng
  python scripts/crawl_article_details_batch.py --limit 10
  
  # Crawl nhưng không translate
  python scripts/crawl_article_details_batch.py --no-auto-translate
  
  # Chỉ translate các article_detail DA đã có
  python scripts/crawl_article_details_batch.py --translate-only
  
  # Crawl nhưng không download images
  python scripts/crawl_article_details_batch.py --no-download-images
        """
    )
    
    parser.add_argument('--list', action='store_true',
                        help='List tất cả articles cần crawl')
    parser.add_argument('--crawl-all', action='store_true',
                        help='Crawl tất cả articles chưa có detail (mặc định: bật nếu không có flag khác)')
    parser.add_argument('--language', '-l', choices=['da', 'kl', 'en'],
                        help='Filter theo language')
    parser.add_argument('--section', '-s',
                        help='Filter theo section (samfund, sport, kultur, etc.)')
    parser.add_argument('--limit', '-n', type=int,
                        help='Giới hạn số lượng articles')
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in no-headless mode (để debug)')
    parser.add_argument('--delay', '-d', type=float, default=2.0,
                        help='Delay giữa các requests (seconds, default: 2.0)')
    parser.add_argument('--no-auto-translate', action='store_true',
                        help='Tắt tự động translate sau khi crawl (mặc định: bật)')
    parser.add_argument('--translate-delay', type=float, default=0.3,
                        help='Delay giữa các lần translate (seconds, default: 0.3)')
    parser.add_argument('--translate-only', action='store_true',
                        help='Chỉ dịch các article_detail DA đã có, không crawl mới')
    parser.add_argument('--translate-limit', type=int,
                        help='Giới hạn số lượng article_detail để dịch')
    parser.add_argument('--no-download-images', action='store_true',
                        help='Tắt tự động download images về .com domain (mặc định: bật)')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.translate_only:
            # Chỉ dịch, không crawl
            translate_da_article_details_to_en(limit=args.translate_limit)
        elif args.list:
            list_articles_to_crawl(
                language=args.language,
                section=args.section,
                limit=args.limit
            )
        else:
            # Mặc định: crawl và translate (nếu không có flag --list hoặc --translate-only)
            # Có thể dùng --crawl-all hoặc không cần flag gì cũng được
            crawl_all(
                language=args.language,
                section=args.section,
                limit=args.limit,
                headless=not args.no_headless,
                delay=args.delay,
                auto_translate=not args.no_auto_translate,  # Mặc định bật auto-translate
                translate_delay=args.translate_delay,
                download_images=not args.no_download_images  # Mặc định bật download images
            )


if __name__ == '__main__':
    main()

