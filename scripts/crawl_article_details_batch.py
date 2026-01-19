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

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from services.article_detail_parser import ArticleDetailParser
from seleniumbase import SB
from googletrans import Translator
import re

# User data directory để lưu session login
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')
LOGIN_URL = "https://www.sermitsiaq.ag/login"
LOGIN_EMAIL = "aluu@greenland.org"
LOGIN_PASSWORD = "LEn924924jfkjfk"


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


def translate_content_blocks(content_blocks: list, source_lang: str = 'da', target_lang: str = 'en') -> list:
    """
    Dịch content_blocks từ source_lang sang target_lang
    
    Args:
        content_blocks: List of content blocks
        source_lang: Source language code ('da')
        target_lang: Target language code ('en')
        
    Returns:
        Translated content blocks
    """
    if not content_blocks:
        return []
    
    translator = Translator()
    translated_blocks = []
    
    for block in content_blocks:
        translated_block = block.copy()
        
        # Chỉ dịch các block có text content
        if block.get('type') in ['paragraph', 'heading', 'intro']:
            # Dịch text
            if block.get('text'):
                try:
                    translated_text = translator.translate(
                        block['text'], 
                        src=source_lang, 
                        dest=target_lang
                    ).text
                    translated_block['text'] = translated_text
                except Exception as e:
                    print(f"   ⚠️  Translation error for text: {e}")
                    # Giữ nguyên text nếu dịch lỗi
                    translated_block['text'] = block['text']
            
            # Dịch HTML content (chỉ dịch text trong tags, giữ nguyên tags)
            if block.get('html'):
                try:
                    # Tách HTML thành tags và text
                    html = block['html']
                    # Tìm tất cả text nodes và dịch
                    def translate_html_text(match):
                        text = match.group(1)
                        if text.strip():
                            try:
                                translated = translator.translate(text, src=source_lang, dest=target_lang).text
                                return f'>{translated}<'
                            except:
                                return match.group(0)
                        return match.group(0)
                    
                    # Dịch text giữa các tags
                    translated_html = re.sub(r'>([^<]+)<', translate_html_text, html)
                    translated_block['html'] = translated_html
                except Exception as e:
                    print(f"   ⚠️  Translation error for HTML: {e}")
                    # Giữ nguyên HTML nếu dịch lỗi
                    translated_block['html'] = block['html']
        
        # Giữ nguyên các block khác (images, ads, paywall_offers, etc.)
        translated_blocks.append(translated_block)
    
    return translated_blocks


def create_en_article_detail_from_da(da_article_detail: ArticleDetail) -> ArticleDetail:
    """
    Tạo article_detail EN từ article_detail DA
    
    Args:
        da_article_detail: ArticleDetail object với language='da'
        
    Returns:
        ArticleDetail object với language='en' hoặc None nếu đã tồn tại
    """
    # Convert URL từ DA sang EN
    en_url = convert_da_url_to_en_url(da_article_detail.published_url)
    
    # Kiểm tra xem đã có EN version chưa
    existing_en_detail = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
    if existing_en_detail:
        print(f"   ℹ️  EN version already exists for {en_url}")
        return existing_en_detail
    
    # Dịch content_blocks
    print(f"   🌐 Translating content blocks from DA to EN...")
    translated_blocks = translate_content_blocks(
        da_article_detail.content_blocks or [],
        source_lang='da',
        target_lang='en'
    )
    
    # Tạo ArticleDetail mới với language='en'
    en_article_detail = ArticleDetail(
        published_url=en_url,
        content_blocks=translated_blocks,
        language='en',
        element_guid=da_article_detail.element_guid
    )
    
    db.session.add(en_article_detail)
    db.session.commit()
    
    print(f"   ✅ Created EN article_detail (ID: {en_article_detail.id})")
    return en_article_detail


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
            
            # Kiểm tra xem đã có EN version chưa
            existing_en = ArticleDetail.query.filter_by(published_url=en_url, language='en').first()
            if existing_en:
                print(f"   ⏭️  Skipped - EN version already exists")
                skip_count += 1
                continue
            
            # Tạo EN version
            en_detail = create_en_article_detail_from_da(da_detail)
            if en_detail:
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
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


