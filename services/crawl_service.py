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
    
    def __init__(self, base_url='https://www.sermitsiaq.ag'):
        self.base_url = base_url
    
    def crawl_section(self, section_url, section_name='erhverv', max_articles=50, scroll_pause=2, headless=True):
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
                    articles = parse_articles_from_html(html_content, self.base_url)
                    
                    if len(articles) >= max_articles:
                        break
                    
                    scroll_count += 1
                    print(f"  Scroll {scroll_count}: Found {len(articles)} articles")
                
                # Get final HTML
                html_content = sb.get_page_source()
                articles = parse_articles_from_html(html_content, self.base_url)
            
            # Limit to max_articles
            articles = articles[:max_articles]
            articles_crawled = len(articles)
            
            print(f"✅ Crawled {articles_crawled} articles")
            
            # Save to database
            print("💾 Saving articles to database...")
            for idx, article_data in enumerate(articles):
                try:
                    # QUAN TRỌNG: Override section từ article_data với section_name đang crawl
                    # Vì parser có thể lấy section từ HTML (có thể không đúng)
                    article_data['section'] = section_name
                    
                    # Dùng ID (primary key) làm unique identifier
                    # Mỗi lần crawl sẽ tạo articles mới với ID mới
                    # Cho phép cùng element_guid xuất hiện ở nhiều sections với ID khác nhau
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
                    )
                    db.session.add(new_article)
                    articles_created += 1
                    
                    # Commit mỗi 10 articles để tránh timeout
                    if articles_created % 10 == 0:
                        db.session.commit()
                        print(f"  💾 Saved {articles_created} articles...")
                
                except Exception as e:
                    error_msg = f"Error saving article {article_data.get('element_guid', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ⚠️  {error_msg}")
                    continue
            
            # Final commit
            db.session.commit()
            
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

