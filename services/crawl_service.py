"""
Crawl service sử dụng SeleniumBase để crawl articles từ sermitsiaq.ag
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from seleniumbase import SB
from services.article_parser import parse_articles_from_html
from database import Article, CrawlLog, db
from datetime import datetime
import time


class SermitsiaqCrawler:
    """Crawler cho sermitsiaq.ag"""
    
    def __init__(self, base_url='https://www.sermitsiaq.ag', language='da'):
        """
        Initialize crawler
        
        Args:
            base_url: Base URL của website (default: https://www.sermitsiaq.ag)
            language: Language code ('da' for Danish, 'kl' for Greenlandic)
        """
        self.base_url = base_url
        self.language = language
    
    def crawl_section(self, section_url, section_name='erhverv', max_articles=50, scroll_pause=2, headless=True, language=None):
        """
        Crawl articles từ một section
        
        Args:
            section_url: URL của section (ví dụ: https://www.sermitsiaq.ag/tag/erhverv)
            section_name: Tên section (erhverv, samfund, kultur, sport, job)
            max_articles: Số lượng articles tối đa cần crawl
            scroll_pause: Thời gian chờ giữa các lần scroll (giây)
        
        Returns:
            dict: Kết quả crawl
        """
        crawl_log = CrawlLog(
            crawl_type='section',
            section=section_name,
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(crawl_log)
        db.session.commit()
        
        articles_crawled = 0
        articles_created = 0
        errors = []
        
        try:
            print(f"📰 Crawling section: {section_name}")
            print(f"🔗 URL: {section_url}")
            
            # Sử dụng SeleniumBase với context manager
            with SB(uc=True, headless=headless) as sb:
                # Navigate to section page
                sb.open(section_url)
                time.sleep(3)  # Wait for page load
                
                # Scroll để load thêm articles (lazy loading)
                print("📜 Scrolling to load articles...")
                scroll_count = 0
                max_scrolls = 10  # Tối đa scroll 10 lần
                
                while scroll_count < max_scrolls and articles_crawled < max_articles:
                    # Scroll down
                    sb.scroll_to_bottom()
                    time.sleep(scroll_pause)
                    
                    # Get current page HTML
                    html_content = sb.get_page_source()
                    articles = parse_articles_from_html(html_content, self.base_url, is_home=False)
                    
                    if len(articles) >= max_articles:
                        break
                    
                    scroll_count += 1
                    print(f"  Scroll {scroll_count}: Found {len(articles)} articles")
                
                # Get final HTML
                html_content = sb.get_page_source()
                articles = parse_articles_from_html(html_content, self.base_url, is_home=False)
            
            # Limit to max_articles
            articles = articles[:max_articles]
            articles_crawled = len(articles)
            
            print(f"✅ Crawled {articles_crawled} articles")
            
            # QUAN TRỌNG: Xóa articles cũ của section CÙNG LANGUAGE trước khi lưu articles mới
            # Determine language from base_url or parameter
            article_language = language or self.language
            print(f"🗑️  Removing old {article_language} articles from section '{section_name}'...")
            old_articles_count = Article.query.filter_by(
                section=section_name,
                language=article_language
            ).count()
            if old_articles_count > 0:
                deleted_count = Article.query.filter_by(
                    section=section_name,
                    language=article_language
                ).delete()
                db.session.commit()
                print(f"   ✅ Deleted {deleted_count} old {article_language} articles")
            else:
                print(f"   ℹ️  No old {article_language} articles to delete")
            
            # Save new articles to database
            print("💾 Saving new articles to database...")
            for idx, article_data in enumerate(articles):
                try:
                    # QUAN TRỌNG: Override section từ article_data với section_name đang crawl
                    # Vì parser có thể lấy section từ HTML (có thể không đúng)
                    article_data['section'] = section_name
                    
                    # Determine language from base_url or parameter
                    article_language = language or self.language
                    
                    # Tạo article mới với ID mới
                    new_article = Article(
                        element_guid=article_data.get('element_guid'),  # Có thể None, không unique
                        title=article_data['title'],
                        slug=article_data['slug'],
                        published_url=article_data['url'],
                        k5a_url=article_data['k5a_url'],
                        section=section_name,
                        site_alias=article_data.get('site_alias', 'sermitsiaq'),
                        instance=article_data.get('instance', ''),
                        published_date=article_data.get('published_date'),
                        is_paywall=article_data['is_paywall'],
                        paywall_class=article_data['paywall_class'],
                        image_data=article_data.get('image_data', {}),
                        display_order=idx,  # Set display_order để match pattern
                        language=article_language,  # Set language
                        original_language=article_language,  # Set original_language
                    )
                    db.session.add(new_article)
                    articles_created += 1
                    
                    # Commit mỗi 10 articles để tránh timeout
                    if articles_created % 10 == 0:
                        db.session.commit()
                        print(f"  💾 Saved {articles_created}/{articles_crawled} articles...")
                
                except Exception as e:
                    error_msg = f"Error saving article {article_data.get('element_guid', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ⚠️  {error_msg}")
                    continue
            
            # Final commit
            db.session.commit()
            print(f"✅ Successfully saved {articles_created} new articles (replaced {old_articles_count} old articles)")
            
            # Update crawl log
            crawl_log.status = 'success' if not errors else 'partial'
            crawl_log.articles_crawled = articles_crawled
            crawl_log.articles_created = articles_created
            crawl_log.articles_updated = 0  # Không còn update, chỉ create mới với ID mới
            crawl_log.completed_at = datetime.utcnow()
            if errors:
                crawl_log.errors = '\n'.join(errors[:10])  # Limit to first 10 errors
            db.session.commit()
            
            print(f"✅ Crawl completed!")
            print(f"   📊 Articles crawled: {articles_crawled}")
            print(f"   ➕ Articles created: {articles_created} (with new IDs)")
            if errors:
                print(f"   ⚠️  Errors: {len(errors)}")
            
            return {
                'success': True,
                'articles_crawled': articles_crawled,
                'articles_created': articles_created,
                'articles_updated': 0,
                'errors': errors
            }
        
        except Exception as e:
            error_msg = f"Crawl failed: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
            
            # Update crawl log
            crawl_log.status = 'failed'
            crawl_log.errors = '\n'.join(errors)
            crawl_log.completed_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': False,
                'articles_crawled': articles_crawled,
                'articles_created': articles_created,
                'articles_updated': 0,
                'errors': errors
            }
    
    def crawl_home(self, home_url=None, max_articles=100, scroll_pause=2, headless=True, language=None):
        """
        Crawl articles từ trang home
        
        Args:
            home_url: URL của trang home
            max_articles: Số lượng articles tối đa cần crawl
            scroll_pause: Thời gian chờ giữa các lần scroll (giây)
            headless: Chạy browser ở chế độ headless
        
        Returns:
            dict: Kết quả crawl
        """
        crawl_log = CrawlLog(
            crawl_type='home',
            section='home',
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(crawl_log)
        db.session.commit()
        
        articles_crawled = 0
        articles_created = 0
        errors = []
        
        try:
            print(f"🏠 Crawling home page: {home_url}")
            
            # Sử dụng SeleniumBase với context manager
            with SB(uc=True, headless=headless) as sb:
                # Navigate to home page
                sb.open(home_url)
                time.sleep(3)  # Wait for page load
                
                # Scroll để load thêm articles (lazy loading)
                print("📜 Scrolling to load articles...")
                scroll_count = 0
                # Tăng max_scrolls nếu crawl all (max_articles=0)
                max_scrolls = 100 if max_articles == 0 else 50  # Tăng số lần scroll để load tất cả articles
                previous_count = 0
                no_new_articles_count = 0
                
                # Crawl tất cả articles nếu max_articles = 0 hoặc rất lớn
                crawl_all = max_articles == 0 or max_articles >= 1000
                
                while scroll_count < max_scrolls:
                    # Scroll down
                    sb.scroll_to_bottom()
                    time.sleep(scroll_pause)
                    
                    # Get current page HTML
                    html_content = sb.get_page_source()
                    articles = parse_articles_from_html(html_content, self.base_url, is_home=True)
                    current_count = len(articles)
                    
                    # Kiểm tra xem có articles mới không
                    if current_count == previous_count:
                        no_new_articles_count += 1
                        # Nếu 3 lần scroll liên tiếp không có articles mới, dừng lại
                        if no_new_articles_count >= 3:
                            print(f"  ⏹️  No new articles found after {no_new_articles_count} scrolls. Stopping.")
                            break
                    else:
                        no_new_articles_count = 0
                    
                    previous_count = current_count
                    scroll_count += 1
                    print(f"  Scroll {scroll_count}: Found {current_count} articles")
                    
                    # Nếu không crawl all và đã đủ số lượng, dừng lại
                    if not crawl_all and current_count >= max_articles:
                        print(f"  ✅ Reached max articles limit ({max_articles})")
                        break
                
                # Get final HTML
                html_content = sb.get_page_source()
                articles = parse_articles_from_html(html_content, self.base_url, is_home=True)
            
            # Limit to max_articles nếu không crawl all
            if not crawl_all and max_articles > 0:
                articles = articles[:max_articles]
            articles_crawled = len(articles)
            
            print(f"✅ Crawled {articles_crawled} articles from home page")
            
            # QUAN TRỌNG: Xóa articles cũ của home CÙNG LANGUAGE trước khi lưu articles mới
            # Determine language from base_url or parameter
            article_language = language or self.language
            print(f"🗑️  Removing old {article_language} articles from home...")
            old_articles_count = Article.query.filter_by(
                section='home', 
                is_home=True,
                language=article_language
            ).count()
            if old_articles_count > 0:
                deleted_count = Article.query.filter_by(
                    section='home', 
                    is_home=True,
                    language=article_language
                ).delete()
                db.session.commit()
                print(f"   ✅ Deleted {deleted_count} old {article_language} home articles")
            else:
                print(f"   ℹ️  No old {article_language} home articles to delete")
            
            # Save new articles to database
            print("💾 Saving new home articles to database...")
            for idx, article_data in enumerate(articles):
                try:
                    # Set section='home' và is_home=True
                    article_data['section'] = 'home'
                    
                    # Sử dụng display_order từ parser nếu có, nếu không thì dùng idx
                    display_order = article_data.get('display_order', idx)
                    
                    # Determine language from base_url or parameter
                    article_language = language or self.language
                    
                    # Tạo article mới với ID mới
                    new_article = Article(
                        element_guid=article_data.get('element_guid'),
                        title=article_data.get('title', 'Untitled'),  # Slider có thể không có title
                        slug=article_data.get('slug', ''),
                        published_url=article_data.get('url', ''),
                        k5a_url=article_data.get('k5a_url', ''),
                        language=article_language,  # Set language
                        original_language=article_language,  # Set original_language
                        section='home',  # Section = 'home'
                        site_alias=article_data.get('site_alias', 'sermitsiaq'),
                        instance=article_data.get('instance', ''),
                        published_date=article_data.get('published_date'),
                        is_paywall=article_data.get('is_paywall', False),
                        paywall_class=article_data.get('paywall_class', ''),
                        image_data=article_data.get('image_data', {}),
                        display_order=display_order,  # Sử dụng display_order từ parser
                        is_home=True,  # Đánh dấu thuộc home
                        layout_type=article_data.get('layout_type'),  # Layout type từ parser
                        layout_data=article_data.get('layout_data', {}),  # Layout data nếu có
                        grid_size=article_data.get('grid_size', 6),  # Grid size từ HTML (5, 6, 7, 8, etc.)
                    )
                    db.session.add(new_article)
                    articles_created += 1
                    
                    # Debug: Log slider info
                    if article_data.get('layout_type') == 'slider':
                        layout_data = article_data.get('layout_data', {})
                        slider_articles = layout_data.get('slider_articles', [])
                        slider_title = layout_data.get('slider_title', 'Untitled')
                        print(f"  🎠 Saving slider '{slider_title}': {len(slider_articles)} articles")
                        if len(slider_articles) < 4:
                            print(f"     ⚠️  WARNING: Slider has only {len(slider_articles)} articles")
                    
                    # Commit mỗi 10 articles để tránh timeout
                    if articles_created % 10 == 0:
                        db.session.commit()
                        print(f"  💾 Saved {articles_created}/{articles_crawled} articles...")
                
                except Exception as e:
                    error_msg = f"Error saving article {article_data.get('element_guid', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ⚠️  {error_msg}")
                    continue
            
            # Final commit
            db.session.commit()
            print(f"✅ Successfully saved {articles_created} new home articles (replaced {old_articles_count} old articles)")
            
            # Update crawl log
            crawl_log.status = 'success' if not errors else 'partial'
            crawl_log.articles_crawled = articles_crawled
            crawl_log.articles_created = articles_created
            crawl_log.articles_updated = 0
            crawl_log.completed_at = datetime.utcnow()
            if errors:
                crawl_log.errors = '\n'.join(errors[:10])
            db.session.commit()
            
            print(f"✅ Home crawl completed!")
            print(f"   📊 Articles crawled: {articles_crawled}")
            print(f"   ➕ Articles created: {articles_created}")
            if errors:
                print(f"   ⚠️  Errors: {len(errors)}")
            
            return {
                'success': True,
                'articles_crawled': articles_crawled,
                'articles_created': articles_created,
                'articles_updated': 0,
                'errors': errors
            }
        
        except Exception as e:
            error_msg = f"Home crawl failed: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
            
            # Update crawl log
            crawl_log.status = 'failed'
            crawl_log.errors = '\n'.join(errors)
            crawl_log.completed_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': False,
                'articles_crawled': articles_crawled,
                'articles_created': articles_created,
                'articles_updated': 0,
                'errors': errors
            }


def crawl_erhverv_section(headless=True, max_articles=50):
    """
    Helper function để crawl section erhverv
    
    Args:
        headless: Chạy browser ở chế độ headless
        max_articles: Số lượng articles tối đa
    
    Returns:
        dict: Kết quả crawl
    """
    crawler = SermitsiaqCrawler()
    result = crawler.crawl_section(
        section_url='https://www.sermitsiaq.ag/tag/erhverv',
        section_name='erhverv',
        max_articles=max_articles,
        headless=headless
    )
    return result


if __name__ == '__main__':
    # Test crawl
    from app import app
    
    with app.app_context():
        result = crawl_erhverv_section(headless=True, max_articles=50)
        print("\n📊 Final Result:")
        print(result)

