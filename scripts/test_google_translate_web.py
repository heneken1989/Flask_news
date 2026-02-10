"""
Script test để dịch text sử dụng Google Translate Web (browser automation)
So sánh với Google Cloud Translation API

Usage:
    # Test với text đơn giản
    python flask/scripts/test_google_translate_web.py --text "Hej, hvordan har du det?"
    
    # Test với article detail từ database
    python flask/scripts/test_google_translate_web.py --article-id 12345
    
    # Test với URL article
    python flask/scripts/test_google_translate_web.py --url "https://www.sermitsiaq.ag/..."
    
    # So sánh với API (mặc định)
    python flask/scripts/test_google_translate_web.py --text "..." --compare
    
    # Chỉ test web (không so sánh)
    python flask/scripts/test_google_translate_web.py --text "..." --web-only
"""
import sys
import os
import argparse
import time
from contextlib import contextmanager

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from seleniumbase import SB
import re
import json
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Google Cloud Translation API key từ environment variable
GOOGLE_TRANSLATE_API_KEY = os.environ.get('GOOGLE_TRANSLATE_API_KEY')

# User data directory để lưu session
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data_translate')


def get_chrome_options_for_headless():
    """Trả về Chrome options cần thiết cho Linux headless server"""
    return "no-sandbox,disable-dev-shm-usage,disable-gpu"


@contextmanager
def start_browser_for_translate(headless=True):
    """
    Start browser để sử dụng Google Translate Web
    
    Args:
        headless: Run browser in headless mode
    
    Yields:
        SB instance
    """
    chrome_opts = get_chrome_options_for_headless()
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    os.chmod(USER_DATA_DIR, 0o755)
    
    sb_context = SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR, chromium_arg=chrome_opts)
    sb = sb_context.__enter__()
    
    try:
        yield sb
    finally:
        sb_context.__exit__(None, None, None)


