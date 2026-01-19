"""
Script test để kiểm tra parser có lấy được subtitle và header image caption
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.article_detail_parser import ArticleDetailParser
from seleniumbase import SB
from bs4 import BeautifulSoup
import json

# User data directory để lưu session login
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')
LOGIN_URL = "https://www.sermitsiaq.ag/login"
LOGIN_EMAIL = "aluu@greenland.org"
LOGIN_PASSWORD = "LEn924924jfkjfk"

TEST_URL = "https://www.sermitsiaq.ag/erhverv/gronlandsudvalget-inviteret-til-avannaata-qimussersua/2329146"


def ensure_login(sb):
    """Đảm bảo đã login"""
    try:
        # Check if already logged in
        sb.open("https://www.sermitsiaq.ag")
        sb.sleep(2)
        
        # Try to find login button or user menu
        try:
            login_btn = sb.find_element('a[href*="login"]', timeout=3)
            if login_btn:
                print("   🔐 Not logged in, attempting login...")
                sb.open(LOGIN_URL)
                sb.sleep(2)
                
                # Fill login form
                email_input = sb.find_element('input[type="email"], input[name="email"]', timeout=5)
                password_input = sb.find_element('input[type="password"], input[name="password"]', timeout=5)
                
                if email_input and password_input:
                    email_input.clear()
                    email_input.send_keys(LOGIN_EMAIL)
                    password_input.clear()
                    password_input.send_keys(LOGIN_PASSWORD)
                    
                    # Submit form
                    submit_btn = sb.find_element('button[type="submit"], input[type="submit"]', timeout=5)
                    if submit_btn:
                        submit_btn.click()
                        sb.sleep(3)
                        print("   ✅ Login successful")
                        return True
        except:
            print("   ✅ Already logged in or login not needed")
            return True
    except Exception as e:
        print(f"   ⚠️  Login check error: {e}")
        return True  # Continue anyway


def test_parse_article():
    """Test parse article từ URL"""
    print(f"🧪 Testing parser with URL: {TEST_URL}")
    print("=" * 80)
    
    # Tạo user_data_dir nếu chưa tồn tại
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    with SB(uc=True, headless=False, user_data_dir=USER_DATA_DIR) as sb:
        # Đảm bảo đã login
        ensure_login(sb)
        
        try:
            # Navigate to URL
            print(f"\n📄 Opening URL...")
            sb.open(TEST_URL)
            sb.sleep(3)  # Wait for page to load
            
            # Wait for articleHeader
            try:
                sb.wait_for_element('.articleHeader', timeout=10)
                print("   ✅ Found .articleHeader")
            except:
                print("   ⚠️  Timeout waiting for .articleHeader")
            
            # Get articleHeader HTML
            article_header_html = None
            try:
                article_header = sb.find_element('.articleHeader', timeout=5)
                if article_header:
                    article_header_html = article_header.get_attribute('outerHTML')
                    print(f"   ✅ Got articleHeader HTML ({len(article_header_html)} chars)")
            except:
                # Fallback: parse from page source
                try:
                    page_source = sb.get_page_source()
                    soup = BeautifulSoup(page_source, 'html.parser')
                    article_header = soup.find('div', class_='articleHeader')
                    if article_header:
                        article_header_html = str(article_header)
                        print(f"   ✅ Got articleHeader HTML from page source ({len(article_header_html)} chars)")
                except Exception as e:
                    print(f"   ❌ Error getting articleHeader: {e}")
            
            # Get bodytext HTML
            bodytext_html = None
            try:
                page_source = sb.get_page_source()
                soup = BeautifulSoup(page_source, 'html.parser')
                bodytext_div = soup.find('div', class_='bodytext', attrs={'data-element-guid': True})
                if bodytext_div:
                    bodytext_html = str(bodytext_div)
                    print(f"   ✅ Got bodytext HTML ({len(bodytext_html)} chars)")
            except Exception as e:
                print(f"   ⚠️  Error getting bodytext: {e}")
            
            # Combine HTML
            full_html = ''
            if article_header_html:
                full_html = article_header_html
            if bodytext_html:
                full_html += bodytext_html
            
            if not full_html:
                print("   ❌ No HTML content found")
                return
            
            print(f"\n📝 Parsing HTML content ({len(full_html)} chars)...")
            print("=" * 80)
            
            # Parse HTML
            blocks = ArticleDetailParser.parse_html_content(full_html)
            
            print(f"\n✅ Parsed {len(blocks)} blocks")
            print("=" * 80)
            
            # Find subtitle block
            subtitle_block = None
            for block in blocks:
                if block.get('type') == 'subtitle':
                    subtitle_block = block
                    break
            
            # Find header_image_caption block
            header_caption_block = None
            for block in blocks:
                if block.get('type') == 'header_image_caption':
                    header_caption_block = block
                    break
            
            # Print results
            print("\n📋 RESULTS:")
            print("=" * 80)
            
            if subtitle_block:
                print(f"\n✅ SUBTITLE FOUND:")
                print(f"   Text: {subtitle_block.get('text', '')[:200]}...")
                print(f"   HTML: {subtitle_block.get('html', '')[:200]}...")
            else:
                print(f"\n❌ SUBTITLE NOT FOUND")
                # Try to find h2.subtitle in raw HTML
                soup = BeautifulSoup(full_html, 'html.parser')
                h2_subtitle = soup.find('h2', class_='subtitle')
                if h2_subtitle:
                    print(f"   ⚠️  But found h2.subtitle in HTML: {h2_subtitle.get_text(strip=True)[:200]}...")
                else:
                    print(f"   ⚠️  No h2.subtitle found in HTML")
            
            if header_caption_block:
                print(f"\n✅ HEADER IMAGE CAPTION FOUND:")
                print(f"   Caption: {header_caption_block.get('caption', '')[:200]}...")
                print(f"   Author: {header_caption_block.get('author', '')}")
            else:
                print(f"\n❌ HEADER IMAGE CAPTION NOT FOUND")
                # Try to find div.caption in articleHeader
                soup = BeautifulSoup(full_html, 'html.parser')
                article_header = soup.find('div', class_='articleHeader')
                if article_header:
                    caption_div = article_header.find('div', class_='caption')
                    if caption_div:
                        caption_elem = caption_div.find('figcaption', itemprop='caption')
                        author_elem = caption_div.find('figcaption', itemprop='author')
                        if caption_elem or author_elem:
                            print(f"   ⚠️  But found div.caption in articleHeader:")
                            if caption_elem:
                                print(f"      Caption: {caption_elem.get_text(strip=True)[:200]}...")
                            if author_elem:
                                print(f"      Author: {author_elem.get_text(strip=True)}")
            
            # Print all blocks for debugging
            print(f"\n📦 ALL BLOCKS ({len(blocks)}):")
            print("=" * 80)
            for i, block in enumerate(blocks, 1):
                block_type = block.get('type', 'unknown')
                print(f"\n{i}. Type: {block_type}")
                if block_type == 'subtitle':
                    print(f"   Text: {block.get('text', '')[:100]}...")
                elif block_type == 'header_image_caption':
                    print(f"   Caption: {block.get('caption', '')[:100]}...")
                    print(f"   Author: {block.get('author', '')}")
                elif block_type == 'image':
                    print(f"   Classes: {block.get('classes', [])}")
                    print(f"   Is header image: {block.get('is_header_image', False)}")
                    print(f"   Caption: {block.get('caption', '')[:100] if block.get('caption') else 'None'}...")
                    print(f"   Author: {block.get('author', '')}")
                elif block_type == 'paragraph':
                    print(f"   Text: {block.get('text', '')[:100]}...")
                elif block_type == 'article_meta':
                    print(f"   Bylines: {len(block.get('bylines', []))}")
                    print(f"   Dates: {block.get('dates', {})}")
            
            print("\n" + "=" * 80)
            print("✅ Test completed!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    with app.app_context():
        test_parse_article()