def crawl_article_detail(url: str, language: str = 'da', headless: bool = True):
    """
    Crawl article detail page và lưu vào database
    
    Args:
        url: URL của article detail page
        language: Language code ('da', 'kl', 'en')
        headless: Run browser in headless mode
    
    Returns:
        ArticleDetail object or None
    """
    print(f"🔍 Crawling: {url[:70]}...")
    
    # Tạo user_data_dir nếu chưa tồn tại
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    with SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR) as sb:
        # Đảm bảo đã login trước khi crawl (chỉ login 1 lần cho batch)
        # Note: Login sẽ được thực hiện ở batch_crawl_articles, không cần login lại mỗi article
        try:
            # Navigate to URL
            sb.open(url)
            sb.sleep(2)  # Wait for page to load
            
            # Wait for bodytext content
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
            
            # Get article meta (bylines and dates)
            meta_html = None
            try:
                article_header = sb.find_element('.articleHeader', timeout=5)
                if article_header:
                    meta_elem = article_header.find_element('.meta', timeout=3)
                    if meta_elem:
                        meta_html = meta_elem.get_attribute('outerHTML')
            except:
                # Fallback: parse from page source
                try:
                    from bs4 import BeautifulSoup
                    page_source = sb.get_page_source()
                    soup = BeautifulSoup(page_source, 'html.parser')
                    article_header = soup.find('div', class_='articleHeader')
                    if article_header:
                        meta_div = article_header.find('div', class_='meta')
                        if meta_div:
                            meta_html = str(meta_div)
                except:
                    pass
            
            # Get bodytext HTML
            bodytext_html = None
            try:
                page_source = sb.get_page_source()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')
                
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
                print(f"   ⚠️  Error parsing bodytext: {e}")
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
            
            # Combine HTML
            full_html = ''
            if meta_html:
                full_html = meta_html
            if bodytext_html:
                full_html += bodytext_html
            if offers_html:
                full_html += offers_html
            if footer_html:
                full_html += footer_html
            
            if not full_html:
                print(f"   ❌ Could not find content")
                return None
            
            # Get element_guid from bodytext
            element_guid = None
            if bodytext_html:
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


def crawl_all(language=None, section=None, limit=None, headless=True, delay=2):
    """
    Crawl tất cả articles chưa có detail
    
    Args:
        language: Filter theo language
        section: Filter theo section
        limit: Giới hạn số lượng
        headless: Run browser in headless mode
        delay: Delay giữa các requests (seconds)
    """
    articles = get_articles_to_crawl(language=language, section=section, limit=limit)
    
    if not articles:
        print("\n✅ Không có articles nào cần crawl!")
        return
    
    print(f"\n🚀 Bắt đầu crawl {len(articles)} articles...")
    if language:
        print(f"   Language: {language}")
    if section:
        print(f"   Section: {section}")
    if limit:
        print(f"   Limit: {limit}")
    print(f"   Headless: {headless}")
    print(f"   Delay: {delay}s giữa các requests\n")
    
    # Tạo user_data_dir nếu chưa tồn tại
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    # Login một lần trước khi bắt đầu crawl (sử dụng user_data_dir để lưu session)
    print("🔐 Initializing browser session with login...")
    with SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR) as sb:
        if not ensure_login(sb):
            print("❌ Failed to login, cannot proceed with crawling")
            return
    
    # Sau khi login xong, session đã được lưu trong user_data_dir
    # Các lần crawl tiếp theo sẽ tự động sử dụng session đã lưu
    print("✅ Login session saved, starting to crawl articles...\n")
    
    success_count = 0
    fail_count = 0
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] Article ID: {article.id}")
        
        result = crawl_article_detail(
            url=article.published_url,
            language=article.language,
            headless=headless
        )
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        # Delay giữa các requests
        if i < len(articles):
            time.sleep(delay)
    
    print(f"\n{'='*60}")
    print(f"✅ Hoàn thành!")
    print(f"   Success: {success_count}/{len(articles)}")
    print(f"   Failed: {fail_count}/{len(articles)}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Crawl article detail pages theo batch',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
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
        """
    )
    
    parser.add_argument('--list', action='store_true',
                        help='List tất cả articles cần crawl')
    parser.add_argument('--crawl-all', action='store_true',
                        help='Crawl tất cả articles chưa có detail')
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
    parser.add_argument('--translate-da-to-en', action='store_true',
                        help='Dịch article_detail từ DA sang EN sau khi crawl')
    parser.add_argument('--translate-only', action='store_true',
                        help='Chỉ dịch các article_detail DA đã có, không crawl mới')
    parser.add_argument('--translate-limit', type=int,
                        help='Giới hạn số lượng article_detail để dịch')
    
    args = parser.parse_args()
    
    if not args.list and not args.crawl_all:
        parser.print_help()
        return
    
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
        elif args.crawl_all:
            crawl_all(
                language=args.language,
                section=args.section,
                limit=args.limit,
                headless=not args.no_headless,
                delay=args.delay
            )
            
            # Dịch DA sang EN sau khi crawl nếu được yêu cầu
            if args.translate_da_to_en:
                print("\n" + "="*60)
                print("🌐 Starting translation from DA to EN...")
                print("="*60 + "\n")
                translate_da_article_details_to_en(limit=args.translate_limit)


if __name__ == '__main__':
    main()

