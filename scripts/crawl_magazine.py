"""
Script để crawl magazine từ e-pages.pub
- Vào link magazine
- Click vào button Next để navigate qua các pages
- Thu thập data-article và lưu vào CSV

Usage:
    python scripts/crawl_magazine.py
    python scripts/crawl_magazine.py --no-headless  # Để xem browser
    python scripts/crawl_magazine.py --magazine-start 7 --magazine-end 164  # Chạy từ magazine 7 đến 164
"""
import sys
import os
import argparse
import time
import csv
import re
from collections import OrderedDict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seleniumbase import SB

# User data directory để lưu session (dùng chung với crawl script)
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')
LOGIN_EMAIL = "aluu@greenland.org"
LOGIN_PASSWORD = "LEn924924jfkjfk"

# Base URL template
BASE_URL_TEMPLATE = "https://sermitsiaq.e-pages.pub/titles/ag/13765/publications/{magazine_id}/pages/1"


def handle_login_if_needed(sb):
    """
    Kiểm tra và xử lý login nếu page yêu cầu đăng nhập
    Form login nằm trong shadow DOM của element LOGIN-DIALOG
    
    Args:
        sb: SeleniumBase instance
    
    Returns:
        bool: True nếu đã login thành công hoặc không cần login, False nếu login thất bại
    """
    try:
        print("🔍 Checking for login form...")
        sb.sleep(5)  # Đợi JS render
        
        # Kiểm tra xem có form login không
        needs_login = False
        try:
            page_source = sb.get_page_source()
            if 'Er du allerede abonnent' in page_source:
                needs_login = True
                print("🔐 Found login form in page source")
        except:
            pass
        
        if not needs_login:
            print("✅ No login required")
            return True
        
        print("🔐 Login form detected, attempting to login...")
        
        # Tìm và điền form trong shadow DOM của LOGIN-DIALOG
        login_success = sb.execute_script("""
            var email = arguments[0];
            var password = arguments[1];
            
            // Tìm LOGIN-DIALOG element
            var loginDialogs = document.querySelectorAll('login-dialog');
            for (var i = 0; i < loginDialogs.length; i++) {
                var loginDialog = loginDialogs[i];
                if (loginDialog.shadowRoot) {
                    var shadowRoot = loginDialog.shadowRoot;
                    
                    // Tìm email input
                    var emailInput = shadowRoot.querySelector('input[type="email"], input[name="email"]');
                    if (emailInput && emailInput.offsetParent !== null) {
                        emailInput.value = email;
                        emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                        emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        // Tìm password input
                        var passwordInput = shadowRoot.querySelector('input[type="password"], input[name="password"]');
                        if (passwordInput && passwordInput.offsetParent !== null) {
                            passwordInput.value = password;
                            passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
                            passwordInput.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // Tìm và click submit button
                            var submitButton = shadowRoot.querySelector('button.login-button, button[type="submit"]');
                            if (!submitButton) {
                                // Fallback: tìm button có text "Log på"
                                var buttons = shadowRoot.querySelectorAll('button');
                                for (var j = 0; j < buttons.length; j++) {
                                    var btn = buttons[j];
                                    var text = btn.textContent || btn.innerText || '';
                                    if (text.includes('Log på') && btn.offsetParent !== null) {
                                        submitButton = btn;
                                        break;
                                    }
                                }
                            }
                            
                            if (submitButton && submitButton.offsetParent !== null) {
                                submitButton.click();
                                return true;
                            }
                        }
                    }
                }
            }
            return false;
        """, LOGIN_EMAIL, LOGIN_PASSWORD)
        
        if login_success:
            print("✅ Filled form and clicked submit")
        else:
            print("⚠️  Could not fill form or click submit")
        
        # Đợi sau khi submit
        sb.sleep(5)
        
        # Kiểm tra login thành công
        try:
            page_source = sb.get_page_source()
            if 'Du er allerede logget ind' in page_source or 'Log ud' in page_source:
                print("✅ Login successful!")
                return True
        except:
            pass
        
        # Kiểm tra xem form login còn không
        try:
            # Kiểm tra trong shadow DOM
            form_still_present = sb.execute_script("""
                var loginDialogs = document.querySelectorAll('login-dialog');
                for (var i = 0; i < loginDialogs.length; i++) {
                    if (loginDialogs[i].shadowRoot) {
                        var passwordInput = loginDialogs[i].shadowRoot.querySelector('input[type="password"]');
                        if (passwordInput && passwordInput.offsetParent !== null) {
                            return true;
                        }
                    }
                }
                return false;
            """)
            
            if form_still_present:
                print("⚠️  Login form still present, login may have failed")
                return False
            else:
                print("✅ Login successful (login form no longer present)")
                return True
        except:
            print("✅ Login successful (could not verify)")
            return True
        
    except Exception as e:
        print(f"⚠️  Error during login: {e}")
        import traceback
        traceback.print_exc()
        return True


