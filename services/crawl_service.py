"""
Crawl service sử dụng SeleniumBase để crawl articles từ sermitsiaq.ag
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from seleniumbase import SB
from services.article_parser import parse_articles_from_html
from services.image_downloader import download_and_update_image_data
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
            section_name: Tên section (erhverv, samfund, kultur, sport, podcasti)
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
                max_scrolls = 3  # Tối đa scroll 3 lần
                previous_count = 0
                no_new_articles_count = 0
                
                while scroll_count < max_scrolls and (max_articles == 0 or articles_crawled < max_articles):
                    # Scroll down
                    sb.scroll_to_bottom()
                    time.sleep(scroll_pause)
                    
                    # Get current page HTML
                    html_content = sb.get_page_source()
                    articles = parse_articles_from_html(html_content, self.base_url, is_home=False)
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
                    
                    if max_articles > 0 and current_count >= max_articles:
                        break
                
                # Get final HTML
                html_content = sb.get_page_source()
                articles = parse_articles_from_html(html_content, self.base_url, is_home=False)
                print(f"🔍 After parsing: {len(articles)} articles")
            
            # Limit to max_articles (0 = no limit, crawl all)
            if max_articles > 0:
                articles = articles[:max_articles]
                print(f"🔍 After limiting to {max_articles}: {len(articles)} articles")
            articles_crawled = len(articles)
            
            print(f"✅ Crawled {articles_crawled} articles")
            
            # Determine language from base_url or parameter
            article_language = language or self.language
            
            # Check existing articles to avoid duplicates
            # ⚠️ QUAN TRỌNG: Với section crawl, CHỈ check trong section đó
            # (khác với home crawl - home cần check ALL vì có articles từ nhiều sections)
            print(f"🔍 Checking for existing {article_language} articles in section '{section_name}'...")
            existing_urls = {}  # Dict: {published_url: Article object}
            
            # ⚠️ CRITICAL: Refresh database session để tránh lấy cached data cũ
            db.session.expire_all()
            
            # CHỈ check articles trong section này
            existing_articles = Article.query.filter_by(
                section=section_name,
                language=article_language
            ).all()
            for art in existing_articles:
                if art.published_url:
                    existing_urls[art.published_url] = art
            print(f"   Found {len(existing_urls)} existing articles in section '{section_name}'")
            
            # Save new articles to database (only if not exists)
            print("💾 Saving new articles to database...")
            articles_skipped = 0
            for idx, article_data in enumerate(articles):
                try:
                    # QUAN TRỌNG: Override section từ article_data với section_name đang crawl
                    # Vì parser có thể lấy section từ HTML (có thể không đúng)
                    article_data['section'] = section_name
                    
                    # Determine language from base_url or parameter
                    article_language = language or self.language
                    
                    # Check if article already exists (by published_url)
                    article_url = article_data.get('url', '')
                    if article_url in existing_urls:
                        articles_skipped += 1
                        if articles_skipped % 10 == 0:
                            print(f"  ⏭️  Skipped {articles_skipped} existing articles...")
                        continue
                    
                    # Download và cập nhật image_data nếu có
                    image_data = article_data.get('image_data', {})
                    if image_data:
                        try:
                            print(f"  📥 Downloading header image for article: {article_data.get('title', '')[:50]}...")
                            image_data = download_and_update_image_data(
                                image_data,
                                base_url='https://www.sermitsiaq.com',
                                download_all_formats=False  # Chỉ download desktop_webp và fallback
                            )
                        except Exception as e:
                            print(f"  ⚠️  Error downloading image: {e}")
                            # Giữ nguyên image_data gốc nếu lỗi
                    
                    # Tạo article mới
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
                        image_data=image_data,  # Đã được download và cập nhật
                        display_order=idx,  # Set display_order để match pattern
                        language=article_language,  # Set language
                        original_language=article_language,  # Set original_language
                    )
                    db.session.add(new_article)
                    
                    # ⚠️ CRITICAL: Wrap commit trong try-except để catch IntegrityError (race condition)
                    try:
                        # Commit mỗi 10 articles để tránh timeout
                        if (articles_created + 1) % 10 == 0:
                            db.session.commit()
                            print(f"  💾 Saved {articles_created + 1} new articles, skipped {articles_skipped} existing...")
                        
                        articles_created += 1
                        if article_url:
                            existing_urls[article_url] = new_article  # Add to dict to avoid duplicates in same batch
                    except Exception as commit_error:
                        # IntegrityError hoặc unique constraint violation (race condition)
                        db.session.rollback()
                        error_msg_str = str(commit_error)
                        if 'unique' in error_msg_str.lower() or 'duplicate' in error_msg_str.lower():
                            print(f"  ⏭️  Article already exists (duplicate detected during commit), skipping...")
                            articles_skipped += 1
                            if article_url:
                                existing_urls[article_url] = None  # Mark as processed
                        else:
                            # Re-raise nếu không phải duplicate error
                            raise
                
                except Exception as e:
                    error_msg = f"Error saving article {article_data.get('element_guid', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ⚠️  {error_msg}")
                    db.session.rollback()
                    continue
            
            # Final commit
            db.session.commit()
            print(f"✅ Successfully saved {articles_created} new articles, skipped {articles_skipped} existing articles")
            
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
        articles_updated = 0
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
            
            # Log thông tin về rows nếu có
            if articles:
                row_info = {}
                for article_data in articles:
                    row_idx = article_data.get('row_index', -1)
                    if row_idx >= 0:
                        if row_idx not in row_info:
                            row_info[row_idx] = []
                        row_info[row_idx].append({
                            'title': article_data.get('title', 'N/A')[:40],
                            'layout_type': article_data.get('layout_type', 'N/A'),
                            'display_order': article_data.get('display_order', 0)
                        })
                
                print(f"📐 Home page structure summary:")
                print(f"   Total rows: {articles[0].get('total_rows', 'N/A') if articles else 'N/A'}")
                for row_idx in sorted(row_info.keys()):
                    articles_in_row = row_info[row_idx]
                    print(f"   Row {row_idx + 1}: {len(articles_in_row)} items - {[a['layout_type'] for a in articles_in_row]}")
            
            # Determine language from base_url or parameter
            article_language = language or self.language
            
            # Check existing articles trước khi crawl để biết articles nào đã tồn tại
            print(f"🔍 Checking for existing {article_language} articles...")
            
            # ⚠️ CRITICAL: Refresh database session để tránh lấy cached data cũ
            db.session.expire_all()
            
            existing_articles_map = {}  # Dict: {published_url: Article} hoặc {(layout_type, display_order): Article} cho sliders
            
            # ⚠️ CRITICAL: Check TẤT CẢ articles theo published_url + language
            # KHÔNG filter theo section vì articles từ các sections khác có thể xuất hiện trên home
            # (ví dụ: erhverv articles trên home page)
            existing_articles = Article.query.filter_by(
                language=article_language
            ).all()
            
            for art in existing_articles:
                if art.published_url:
                    existing_articles_map[art.published_url] = art
                elif art.layout_type in ['slider', 'job_slider']:
                    # Slider containers: key bằng (layout_type, display_order)
                    # Chỉ lưu sliders có section='home'
                    if art.section == 'home':
                        key = (art.layout_type, art.display_order)
                        existing_articles_map[key] = art
            
            print(f"   Found {len(existing_articles_map)} existing {article_language} articles (all sections)")
            
            # Save new articles to database (update sẽ làm sau)
            print("💾 Saving new home articles...")
            articles_skipped = 0
            articles_updated = 0
            articles_not_found_in_home = 0  # Track articles không tìm thấy trong home
            updated_article_ids = set()  # Track IDs đã được update để tránh đếm trùng
            skipped_articles_info = []  # Track thông tin articles bị skip để debug
            articles_to_update = []  # Track articles cần update sau khi save xong
            existing_urls = {}  # Dict: {published_url: Article} - Track URLs trong batch này để tránh duplicate
            for idx, article_data in enumerate(articles):
                try:
                    # ⚠️ KHÔNG set section='home' hardcoded ở đây
                    # Section sẽ được detect từ URL cho các layout types: 1_full, 1_article, 2_articles, 3_articles, 1_special_bg
                    # (xem logic ở dòng 690-711)
                    
                    # Sử dụng display_order từ parser nếu có, nếu không thì dùng idx
                    display_order = article_data.get('display_order', idx)
                    
                    # Check if article already exists (by published_url, section='home', is_home=True, language)
                    article_url = article_data.get('url', '')
                    layout_type = article_data.get('layout_type', '')
                    
                    # Slider containers (slider, job_slider, 5_articles) không có URL nhưng vẫn cần được lưu để giữ cấu trúc home page
                    # Sử dụng element_guid hoặc display_order để identify
                    # ⚠️ QUAN TRỌNG: 5_articles giờ là container (không tạo individual articles), giống slider và job_slider
                    is_slider_container = layout_type in ['slider', 'job_slider', '5_articles'] and not article_url
                    
                    if not article_url and not is_slider_container:
                        # Không có URL và không phải slider container, skip
                        skip_info = {
                            'layout_type': layout_type,
                            'display_order': display_order,
                            'title': article_data.get('title', 'N/A')[:50],
                            'url': article_url or '(no URL)',
                            'reason': 'no_url_not_slider'
                        }
                        skipped_articles_info.append(skip_info)
                        print(f"  ⚠️  Skipping article without URL (not a slider): layout_type={layout_type}, display_order={display_order}, title={skip_info['title']}, url={skip_info['url']}")
                        articles_skipped += 1
                        continue
                    
                    # Với slider containers, sử dụng element_guid hoặc display_order làm identifier
                    if is_slider_container:
                        # TẠM BỎ QUA: Update logic - luôn tạo mới slider container
                        # Tạo một identifier duy nhất cho slider container
                        element_guid = article_data.get('element_guid', '')
                        slider_id = article_data.get('layout_data', {}).get('slider_id', '')
                        slider_title = article_data.get('layout_data', {}).get('slider_title', 'Untitled')
                        # Sử dụng element_guid hoặc slider_id làm identifier
                        article_identifier = element_guid or slider_id or f"slider_{display_order}"
                        # TẠM BỎ QUA: Check existing slider container - luôn tạo mới
                        # existing_slider = Article.query.filter_by(
                        #     section='home',
                        #     is_home=True,
                        #     language=article_language,
                        #     layout_type=layout_type,
                        #     display_order=display_order
                        # ).first()
                        # 
                        # if existing_slider:
                        #     # Update existing slider container
                        #     existing_slider.display_order = display_order
                        #     existing_slider.layout_type = layout_type
                        #     layout_data = article_data.get('layout_data', {})
                        #     layout_data['row_index'] = article_data.get('row_index', -1)
                        #     layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                        #     layout_data['total_rows'] = article_data.get('total_rows', 0)
                        #     existing_slider.layout_data = layout_data
                        #     existing_slider.grid_size = article_data.get('grid_size', 6)
                        #     existing_slider.is_home = True
                        #     existing_slider.section = 'home'
                        #     
                        #     if existing_slider.id not in updated_article_ids:
                        #         updated_article_ids.add(existing_slider.id)
                        #         articles_updated += 1
                        #         print(f"  🔄 Updated slider container: {layout_type} '{slider_title}' (display_order={display_order})")
                        #     
                        #     # Không đếm vào articles_skipped vì đã được update
                        #     continue
                        # Nếu không tìm thấy, sẽ tạo mới ở dưới (với published_url='')
                        print(f"  ➕ Will create new slider container: {layout_type} '{slider_title}' (display_order={display_order})")
                        article_url = ''  # Giữ empty để không match với existing_urls
                        # Note: Slider containers sẽ được tạo mới ở phần tạo article bên dưới
                    
                    # TẠM BỎ QUA: Tất cả logic update - luôn tạo mới article (chỉ cho home)
                    # if article_url in existing_urls:
                    # Bỏ qua tất cả check existing article, luôn tạo mới
                    # if article_url:  # Chỉ check nếu có URL
                    #     # QUAN TRỌNG: Chỉ check duplicate trong phạm vi home page (section='home', is_home=True)
                    #     existing_article = Article.query.filter_by(
                    #         published_url=article_url,
                    #         language=article_language,
                    #         section='home',
                    #         is_home=True  # QUAN TRỌNG: Chỉ check với is_home=True
                    #     ).first()
                    #     
                    #     if existing_article:
                    #         # Verify điều kiện trước khi update
                    #         if existing_article.section != 'home' or not existing_article.is_home:
                    #             skip_info = {
                    #                 'layout_type': layout_type,
                    #                 'display_order': display_order,
                    #                 'title': article_data.get('title', 'N/A')[:50],
                    #                 'url': article_url,
                    #                 'reason': f'section_mismatch (section={existing_article.section}, is_home={existing_article.is_home})'
                    #             }
                    #             skipped_articles_info.append(skip_info)
                    #             print(f"  ⚠️  WARNING: Found article ID {existing_article.id} but section={existing_article.section}, is_home={existing_article.is_home}. Skipping update. URL: {article_url}")
                    #             articles_skipped += 1
                    #             continue
                    #         
                    #         # Article đã tồn tại trong home: update display_order, layout_type, layout_data để giữ đúng thứ tự
                    #         existing_article.display_order = display_order
                    #         existing_article.layout_type = article_data.get('layout_type')
                    #         
                    #         # Merge layout_data với thông tin row
                    #         layout_data = article_data.get('layout_data', {})
                    #         layout_data['row_index'] = article_data.get('row_index', -1)
                    #         layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                    #         layout_data['total_rows'] = article_data.get('total_rows', 0)
                    #         existing_article.layout_data = layout_data
                    #         
                    #         existing_article.grid_size = article_data.get('grid_size', 6)
                    #         # Đảm bảo is_home=True và section='home'
                    #         existing_article.is_home = True
                    #         existing_article.section = 'home'
                    #         
                    #         # Chỉ đếm nếu chưa được update trước đó
                    #         if existing_article.id not in updated_article_ids:
                    #             updated_article_ids.add(existing_article.id)
                    #             articles_updated += 1
                    #         
                    #         # Không đếm vào articles_skipped vì đã được update
                    #         if articles_updated % 10 == 0:
                    #             print(f"  🔄 Updated display_order for {articles_updated} existing home articles...")
                    #         continue
                    #     else:
                    #         # Có trong existing_urls nhưng không tìm thấy với điều kiện đầy đủ
                    #         # Có thể là article từ section page, không phải home
                    #         # Hoặc có thể có vấn đề với URL format
                    #         # Tìm article ở section khác và update để thêm vào home
                    #         all_articles_with_url = Article.query.filter_by(
                    #             published_url=article_url,
                    #             language=article_language
                    #         ).all()
                    #         
                    #         if all_articles_with_url:
                    #             # Tìm article đầu tiên (có thể có nhiều bản copy)
                    #             article_to_update = all_articles_with_url[0]
                    #             
                    #             # Update article này để thêm vào home page
                    #             if article_to_update.id not in updated_article_ids:
                    #                 article_to_update.display_order = display_order
                    #                 article_to_update.layout_type = article_data.get('layout_type')
                    #                 layout_data = article_data.get('layout_data', {})
                    #                 layout_data['row_index'] = article_data.get('row_index', -1)
                    #                 layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                    #                 layout_data['total_rows'] = article_data.get('total_rows', 0)
                    #                 article_to_update.layout_data = layout_data
                    #                 article_to_update.grid_size = article_data.get('grid_size', 6)
                    #                 # Đảm bảo is_home=True và section='home'
                    #                 article_to_update.is_home = True
                    #                 article_to_update.section = 'home'
                    #                 
                    #                 updated_article_ids.add(article_to_update.id)
                    #                 articles_updated += 1
                    #                 
                    #                 if articles_updated % 10 == 0:
                    #                     print(f"  🔄 Updated display_order for {articles_updated} existing home articles...")
                    #             # else: article đã được update trước đó, không cần đếm lại
                    #         else:
                    #             # Không tìm thấy article nào, sẽ tạo mới ở dưới
                    #             articles_not_found_in_home += 1
                    #             print(f"  ⚠️  WARNING: URL '{article_url[:60]}...' not found in database. Will create new article.")
                    
                    # Determine language from base_url or parameter (cần xác định trước khi check skip)
                    article_language = language or self.language
                    
                    # Check xem article đã tồn tại chưa (chỉ check, không update ngay)
                    if is_slider_container:
                        # Slider containers: check bằng (layout_type, display_order)
                        key = (layout_type, display_order)
                        if key in existing_articles_map:
                            # Đã tồn tại, sẽ update sau khi save xong tất cả articles mới
                            articles_to_update.append({
                                'type': 'slider',
                                'key': key,
                                'article': existing_articles_map[key],
                                'article_data': article_data,
                                'display_order': display_order
                            })
                            continue
                    elif article_url:
                        # Articles có URL: check bằng published_url
                        # ⚠️ QUAN TRỌNG: Với 1_with_list_left/right, chỉ check trong section='home'
                        # Vì chúng chỉ xuất hiện ở home, không nên check trong các sections khác
                        if layout_type in ['1_with_list_left', '1_with_list_right']:
                            # Check riêng trong section='home'
                            existing_article = Article.query.filter_by(
                                published_url=article_url,
                                language=article_language,
                                section='home'
                            ).first()
                            
                            if existing_article:
                                # Đã tồn tại trong section='home', sẽ update sau
                                articles_to_update.append({
                                    'type': 'article',
                                    'key': article_url,
                                    'article': existing_article,
                                    'article_data': article_data,
                                    'display_order': display_order
                                })
                                continue
                        else:
                            # Articles khác: check trong tất cả sections (như hiện tại)
                            if article_url in existing_articles_map:
                                # Đã tồn tại, sẽ update sau khi save xong tất cả articles mới
                                articles_to_update.append({
                                    'type': 'article',
                                    'key': article_url,
                                    'article': existing_articles_map[article_url],
                                    'article_data': article_data,
                                    'display_order': display_order
                                })
                                continue
                    
                    # Luôn tạo mới article (nếu chưa tồn tại)
                    print(f"  ➕ Will create new article: {article_data.get('title', 'Untitled')[:50]}... (URL: {article_url[:60] if article_url else 'no URL'}...)")
                    
                    # Download và cập nhật image_data nếu có
                    image_data = article_data.get('image_data', {})
                    if image_data:
                        try:
                            print(f"  📥 Downloading header image for article: {article_data.get('title', 'Untitled')[:50]}...")
                            image_data = download_and_update_image_data(
                                image_data,
                                base_url='https://www.sermitsiaq.com',
                                download_all_formats=False  # Chỉ download desktop_webp và fallback
                            )
                        except Exception as e:
                            print(f"  ⚠️  Error downloading image: {e}")
                            # Giữ nguyên image_data gốc nếu lỗi
                    
                    # Merge layout_data với thông tin row
                    layout_data = article_data.get('layout_data', {})
                    layout_data['row_index'] = article_data.get('row_index', -1)
                    layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                    layout_data['total_rows'] = article_data.get('total_rows', 0)
                    
                    # TẠM BỎ QUA: Kiểm tra lại một lần nữa trước khi tạo - luôn tạo mới (chỉ cho home)
                    # # Kiểm tra lại một lần nữa trước khi tạo
                    # # Với slider containers (không có URL), check bằng display_order + layout_type
                    # # Với articles có URL, check bằng published_url
                    # if is_slider_container:
                    #     # Slider containers: check bằng display_order + layout_type
                    #     final_check = Article.query.filter_by(
                    #         section='home',
                    #         is_home=True,
                    #         language=article_language,
                    #         layout_type=layout_type,
                    #         display_order=display_order
                    #     ).first()
                    #     
                    #     if final_check:
                    #         # Update existing slider container
                    #         final_check.display_order = display_order
                    #         final_check.layout_type = layout_type
                    #         layout_data = article_data.get('layout_data', {})
                    #         layout_data['row_index'] = article_data.get('row_index', -1)
                    #         layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                    #         layout_data['total_rows'] = article_data.get('total_rows', 0)
                    #         final_check.layout_data = layout_data
                    #         final_check.grid_size = article_data.get('grid_size', 6)
                    #         final_check.is_home = True
                    #         final_check.section = 'home'
                    #         
                    #         if final_check.id not in updated_article_ids:
                    #             updated_article_ids.add(final_check.id)
                    #             articles_updated += 1
                    #         
                    #         # Không đếm vào articles_skipped vì đã được update
                    #         continue
                    #     # Nếu không tìm thấy, sẽ tạo mới ở dưới
                    # TẠM BỎ QUA: Final check - luôn tạo mới (chỉ cho home)
                    # elif article_url and article_url not in existing_urls:
                    #     # Articles có URL: check bằng published_url
                    #     final_check = Article.query.filter_by(
                    #         published_url=article_url,
                    #         language=article_language,
                    #         section='home',
                    #         is_home=True
                    #     ).first()
                    #     
                    #     if final_check:
                    #         # Verify điều kiện trước khi update
                    #         if final_check.section != 'home' or not final_check.is_home:
                    #             skip_info = {
                    #                 'layout_type': layout_type,
                    #                 'display_order': display_order,
                    #                 'title': article_data.get('title', 'N/A')[:50],
                    #                 'url': article_url,
                    #                 'reason': f'final_check_section_mismatch (section={final_check.section}, is_home={final_check.is_home})'
                    #             }
                    #             skipped_articles_info.append(skip_info)
                    #             print(f"  ⚠️  WARNING: Found article ID {final_check.id} in final_check but section={final_check.section}, is_home={final_check.is_home}. Skipping update. URL: {article_url}")
                    #             existing_urls.add(article_url)  # Add để tránh check lại
                    #             articles_skipped += 1
                    #             continue
                    #         
                    #         # Đã tồn tại, skip và update (chỉ update nếu chưa được update ở trên)
                    #         final_check.display_order = display_order
                    #         final_check.layout_type = article_data.get('layout_type')
                    #         layout_data = article_data.get('layout_data', {})
                    #         layout_data['row_index'] = article_data.get('row_index', -1)
                    #         layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                    #         layout_data['total_rows'] = article_data.get('total_rows', 0)
                    #         final_check.layout_data = layout_data
                    #         final_check.grid_size = article_data.get('grid_size', 6)
                    #         # Đảm bảo is_home=True và section='home'
                    #         final_check.is_home = True
                    #         final_check.section = 'home'
                    #         
                    #         # Chỉ đếm nếu chưa được update trước đó
                    #         if final_check.id not in updated_article_ids:
                    #             updated_article_ids.add(final_check.id)
                    #             articles_updated += 1
                    #         
                    #         # Không đếm vào articles_skipped vì đã được update
                    #         existing_urls.add(article_url)  # Add để tránh duplicate trong cùng batch
                    #         if articles_updated % 10 == 0:
                    #             print(f"  ⏭️  Updated {articles_updated} existing home articles (final check)...")
                    #         continue
                    
                    # Add vào existing_urls để tránh duplicate trong cùng batch (nếu chưa có)
                    if article_url and article_url not in existing_urls:
                        existing_urls[article_url] = None  # Mark as will be created
                    
                    # ⚠️ QUAN TRỌNG: Mọi article tạo ra từ crawl home phải có section='home'
                    # Không detect section từ URL nữa, tất cả đều là section='home'
                    article_section = 'home'
                    
                    # Tạo article mới cho home page
                    new_article = Article(
                        element_guid=article_data.get('element_guid'),
                        title=article_data.get('title', 'Untitled'),  # Slider có thể không có title
                        slug=article_data.get('slug', ''),
                        published_url=article_data.get('url', ''),
                        k5a_url=article_data.get('k5a_url', ''),
                        language=article_language,  # Set language
                        original_language=article_language,  # Set original_language
                        section=article_section,  # ⚠️ Detect section từ URL cho 1_article, 2_articles, 3_articles
                        site_alias=article_data.get('site_alias', 'sermitsiaq'),
                        instance=article_data.get('instance', ''),
                        published_date=article_data.get('published_date'),
                        is_paywall=article_data.get('is_paywall', False),
                        paywall_class=article_data.get('paywall_class', ''),
                        image_data=image_data,  # Đã được download và cập nhật
                        display_order=display_order,  # Sử dụng display_order từ parser
                        is_home=True,  # QUAN TRỌNG: Đánh dấu thuộc home
                        layout_type=layout_type,  # Layout type từ parser
                        layout_data=layout_data,  # Layout data với thông tin row
                        grid_size=article_data.get('grid_size', 6),  # Grid size từ HTML (5, 6, 7, 8, etc.)
                    )
                    db.session.add(new_article)
                    
                    # Debug: Log slider info
                    if article_data.get('layout_type') == 'slider':
                        layout_data = article_data.get('layout_data', {})
                        slider_articles = layout_data.get('slider_articles', [])
                        slider_title = layout_data.get('slider_title', 'Untitled')
                        print(f"  🎠 Saving slider '{slider_title}': {len(slider_articles)} articles")
                        if len(slider_articles) < 4:
                            print(f"     ⚠️  WARNING: Slider has only {len(slider_articles)} articles")
                    
                    # ⚠️ CRITICAL: Wrap commit trong try-except để catch IntegrityError (race condition)
                    try:
                        # Commit mỗi 10 articles để tránh timeout
                        if (articles_created + articles_updated + 1) % 10 == 0:
                            db.session.commit()
                            print(f"  💾 Saved {articles_created + 1} new articles, updated {articles_updated} existing...")
                        
                        articles_created += 1
                        if article_url:
                            existing_urls[article_url] = new_article  # Add to dict to avoid duplicates in same batch
                    except Exception as commit_error:
                        # IntegrityError hoặc unique constraint violation (race condition)
                        db.session.rollback()
                        error_msg_str = str(commit_error)
                        if 'unique' in error_msg_str.lower() or 'duplicate' in error_msg_str.lower():
                            print(f"  ⏭️  Article already exists (duplicate detected during commit), skipping...")
                            articles_skipped += 1
                            if article_url:
                                existing_urls[article_url] = None  # Mark as processed
                        else:
                            # Re-raise nếu không phải duplicate error
                            raise
                
                except Exception as e:
                    error_msg = f"Error saving article {article_data.get('element_guid', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ⚠️  {error_msg}")
                    db.session.rollback()
                    continue
            
            # Final commit cho articles mới
            db.session.commit()
            print(f"✅ Successfully saved {articles_created} new home articles")
            
            # Sau khi save đầy đủ articles mới, mới chạy logic update cho articles đã tồn tại
            print(f"\n🔄 Updating existing articles...")
            for update_info in articles_to_update:
                try:
                    existing_article = update_info['article']
                    article_data = update_info['article_data']
                    display_order = update_info['display_order']
                    layout_type = article_data.get('layout_type', '')
                    
                    if update_info['type'] == 'slider':
                        # Update slider container
                        existing_article.display_order = display_order
                        existing_article.layout_type = layout_type
                        layout_data = article_data.get('layout_data', {})
                        layout_data['row_index'] = article_data.get('row_index', -1)
                        layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                        layout_data['total_rows'] = article_data.get('total_rows', 0)
                        existing_article.layout_data = layout_data
                        existing_article.grid_size = article_data.get('grid_size', 6)
                        existing_article.is_home = True
                        existing_article.section = 'home'
                        
                        if existing_article.id not in updated_article_ids:
                            updated_article_ids.add(existing_article.id)
                            articles_updated += 1
                            slider_title = article_data.get('layout_data', {}).get('slider_title', 'Untitled')
                            print(f"  🔄 Updated slider container: {layout_type} '{slider_title}' (display_order={display_order})")
                    else:
                        # Update article có URL
                        existing_article.display_order = display_order
                        existing_article.layout_type = layout_type
                        
                        # Merge layout_data với thông tin row
                        layout_data = article_data.get('layout_data', {})
                        layout_data['row_index'] = article_data.get('row_index', -1)
                        layout_data['article_index_in_row'] = article_data.get('article_index_in_row', -1)
                        layout_data['total_rows'] = article_data.get('total_rows', 0)
                        existing_article.layout_data = layout_data
                        
                        existing_article.grid_size = article_data.get('grid_size', 6)
                        existing_article.is_home = True
                        # ⚠️ KHÔNG đổi section gốc của existing articles - giữ nguyên section ban đầu
                        
                        if existing_article.id not in updated_article_ids:
                            updated_article_ids.add(existing_article.id)
                            articles_updated += 1
                            if articles_updated % 10 == 0:
                                print(f"  🔄 Updated display_order for {articles_updated} existing home articles...")
                except Exception as e:
                    error_msg = f"Error updating article {update_info.get('key', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ⚠️  {error_msg}")
                    continue
            
            # Commit tất cả updates
            if articles_to_update:
                db.session.commit()
                print(f"✅ Updated {articles_updated} existing articles")
            
            print(f"✅ Successfully saved {articles_created} new home articles, updated {articles_updated} existing articles (display_order)")
            if articles_not_found_in_home > 0:
                print(f"   ⚠️  {articles_not_found_in_home} articles not found in database (should have been created)")
            print(f"   📊 Summary: {articles_crawled} crawled, {articles_created} created, {articles_updated} updated, {articles_skipped} skipped")
            
            # Debug: Show skipped articles info
            if skipped_articles_info:
                print(f"   📋 Skipped articles details ({len(skipped_articles_info)}):")
                for skip_info in skipped_articles_info:
                    print(f"      - {skip_info['reason']}: layout_type={skip_info['layout_type']}, display_order={skip_info['display_order']}, title={skip_info['title'][:50]}, url={skip_info.get('url', 'N/A')}")
            
            if articles_crawled != (articles_created + articles_updated + articles_skipped):
                missing = articles_crawled - (articles_created + articles_updated + articles_skipped)
                print(f"   ⚠️  WARNING: {missing} articles were not processed (crawled={articles_crawled}, processed={articles_created + articles_updated + articles_skipped})")
                print(f"   🔍 This might indicate articles that were crawled but not saved/updated/skipped properly")
            
            # Update crawl log
            crawl_log.status = 'success' if not errors else 'partial'
            crawl_log.articles_crawled = articles_crawled
            crawl_log.articles_created = articles_created
            crawl_log.articles_updated = articles_updated
            crawl_log.completed_at = datetime.utcnow()
            if errors:
                crawl_log.errors = '\n'.join(errors[:10])
            db.session.commit()
            
            print(f"✅ Home crawl completed!")
            print(f"   📊 Articles crawled: {articles_crawled}")
            print(f"   ➕ Articles created: {articles_created}")
            print(f"   🔄 Articles updated (display_order): {articles_updated}")
            if errors:
                print(f"   ⚠️  Errors: {len(errors)}")
            
            return {
                'success': True,
                'articles_crawled': articles_crawled,
                'articles_created': articles_created,
                'articles_updated': articles_updated,
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