def translate_text_with_google_cloud(text, source_lang='da', target_lang='en'):
    """
    Dịch text với Google Cloud Translation API (phương pháp hiện tại)
    
    Args:
        text: Text cần dịch
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Translated text hoặc None nếu lỗi
    """
    if not GOOGLE_TRANSLATE_API_KEY:
        print(f"      ⚠️  GOOGLE_TRANSLATE_API_KEY not set in environment")
        return None
    
    try:
        url = "https://translation.googleapis.com/language/translate/v2"
        params = {
            'key': GOOGLE_TRANSLATE_API_KEY,
            'q': text,
            'source': source_lang,
            'target': target_lang,
            'format': 'text'
        }
        
        response = requests.post(url, params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result['data']['translations'][0]['translatedText']
        else:
            print(f"      ⚠️  Google Cloud API Error: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"      ⚠️  Error with Google Cloud Translation: {e}")
        return None


def translate_text_with_google_web(sb, text, source_lang='da', target_lang='en', max_retries=3):
    """
    Dịch text sử dụng Google Translate Web (browser automation)
    
    Args:
        sb: SeleniumBase instance
        text: Text cần dịch
        source_lang: Source language code ('da', 'en', 'kl', etc.)
        target_lang: Target language code ('en', 'da', etc.)
        max_retries: Số lần retry nếu lỗi
    
    Returns:
        Translated text hoặc None nếu lỗi
    """
    if not text or not text.strip():
        return text
    
    # Map language codes to Google Translate language names
    lang_map = {
        'da': 'Danish',
        'en': 'English',
        'kl': 'Kalaallisut',  # Greenlandic
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'nl': 'Dutch',
        'sv': 'Swedish',
        'no': 'Norwegian',
        'fi': 'Finnish',
        'pl': 'Polish',
        'tr': 'Turkish',
    }
    
    source_lang_name = lang_map.get(source_lang, source_lang)
    target_lang_name = lang_map.get(target_lang, target_lang)
    
    try:
        # Mở Google Translate
        translate_url = f"https://translate.google.com/?sl={source_lang}&tl={target_lang}&op=translate"
        sb.open(translate_url)
        sb.sleep(2)  # Đợi trang load
        
        # Xử lý cookie consent nếu có
        try:
            # Tìm và click nút "Accept all" hoặc "I agree"
            accept_buttons = sb.find_elements('button', timeout=3)
            for btn in accept_buttons:
                btn_text = btn.text.lower()
                if 'accept' in btn_text or 'agree' in btn_text or 'got it' in btn_text:
                    sb.click(btn)
                    sb.sleep(1)
                    break
        except:
            pass
        
        # Tìm textarea input (có thể có nhiều textarea, cần tìm đúng)
        # Google Translate có textarea với aria-label chứa "Source text"
        input_found = False
        for attempt in range(max_retries):
            try:
                # Thử nhiều selector khác nhau
                selectors = [
                    'textarea[aria-label*="Source"]',
                    'textarea[aria-label*="source"]',
                    'textarea[aria-label*="Text"]',
                    'textarea[aria-label*="text"]',
                    'textarea.cSNK3d',  # Class mới của Google Translate
                    'textarea[jsname="BJE2fc"]',  # JS name
                    'textarea',  # Fallback: lấy textarea đầu tiên
                ]
                
                textarea = None
                for selector in selectors:
                    try:
                        textarea = sb.find_element(selector, timeout=2)
                        if textarea:
                            input_found = True
                            break
                    except:
                        continue
                
                if not textarea:
                    # Thử tìm bằng xpath
                    try:
                        textarea = sb.find_element('//textarea', timeout=2)
                        input_found = True
                    except:
                        pass
                
                if textarea and input_found:
                    # Clear textarea trước
                    sb.clear(textarea)
                    sb.sleep(0.5)
                    
                    # Nhập text (chia nhỏ nếu quá dài để tránh timeout)
                    if len(text) > 5000:
                        # Text quá dài, chỉ lấy 5000 ký tự đầu
                        text_to_translate = text[:5000]
                        print(f"      ⚠️  Text too long ({len(text)} chars), truncating to 5000 chars")
                    else:
                        text_to_translate = text
                    
                    # Nhập text vào textarea
                    sb.type(textarea, text_to_translate, clear_first=True)
                    sb.sleep(2)  # Đợi Google Translate xử lý
                    
                    # Đợi kết quả dịch xuất hiện
                    # Google Translate hiển thị kết quả trong một div/span với class cụ thể
                    translated_text = None
                    wait_time = 0
                    max_wait = 10  # Tối đa 10 giây
                    
                    while wait_time < max_wait:
                        try:
                            # Thử nhiều selector để lấy kết quả dịch
                            result_selectors = [
                                'span[data-language-to]',
                                'span[jsname="W297wb"]',  # JS name của output
                                'div[data-result-index]',
                                'div[jsname="jqKxS"]',  # JS name khác
                                'span.VIiyi',  # Class mới
                                'div.VIiyi',  # Class mới
                                'span[lang]',  # Span có lang attribute
                            ]
                            
                            for selector in result_selectors:
                                try:
                                    result_elem = sb.find_element(selector, timeout=1)
                                    if result_elem:
                                        translated_text = result_elem.text
                                        if translated_text and translated_text.strip():
                                            break
                                except:
                                    continue
                            
                            # Nếu chưa tìm thấy, thử lấy từ page source
                            if not translated_text or not translated_text.strip():
                                page_source = sb.get_page_source()
                                # Tìm trong HTML
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(page_source, 'html.parser')
                                
                                # Tìm các span/div có chứa text dịch
                                result_spans = soup.find_all('span', {'data-language-to': target_lang})
                                if not result_spans:
                                    result_spans = soup.find_all('span', class_='VIiyi')
                                if not result_spans:
                                    result_spans = soup.find_all('div', class_='VIiyi')
                                
                                for span in result_spans:
                                    text_content = span.get_text(strip=True)
                                    if text_content and len(text_content) > 10:  # Đảm bảo có nội dung
                                        translated_text = text_content
                                        break
                            
                            if translated_text and translated_text.strip():
                                break
                            
                            # Đợi thêm một chút
                            sb.sleep(1)
                            wait_time += 1
                            
                        except Exception as e:
                            sb.sleep(1)
                            wait_time += 1
                            continue
                    
                    if translated_text and translated_text.strip():
                        # Clean up text (loại bỏ ký tự thừa)
                        translated_text = translated_text.strip()
                        # Loại bỏ "PM" hoặc "AM" ở cuối nếu có (giống logic hiện tại)
                        translated_text = re.sub(r'\s*(PM|AM)$', '', translated_text, flags=re.IGNORECASE)
                        return translated_text
                    else:
                        print(f"      ⚠️  Could not get translated text after {max_wait} seconds")
                        if attempt < max_retries - 1:
                            print(f"      🔄 Retrying... ({attempt + 1}/{max_retries})")
                            sb.sleep(2)
                            continue
                        return None
                
            except Exception as e:
                print(f"      ⚠️  Error in translation attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"      🔄 Retrying... ({attempt + 1}/{max_retries})")
                    sb.sleep(2)
                    # Reload page
                    sb.open(translate_url)
                    sb.sleep(2)
                    continue
                else:
                    return None
        
        if not input_found:
            print(f"      ❌ Could not find input textarea after {max_retries} attempts")
            return None
        
    except Exception as e:
        print(f"      ❌ Error with Google Translate Web: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return None


def test_simple_text(text, source_lang='da', target_lang='en', compare=True, web_only=False, headless=True):
    """
    Test dịch text đơn giản
    
    Args:
        text: Text cần dịch
        source_lang: Source language
        target_lang: Target language
        compare: So sánh với API nếu True
        web_only: Chỉ test web, không so sánh
        headless: Run browser in headless mode
    """
    print(f"\n{'='*60}")
    print(f"🧪 Testing Translation")
    print(f"{'='*60}")
    print(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"Source: {source_lang} → Target: {target_lang}")
    print(f"{'='*60}\n")
    
    # Test với Google Translate Web
    print("🌐 Testing Google Translate Web...")
    start_time = time.time()
    
    with start_browser_for_translate(headless=headless) as sb:
        web_result = translate_text_with_google_web(sb, text, source_lang, target_lang)
    
    web_time = time.time() - start_time
    
    if web_result:
        print(f"✅ Web Result ({web_time:.2f}s):")
        print(f"   {web_result[:200]}{'...' if len(web_result) > 200 else ''}")
    else:
        print(f"❌ Web translation failed")
    
    # So sánh với API nếu cần
    if compare and not web_only:
        print("\n🔌 Testing Google Cloud Translation API...")
        start_time = time.time()
        api_result = translate_text_with_google_cloud(text, source_lang, target_lang)
        api_time = time.time() - start_time
        
        if api_result:
            print(f"✅ API Result ({api_time:.2f}s):")
            print(f"   {api_result[:200]}{'...' if len(api_result) > 200 else ''}")
        else:
            print(f"❌ API translation failed")
        
        # So sánh kết quả
        if web_result and api_result:
            print(f"\n{'='*60}")
            print(f"📊 Comparison")
            print(f"{'='*60}")
            print(f"Web time: {web_time:.2f}s")
            print(f"API time: {api_time:.2f}s")
            print(f"Speed difference: {((web_time - api_time) / api_time * 100):.1f}%")
            
            # So sánh nội dung (đơn giản)
            if web_result.strip().lower() == api_result.strip().lower():
                print(f"✅ Results are identical")
            else:
                print(f"⚠️  Results differ")
                print(f"\nWeb:  {web_result[:150]}")
                print(f"API:  {api_result[:150]}")


def test_article_detail(article_id=None, article_url=None, headless=True):
    """
    Test dịch article detail từ database
    
    Args:
        article_id: ID của ArticleDetail
        article_url: URL của article
        headless: Run browser in headless mode
    """
    with app.app_context():
        # Tìm article detail
        article_detail = None
        if article_id:
            article_detail = ArticleDetail.query.get(article_id)
        elif article_url:
            article_detail = ArticleDetail.query.filter_by(published_url=article_url).first()
        
        if not article_detail:
            print(f"❌ Article detail not found")
            return
        
        print(f"\n{'='*60}")
        print(f"📰 Testing Article Detail Translation")
        print(f"{'='*60}")
        print(f"ID: {article_detail.id}")
        print(f"URL: {article_detail.published_url}")
        print(f"Language: {article_detail.language}")
        print(f"{'='*60}\n")
        
        # Lấy content blocks
        content_blocks = article_detail.content_blocks
        if isinstance(content_blocks, str):
            try:
                content_blocks = json.loads(content_blocks)
            except:
                content_blocks = []
        
        if not isinstance(content_blocks, list) or len(content_blocks) == 0:
            print(f"❌ No content blocks found")
            return
        
        # Tìm các paragraph blocks để test
        test_blocks = []
        for block in content_blocks[:5]:  # Chỉ test 5 blocks đầu
            if block.get('type') in ['paragraph', 'intro', 'heading']:
                if block.get('text') or block.get('html'):
                    test_blocks.append(block)
        
        if not test_blocks:
            print(f"❌ No text blocks found to test")
            return
        
        print(f"📝 Found {len(test_blocks)} blocks to test\n")
        
        # Test từng block
        with start_browser_for_translate(headless=headless) as sb:
            for i, block in enumerate(test_blocks, 1):
                print(f"\n[{i}/{len(test_blocks)}] Testing block type: {block.get('type')}")
                
                text_to_test = block.get('text', '')
                if not text_to_test and block.get('html'):
                    # Extract text từ HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(block['html'], 'html.parser')
                    text_to_test = soup.get_text(separator=' ', strip=True)
                
                if not text_to_test or len(text_to_test.strip()) < 10:
                    print(f"   ⏭️  Skipped (text too short)")
                    continue
                
                # Giới hạn text để test (tránh quá dài)
                if len(text_to_test) > 1000:
                    text_to_test = text_to_test[:1000] + "..."
                
                print(f"   Original: {text_to_test[:100]}...")
                
                # Test với Web
                start_time = time.time()
                web_result = translate_text_with_google_web(sb, text_to_test, 'da', 'en')
                web_time = time.time() - start_time
                
                if web_result:
                    print(f"   ✅ Web ({web_time:.2f}s): {web_result[:100]}...")
                else:
                    print(f"   ❌ Web failed")
                
                # Delay giữa các requests
                time.sleep(2)


def main():
    parser = argparse.ArgumentParser(
        description='Test Google Translate Web (browser automation)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--text', '-t', type=str,
                        help='Text to translate')
    parser.add_argument('--article-id', '-a', type=int,
                        help='ArticleDetail ID to test')
    parser.add_argument('--url', '-u', type=str,
                        help='Article URL to test')
    parser.add_argument('--source-lang', '-s', type=str, default='da',
                        help='Source language code (default: da)')
    parser.add_argument('--target-lang', type=str, default='en',
                        help='Target language code (default: en)')
    parser.add_argument('--compare', action='store_true',
                        help='Compare with Google Cloud API')
    parser.add_argument('--web-only', action='store_true',
                        help='Only test web, do not compare')
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in visible mode (for debugging)')
    
    args = parser.parse_args()
    
    if args.text:
        test_simple_text(
            args.text,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            compare=args.compare or not args.web_only,
            web_only=args.web_only,
            headless=not args.no_headless
        )
    elif args.article_id or args.url:
        test_article_detail(
            article_id=args.article_id,
            article_url=args.url,
            headless=not args.no_headless
        )
    else:
        # Default: test với text mẫu
        sample_text = "Hej, hvordan har du det? Jeg håber, du har det godt."
        test_simple_text(
            sample_text,
            source_lang='da',
            target_lang='en',
            compare=True,
            web_only=False,
            headless=not args.no_headless
        )


if __name__ == '__main__':
    main()
