"""
Script để crawl article detail page và lưu vào article_details table
Usage: python scripts/crawl_article_detail.py <url>
"""
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from services.article_detail_parser import ArticleDetailParser
from seleniumbase import SB

# User data directory để lưu session login
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')
LOGIN_URL = "https://www.sermitsiaq.ag/login"
LOGIN_EMAIL = "aluu@greenland.org"
LOGIN_PASSWORD = "LEn924924jfkjfk"


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


def crawl_article_detail(url: str, language: str = 'da'):
    """
    Crawl article detail page và lưu vào database
    
    Args:
        url: URL của article detail page
        language: Language code ('da', 'kl', 'en')
    """
    print(f"🔍 Crawling article detail: {url}")
    print(f"   Language: {language}")
    
    # Tạo user_data_dir nếu chưa tồn tại
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    with SB(uc=True, headless=True, user_data_dir=USER_DATA_DIR) as sb:
        # Đảm bảo đã login trước khi crawl
        if not ensure_login(sb):
            print("❌ Failed to login, cannot proceed with crawling")
            return None
        try:
            # Navigate to URL
            sb.open(url)
            sb.sleep(2)  # Wait for page to load
            
            # Wait for bodytext content
            sb.wait_for_element('.bodytext', timeout=10)
            
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
                            print(f"   ✅ Found article meta via Selenium ({len(meta_html)} chars)")
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
                            print(f"   ✅ Found article meta from page source ({len(meta_html)} chars)")
                except Exception as e:
                    print(f"   ⚠️  Could not find articleHeader: {e}")
            
            # Get bodytext HTML - lấy toàn bộ bodytext container bao gồm cả intro và content-text
            # Sử dụng page source để đảm bảo lấy đầy đủ HTML
            bodytext_html = None
            try:
                # Get full page source và parse bằng BeautifulSoup
                page_source = sb.get_page_source()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Tìm bodytext div chính (có data-element-guid)
                bodytext_div = soup.find('div', class_='bodytext', attrs={'data-element-guid': True})
                if bodytext_div:
                    bodytext_html = str(bodytext_div)
                    print(f"   Found bodytext from page source ({len(bodytext_html)} chars)")
                    
                    # Kiểm tra xem có content-text không
                    if 'content-text' in bodytext_html:
                        print(f"   ✅ Contains content-text section")
                    else:
                        print(f"   ⚠️  No content-text section found")
                else:
                    print(f"   ⚠️  Could not find bodytext div")
            except Exception as e:
                print(f"   ❌ Error parsing page source: {e}")
                # Fallback: try Selenium element
                try:
                    bodytext_elem = sb.find_element('div.bodytext.large-12', timeout=5)
                    if bodytext_elem:
                        bodytext_html = bodytext_elem.get_attribute('outerHTML')
                        print(f"   Found bodytext via Selenium ({len(bodytext_html)} chars)")
                except:
                    pass
            
            # Get paywall offers section
            offers_html = None
            try:
                offers_elem = sb.find_element('.iteras-offers', timeout=5)
                if offers_elem:
                    offers_html = offers_elem.get_attribute('outerHTML')
            except:
                pass
            
            # Get article footer tags section - tìm từ page source để đảm bảo
            footer_html = None
            try:
                # Try Selenium first
                footer_elem = sb.find_element('.articleFooter', timeout=5)
                if footer_elem:
                    footer_html = footer_elem.get_attribute('outerHTML')
                    print(f"   ✅ Found articleFooter via Selenium ({len(footer_html)} chars)")
            except:
                # Fallback: parse from page source
                try:
                    from bs4 import BeautifulSoup
                    page_source = sb.get_page_source()
                    soup = BeautifulSoup(page_source, 'html.parser')
                    footer_div = soup.find('div', class_='articleFooter')
                    if footer_div:
                        footer_html = str(footer_div)
                        print(f"   ✅ Found articleFooter from page source ({len(footer_html)} chars)")
                except Exception as e:
                    print(f"   ⚠️  Could not find articleFooter: {e}")
            
            # Combine HTML - articleHeader (chứa subtitle) nên đặt đầu tiên, sau đó meta, rồi bodytext
            full_html = ''
            if article_header_html:
                # Sử dụng articleHeader HTML để parser có thể parse subtitle
                full_html = article_header_html
                print(f"   ✅ Added articleHeader to HTML ({len(article_header_html)} chars)")
            elif meta_html:
                # Fallback: chỉ có meta nếu không có articleHeader
                full_html = meta_html
                print(f"   ✅ Added article meta to HTML ({len(meta_html)} chars)")
            if bodytext_html:
                full_html += bodytext_html
            if offers_html:
                full_html += offers_html
            if footer_html:
                full_html += footer_html
                print(f"   ✅ Found articleFooter ({len(footer_html)} chars)")
            
            if not full_html:
                print("❌ Could not find bodytext content")
                return None
            
            print(f"✅ Found content ({len(full_html)} chars)")
            
            # Get element_guid from bodytext
            element_guid = None
            if bodytext_html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(bodytext_html, 'html.parser')
                bodytext_div = soup.find('div', class_='bodytext')
                if bodytext_div:
                    element_guid = bodytext_div.get('data-element-guid', '')
            
            # Parse and save to database
            with app.app_context():
                article_detail = ArticleDetailParser.save_article_detail(
                    published_url=url,
                    html_content=full_html,
                    language=language,
                    element_guid=element_guid
                )
                
                print(f"✅ Saved article detail (ID: {article_detail.id})")
                print(f"   Blocks: {len(article_detail.content_blocks)}")
                
                # Also update article if exists
                article = Article.query.filter_by(published_url=url).first()
                if article:
                    print(f"✅ Found matching article (ID: {article.id})")
                    if title and not article.title:
                        article.title = title
                    if excerpt and not article.excerpt:
                        article.excerpt = excerpt
                    db.session.commit()
                else:
                    print(f"⚠️  No matching article found with published_url={url}")
                
                return article_detail
                
        except Exception as e:
            print(f"❌ Error crawling: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser(description='Crawl article detail page')
    parser.add_argument('url', help='URL of article detail page')
    parser.add_argument('--language', '-l', default='da', choices=['da', 'kl', 'en'],
                        help='Language code (default: da)')
    
    args = parser.parse_args()
    
    with app.app_context():
        article_detail = crawl_article_detail(args.url, args.language)
        
        if article_detail:
            # Query again from database to avoid DetachedInstanceError
            saved_detail = ArticleDetail.query.filter_by(published_url=args.url).first()
            print(f"\n✅ Success!")
            if saved_detail:
                print(f"   Article Detail ID: {saved_detail.id}")
                print(f"   Published URL: {saved_detail.published_url}")
                print(f"   Blocks: {len(saved_detail.content_blocks) if saved_detail.content_blocks else 0}")
            print(f"\n📝 Test URL: http://localhost:5000/article/detail/test?url={args.url}")
        else:
            print("\n❌ Failed to crawl article detail")


if __name__ == '__main__':
    main()

