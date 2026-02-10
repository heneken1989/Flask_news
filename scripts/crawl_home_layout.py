#!/usr/bin/env python3
"""
Script mới để crawl layout structure của home page
Chỉ lấy metadata: published_url, layout_type, display_order
Không tạo articles mới, chỉ lưu layout structure để link với articles đã có

Flow:
1. Crawl home page → parse layout structure
2. Lưu layout structure vào JSON hoặc return dict
3. Script khác sẽ dùng layout này để link với articles đã có trong DB
"""

import sys
import os
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from seleniumbase import SB
from services.article_parser import parse_articles_from_html, parse_article_element
from services.image_downloader import download_and_update_image_data
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from sqlalchemy import or_
import time
import re
import requests

# Import app và database khi cần (sẽ import trong function khi cần app context)

# Import database sau khi có app context


def get_chrome_options_for_headless():
    """
    Trả về Chrome options cần thiết cho Linux headless server
    Cần thiết khi chạy với root hoặc không có display
    """
    # --no-sandbox: Bỏ qua sandbox (cần thiết khi chạy với root)
    # --disable-dev-shm-usage: Tránh lỗi shared memory trên VPS
    # --disable-gpu: Tắt GPU (không cần trên server)
    return "no-sandbox,disable-dev-shm-usage,disable-gpu"


def resolve_final_url(url, timeout=5):
    """
    Theo dõi redirect để lấy URL cuối cùng (canonical) cho các articles dạng liveblog.
    
    Nếu có lỗi hoặc không resolve được, trả lại URL gốc.
    """
    if not url:
        return url
    
    try:
        # Chuẩn hóa URL: layout có thể lưu dạng absolute hoặc relative
        if url.startswith('http://') or url.startswith('https://'):
            full_url = url
        else:
            # Home layout luôn crawl từ sermitisiaq.ag
            full_url = urljoin('https://www.sermitsiaq.ag', url)
        
        # Cố gắng dùng HEAD để nhẹ hơn, nếu fail thì fallback GET
        try:
            resp = requests.head(full_url, allow_redirects=True, timeout=timeout)
            final_url = resp.url
        except Exception:
            resp = requests.get(full_url, allow_redirects=True, timeout=timeout)
            final_url = resp.url
        
        # Nếu server trả redirect (ví dụ liveblog slug mới) thì resp.url sẽ là URL cuối
        return final_url or url
    except Exception as e:
        print(f"   ⚠️  resolve_final_url error for '{url}': {e}")
        return url


def extract_section_from_url(url):
    """
    Extract section từ URL
    
    Args:
        url: Article URL (ví dụ: https://www.sermitsiaq.ag/kultur/debut-ep-fra-max-5-tassa/2331684)
    
    Returns:
        str: Section name ('kultur', 'samfund', 'erhverv', 'sport', 'podcasti') hoặc 'home' nếu không match
    """
    if not url:
        return 'home'
    
    # Parse URL để lấy path
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Valid sections
    valid_sections = ['kultur', 'samfund', 'erhverv', 'sport', 'podcasti']
    
    # Extract section từ path (phần đầu tiên sau domain)
    # Ví dụ: /kultur/debut-ep-fra-max-5-tassa/2331684 → 'kultur'
    path_parts = path.split('/')
    if path_parts and path_parts[0] in valid_sections:
        return path_parts[0]
    
    # Nếu không match → return 'home'
    return 'home'


def parse_job_article_manual(soup, article_url, article_title):
    """
    Parse job article từ sjob.gl manually - chỉ lấy image, title và URL
    (Vì URL sẽ link sang trang khác, không cần parse toàn bộ detail)
    
    Args:
        soup: BeautifulSoup object của article page
        article_url: URL của article
        article_title: Title từ layout (fallback)
    
    Returns:
        dict: Article data với image, title, url hoặc None
    """
    try:
        # Extract title
        title = article_title
        title_elem = soup.find('h1') or soup.find('h2', class_='headline') or soup.find('h2')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Extract image (nếu có) - tìm image trong article hoặc header
        image_data = {}
        img_elem = soup.find('img')
        if img_elem:
            img_src = img_elem.get('src', '')
            if img_src:
                if not img_src.startswith('http'):
                    img_src = urljoin(article_url, img_src)
                image_data = {
                    'fallback': img_src,
                    'desktop_webp': img_src,
                    'desktop_jpeg': img_src
                }
        
        # Extract slug từ URL (đơn giản)
        slug = ''
        url_parts = article_url.rstrip('/').split('/')
        if len(url_parts) >= 2:
            slug = url_parts[-2]  # Lấy phần trước số ID
        
        # Extract instance từ URL (số ID cuối)
        instance = ''
        if url_parts:
            instance = url_parts[-1] if url_parts[-1].isdigit() else ''
        
        # Extract element_guid (nếu có)
        element_guid = ''
        guid_elem = soup.find(attrs={'data-element-guid': True})
        if guid_elem:
            element_guid = guid_elem.get('data-element-guid', '')
        
        # Chỉ cần image, title và URL - đơn giản hóa
        return {
            'element_guid': element_guid,
            'title': title,
            'slug': slug,
            'url': article_url,
            'k5a_url': article_url,  # Job articles thường không có k5a_url riêng
            'site_alias': 'sjob',
            'instance': instance,
            'published_date': None,  # Không cần date cho job articles
            'is_paywall': False,
            'paywall_class': '',
            'image_data': image_data
        }
    except Exception as e:
        print(f"      ⚠️  Error parsing job article manually: {e}")
        import traceback
        traceback.print_exc()
        return None