def extract_magazine_id_from_url(url: str) -> int:
    """
    Extract magazine ID từ URL
    Ví dụ: https://sermitsiaq.e-pages.pub/titles/ag/13765/publications/7/pages/1 -> 7
    
    Args:
        url: Magazine URL
    
    Returns:
        int: Magazine ID hoặc None nếu không tìm thấy
    """
    match = re.search(r'/publications/(\d+)/', url)
    if match:
        return int(match.group(1))
    return None


def get_crawled_magazines(output_file: str = 'magazine_articles.csv') -> set:
    """
    Đọc CSV file để lấy danh sách magazine_id đã crawl
    
    Args:
        output_file: Tên file CSV
    
    Returns:
        set: Set các magazine_id đã crawl
    """
    crawled_magazines = set()
    
    if not os.path.exists(output_file):
        return crawled_magazines
    
    try:
        with open(output_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                magazine_id = row.get('magazine_id', '').strip()
                if magazine_id and magazine_id.isdigit():
                    crawled_magazines.add(int(magazine_id))
    except Exception as e:
        print(f"⚠️  Error reading {output_file}: {e}")
    
    return crawled_magazines


def save_articles_to_csv(articles: list, output_file: str = 'magazine_articles.csv'):
    """
    Lưu articles vào CSV file, drop duplicate dựa trên data_article
    
    Args:
        articles: List các articles
        output_file: Tên file CSV output
    """
    if not articles:
        print("⚠️  No articles to save")
        return
    
    # Drop duplicate dựa trên data_article, giữ lại entry đầu tiên
    seen = OrderedDict()
    for article in articles:
        data_article = article.get('data_article', '')
        if data_article and data_article not in seen:
            seen[data_article] = article
    
    unique_articles = list(seen.values())
    
    # Sort by magazine_id, then by data_article
    unique_articles.sort(key=lambda x: (x.get('magazine_id', 0), x.get('data_article', '')))
    
    # Write to CSV
    fieldnames = ['magazine_id', 'data_article', 'data_external_id', 'aria_label', 'lang', 
                  'tag_name', 'class_name', 'page_number', 'url']
    
    file_exists = os.path.exists(output_file)
    
    # Đọc các articles hiện có để tránh duplicate khi append
    existing_articles = set()
    if file_exists:
        try:
            with open(output_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    data_article = row.get('data_article', '').strip()
                    magazine_id = row.get('magazine_id', '').strip()
                    if data_article and magazine_id:
                        existing_articles.add((magazine_id, data_article))
        except:
            pass
    
    # Filter out articles đã tồn tại
    new_articles = []
    for article in unique_articles:
        key = (str(article.get('magazine_id', '')), article.get('data_article', ''))
        if key not in existing_articles:
            new_articles.append(article)
    
    if not new_articles:
        print(f"⚠️  All articles already exist in {output_file}")
        return
    
    with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for article in new_articles:
            row = {field: article.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"✅ Saved {len(new_articles)} new unique articles to {output_file}")
    print(f"   Total duplicates removed: {len(articles) - len(unique_articles)}")


def crawl_magazine(magazine_id: int, headless: bool = True, max_pages: int = None):
    """
    Crawl magazine page và click Next button, thu thập data-article từ mỗi page
    
    Args:
        magazine_id: Magazine ID (ví dụ: 7, 162, ...)
        headless: Run browser in headless mode
        max_pages: Số lượng pages tối đa để crawl (None = không giới hạn)
    
    Returns:
        list: Danh sách các articles với data-article
    """
    magazine_url = BASE_URL_TEMPLATE.format(magazine_id=magazine_id)
    print(f"\n{'='*60}")
    print(f"🔍 Opening magazine #{magazine_id}: {magazine_url}")
    print(f"{'='*60}")
    
    # List để lưu tất cả articles
    all_articles = []
    
    # Tạo user_data_dir nếu chưa tồn tại
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    with SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR) as sb:
        try:
            # Navigate to magazine URL
            print(f"📖 Navigating to: {magazine_url}")
            sb.open(magazine_url)
            sb.sleep(3)  # Wait for page to load
            
            # Kiểm tra và xử lý login nếu cần
            if not handle_login_if_needed(sb):
                print("❌ Login failed, cannot proceed")
                return
            
            print("✅ Page loaded successfully")
            
            # Tìm và click button "Next" (có thể nằm trong shadow DOM hoặc phần ẩn)
            # Đợi để các custom elements được render
            sb.sleep(3)
            
            # Helper function để extract articles từ page hiện tại
            def extract_articles_from_current_page(page_num):
                """Extract articles từ page hiện tại"""
                # Tìm và hiển thị book-navigation trong shadow DOM của view-publication
                print("🔍 Activating book-navigation...")
                navigation_found = sb.execute_script("""
                // Tìm book-navigation trong shadow DOM của view-publication
                var viewPublications = document.querySelectorAll('view-publication');
                for (var i = 0; i < viewPublications.length; i++) {
                    if (viewPublications[i].shadowRoot) {
                        var bookNav = viewPublications[i].shadowRoot.querySelector('book-navigation');
                        if (bookNav) {
                            // Remove class "hideSectionNavigationSpread" để hiển thị navigation
                            if (bookNav.classList.contains('hideSectionNavigationSpread')) {
                                bookNav.classList.remove('hideSectionNavigationSpread');
                            }
                            
                            // Đảm bảo có class "visible"
                            if (!bookNav.classList.contains('visible')) {
                                bookNav.classList.add('visible');
                            }
                            
                            // Hiển thị navbar trong shadow DOM của book-navigation
                            if (bookNav.shadowRoot) {
                                var navbar = bookNav.shadowRoot.querySelector('.navbar');
                                if (navbar) {
                                    // Remove class "out" để hiển thị navbar
                                    if (navbar.classList.contains('out')) {
                                        navbar.classList.remove('out');
                                    }
                                }
                            }
                            
                            return {found: true};
                        }
                    }
                }
                return {found: false};
            """)
                
                if navigation_found and navigation_found.get('found'):
                    print("   ✅ Activated book-navigation")
                    sb.sleep(2)  # Đợi navigation bar hiển thị
                else:
                    print("   ⚠️  book-navigation not found")
                
                # Unhide book-page elements trước khi tìm articles
                print("🔍 Unhiding book-page elements...")
                sb.execute_script("""
                    // Tìm book-page trong shadow DOM của view-publication
                    var viewPublications = document.querySelectorAll('view-publication');
                    for (var i = 0; i < viewPublications.length; i++) {
                        if (viewPublications[i].shadowRoot) {
                            var shadowRoot = viewPublications[i].shadowRoot;
                            
                            // Tìm tất cả book-page elements
                            var bookPages = shadowRoot.querySelectorAll('book-page');
                            for (var j = 0; j < bookPages.length; j++) {
                                var bookPage = bookPages[j];
                                
                                // Remove aria-hidden và inert để hiển thị
                                if (bookPage.hasAttribute('aria-hidden')) {
                                    bookPage.removeAttribute('aria-hidden');
                                }
                                if (bookPage.hasAttribute('inert')) {
                                    bookPage.removeAttribute('inert');
                                }
                                
                                // Đảm bảo có class "current" hoặc "initialized"
                                if (!bookPage.classList.contains('initialized')) {
                                    bookPage.classList.add('initialized');
                                }
                                
                                // Set style để đảm bảo hiển thị
                                bookPage.style.display = '';
                                bookPage.style.visibility = '';
                                bookPage.style.opacity = '';
                                
                                // Nếu có shadowRoot, cũng unhide các elements bên trong
                                if (bookPage.shadowRoot) {
                                    var pageElements = bookPage.shadowRoot.querySelectorAll('*');
                                    for (var k = 0; k < pageElements.length; k++) {
                                        var el = pageElements[k];
                                        if (el.hasAttribute('aria-hidden')) {
                                            el.removeAttribute('aria-hidden');
                                        }
                                        if (el.hasAttribute('inert')) {
                                            el.removeAttribute('inert');
                                        }
                                    }
                                }
                            }
                        }
                    }
                """)
                sb.sleep(1)  # Đợi elements hiển thị
                
                # Tìm và lưu các elements có data-article từ page hiện tại
                print("🔍 Finding elements with data-article...")
                articles = sb.execute_script("""
                    var result = [];
                    
                    // Tìm trong main document
                    var mainElements = document.querySelectorAll('[data-article]');
                    for (var i = 0; i < mainElements.length; i++) {
                        var el = mainElements[i];
                        var dataArticle = el.getAttribute('data-article') || '';
                        var dataExternalId = el.getAttribute('data-external_id') || '';
                        var ariaLabel = el.getAttribute('aria-label') || '';
                        var lang = el.getAttribute('lang') || '';
                        var tagName = el.tagName || '';
                        var className = el.className || '';
                        
                        result.push({
                            data_article: dataArticle,
                            data_external_id: dataExternalId,
                            aria_label: ariaLabel,
                            lang: lang,
                            tag_name: tagName,
                            class_name: className
                        });
                    }
                    
                    // Tìm trong shadow DOM của view-publication
                    var viewPublications = document.querySelectorAll('view-publication');
                    for (var i = 0; i < viewPublications.length; i++) {
                        if (viewPublications[i].shadowRoot) {
                            var shadowRoot = viewPublications[i].shadowRoot;
                            
                            // Tìm trong book-page elements
                            var bookPages = shadowRoot.querySelectorAll('book-page');
                            for (var j = 0; j < bookPages.length; j++) {
                                var bookPage = bookPages[j];
                                
                                // Tìm trong book-page (có thể có shadowRoot hoặc không)
                                var pageElements = [];
                                if (bookPage.shadowRoot) {
                                    pageElements = bookPage.shadowRoot.querySelectorAll('[data-article]');
                                } else {
                                    // Nếu không có shadowRoot, tìm trực tiếp trong book-page
                                    pageElements = bookPage.querySelectorAll('[data-article]');
                                }
                                
                                for (var k = 0; k < pageElements.length; k++) {
                                    var el = pageElements[k];
                                    var dataArticle = el.getAttribute('data-article') || '';
                                    var dataExternalId = el.getAttribute('data-external_id') || '';
                                    var ariaLabel = el.getAttribute('aria-label') || '';
                                    var lang = el.getAttribute('lang') || '';
                                    var tagName = el.tagName || '';
                                    var className = el.className || '';
                                    
                                    result.push({
                                        data_article: dataArticle,
                                        data_external_id: dataExternalId,
                                        aria_label: ariaLabel,
                                        lang: lang,
                                        tag_name: tagName,
                                        class_name: className
                                    });
                                }
                            }
                            
                            // Tìm trực tiếp trong shadowRoot của view-publication
                            var shadowElements = shadowRoot.querySelectorAll('[data-article]');
                            for (var m = 0; m < shadowElements.length; m++) {
                                var el = shadowElements[m];
                                var dataArticle = el.getAttribute('data-article') || '';
                                var dataExternalId = el.getAttribute('data-external_id') || '';
                                var ariaLabel = el.getAttribute('aria-label') || '';
                                var lang = el.getAttribute('lang') || '';
                                var tagName = el.tagName || '';
                                var className = el.className || '';
                                
                                result.push({
                                    data_article: dataArticle,
                                    data_external_id: dataExternalId,
                                    aria_label: ariaLabel,
                                    lang: lang,
                                    tag_name: tagName,
                                    class_name: className
                                });
                            }
                        }
                    }
                    
                    return result;
                """)
                
                if articles:
                    print(f"   📊 Found {len(articles)} article(s) with data-article on page {page_num}:")
                    for idx, article in enumerate(articles):
                        print(f"      Article {idx + 1}:")
                        print(f"         - data-article: '{article.get('data_article', '')}'")
                        print(f"         - data-external_id: '{article.get('data_external_id', '')}'")
                        print(f"         - aria-label: '{article.get('aria_label', '')}'")
                        print(f"         - lang: '{article.get('lang', '')}'")
                        print(f"         - tag: '{article.get('tag_name', '')}'")
                    
                    # Thêm page number, magazine_id và URL vào mỗi article và lưu vào list
                    for article in articles:
                        article['page_number'] = page_num
                        article['magazine_id'] = magazine_id
                        article['url'] = sb.get_current_url()
                    return articles
                else:
                    print("   ⚠️  No articles found with data-article attribute")
                    return []
            
            # Page 1: Extract articles từ page đầu tiên
            page_count = 1
            print(f"\n📄 Processing page {page_count}...")
            articles_page1 = extract_articles_from_current_page(page_count)
            if articles_page1:
                all_articles.extend(articles_page1)
            
            # Click Next button 1 lần
            print("\n🔍 Looking for 'Next' button...")
            next_clicked = sb.execute_script("""
                // Tìm book-navigation trong shadow DOM của view-publication
                var viewPublications = document.querySelectorAll('view-publication');
                for (var i = 0; i < viewPublications.length; i++) {
                    if (viewPublications[i].shadowRoot) {
                        var bookNav = viewPublications[i].shadowRoot.querySelector('book-navigation');
                        if (bookNav && bookNav.shadowRoot) {
                            var buttons = bookNav.shadowRoot.querySelectorAll('button, [role="button"]');
                            
                            for (var j = 0; j < buttons.length; j++) {
                                var btn = buttons[j];
                                var ariaLabel = (btn.getAttribute('aria-label') || '').trim();
                                var dataType = (btn.getAttribute('data-type') || '').trim();
                                var disabled = btn.hasAttribute('disabled');
                                
                                // Tìm button "Næste side" với data-type="next" và không bị disabled
                                if (dataType === 'next' && !disabled && ariaLabel.toLowerCase().includes('næste side')) {
                                    btn.click();
                                    return {success: true, method: 'book-navigation', ariaLabel: ariaLabel};
                                }
                            }
                        }
                    }
                }
                return {success: false, message: 'Could not find Next button'};
            """)
            
            if not next_clicked or not next_clicked.get('success'):
                print("⚠️  Could not find 'Next' button - only page 1 will be processed")
            else:
                print(f"✅ Clicked 'Next' button, waiting for page to load...")
                sb.sleep(3)  # Wait for navigation
                
                # Page 2: Extract articles từ page sau khi click Next
                page_count = 2
                print(f"\n📄 Processing page {page_count}...")
                articles_page2 = extract_articles_from_current_page(page_count)
                if articles_page2:
                    all_articles.extend(articles_page2)
                
                # Kiểm tra xem URL có thay đổi không (để xác nhận đã chuyển page)
                new_url = sb.get_current_url()
                print(f"   Current URL: {new_url}")
            
            # Tổng kết
            print(f"\n✅ Crawling completed!")
            print(f"   Total pages processed: {page_count}")
            print(f"   Total articles found: {len(all_articles)}")
            
            return all_articles
            
        except Exception as e:
            print(f"❌ Error during crawling: {e}")
            import traceback
            traceback.print_exc()
            
            # In ra thông tin để debug
            try:
                print(f"\n📄 Current URL: {sb.get_current_url()}")
                print(f"📄 Page title: {sb.get_title()}")
            except:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Crawl magazine from e-pages.pub')
    parser.add_argument('--no-headless', action='store_true', help='Run browser in visible mode (for debugging)')
    parser.add_argument('--max-pages', type=int, default=None, help='Maximum number of pages to crawl per magazine (default: unlimited)')
    parser.add_argument('--magazine-start', type=int, default=7, help='Start magazine ID (default: 7)')
    parser.add_argument('--magazine-end', type=int, default=164, help='End magazine ID (default: 164)')
    parser.add_argument('--magazine-id', type=int, default=None, help='Crawl single magazine ID (overrides start/end)')
    parser.add_argument('--output', type=str, default='magazine_articles.csv', help='Output CSV file (default: magazine_articles.csv)')
    parser.add_argument('--no-resume', action='store_true', help='Disable resume mode (crawl all magazines even if already crawled)')
    parser.add_argument('--force', action='store_true', help='Force re-crawl all magazines (ignore existing data)')
    
    args = parser.parse_args()
    
    headless = not args.no_headless
    output_file = args.output
    
    # Resume mode là mặc định (trừ khi có --no-resume hoặc --force)
    resume_mode = not args.no_resume and not args.force
    
    # Kiểm tra progress nếu có resume mode (mặc định là True)
    crawled_magazines = set()
    if resume_mode and os.path.exists(output_file):
        crawled_magazines = get_crawled_magazines(output_file)
        if crawled_magazines:
            print(f"📊 Found {len(crawled_magazines)} already crawled magazine(s): {sorted(crawled_magazines)}")
            print(f"   Will skip these magazines and continue from where we left off")
        else:
            print(f"📊 No previously crawled magazines found in {output_file}")
    elif args.force:
        print(f"🔄 Force mode: Will re-crawl all magazines")
    elif args.no_resume:
        print(f"🔄 Resume mode disabled: Will crawl all magazines")
    
    # Remove existing output file nếu force mode
    if args.force and args.magazine_id is None:
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"🗑️  Removed existing {output_file} (force mode)")
            crawled_magazines = set()
    
    all_collected_articles = []
    
    if args.magazine_id:
        # Crawl single magazine
        print(f"📚 Crawling single magazine: {args.magazine_id}")
        articles = crawl_magazine(args.magazine_id, headless=headless, max_pages=args.max_pages)
        if articles:
            all_collected_articles.extend(articles)
            save_articles_to_csv(articles, output_file)
    else:
        # Crawl multiple magazines
        magazine_start = args.magazine_start
        magazine_end = args.magazine_end
        
        print(f"📚 Crawling magazines from {magazine_start} to {magazine_end}")
        
        skipped_count = 0
        for magazine_id in range(magazine_start, magazine_end + 1):
            # Skip nếu đã crawl và có resume mode (mặc định)
            if resume_mode and magazine_id in crawled_magazines:
                print(f"⏭️  Skipping magazine #{magazine_id} (already crawled)")
                skipped_count += 1
                continue
            
            try:
                articles = crawl_magazine(magazine_id, headless=headless, max_pages=args.max_pages)
                if articles:
                    all_collected_articles.extend(articles)
                    # Save sau mỗi magazine để không mất dữ liệu nếu có lỗi
                    save_articles_to_csv(articles, output_file)
                else:
                    print(f"⚠️  No articles found in magazine #{magazine_id}")
                
                # Đợi một chút giữa các magazines
                time.sleep(2)
            except Exception as e:
                print(f"❌ Error crawling magazine #{magazine_id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if skipped_count > 0:
            print(f"\n⏭️  Skipped {skipped_count} already crawled magazine(s)")
    
    # Tổng kết cuối cùng
    if all_collected_articles:
        # Drop duplicate một lần nữa để đảm bảo
        seen = OrderedDict()
        for article in all_collected_articles:
            data_article = article.get('data_article', '')
            if data_article and data_article not in seen:
                seen[data_article] = article
        
        unique_count = len(seen)
        total_count = len(all_collected_articles)
        
        print(f"\n{'='*60}")
        print(f"📋 FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"   Total articles collected: {total_count}")
        print(f"   Unique articles (after deduplication): {unique_count}")
        print(f"   Duplicates removed: {total_count - unique_count}")
        print(f"   Output file: {output_file}")
        print(f"{'='*60}")
    else:
        print("\n⚠️  No articles collected")