def crawl_home_layout(home_url='https://www.sermitsiaq.ag', language='da', 
                      max_articles=0, scroll_pause=2, headless=True):
    """
    Crawl layout structure của home page
    
    Args:
        home_url: URL của trang home
        language: Language code ('da', 'kl', 'en')
        max_articles: Số lượng articles tối đa (0 = tất cả)
        scroll_pause: Thời gian chờ giữa các lần scroll
        headless: Chạy browser ở chế độ headless
    
    Returns:
        list: List of layout items, mỗi item có:
            - published_url: URL của article
            - layout_type: Loại layout (1_full, 2_articles, slider, etc.)
            - display_order: Thứ tự hiển thị
            - row_index: Index của row
            - article_index_in_row: Index trong row
            - total_rows: Tổng số rows
            - grid_size: Grid size (6, 4, 12, etc.)
            - layout_data: Layout data (cho slider)
    """
    print(f"\n{'='*60}")
    print(f"🏠 Crawling home layout structure")
    print(f"{'='*60}")
    print(f"   URL: {home_url}")
    print(f"   Language: {language}")
    print(f"   Max articles: {max_articles if max_articles > 0 else 'All'}")
    print(f"   Headless: {headless}")
    
    layout_items = []
    
    # Chrome options cho Linux headless server
    chrome_opts = get_chrome_options_for_headless()
    
    try:
        with SB(uc=True, headless=headless, chromium_arg=chrome_opts) as sb:
            # Navigate to home page
            print(f"\n📡 Opening {home_url}...")
            sb.open(home_url)
            time.sleep(3)
            
            # Scroll để load thêm articles
            print("📜 Scrolling to load articles...")
            scroll_count = 0
            max_scrolls = 100 if max_articles == 0 else 50
            previous_count = 0
            no_new_articles_count = 0
            
            while scroll_count < max_scrolls:
                sb.scroll_to_bottom()
                time.sleep(scroll_pause)
                scroll_count += 1
                
                # Check số lượng articles hiện tại
                current_count = len(sb.find_elements('article[data-element-guid]'))
                
                if current_count == previous_count:
                    no_new_articles_count += 1
                    if no_new_articles_count >= 3:
                        print(f"   ✅ No new articles after {no_new_articles_count} scrolls, stopping...")
                        break
                else:
                    no_new_articles_count = 0
                    print(f"   📊 Found {current_count} articles after {scroll_count} scrolls...")
                
                previous_count = current_count
                
                # Nếu đã đủ số lượng articles cần thiết
                if max_articles > 0 and current_count >= max_articles:
                    print(f"   ✅ Reached {max_articles} articles, stopping scroll...")
                    break
            
            # Get HTML content
            print(f"\n📄 Extracting HTML content...")
            html_content = sb.get_page_source()
            
            # Parse articles từ HTML (chỉ lấy layout structure)
            print(f"🔍 Parsing layout structure...")
            articles = parse_articles_from_html(html_content, base_url=home_url, is_home=True)
            
            print(f"✅ Parsed {len(articles)} layout items")
            
            # Convert articles thành layout items (chỉ lấy metadata cần thiết)
            for article_data in articles:
                layout_type = article_data.get('layout_type', '')
                layout_data = article_data.get('layout_data', {})
                
                published_url = article_data.get('url', '')
                
                # ⚠️ QUAN TRỌNG: Với liveblog articles, resolve final URL ngay khi crawl layout
                # Để layout file JSON có URL đúng (sau redirect), không phải URL gốc
                kicker_floating = layout_data.get('kicker_floating', '')
                if kicker_floating and 'liveblog' in kicker_floating.lower():
                    print(f"   🔍 Detected liveblog article, resolving final URL: {published_url[:60]}...")
                    resolved_url = resolve_final_url(published_url)
                    if resolved_url != published_url:
                        print(f"      🔁 Resolved redirect: {published_url[:60]}... → {resolved_url[:60]}...")
                        published_url = resolved_url
                    else:
                        print(f"      ℹ️  No redirect, using original URL")
                
                layout_item = {
                    'published_url': published_url,  # Dùng URL đã resolve (nếu là liveblog)
                    'layout_type': layout_type,
                    'display_order': article_data.get('display_order', 0),
                    'row_index': article_data.get('row_index', -1),
                    'article_index_in_row': article_data.get('article_index_in_row', -1),
                    'total_rows': article_data.get('total_rows', 0),
                    'grid_size': article_data.get('grid_size', 6),
                    'layout_data': layout_data,
                    'element_guid': article_data.get('element_guid', ''),
                    'k5a_url': article_data.get('k5a_url', ''),
                    'title': article_data.get('title', ''),  # Lưu title để dùng trong CSV
                }
                
                # Với slider containers, lưu thêm thông tin slider
                if layout_type in ['slider', 'job_slider']:
                    layout_item['slider_title'] = layout_data.get('slider_title', '')
                    layout_item['slider_articles'] = []
                    # Lưu published_url của các articles trong slider
                    for slider_article in layout_data.get('slider_articles', []):
                        if slider_article.get('url'):
                            layout_item['slider_articles'].append({
                                'published_url': slider_article.get('url'),
                                'title': slider_article.get('title', ''),
                                'image_data': slider_article.get('image_data', {})
                            })
                
                # Với 1_with_list_left/right, đảm bảo list_items được lưu
                elif layout_type in ['1_with_list_left', '1_with_list_right']:
                    list_items = layout_data.get('list_items', [])
                    list_title = layout_data.get('list_title', '')
                    
                    # Log để debug
                    if list_items:
                        print(f"   📋 Found {len(list_items)} list items for {layout_type} (title: {list_title})")
                    else:
                        print(f"   ⚠️  No list items found for {layout_type} - layout_data: {list(layout_data.keys())}")
                    
                    # Đảm bảo list_items được lưu trong layout_data
                    layout_item['list_title'] = list_title
                    layout_item['list_items'] = list_items
                    # Cập nhật lại layout_data để đảm bảo có list_items
                    layout_item['layout_data']['list_items'] = list_items
                    layout_item['layout_data']['list_title'] = list_title
                
                layout_items.append(layout_item)
            
            print(f"\n✅ Successfully extracted {len(layout_items)} layout items")
            
            # Print summary
            print(f"\n📊 Layout Summary:")
            layout_types = {}
            for item in layout_items:
                layout_type = item['layout_type']
                layout_types[layout_type] = layout_types.get(layout_type, 0) + 1
            
            for layout_type, count in sorted(layout_types.items()):
                print(f"   - {layout_type}: {count} items")
            
            # Crawl và tạo articles từ home page
            # ⚠️ LƯU Ý: 
            # - Crawl tất cả articles (1_full, 2_articles, 3_articles, etc.) và set is_home=True, section='home'
            # - list_items trong 1_with_list_left/right chỉ là links, không cần crawl
            # - job_slider: Chỉ tạo container, items từ sjob.gl không cần crawl (lưu trong layout_data)
            print(f"\n{'='*60}")
            print(f"🕷️  Crawling articles from home page")
            print(f"{'='*60}")
            print(f"   ℹ️  Note: list_items trong 1_with_list_left/right chỉ là links, không cần crawl")
            
            # Collect tất cả articles cần crawl
            articles_to_crawl = []
            
            # 1. Collect các articles thông thường (1_full, 2_articles, 3_articles, 5_articles, etc.)
            # ⚠️ LƯU Ý: Bỏ qua các articles không có URL (chỉ là label như "NYHEDER", "Se alle jobs")
            regular_layout_types = ['1_full', '2_articles', '3_articles', '5_articles', '1_with_list_left', '1_with_list_right']
            for item in layout_items:
                layout_type = item.get('layout_type', '')
                published_url = item.get('published_url', '')
                
                # Skip nếu không có URL (chỉ là label)
                if not published_url or not published_url.strip():
                    if layout_type in regular_layout_types:
                        print(f"   ⏭️  Skipping {layout_type} without URL (label only): {item.get('title', 'N/A')[:50]}")
                    continue
                
                if layout_type in regular_layout_types:
                    # Resolve relative URL
                    if not published_url.startswith('http'):
                        published_url = urljoin(home_url, published_url)
                    
                    if published_url not in [a['url'] for a in articles_to_crawl]:
                        articles_to_crawl.append({
                            'url': published_url,
                            'title': item.get('title', ''),
                            'source': 'home_article',
                            'layout_type': layout_type,
                            'display_order': item.get('display_order', 0),
                            'element_guid': item.get('element_guid', ''),
                            'k5a_url': item.get('k5a_url', '')
                        })
            
            # 2. Log job_slider (chỉ tạo container, không crawl individual items)
            for item in layout_items:
                layout_type = item.get('layout_type', '')
                
                if layout_type == 'job_slider':
                    slider_articles = item.get('slider_articles', [])
                    slider_title = item.get('slider_title', '')
                    print(f"   💼 Found job_slider with {len(slider_articles)} articles (title: {slider_title}) - Container only, items from sjob.gl không cần crawl")
            
            # 3. Log list_items (không crawl, chỉ là links)
            for item in layout_items:
                layout_type = item.get('layout_type', '')
                if layout_type in ['1_with_list_left', '1_with_list_right']:
                    list_items = item.get('list_items', []) or item.get('layout_data', {}).get('list_items', [])
                    list_title = item.get('list_title', '') or item.get('layout_data', {}).get('list_title', '')
                    print(f"   📋 {layout_type} has {len(list_items)} list items (title: {list_title}) - URLs đã lưu trong layout_data, không cần crawl")
            
            print(f"\n   📊 Summary:")
            print(f"      - Regular articles to crawl: {len([a for a in articles_to_crawl if a['source'] == 'home_article'])} articles")
            print(f"      - Job slider: Container only (items từ sjob.gl không cần crawl)")
            print(f"      - List items (1_with_list_left/right): Chỉ là links, không cần crawl")
            
            # Crawl tất cả articles
            if articles_to_crawl:
                # Import app và database khi cần
                from app import app
                from database import db, Article
                
                with app.app_context():
                    articles_created = 0
                    articles_skipped = 0
                    articles_updated = 0
                    
                    # ⚠️ CRITICAL: Track URLs đã crawled trong session này để tránh duplicate
                    crawled_urls_in_session = set()
                    
                    for idx, article_info in enumerate(articles_to_crawl, 1):
                        article_url = article_info['url']
                        article_title = article_info['title']
                        source = article_info['source']
                        layout_type = article_info.get('layout_type', '')
                        
                        print(f"\n   [{idx}/{len(articles_to_crawl)}] Crawling: {article_title[:50] if article_title else 'N/A'}...")
                        print(f"      URL: {article_url[:80]}...")
                        print(f"      Source: {source}, Layout: {layout_type}")
                        
                        # ⚠️ CRITICAL: Check xem URL đã crawled trong session này chưa
                        if article_url in crawled_urls_in_session:
                            print(f"      ⏭️  URL already crawled in this session, skipping...")
                            articles_skipped += 1
                            continue
                        
                        # Check if article already exists in database
                        # Dùng db.session.expire_all() để refresh query và tránh cache cũ
                        db.session.expire_all()
                        
                        # ⚠️ QUAN TRỌNG: Với 1_with_list_left/right, chỉ tìm articles có section='home' và chưa bị deleted
                        # Vì chúng cần tạo mới mỗi lần chạy (old articles đã bị mark is_deleted=True)
                        if layout_type in ['1_with_list_left', '1_with_list_right']:
                            # Tìm article với section='home' và chưa bị deleted
                            existing = Article.query.filter_by(
                                published_url=article_url,
                                language=language,
                                section='home'
                            ).filter(
                                or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                            ).first()
                            
                            if existing:
                                # Article đã có với section='home' và chưa bị deleted → skip (đã tạo trong session này)
                                print(f"      ⏭️  1_with_list article already exists in section='home' (ID: {existing.id}), skipping...")
                                articles_skipped += 1
                                crawled_urls_in_session.add(article_url)
                                continue
                            else:
                                # Không tìm thấy (vì đã bị mark deleted hoặc chưa có) → tạo mới
                                print(f"      ✅ Creating new 1_with_list article (old one marked deleted or not exists)")
                                # Proceed to create new article below
                        else:
                            # Với các layout type khác, query như cũ (không filter section)
                            existing = Article.query.filter_by(
                                published_url=article_url,
                                language=language
                            ).first()
                            
                            if existing:
                                # Update existing article: set is_home=True, display_order, layout_type
                                # ⚠️ KHÔNG update section - giữ nguyên section gốc (có thể từ section pages)
                                # ⚠️ KHÔNG set is_temp=True khi update (chỉ set khi tạo mới)
                                needs_update = False
                                if not existing.is_home:
                                    needs_update = True
                                if article_info.get('display_order') and existing.display_order != article_info.get('display_order'):
                                    needs_update = True
                                if layout_type and existing.layout_type != layout_type:
                                    needs_update = True
                                
                                if needs_update:
                                    existing.is_home = True
                                    # ⚠️ KHÔNG update section - giữ nguyên section gốc
                                    if article_info.get('display_order'):
                                        existing.display_order = article_info.get('display_order')
                                    if layout_type:
                                        existing.layout_type = layout_type
                                    db.session.commit()
                                    articles_updated += 1
                                    print(f"      ✅ Updated existing article (ID: {existing.id}, section='{existing.section}'): is_home=True")
                                else:
                                    print(f"      ⏭️  Article already exists and is up-to-date (ID: {existing.id}, section='{existing.section}'), skipping...")
                                articles_skipped += 1
                                # Mark URL as crawled trong session
                                crawled_urls_in_session.add(article_url)
                                continue
                        
                        try:
                            # Navigate to article page
                            sb.open(article_url)
                            time.sleep(2)
                            
                            # Get HTML content
                            html_content = sb.get_page_source()
                            
                            # Parse article element từ HTML
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Tìm article element - thử nhiều cách
                            article_elem = None
                            
                            # Cách 1: Tìm <article> tag
                            article_elem = soup.find('article')
                            
                            # Cách 2: Tìm bằng data-element-guid
                            if not article_elem:
                                article_elem = soup.find('div', attrs={'data-element-guid': True})
                            
                            # Cách 3: Tìm bằng class hoặc id thường dùng
                            if not article_elem:
                                article_elem = soup.find('div', class_=lambda x: x and ('article' in x.lower() or 'content' in x.lower()))
                            
                            # Cách 4: Tìm main content area
                            if not article_elem:
                                article_elem = soup.find('main') or soup.find('div', id='content') or soup.find('div', id='main')
                            
                            # Parse article data
                            article_data = None
                            
                            if article_elem:
                                # Try parse với parse_article_element (cho sermitsiaq.ag)
                                try:
                                    article_data = parse_article_element(article_elem, base_url=home_url)
                                except Exception as e:
                                    print(f"      ⚠️  Error parsing with parse_article_element: {e}")
                                    article_data = None
                            
                            # Nếu không parse được, thử parse thủ công
                            if not article_data:
                                # Check xem có phải job article từ sjob.gl không
                                if 'sjob.gl' in article_url:
                                    print(f"      ℹ️  Job article from sjob.gl, parsing manually...")
                                    article_data = parse_job_article_manual(soup, article_url, article_title)
                                else:
                                    # Thử parse thủ công cho sermitsiaq.ag articles
                                    print(f"      ℹ️  Trying manual parsing...")
                                    try:
                                        # Extract basic info từ HTML
                                        title = article_title
                                        title_elem = soup.find('h1') or soup.find('h2', class_='headline') or soup.find('h2')
                                        if title_elem:
                                            title = title_elem.get_text(strip=True)
                                        
                                        # Extract image - tìm trong picture tag với source tags
                                        image_data = {}
                                        
                                        # Cách 1: Tìm <picture> tag (ưu tiên nhất - có nhiều formats)
                                        picture_elem = soup.find('picture')
                                        if picture_elem:
                                            # Lấy các source tags
                                            sources = picture_elem.find_all('source')
                                            
                                            # Tìm desktop_webp (media="(min-width: 768px)" type="image/webp")
                                            desktop_webp = None
                                            desktop_jpeg = None
                                            mobile_webp = None
                                            mobile_jpeg = None
                                            
                                            for source in sources:
                                                srcset = source.get('srcset', '')
                                                media = source.get('media', '')
                                                source_type = source.get('type', '')
                                                
                                                if not srcset:
                                                    continue
                                                
                                                # Extract URL từ srcset (có thể có nhiều URLs, lấy đầu tiên)
                                                srcset_url = srcset.split(',')[0].strip().split()[0] if srcset else ''
                                                
                                                # Phân loại theo media và type
                                                if '(min-width: 768px)' in media:
                                                    if 'image/webp' in source_type:
                                                        desktop_webp = srcset_url
                                                    elif 'image/jpeg' in source_type or 'image/jpg' in source_type:
                                                        desktop_jpeg = srcset_url
                                                elif '(max-width: 767px)' in media:
                                                    if 'image/webp' in source_type:
                                                        mobile_webp = srcset_url
                                                    elif 'image/jpeg' in source_type or 'image/jpg' in source_type:
                                                        mobile_jpeg = srcset_url
                                            
                                            # Lấy fallback từ img tag trong picture
                                            img_in_picture = picture_elem.find('img')
                                            fallback = None
                                            if img_in_picture:
                                                fallback = img_in_picture.get('src', '')
                                            
                                            # Tạo image_data từ picture sources
                                            if desktop_webp or desktop_jpeg or mobile_webp or mobile_jpeg or fallback:
                                                image_data = {
                                                    'desktop_webp': desktop_webp or fallback or desktop_jpeg,
                                                    'desktop_jpeg': desktop_jpeg or fallback or desktop_webp,
                                                    'mobile_webp': mobile_webp or fallback or mobile_jpeg,
                                                    'mobile_jpeg': mobile_jpeg or fallback or mobile_webp,
                                                    'fallback': fallback or desktop_webp or desktop_jpeg or mobile_webp or mobile_jpeg
                                                }
                                                
                                                # Resolve relative URLs
                                                for key in image_data:
                                                    if image_data[key] and not image_data[key].startswith('http'):
                                                        image_data[key] = urljoin(article_url, image_data[key])
                                                
                                                print(f"         ℹ️  Found image from <picture> tag:")
                                                if desktop_webp:
                                                    print(f"            desktop_webp: {desktop_webp[:80]}...")
                                                if fallback:
                                                    print(f"            fallback: {fallback[:80]}...")
                                        
                                        # Cách 2: Nếu không có picture, tìm img trong figure hoặc article
                                        if not image_data:
                                            figure_elem = soup.find('figure')
                                            if figure_elem:
                                                img_elem = figure_elem.find('img')
                                            else:
                                                # Tìm img trong article hoặc content
                                                article_elem = soup.find('article') or soup.find('div', class_='content')
                                                if article_elem:
                                                    img_elem = article_elem.find('img')
                                                else:
                                                    img_elem = soup.find('img')
                                            
                                            if img_elem:
                                                # Ưu tiên data-src, data-lazy-src, rồi mới đến src
                                                img_src = (img_elem.get('data-src') or 
                                                          img_elem.get('data-lazy-src') or 
                                                          img_elem.get('src') or 
                                                          img_elem.get('data-original', ''))
                                                
                                                # Bỏ qua logo.svg và các image không phải article image
                                                if img_src and 'logo.svg' not in img_src and 'image.sermitsiaq.ag' in img_src:
                                                    # Resolve relative URL
                                                    if not img_src.startswith('http'):
                                                        img_src = urljoin(article_url, img_src)
                                                    
                                                    # Tạo image_data với tất cả formats
                                                    image_data = {
                                                        'fallback': img_src,
                                                        'desktop_webp': img_src,
                                                        'desktop_jpeg': img_src,
                                                        'mobile_webp': img_src,
                                                        'mobile_jpeg': img_src
                                                    }
                                                    
                                                    print(f"         ℹ️  Found image from <img> tag: {img_src[:80]}...")
                                                elif img_src and 'logo.svg' in img_src:
                                                    print(f"         ⚠️  Skipping logo.svg image")
                                        
                                        # Extract slug và instance từ URL
                                        url_parts = article_url.rstrip('/').split('/')
                                        slug = url_parts[-2] if len(url_parts) >= 2 else ''
                                        instance = url_parts[-1] if url_parts and url_parts[-1].isdigit() else ''
                                        
                                        # Extract element_guid
                                        element_guid = ''
                                        guid_elem = soup.find(attrs={'data-element-guid': True})
                                        if guid_elem:
                                            element_guid = guid_elem.get('data-element-guid', '')
                                        
                                        # Extract published_date từ <time itemprop="datePublished" datetime="...">
                                        published_date = None
                                        time_elem = soup.find('time', attrs={'itemprop': 'datePublished'})
                                        if time_elem:
                                            datetime_attr = time_elem.get('datetime', '')
                                            if datetime_attr:
                                                try:
                                                    # Parse ISO format: 2025-11-08T11:32:36+01:00
                                                    # Thay Z thành +00:00 nếu có
                                                    datetime_str = datetime_attr.replace('Z', '+00:00')
                                                    published_date = datetime.fromisoformat(datetime_str)
                                                    print(f"         ✅ Extracted published_date: {published_date}")
                                                except Exception as e:
                                                    print(f"         ⚠️  Could not parse datetime '{datetime_attr}': {e}")
                                                    # Thử parse format khác nếu cần
                                                    try:
                                                        # Thử format: 2025-11-08T11:32:36
                                                        if 'T' in datetime_attr and '+' not in datetime_attr and 'Z' not in datetime_attr:
                                                            published_date = datetime.fromisoformat(datetime_attr)
                                                            print(f"         ✅ Extracted published_date (no timezone): {published_date}")
                                                    except:
                                                        pass
                                        
                                        article_data = {
                                            'element_guid': element_guid,
                                            'title': title,
                                            'slug': slug,
                                            'url': article_url,
                                            'k5a_url': article_url,
                                            'site_alias': 'sermitsiaq',
                                            'instance': instance,
                                            'published_date': published_date,
                                            'is_paywall': False,
                                            'paywall_class': '',
                                            'image_data': image_data
                                        }
                                        print(f"      ✅ Manual parsing successful")
                                    except Exception as e:
                                        print(f"      ⚠️  Error in manual parsing: {e}")
                                        article_data = None
                                
                                if not article_data:
                                    print(f"      ⚠️  Could not parse article data, skipping...")
                                    print(f"         ℹ️  URL: {article_url}")
                                    continue
                            
                            # Download image
                            image_data = article_data.get('image_data', {})
                            if image_data:
                                # Log image_data trước khi download để debug
                                print(f"      ℹ️  Image data before download:")
                                for key, value in image_data.items():
                                    if value:
                                        print(f"         {key}: {value[:100]}...")
                                
                                try:
                                    image_data = download_and_update_image_data(
                                        image_data,
                                        base_url='https://www.sermitsiaq.com',
                                        download_all_formats=False
                                    )
                                    
                                    # Log imageId nếu extract được
                                    from services.image_downloader import extract_image_id_from_url
                                    image_id = None
                                    for key in ['desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg', 'fallback']:
                                        if image_data.get(key):
                                            image_id = extract_image_id_from_url(image_data[key])
                                            if image_id:
                                                print(f"      ✅ Extracted imageId: {image_id} from {key}")
                                                break
                                    
                                    if not image_id:
                                        print(f"      ⚠️  Could not extract imageId - checking image URLs:")
                                        for key, value in image_data.items():
                                            if value:
                                                print(f"         {key}: {value[:120]}")
                                except Exception as e:
                                    print(f"      ⚠️  Error downloading image: {e}")
                                    import traceback
                                    traceback.print_exc()
                            
                            # Set section='home' và is_home=True cho tất cả articles từ home page
                            # ⚠️ QUAN TRỌNG: Tất cả articles từ home page đều có section='home' và is_home=True
                            
                            # Create Article record
                            # ⚠️ QUAN TRỌNG: Set is_temp=True cho 1_article, 2_article, 3_article
                            # (cần crawl detail trước khi show trên home)
                            layout_type_final = layout_type or source
                            is_temp_value = layout_type_final in ['1_article', '2_articles', '3_articles']
                            
                            # ⚠️ QUAN TRỌNG: TẤT CẢ articles TẠO MỚI từ home crawl đều có section='home'
                            # (Không detect từ URL, không quan tâm layout_type)
                            article_section = 'home'
                            
                            new_article = Article(
                                element_guid=article_data.get('element_guid', '') or article_info.get('element_guid', ''),
                                title=article_data.get('title', article_title),
                                slug=article_data.get('slug', ''),
                                published_url=article_url,
                                k5a_url=article_data.get('k5a_url', '') or article_info.get('k5a_url', ''),
                                section=article_section,  # ⚠️ TẤT CẢ articles từ home crawl đều có section='home'
                                site_alias=article_data.get('site_alias', 'sermitsiaq'),
                                instance=article_data.get('instance', ''),
                                published_date=article_data.get('published_date'),
                                is_paywall=article_data.get('is_paywall', False),
                                paywall_class=article_data.get('paywall_class', ''),
                                image_data=image_data,
                                language=language,
                                original_language=language,
                                is_home=True,  # ⚠️ Tất cả articles từ home page có is_home=True
                                layout_type=layout_type_final,
                                display_order=article_info.get('display_order', 0),
                                is_temp=is_temp_value  # ⚠️ Set is_temp=True cho 1_article, 2_article, 3_article
                            )
                            
                            db.session.add(new_article)
                            
                            # ⚠️ CRITICAL: Wrap commit trong try-except để catch IntegrityError
                            # (race condition nếu 2 processes tạo cùng article)
                            try:
                                db.session.commit()
                                articles_created += 1
                                
                                # Mark URL as crawled trong session
                                crawled_urls_in_session.add(article_url)
                                
                                print(f"      ✅ Created article (ID: {new_article.id})")
                                
                                # Commit mỗi 5 articles
                                if articles_created % 5 == 0:
                                    print(f"   💾 Created {articles_created} articles so far...")
                            except Exception as commit_error:
                                # IntegrityError hoặc unique constraint violation
                                db.session.rollback()
                                error_msg = str(commit_error)
                                if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower():
                                    print(f"      ⏭️  Article already exists (duplicate detected during commit), skipping...")
                                    articles_skipped += 1
                                    crawled_urls_in_session.add(article_url)
                                else:
                                    print(f"      ⚠️  Error committing article: {commit_error}")
                                    raise  # Re-raise if not duplicate error
                        
                        except Exception as e:
                            print(f"      ⚠️  Error crawling article: {e}")
                            import traceback
                            traceback.print_exc()
                            db.session.rollback()
                            # Mark URL as attempted (failed) để tránh retry trong cùng session
                            crawled_urls_in_session.add(article_url)
                            continue
                    
                    print(f"\n✅ Home articles crawl completed:")
                    print(f"   - Created: {articles_created}")
                    print(f"   - Updated: {articles_updated}")
                    print(f"   - Skipped (already exist): {articles_skipped}")
            
            return layout_items
            
    except Exception as e:
        print(f"❌ Error crawling home layout: {e}")
        import traceback
        traceback.print_exc()
        return []


def save_layout_to_file(layout_items, output_file=None, language='da'):
    """
    Lưu layout structure vào file JSON
    
    ⚠️ QUAN TRỌNG: Luôn ghi đè file cũ (mode 'w') để đảm bảo layout mới nhất được lưu.
    
    Args:
        layout_items: List of layout items
        output_file: Path to output file (nếu None, tự động tạo tên)
        language: Language code để tạo tên file
    
    Returns:
        str: Path to saved file
    """
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"home_layout_{language}_{timestamp}.json"
    
    output_path = Path(__file__).parent / 'home_layouts' / output_file
    
    # ⚠️ QUAN TRỌNG: Đảm bảo directory tồn tại
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"   📁 Output directory: {output_path.parent} (exists: {output_path.parent.exists()})")
    except Exception as e:
        print(f"   ❌ Error creating directory {output_path.parent}: {e}")
        raise
    
    layout_data = {
        'language': language,
        'crawled_at': datetime.now().isoformat(),
        'total_items': len(layout_items),
        'layout_items': layout_items
    }
    
    # ⚠️ QUAN TRỌNG: Luôn ghi đè file cũ (mode 'w')
    try:
        # Check nếu file cũ tồn tại
        file_existed = output_path.exists()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)
        
        # Verify file đã được ghi
        if output_path.exists() and output_path.stat().st_size > 0:
            action = "Overwritten" if file_existed else "Created"
            print(f"   ✅ {action} layout file: {output_path}")
            print(f"      File size: {output_path.stat().st_size:,} bytes")
            print(f"      Total items: {len(layout_items)}")
        else:
            raise Exception(f"File was not written correctly (size: {output_path.stat().st_size if output_path.exists() else 0})")
            
    except PermissionError as e:
        print(f"   ❌ Permission denied writing to {output_path}: {e}")
        print(f"      Please check file permissions and directory ownership")
        raise
    except Exception as e:
        print(f"   ❌ Error saving layout to {output_path}: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return str(output_path)


def save_layout_to_csv(layout_items, output_file=None, language='da'):
    """
    Lưu layout structure vào file CSV
    
    Args:
        layout_items: List of layout items
        output_file: Path to output file (nếu None, tự động tạo tên)
        language: Language code để tạo tên file
    
    Returns:
        str: Path to CSV file
    """
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"home_layout_{language}_{timestamp}.csv"
    
    output_path = Path(__file__).parent / 'home_layouts' / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Group items theo row_index
    row_to_items = {}  # Map row_index -> list of items
    
    for item in layout_items:
        row_index = item.get('row_index', -1)
        if row_index not in row_to_items:
            row_to_items[row_index] = []
        row_to_items[row_index].append(item)
    
    # Sắp xếp các row_index và đánh số lại liên tục (bỏ qua hàng trống)
    sorted_row_indices = sorted([idx for idx in row_to_items.keys() if idx >= 0])
    
    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Hàng',
            'Thứ tự',
            'Dạng Layout',
            'URL',
            'Tiêu đề',
            'Grid Size',
            'Ghi chú'
        ])
        
        # Ghi chỉ các hàng có items, đánh số lại liên tục từ 1
        display_row_number = 1
        for original_row_idx in sorted_row_indices:
            items = row_to_items[original_row_idx]
            
            for item in items:
                display_order = item.get('display_order', 0)
                layout_type = item.get('layout_type', '')
                published_url = item.get('published_url', '')
                grid_size = item.get('grid_size', '')
                
                # Lấy title từ layout_data hoặc slider_title
                title = item.get('title', '')  # Lấy title từ layout_item nếu có
                note = ''
                
                if layout_type in ['slider', 'job_slider']:
                    slider_title = item.get('slider_title', '')
                    if slider_title:
                        title = slider_title
                    slider_articles = item.get('slider_articles', [])
                    note = f"Slider với {len(slider_articles)} articles"
                    
                    # Ghi slider container
                    writer.writerow([
                        display_row_number,  # Đánh số lại liên tục từ 1 (bỏ qua hàng trống)
                        display_order,
                        layout_type,
                        '',  # Slider container không có URL
                        title,
                        grid_size,
                        note
                    ])
                    
                    # Ghi từng article trong slider (mỗi article một dòng, cùng số hàng)
                    for slider_article in slider_articles:
                        slider_article_url = slider_article.get('published_url', '')
                        slider_article_title = slider_article.get('title', '')
                        
                        writer.writerow([
                            display_row_number,  # Cùng số hàng với slider container
                            '',  # Không có display_order riêng cho từng article trong slider
                            f'{layout_type}_item',  # Đánh dấu là item trong slider
                            slider_article_url,
                            slider_article_title,
                            '',  # Không có grid_size riêng
                            'Article trong slider'
                        ])
                elif layout_type in ['1_with_list_left', '1_with_list_right']:
                    # Article với list
                    list_title = item.get('list_title', '') or item.get('layout_data', {}).get('list_title', '')
                    list_items = item.get('list_items', []) or item.get('layout_data', {}).get('list_items', [])
                    note = f"List: {list_title} ({len(list_items)} items)"
                    
                    # Ghi article chính
                    writer.writerow([
                        display_row_number,
                        display_order,
                        layout_type,
                        published_url,
                        title,
                        grid_size,
                        note
                    ])
                    
                    # Ghi từng item trong list (mỗi item một dòng, cùng số hàng)
                    for list_item in list_items:
                        list_item_url = list_item.get('url', '')
                        list_item_title = list_item.get('title', '')
                        
                        writer.writerow([
                            display_row_number,  # Cùng số hàng với article chính
                            '',  # Không có display_order riêng
                            f'{layout_type}_list_item',  # Đánh dấu là item trong list
                            list_item_url,
                            list_item_title,
                            '',  # Không có grid_size riêng
                            f'Item trong list "{list_title}"'
                        ])
                else:
                    # Article thông thường (không phải slider)
                    if not title and published_url:
                        # Fallback: Lấy slug từ URL nếu không có title
                        try:
                            title = published_url.split('/')[-2] if published_url else ''
                        except:
                            title = ''
                    
                    writer.writerow([
                        display_row_number,  # Đánh số lại liên tục từ 1 (bỏ qua hàng trống)
                        display_order,
                        layout_type,
                        published_url,
                        title,
                        grid_size,
                        note
                    ])
            
            # Tăng số hàng sau khi ghi xong tất cả items trong hàng này
            display_row_number += 1
    
    print(f"\n💾 Saved layout CSV to: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description='Crawl home page layout structure (chỉ metadata, không tạo articles)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl DA home layout
  python scripts/crawl_home_layout.py --language da
  
  # Crawl KL home layout
  python scripts/crawl_home_layout.py --language kl --url https://kl.sermitsiaq.ag
  
  # Crawl và lưu vào file
  python scripts/crawl_home_layout.py --language da --save
  
  # Crawl với no-headless để debug
  python scripts/crawl_home_layout.py --language da --no-headless
        """
    )
    
    parser.add_argument('--url', '-u', default='https://www.sermitsiaq.ag',
                       help='URL của trang home (default: https://www.sermitsiaq.ag)')
    parser.add_argument('--language', '-l', default='da', choices=['da', 'kl', 'en'],
                       help='Language code (default: da)')
    parser.add_argument('--max-articles', '-n', type=int, default=0,
                       help='Số lượng articles tối đa (0 = tất cả)')
    parser.add_argument('--scroll-pause', type=float, default=2.0,
                       help='Thời gian chờ giữa các lần scroll (seconds)')
    parser.add_argument('--no-headless', action='store_true',
                       help='Chạy browser ở chế độ no-headless (để debug)')
    parser.add_argument('--save', '-s', action='store_true',
                       help='Lưu layout vào file JSON')
    parser.add_argument('--csv', action='store_true',
                       help='Lưu layout vào file CSV')
    parser.add_argument('--output', '-o',
                       help='Tên file output (nếu không có, tự động tạo)')
    
    args = parser.parse_args()
    
    # Adjust URL based on language
    if args.language == 'kl':
        if 'kl.' not in args.url:
            args.url = args.url.replace('www.', 'kl.')
    elif args.language == 'en':
        # EN có thể dùng cùng URL với DA hoặc URL riêng
        pass
    
    # Crawl layout
    layout_items = crawl_home_layout(
        home_url=args.url,
        language=args.language,
        max_articles=args.max_articles,
        scroll_pause=args.scroll_pause,
        headless=not args.no_headless
    )
    
    if not layout_items:
        print("❌ No layout items found")
        return
    
    # Save to file if requested
    if args.csv:
        csv_path = save_layout_to_csv(layout_items, args.output, args.language)
        print(f"\n✅ CSV file saved: {csv_path}")
    
    if args.save or args.output:
        json_path = save_layout_to_file(layout_items, args.output, args.language)
        if not args.csv:
            print(f"\n✅ JSON file saved: {json_path}")
    
    if not args.save and not args.csv and not args.output:
        # Print summary
        print(f"\n📋 Layout Items (first 10):")
        for i, item in enumerate(layout_items[:10], 1):
            print(f"   {i}. display_order={item['display_order']}, "
                  f"layout_type={item['layout_type']}, "
                  f"url={item['published_url'][:60] if item['published_url'] else 'N/A'}...")
        
        if len(layout_items) > 10:
            print(f"   ... and {len(layout_items) - 10} more items")
        
        print(f"\n💡 Tip: Use --save to save layout to file for later use")


if __name__ == '__main__':
    main()

