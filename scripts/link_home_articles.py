#!/usr/bin/env python3
"""
Script để link articles đã có trong DB với home layout structure
Chỉ update metadata: display_order, layout_type, layout_data, is_home, section
Không tạo articles mới, không crawl lại nội dung

Flow:
1. Load layout structure từ file JSON hoặc từ crawl trực tiếp
2. Với mỗi layout item:
   a. Tìm article trong DB bằng published_url
   b. Nếu tìm thấy → update metadata
   c. Nếu không tìm thấy → log warning (không tạo mới)
3. Xử lý slider containers đặc biệt
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article
from scripts.crawl_home_layout import crawl_home_layout, save_layout_to_file
from services.translation_service import translate_article
from scripts.translate_article_urls import translate_url
from scripts.generate_sitemaps import generate_sitemap
from scripts.google_translate_web_helper import translate_text_with_google_web
from sqlalchemy import or_
import time
from contextlib import contextmanager
from seleniumbase import SB

# User data directory riêng cho Google Translate Web
USER_DATA_DIR_TRANSLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data_translate')


def get_chrome_options_for_headless():
    """
    Trả về Chrome options cần thiết cho Linux headless server
    """
    return "no-sandbox,disable-dev-shm-usage,disable-gpu"


@contextmanager
def start_browser_for_translate(headless=True):
    """
    Start browser để sử dụng Google Translate Web cho title/title_parts
    
    Args:
        headless: Run browser in headless mode
    
    Yields:
        SB instance
    """
    chrome_opts = get_chrome_options_for_headless()
    os.makedirs(USER_DATA_DIR_TRANSLATE, exist_ok=True)
    os.chmod(USER_DATA_DIR_TRANSLATE, 0o755)
    
    sb_context = SB(uc=True, headless=headless, user_data_dir=USER_DATA_DIR_TRANSLATE, chromium_arg=chrome_opts)
    sb = sb_context.__enter__()
    
    try:
        yield sb
    finally:
        sb_context.__exit__(None, None, None)


def translate_title_with_web(text, source_lang='da', target_lang='en', sb=None, headless=True):
    """
    Dịch title sử dụng Google Translate Web
    
    Args:
        text: Text cần dịch
        source_lang: Source language code
        target_lang: Target language code
        sb: SeleniumBase instance (nếu có, sẽ dùng lại; nếu None, sẽ tạo mới)
        headless: Run browser in headless mode (chỉ dùng khi sb=None)
    
    Returns:
        Translated text hoặc None nếu lỗi
    """
    if not text or not text.strip():
        return text
    
    if sb:
        # Dùng browser instance đã có
        return translate_text_with_google_web(sb, text, source_lang, target_lang)
    else:
        # Tạo browser instance mới
        with start_browser_for_translate(headless=headless) as sb_instance:
            return translate_text_with_google_web(sb_instance, text, source_lang, target_lang)


def load_layout_from_file(layout_file):
    """
    Load layout structure từ file JSON
    
    Args:
        layout_file: Path to JSON file
    
    Returns:
        list: List of layout items
    """
    layout_path = Path(layout_file)
    if not layout_path.exists():
        print(f"❌ Layout file not found: {layout_file}")
        return None
    
    with open(layout_path, 'r', encoding='utf-8') as f:
        layout_data = json.load(f)
    
    print(f"✅ Loaded layout from {layout_file}")
    print(f"   Language: {layout_data.get('language', 'N/A')}")
    print(f"   Total items: {layout_data.get('total_items', 0)}")
    print(f"   Crawled at: {layout_data.get('crawled_at', 'N/A')}")
    
    return layout_data.get('layout_items', [])


def link_articles_with_layout(layout_items, language='da', dry_run=False, reset_first=True):
    """
    Link articles đã có trong DB với home layout structure
    
    Args:
        layout_items: List of layout items từ crawl
        language: Language code
        dry_run: Nếu True, chỉ log không update
        reset_first: Nếu True, reset tất cả is_home=False trước khi link (default: True)
    
    Returns:
        dict: Statistics về quá trình link
    """
    print(f"\n{'='*60}")
    print(f"🔗 Linking articles with home layout")
    print(f"{'='*60}")
    print(f"   Language: {language}")
    print(f"   Total layout items: {len(layout_items)}")
    print(f"   Dry run: {dry_run}")
    print(f"   Reset first: {reset_first}")
    print(f"   ⚠️  Note: Only linking articles with is_deleted=False or NULL")
    
    stats = {
        'total_items': len(layout_items),
        'articles_found': 0,
        'articles_updated': 0,
        'articles_not_found': 0,
        'sliders_processed': 0,
        'articles_disabled': 0,  # Articles set is_home=False (not in layout)
        'articles_enabled': 0,   # Articles set is_home=True (in layout)
        'errors': []
    }
    
    with app.app_context():
        # ⚠️ TỐI ƯU: Tạo set các URLs và slider keys từ layout trước
        # Để biết articles nào nên có is_home=True
        print(f"\n📋 Building layout reference sets...")
        layout_urls = set()  # URLs của articles trong layout
        layout_slider_keys = set()  # (layout_type, display_order) của sliders trong layout
        
        for layout_item in layout_items:
            published_url = layout_item.get('published_url', '')
            layout_type = layout_item.get('layout_type', '')
            display_order = layout_item.get('display_order', 0)
            
            if layout_type in ['slider', 'job_slider']:
                # Slider container: dùng (layout_type, display_order) làm key
                layout_slider_keys.add((layout_type, display_order))
            elif published_url:
                # Article thông thường: dùng published_url
                layout_urls.add(published_url)
        
        print(f"   Found {len(layout_urls)} article URLs in layout")
        print(f"   Found {len(layout_slider_keys)} slider containers in layout")
        
        # Pre-fetch tất cả articles của language này để lookup nhanh
        # ⚠️ QUAN TRỌNG: Chỉ lấy articles chưa bị mark deleted (is_deleted=False hoặc NULL)
        print(f"\n📚 Pre-fetching articles for language '{language}'...")
        all_articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != '',
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).all()
        
        # Tạo map: published_url -> Article
        articles_map = {}
        for article in all_articles:
            if article.published_url:
                # Có thể có nhiều articles cùng URL (khác language/section)
                # Lưu tất cả vào list
                if article.published_url not in articles_map:
                    articles_map[article.published_url] = []
                articles_map[article.published_url].append(article)
        
        print(f"   Found {len(articles_map)} unique URLs in database")
        
        # ⚠️ TỐI ƯU: Thay vì reset tất cả, chỉ update articles cần thay đổi
        if reset_first:
            print(f"\n🔄 Optimizing is_home flags (only update changed articles)...")
            
            # Tìm articles có is_home=True nhưng KHÔNG trong layout → set is_home=False
            articles_to_disable = []
            
            # 1. Articles với published_url không trong layout
            # ⚠️ Chỉ disable articles chưa bị mark deleted
            articles_with_url = Article.query.filter(
                Article.language == language,
                Article.is_home == True,
                Article.published_url.isnot(None),
                Article.published_url != '',
                Article.published_url.notin_(layout_urls),
                or_(Article.is_deleted == False, Article.is_deleted.is_(None))
            ).all()
            
            for article in articles_with_url:
                # Với 1_with_list_left/right, chỉ disable nếu section='home' (vì chúng chỉ có ở home)
                if article.layout_type in ['1_with_list_left', '1_with_list_right']:
                    if article.section == 'home':
                        articles_to_disable.append(article)
                else:
                    # Với articles khác, disable nếu không trong layout
                    articles_to_disable.append(article)
            
            # 2. Slider containers không trong layout
            # ⚠️ Chỉ disable slider containers chưa bị mark deleted
            slider_containers = Article.query.filter(
                Article.language == language,
                Article.is_home == True,
                Article.layout_type.in_(['slider', 'job_slider']),
                Article.section == 'home',
                or_(Article.is_deleted == False, Article.is_deleted.is_(None))
            ).all()
            
            for slider in slider_containers:
                slider_key = (slider.layout_type, slider.display_order)
                if slider_key not in layout_slider_keys:
                    articles_to_disable.append(slider)
            
            if not dry_run:
                for article in articles_to_disable:
                    article.is_home = False
                if articles_to_disable:
                    db.session.commit()
                    stats['articles_disabled'] = len(articles_to_disable)
                    print(f"   ✅ Set is_home=False for {len(articles_to_disable)} articles not in layout")
                else:
                    print(f"   ✅ No articles to disable")
            else:
                stats['articles_disabled'] = len(articles_to_disable)
                print(f"   ⚠️  Would set is_home=False for {len(articles_to_disable)} articles (dry run)")
        
        # Process từng layout item
        print(f"\n🔄 Processing layout items...")
        updated_article_ids = set()
        
        # ⚠️ QUAN TRỌNG: Sắp xếp layout items để ưu tiên items có row_index >= 0
        # Nếu một article xuất hiện nhiều lần trong layout, ưu tiên layout item có row_index >= 0
        # (bỏ qua các items từ NUUK slider hoặc items không có row_index)
        print(f"   📋 Sorting layout items to prioritize row_index >= 0...")
        layout_items_sorted = sorted(layout_items, key=lambda x: (
            x.get('row_index', -1) < 0,  # row_index < 0 sẽ ở sau
            x.get('display_order', 999999)  # Sau đó sắp xếp theo display_order
        ))
        
        # Đếm số items bị thay đổi thứ tự
        items_reordered = sum(1 for i, (orig, sorted_item) in enumerate(zip(layout_items, layout_items_sorted)) if orig != sorted_item)
        if items_reordered > 0:
            print(f"   ✅ Reordered {items_reordered} layout items to prioritize row_index >= 0")
        
        # Track các URL đã được xử lý để tránh update nhiều lần
        processed_urls = set()  # Track các URL đã được xử lý
        
        for idx, layout_item in enumerate(layout_items_sorted, 1):
            try:
                published_url = layout_item.get('published_url', '')
                layout_type = layout_item.get('layout_type', '')
                display_order = layout_item.get('display_order', 0)
                
                # Xử lý 5_articles (NUUK slider) đặc biệt
                # 5_articles cũng là slider container, nhưng chỉ có 1 record duy nhất mỗi ngôn ngữ
                # → Tìm và update thay vì tạo mới (tránh duplicates)
                if layout_type == '5_articles':
                    stats['sliders_processed'] += 1
                    print(f"   [{idx}/{len(layout_items)}] Processing 5_articles (NUUK): (display_order={display_order})")
                    
                    # Tìm 5_articles record mới nhất cho language này
                    # ⚠️ Chỉ filter by (section='home', language, layout_type='5_articles')
                    # KHÔNG dùng display_order vì có thể thay đổi
                    existing_5articles = Article.query.filter_by(
                        section='home',
                        language=language,
                        layout_type='5_articles'
                    ).filter(
                        or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                    ).order_by(Article.created_at.desc()).first()
                    
                    if existing_5articles:
                        # Update existing record
                        needs_update = False
                        was_home = existing_5articles.is_home
                        new_layout_data = layout_item.get('layout_data', {})
                        new_grid_size = layout_item.get('grid_size', 6)
                        new_title = layout_item.get('title', '')
                        
                        # Check các fields cần update
                        if existing_5articles.display_order != display_order:
                            needs_update = True
                        if existing_5articles.grid_size != new_grid_size:
                            needs_update = True
                        if existing_5articles.title != new_title:
                            needs_update = True
                        if existing_5articles.layout_data != new_layout_data:
                            needs_update = True
                        if not was_home:
                            needs_update = True
                        
                        if not dry_run and needs_update:
                            existing_5articles.display_order = display_order
                            existing_5articles.layout_data = new_layout_data
                            existing_5articles.grid_size = new_grid_size
                            existing_5articles.title = new_title
                            existing_5articles.is_home = True
                            existing_5articles.section = 'home'
                            existing_5articles.element_guid = layout_item.get('element_guid', '')
                            
                            if existing_5articles.id not in updated_article_ids:
                                updated_article_ids.add(existing_5articles.id)
                                stats['articles_updated'] += 1
                                if not was_home:
                                    stats['articles_enabled'] += 1
                                db.session.commit()
                            
                            print(f"      ✅ Updated 5_articles (ID: {existing_5articles.id})")
                        elif not dry_run:
                            print(f"      ⏭️  5_articles already up-to-date (ID: {existing_5articles.id})")
                        else:
                            print(f"      ⚠️  Would update 5_articles (ID: {existing_5articles.id}) - dry run")
                    else:
                        # 5_articles chưa tồn tại → tạo mới
                        if not dry_run:
                            new_5articles = Article(
                                published_url='',  # 5_articles container không có URL
                                layout_type='5_articles',
                                display_order=display_order,
                                layout_data=layout_item.get('layout_data', {}),
                                grid_size=layout_item.get('grid_size', 6),
                                section='home',
                                is_home=True,
                                language=language,
                                title=layout_item.get('title', ''),
                                slug='',
                                element_guid=layout_item.get('element_guid', ''),
                                k5a_url='',
                                site_alias='sermitsiaq',
                                instance='',
                                is_paywall=False,
                                paywall_class=''
                            )
                            db.session.add(new_5articles)
                            db.session.commit()
                            stats['articles_updated'] += 1
                            print(f"      ✅ Created 5_articles (ID: {new_5articles.id})")
                        else:
                            print(f"      ⚠️  Would create 5_articles (dry run)")
                    
                    # Articles trong 5_articles slider đã được lưu trong layout_data
                    slider_articles = layout_item.get('layout_data', {}).get('slider_articles', [])
                    if slider_articles:
                        print(f"         📋 5_articles contains {len(slider_articles)} articles (stored in layout_data only)")
                    
                    continue
                
                # Xử lý slider containers đặc biệt
                if layout_type in ['slider', 'job_slider']:
                    stats['sliders_processed'] += 1
                    print(f"   [{idx}/{len(layout_items)}] Processing slider: {layout_type} (display_order={display_order})")
                    
                    # Với slider, tìm hoặc tạo slider container article
                    # Slider container không có published_url, dùng (layout_type, display_order) làm key
                    # ⚠️ KHÔNG filter is_home=True vì có thể slider đang is_home=False cần được enable
                    # ⚠️ Chỉ tìm slider chưa bị mark deleted
                    existing_slider = Article.query.filter_by(
                        section='home',
                        language=language,
                        layout_type=layout_type,
                        display_order=display_order
                    ).filter(
                        or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                    ).first()
                    
                    if existing_slider:
                        # ⚠️ TỐI ƯU: Check xem có cần update không
                        needs_update = False
                        was_home = existing_slider.is_home
                        new_layout_data = layout_item.get('layout_data', {})
                        new_grid_size = layout_item.get('grid_size', 6)
                        new_title = layout_item.get('slider_title', '')
                        
                        # Check các fields cần update
                        if existing_slider.display_order != display_order:
                            needs_update = True
                        if existing_slider.layout_type != layout_type:
                            needs_update = True
                        if existing_slider.grid_size != new_grid_size:
                            needs_update = True
                        if existing_slider.title != new_title:
                            needs_update = True
                        if existing_slider.layout_data != new_layout_data:
                            needs_update = True
                        if not was_home:
                            needs_update = True  # Cần enable is_home
                        
                        # Update existing slider container chỉ khi cần
                        if not dry_run and needs_update:
                            existing_slider.display_order = display_order
                            existing_slider.layout_type = layout_type
                            existing_slider.layout_data = new_layout_data
                            existing_slider.grid_size = new_grid_size
                            existing_slider.title = new_title
                            existing_slider.is_home = True
                            existing_slider.section = 'home'
                            
                            if existing_slider.id not in updated_article_ids:
                                updated_article_ids.add(existing_slider.id)
                                stats['articles_updated'] += 1
                                if not was_home:
                                    stats['articles_enabled'] += 1
                                db.session.commit()
                            
                            print(f"      ✅ Updated slider container (ID: {existing_slider.id})")
                        elif not dry_run:
                            print(f"      ⏭️  Slider container already up-to-date (ID: {existing_slider.id})")
                        else:
                            print(f"      ⚠️  Would update slider container (ID: {existing_slider.id}) - dry run")
                    else:
                        # Slider container chưa tồn tại → tạo mới (chỉ container, không có content)
                        if not dry_run:
                            new_slider = Article(
                                published_url='',  # Slider container không có URL
                                layout_type=layout_type,
                                display_order=display_order,
                                layout_data=layout_item.get('layout_data', {}),
                                grid_size=layout_item.get('grid_size', 6),
                                section='home',
                                is_home=True,
                                language=language,
                                title=layout_item.get('slider_title', ''),
                                slug='',
                                k5a_url=layout_item.get('k5a_url', ''),
                                site_alias='sermitsiaq',
                                instance='',
                                is_paywall=False,
                                paywall_class=''
                            )
                            db.session.add(new_slider)
                            db.session.commit()
                            stats['articles_updated'] += 1
                            print(f"      ✅ Created slider container (ID: {new_slider.id})")
                        else:
                            print(f"      ⚠️  Would create slider container (dry run)")
                    
                    # ⚠️ QUAN TRỌNG: KHÔNG tạo hoặc update articles trong slider
                    # Chỉ lưu thông tin articles trong layout_data của slider container
                    # Để tránh duplicate URLs và tránh update articles không cần thiết
                    slider_articles = layout_item.get('slider_articles', [])
                    if slider_articles:
                        print(f"         📋 Slider contains {len(slider_articles)} articles (stored in layout_data only)")
                        # Articles trong slider đã được lưu trong layout_data của slider container
                        # Không cần update is_home=True cho các articles này
                        # Vì chúng chỉ là thông tin reference, không phải articles thực sự trên home
                    
                    continue
                
                # Xử lý articles thông thường (có published_url)
                if not published_url:
                    print(f"   [{idx}/{len(layout_items)}] ⚠️  Skipping item without URL (layout_type={layout_type})")
                    continue
                
                print(f"   [{idx}/{len(layout_items)}] Processing: {published_url[:60]}... (layout_type={layout_type}, display_order={display_order})")
                
                # Xử lý list_items cho 1_with_list_left/right
                list_items = []
                list_title = ''
                if layout_type in ['1_with_list_left', '1_with_list_right']:
                    # Thử lấy từ nhiều nguồn
                    list_items = (layout_item.get('list_items') or 
                                 layout_item.get('layout_data', {}).get('list_items', []) or 
                                 [])
                    list_title = (layout_item.get('list_title') or 
                                 layout_item.get('layout_data', {}).get('list_title', '') or 
                                 '')
                    
                    # Debug logging
                    layout_data_dict = layout_item.get('layout_data', {})
                    print(f"      📋 Checking list_items for {layout_type}:")
                    print(f"         layout_item.get('list_items'): {layout_item.get('list_items')}")
                    print(f"         layout_data.get('list_items'): {layout_data_dict.get('list_items')}")
                    print(f"         Final list_items count: {len(list_items)}")
                    print(f"         Final list_title: '{list_title}'")
                    
                    if list_items:
                        print(f"      ✅ Found {len(list_items)} list items (title: {list_title})")
                    else:
                        print(f"      ⚠️  No list items found for {layout_type}")
                        print(f"         layout_item keys: {list(layout_item.keys())}")
                        if layout_item.get('layout_data'):
                            print(f"         layout_data keys: {list(layout_item.get('layout_data', {}).keys())}")
                
                # Tìm article trong DB
                # ⚠️ QUAN TRỌNG: 
                # - Layout được crawl từ DA URL → published_url trong layout là DA URL
                # - EN articles có: published_url = DA URL, published_url_en = EN URL
                # - Khi link EN, cần tìm EN article có published_url = DA URL (từ layout)
                # - Với 1_with_list_left/right: chỉ tìm articles có section='home' (vì chúng chỉ có ở home)
                matched_article = None
                
                # ⚠️ QUAN TRỌNG: Với 1_with_list_left/right, chỉ tìm articles có section='home'
                require_home_section = layout_type in ['1_with_list_left', '1_with_list_right']
                
                if published_url in articles_map:
                    # Tìm article cùng language
                    # Với EN: tìm EN article có published_url = DA URL (từ layout)
                    # Với DA: tìm DA article có published_url = DA URL (từ layout)
                    for article in articles_map[published_url]:
                        if article.language == language:
                            # Với 1_with_list_left/right: chỉ lấy article có section='home'
                            if require_home_section:
                                if article.section == 'home':
                                    matched_article = article
                                    break
                            else:
                                matched_article = article
                                break
                    
                    # Nếu không tìm thấy và language='en', thử tìm bằng cách khác
                    if not matched_article and language == 'en':
                        # Tìm DA article trước
                        da_article = None
                        for article in articles_map[published_url]:
                            if article.language == 'da':
                                # Với 1_with_list_left/right: chỉ lấy article có section='home'
                                if require_home_section:
                                    if article.section == 'home':
                                        da_article = article
                                        break
                                else:
                                    da_article = article
                                    break
                        
                        if da_article:
                            # Tìm EN version từ DA article
                            # Cách 1: Tìm bằng canonical_id (EN có canonical_id = DA.id)
                            # Với 1_with_list_left/right: chỉ tìm EN article có section='home'
                            # ⚠️ Chỉ tìm EN article chưa bị mark deleted
                            query = Article.query.filter_by(
                                canonical_id=da_article.id,
                                language='en'
                            ).filter(
                                or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                            )
                            if require_home_section:
                                query = query.filter_by(section='home')
                            en_article = query.first()
                            
                            if en_article:
                                matched_article = en_article
                                print(f"      🔍 Found EN article via canonical_id (DA ID: {da_article.id}, EN ID: {en_article.id})")
                                print(f"         EN published_url: {en_article.published_url[:60] if en_article.published_url else 'N/A'}...")
                                print(f"         EN published_url_en: {en_article.published_url_en[:60] if en_article.published_url_en else 'N/A'}...")
                                if require_home_section:
                                    print(f"         ✅ Section='home' (required for {layout_type})")
                            else:
                                # Không tìm thấy EN article → tự động tạo
                                if not dry_run:
                                    print(f"      🌐 EN article not found, creating from DA article (ID: {da_article.id})...")
                                    try:
                                        from services.translation_service import translate_article
                                        from scripts.translate_article_urls import translate_url
                                        
                                        # ⚠️ CRITICAL: Check lần cuối xem EN article đã tồn tại chưa
                                        # (có thể đã được tạo bởi iteration trước trong cùng 1 lần chạy)
                                        # ⚠️ Chỉ check EN article chưa bị mark deleted
                                        final_check = Article.query.filter_by(
                                            published_url=da_article.published_url,
                                            language='en'
                                        ).filter(
                                            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                                        )
                                        if require_home_section:
                                            final_check = final_check.filter_by(section='home')
                                        existing_en_final = final_check.first()
                                        
                                        if existing_en_final:
                                            print(f"      ⏭️  EN article found in final check (ID: {existing_en_final.id}), skipping creation...")
                                            matched_article = existing_en_final
                                            
                                            # Add to articles_map để tránh query lại
                                            if published_url not in articles_map:
                                                articles_map[published_url] = []
                                            articles_map[published_url].append(existing_en_final)
                                        else:
                                            # Translate article
                                            en_article = translate_article(
                                                da_article,
                                                target_language='en',
                                                delay=0.5
                                            )
                                            
                                            if en_article:
                                                # Translate URL cho EN article
                                                if da_article.published_url:
                                                    en_url = translate_url(da_article.published_url, delay=0.3)
                                                    if en_url:
                                                        en_article.published_url_en = en_url
                                                
                                                # Copy metadata từ DA article
                                                en_article.display_order = da_article.display_order
                                                en_article.layout_type = da_article.layout_type
                                                
                                                # ⚠️ QUAN TRỌNG: Copy section từ DA article
                                                # (Nếu DA được tạo từ home crawl → section='home', nếu từ section pages → section=<section_name>)
                                                en_article.section = da_article.section
                                                
                                                en_article.grid_size = da_article.grid_size
                                                en_article.is_home = da_article.is_home
                                                
                                                # Save vào database
                                                db.session.add(en_article)
                                                db.session.commit()
                                                
                                                matched_article = en_article
                                                print(f"      ✅ Created EN article (ID: {en_article.id})")
                                                
                                                # Add to articles_map để tránh query lại
                                                if published_url not in articles_map:
                                                    articles_map[published_url] = []
                                                articles_map[published_url].append(en_article)
                                            else:
                                                print(f"      ❌ Failed to translate article")
                                    except Exception as e:
                                        print(f"      ❌ Error creating EN article: {e}")
                                        db.session.rollback()
                                else:
                                    print(f"      ⚠️  Would create EN article from DA (dry run)")
                    
                    if matched_article:
                        stats['articles_found'] += 1
                        
                        # ⚠️ TỐI ƯU: Check xem có cần update không
                        needs_update = False
                        was_home = matched_article.is_home
                        
                        # Check các fields cần update
                        if matched_article.display_order != display_order:
                            needs_update = True
                        if matched_article.layout_type != layout_type:
                            needs_update = True
                        if matched_article.grid_size != layout_item.get('grid_size', 6):
                            needs_update = True
                        if not was_home:
                            needs_update = True  # Cần enable is_home
                        
                        # ⚠️ QUAN TRỌNG: Check layout_data có thay đổi không
                        # Merge các field metadata VÀ kicker/title fields từ layout mới
                        existing_layout_data = matched_article.layout_data or {}
                        
                        # Fields cần update từ layout mới:
                        # - Metadata: row_index, article_index_in_row, total_rows, kicker_below_classes, kicker_floating_classes, content_classes
                        # - Display fields: kicker_floating, kicker_below, title_parts
                        # - KHÔNG update: list_items, list_title (xử lý riêng phía dưới)
                        metadata_fields = ['row_index', 'article_index_in_row', 'total_rows', 'kicker_below_classes', 'kicker_floating_classes', 'content_classes']
                        
                        # Kicker/title fields: update cho DA và KL (được crawl riêng), KHÔNG update cho EN (đã translate)
                        if language in ['da', 'kl']:
                            # DA/KL articles: update tất cả fields từ home layout mới (crawl riêng cho mỗi language)
                            display_fields = ['kicker_floating', 'kicker_below', 'title_parts']
                        else:
                            # EN articles: KHÔNG update kicker/title fields (giữ nguyên đã translate từ DA)
                            display_fields = []
                        
                        all_fields = metadata_fields + display_fields
                        layout_data_changed = False
                        
                        # Check và merge các fields
                        for field in all_fields:
                            layout_value = layout_item.get(field) or (layout_item.get('layout_data', {}).get(field) if layout_item.get('layout_data') else None)
                            existing_value = existing_layout_data.get(field)
                            
                            if layout_value is not None and layout_value != existing_value:
                                existing_layout_data[field] = layout_value
                                layout_data_changed = True
                        
                        # ⚠️ QUAN TRỌNG: Với 1_with_list_left/right và EN articles:
                        # - KHÔNG update list_items và list_title từ layout file (vì layout file là DA)
                        # - Chỉ update nếu là DA articles (language='da')
                        # - EN articles đã có list_items và list_title đã được translate từ translate_article()
                        if layout_type in ['1_with_list_left', '1_with_list_right'] and language == 'da':
                            # Chỉ update cho DA articles
                            if list_title and list_title != existing_layout_data.get('list_title'):
                                existing_layout_data['list_title'] = list_title
                                layout_data_changed = True
                            if list_items and list_items != existing_layout_data.get('list_items'):
                                existing_layout_data['list_items'] = list_items
                                layout_data_changed = True
                        # Với EN articles: giữ nguyên list_items và list_title đã được translate
                        
                        # Check nếu layout_data có thay đổi
                        if layout_data_changed:
                            needs_update = True
                        
                        # merged_layout_data = existing_layout_data (đã được update ở trên)
                        merged_layout_data = existing_layout_data
                        
                        # Update metadata chỉ khi cần
                        if not dry_run and needs_update:
                            matched_article.display_order = display_order
                            matched_article.layout_type = layout_type
                            matched_article.grid_size = layout_item.get('grid_size', 6)
                            matched_article.is_home = True
                            
                            # ⚠️ CRITICAL: Chỉ update layout_data và flag_modified KHI layout_data thực sự thay đổi
                            # Tránh unnecessary updates và flag_modified calls
                            if layout_data_changed:
                                matched_article.layout_data = merged_layout_data
                                # SQLAlchemy doesn't auto-detect dict mutations in JSONB fields
                                from sqlalchemy.orm.attributes import flag_modified
                                flag_modified(matched_article, 'layout_data')
                                
                                # ⚠️ QUAN TRỌNG: Nếu là DA article và layout_data có display fields thay đổi
                                # → Tự động update EN article tương ứng (dịch lại display fields)
                                if language == 'da' and any(field in merged_layout_data for field in ['kicker_floating', 'kicker_below', 'title_parts']):
                                    # Tìm EN article tương ứng
                                    en_article = Article.query.filter_by(
                                        canonical_id=matched_article.id,
                                        language='en'
                                    ).filter(
                                        or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                                    ).first()
                                    
                                    if en_article:
                                        try:
                                            from deep_translator import GoogleTranslator
                                            translator = GoogleTranslator(source='da', target='en')
                                            
                                            # Get EN existing layout_data
                                            en_layout_data = en_article.layout_data or {}
                                            en_layout_data_changed = False
                                            
                                            # Translate kicker_floating
                                            if 'kicker_floating' in merged_layout_data and merged_layout_data['kicker_floating']:
                                                translated_kicker = translator.translate(merged_layout_data['kicker_floating'])
                                                if translated_kicker != en_layout_data.get('kicker_floating'):
                                                    en_layout_data['kicker_floating'] = translated_kicker
                                                    en_layout_data_changed = True
                                                    print(f"         🌐 Translated kicker_floating for EN: '{merged_layout_data['kicker_floating']}' → '{translated_kicker}'")
                                            
                                            # Copy kicker_floating_classes (không dịch)
                                            if 'kicker_floating_classes' in merged_layout_data:
                                                if en_layout_data.get('kicker_floating_classes') != merged_layout_data['kicker_floating_classes']:
                                                    en_layout_data['kicker_floating_classes'] = merged_layout_data['kicker_floating_classes']
                                                    en_layout_data_changed = True
                                            
                                            # Translate kicker_below
                                            if 'kicker_below' in merged_layout_data and merged_layout_data['kicker_below']:
                                                translated_kicker_below = translator.translate(merged_layout_data['kicker_below'])
                                                if translated_kicker_below != en_layout_data.get('kicker_below'):
                                                    en_layout_data['kicker_below'] = translated_kicker_below
                                                    en_layout_data_changed = True
                                            
                                            # Copy kicker_below_classes (không dịch)
                                            if 'kicker_below_classes' in merged_layout_data:
                                                if en_layout_data.get('kicker_below_classes') != merged_layout_data['kicker_below_classes']:
                                                    en_layout_data['kicker_below_classes'] = merged_layout_data['kicker_below_classes']
                                                    en_layout_data_changed = True
                                            
                                            # Translate title_parts
                                            # ⚠️ QUAN TRỌNG: Dùng EN article's title để reconstruct title_parts
                                            # thay vì dịch từng part riêng lẻ (tránh dịch sai tên riêng)
                                            if 'title_parts' in merged_layout_data and merged_layout_data['title_parts']:
                                                original_title_parts = merged_layout_data['title_parts']
                                                
                                                # Dùng EN article's title để reconstruct title_parts
                                                if en_article.title:
                                                    translated_title = en_article.title
                                                    
                                                    # Reconstruct title_parts từ translated_title
                                                    # Giữ nguyên color_class từ original parts
                                                    if ':' in translated_title:
                                                        # Split theo ":" để tìm highlighted part
                                                        parts = translated_title.split(':', 1)
                                                        translated_parts = [
                                                            {'text': parts[0] + ':', 'color_class': original_title_parts[0].get('color_class') if original_title_parts and isinstance(original_title_parts[0], dict) else None},
                                                            {'text': parts[1], 'color_class': None}
                                                        ]
                                                    else:
                                                        # Không có ":" - giữ highlight cho toàn bộ hoặc part đầu tiên
                                                        translated_parts = [
                                                            {'text': translated_title, 'color_class': original_title_parts[0].get('color_class') if original_title_parts and isinstance(original_title_parts[0], dict) else None}
                                                        ]
                                                    
                                                    if translated_parts != en_layout_data.get('title_parts'):
                                                        en_layout_data['title_parts'] = translated_parts
                                                        en_layout_data_changed = True
                                                        print(f"         ✅ Reconstructed title_parts from EN article title")
                                                else:
                                                    # Fallback: Dịch từng part bằng Google Translate Web nếu không có EN title
                                                    print(f"         🌐 Translating title_parts using Google Translate Web (fallback)...")
                                                translated_parts = []
                                                    
                                                    # Tạo browser instance để dịch title_parts
                                                    try:
                                                        with start_browser_for_translate(headless=True) as sb_web:
                                                for part in merged_layout_data['title_parts']:
                                                    if isinstance(part, dict) and 'text' in part:
                                                        original_text = part['text']
                                                        
                                                        # Preserve leading/trailing spaces
                                                        leading_space = ' ' if original_text.startswith(' ') else ''
                                                        trailing_space = ' ' if original_text.endswith(' ') and not original_text.endswith('\n') else ''
                                                        
                                                                    # Translate text bằng Google Translate Web
                                                        text_to_translate = original_text.strip()
                                                                    if text_to_translate:
                                                                        translated_text = translate_text_with_google_web(
                                                                            sb_web, 
                                                                            text_to_translate, 
                                                                            source_lang='da', 
                                                                            target_lang='en'
                                                                        )
                                                                        if translated_text:
                                                        # Restore spaces
                                                        translated_text = leading_space + translated_text + trailing_space
                                                                        else:
                                                                            # Fallback: giữ nguyên nếu dịch lỗi
                                                                            translated_text = original_text
                                                                    else:
                                                                        translated_text = original_text
                                                        
                                                        translated_parts.append({
                                                            'text': translated_text,
                                                            'color_class': part.get('color_class')
                                                        })
                                                                    
                                                                    # Delay giữa các lần dịch
                                                                    time.sleep(0.5)
                                                        
                                                if translated_parts != en_layout_data.get('title_parts'):
                                                    en_layout_data['title_parts'] = translated_parts
                                                    en_layout_data_changed = True
                                                            print(f"         ✅ Translated title_parts using Google Translate Web")
                                                    except Exception as e:
                                                        print(f"         ⚠️  Error translating title_parts with Google Translate Web: {e}")
                                                        # Fallback: giữ nguyên title_parts gốc
                                                        pass
                                            
                                            # Copy metadata fields (không dịch)
                                            for meta_field in ['row_index', 'article_index_in_row', 'total_rows', 'content_classes']:
                                                if meta_field in merged_layout_data:
                                                    if en_layout_data.get(meta_field) != merged_layout_data[meta_field]:
                                                        en_layout_data[meta_field] = merged_layout_data[meta_field]
                                                        en_layout_data_changed = True
                                            
                                            # Update EN article nếu có thay đổi
                                            if en_layout_data_changed:
                                                en_article.layout_data = en_layout_data
                                                flag_modified(en_article, 'layout_data')
                                                db.session.commit()
                                                print(f"         ✅ Updated EN article (ID: {en_article.id}) layout_data")
                                        except Exception as e:
                                            print(f"         ⚠️  Error updating EN article: {e}")
                                            # Continue processing, không rollback DA article
                            
                            # ⚠️ KHÔNG update section='home' - giữ nguyên section gốc
                            # ⚠️ KHÔNG set is_temp=True khi link (chỉ set khi crawl mới)
                            
                            # ⚠️ QUAN TRỌNG: Commit TRƯỚC KHI check duplicate
                            # để đảm bảo update được lưu ngay cả khi article xuất hiện nhiều lần trong layout
                            db.session.commit()
                            
                            # Track updated articles để báo cáo stats
                            if matched_article.id not in updated_article_ids:
                                updated_article_ids.add(matched_article.id)
                                stats['articles_updated'] += 1
                                if not was_home:
                                    stats['articles_enabled'] += 1
                            
                            # Mark URL as processed
                            processed_urls.add(published_url)
                            
                            print(f"      ✅ Updated article (ID: {matched_article.id})")
                            if require_home_section:
                                print(f"         ✅ Section='home' (required for {layout_type})")
                            if list_items:
                                print(f"         📋 List items saved: {len(list_items)} items")
                        elif not dry_run:
                            # Không cần update, nhưng vẫn mark URL as processed
                            processed_urls.add(published_url)
                            print(f"      ⏭️  Article already up-to-date (ID: {matched_article.id})")
                        else:
                            # Dry run
                            print(f"      ⚠️  Would update article (ID: {matched_article.id}) - dry run")
                    else:
                        if require_home_section:
                            print(f"      ⚠️  Article not found in DB with section='home' and language='{language}' (required for {layout_type}): {published_url[:60]}...")
                        else:
                            print(f"      ⚠️  Article found but language mismatch (need '{language}')")
                        stats['articles_not_found'] += 1
                else:
                    if require_home_section:
                        print(f"      ⚠️  Article not found in DB with section='home' and language='{language}' (required for {layout_type}): {published_url[:60]}...")
                    else:
                        print(f"      ⚠️  Article not found in DB: {published_url[:60]}...")
                    stats['articles_not_found'] += 1
                    stats['errors'].append({
                        'url': published_url,
                        'reason': 'not_found_in_db',
                        'layout_type': layout_type,
                        'require_home_section': require_home_section
                    })
                
            except Exception as e:
                error_msg = f"Error processing layout item {idx}: {e}"
                print(f"      ❌ {error_msg}")
                stats['errors'].append({
                    'index': idx,
                    'error': str(e)
                })
                if not dry_run:
                    db.session.rollback()
                continue
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ Linking completed")
        print(f"{'='*60}")
        print(f"   Total layout items: {stats['total_items']}")
        print(f"   Articles found: {stats['articles_found']}")
        print(f"   Articles updated: {stats['articles_updated']}")
        print(f"   Articles not found: {stats['articles_not_found']}")
        print(f"   Sliders processed: {stats['sliders_processed']}")
        if reset_first:
            print(f"   📊 Optimization stats:")
            print(f"      Articles disabled (not in layout): {stats['articles_disabled']}")
            print(f"      Articles enabled (in layout): {stats['articles_enabled']}")
        if stats['errors']:
            print(f"   Errors: {len(stats['errors'])}")
            print(f"\n   First 5 errors:")
            for error in stats['errors'][:5]:
                print(f"      - {error}")
        
        return stats


def cleanup_5articles_duplicates(language='da', dry_run=False):
    """
    Cleanup các duplicate 5_articles records, chỉ giữ lại 1 record mới nhất
    
    Args:
        language: Language code
        dry_run: Nếu True, chỉ log không xóa
    
    Returns:
        dict: Statistics về quá trình cleanup
    """
    print(f"\n{'='*60}")
    print(f"🧹 Cleaning up 5_articles duplicates")
    print(f"{'='*60}")
    print(f"   Language: {language}")
    print(f"   Dry run: {dry_run}")
    
    stats = {
        'total_found': 0,
        'kept': 0,
        'deleted': 0
    }
    
    with app.app_context():
        # Tìm tất cả 5_articles cho language này
        all_5articles = Article.query.filter_by(
            section='home',
            language=language,
            layout_type='5_articles'
        ).filter(
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).order_by(Article.created_at.desc()).all()
        
        stats['total_found'] = len(all_5articles)
        
        if stats['total_found'] == 0:
            print("   ℹ️  No 5_articles found")
            return stats
        
        if stats['total_found'] == 1:
            print(f"   ✅ Only 1 5_articles found (ID: {all_5articles[0].id}) - no cleanup needed")
            stats['kept'] = 1
            return stats
        
        # Giữ record mới nhất (đầu tiên trong list đã sort desc)
        latest = all_5articles[0]
        duplicates = all_5articles[1:]
        
        print(f"   Found {len(all_5articles)} 5_articles records")
        print(f"   ✅ Keeping latest record (ID: {latest.id}, Created: {latest.created_at})")
        stats['kept'] = 1
        
        # Xóa các duplicates
        for duplicate in duplicates:
            print(f"   🗑️  Deleting duplicate (ID: {duplicate.id}, Created: {duplicate.created_at})")
            if not dry_run:
                db.session.delete(duplicate)
                stats['deleted'] += 1
            else:
                print(f"      ⚠️  Would delete (dry run)")
        
        if not dry_run and stats['deleted'] > 0:
            db.session.commit()
            print(f"\n   ✅ Cleanup completed: {stats['deleted']} duplicates deleted")
        elif dry_run:
            print(f"\n   ⚠️  Dry run: would delete {len(duplicates)} duplicates")
        
        return stats


def mark_list_articles_for_deletion(language='da', dry_run=False):
    """
    Mark các 1_with_list_left/right articles là is_deleted=True trước khi crawl lại
    Mục đích: Đánh dấu để xóa sau khi đã tạo mới và link xong
    
    Args:
        language: Language code
        dry_run: Nếu True, chỉ log không update
    
    Returns:
        dict: Statistics về quá trình mark
    """
    print(f"\n{'='*60}")
    print(f"🗑️  Marking old 1_with_list articles for deletion")
    print(f"{'='*60}")
    print(f"   Language: {language}")
    print(f"   Dry run: {dry_run}")
    
    stats = {
        'marked': 0,
        'errors': 0
    }
    
    with app.app_context():
        try:
            # Find all 1_with_list_left/right articles chưa bị mark deleted
            list_articles = Article.query.filter(
                Article.language == language,
                Article.layout_type.in_(['1_with_list_left', '1_with_list_right']),
                Article.section == 'home',
                or_(Article.is_deleted == False, Article.is_deleted.is_(None))
            ).all()
            
            print(f"   Found {len(list_articles)} 1_with_list articles to mark")
            
            if not dry_run:
                for article in list_articles:
                    article.is_deleted = True
                    stats['marked'] += 1
                
                if list_articles:
                    db.session.commit()
                    print(f"   ✅ Marked {stats['marked']} articles for deletion")
                else:
                    print(f"   ℹ️  No articles to mark")
            else:
                stats['marked'] = len(list_articles)
                print(f"   ⚠️  Would mark {len(list_articles)} articles (dry run)")
        
        except Exception as e:
            stats['errors'] += 1
            print(f"   ❌ Error marking articles: {e}")
            if not dry_run:
                db.session.rollback()
            raise
    
    return stats


def delete_marked_articles(language='da', dry_run=False):
    """
    Delete các articles có is_deleted=True sau khi đã tạo mới và link xong
    
    Args:
        language: Language code
        dry_run: Nếu True, chỉ log không delete
    
    Returns:
        dict: Statistics về quá trình delete
    """
    print(f"\n{'='*60}")
    print(f"🗑️  Deleting old marked articles")
    print(f"{'='*60}")
    print(f"   Language: {language}")
    print(f"   Dry run: {dry_run}")
    
    stats = {
        'deleted': 0,
        'errors': 0
    }
    
    with app.app_context():
        try:
            # Find all articles with is_deleted=True for this language
            marked_articles = Article.query.filter(
                Article.language == language,
                Article.is_deleted == True
            ).all()
            
            print(f"   Found {len(marked_articles)} marked articles to delete")
            
            if not dry_run:
                for article in marked_articles:
                    db.session.delete(article)
                    stats['deleted'] += 1
                
                if marked_articles:
                    db.session.commit()
                    print(f"   ✅ Deleted {stats['deleted']} old articles")
                else:
                    print(f"   ℹ️  No articles to delete")
            else:
                stats['deleted'] = len(marked_articles)
                print(f"   ⚠️  Would delete {len(marked_articles)} articles (dry run)")
        
        except Exception as e:
            stats['errors'] += 1
            print(f"   ❌ Error deleting articles: {e}")
            if not dry_run:
                db.session.rollback()
            raise
    
    return stats


def translate_slider_containers(language='da', dry_run=False, delay=0.5):
    """
    Translate slider/job_slider containers từ DA sang EN
    
    Args:
        language: Language của source sliders (chỉ 'da' được support)
        dry_run: Nếu True, chỉ log không translate
        delay: Delay giữa các lần translate (giây)
    
    Returns:
        dict: Statistics về quá trình translate
    """
    if language != 'da':
        print(f"⚠️  Only 'da' language is supported for translating slider containers")
        return {'translated': 0, 'skipped': 0, 'errors': 0}
    
    print(f"\n{'='*60}")
    print(f"🌐 Translating slider containers from DA to EN")
    print(f"{'='*60}")
    print(f"   Dry run: {dry_run}")
    
    stats = {
        'checked': 0,
        'translated': 0,
        'skipped': 0,
        'errors': 0,
        'error_list': []
    }
    
    with app.app_context():
        # Tìm DA sliders
        da_sliders = Article.query.filter(
            Article.layout_type.in_(['slider', 'job_slider']),
            Article.section == 'home',
            Article.language == 'da',
            Article.is_home == True
        ).order_by(Article.display_order).all()
        
        print(f"   Found {len(da_sliders)} DA slider containers to check")
        
        for idx, da_slider in enumerate(da_sliders, 1):
            try:
                stats['checked'] += 1
                
                print(f"   [{idx}/{len(da_sliders)}] Processing {da_slider.layout_type} (display_order={da_slider.display_order})")
                
                # Check xem đã có EN version chưa
                en_slider = Article.query.filter_by(
                    layout_type=da_slider.layout_type,
                    section='home',
                    language='en',
                    display_order=da_slider.display_order,
                    is_home=True
                ).first()
                
                if en_slider:
                    print(f"      ✅ EN version exists (ID: {en_slider.id}), checking if needs update...")
                    
                    # Check nếu EN slider title vẫn là DA
                    en_title = en_slider.title
                    da_title = da_slider.title
                    
                    needs_translation = (
                        en_title == da_title or 
                        not en_title or 
                        (en_slider.layout_data and en_slider.layout_data.get('slider_title') == da_slider.layout_data.get('slider_title'))
                    )
                    
                    if not needs_translation:
                        print(f"         ✅ Already translated, skipping")
                        stats['skipped'] += 1
                        continue
                    
                    print(f"         🔄 Needs translation (title: '{en_title}' == '{da_title}')")
                else:
                    # Chưa có EN version → tạo mới
                    print(f"      🌐 Creating EN slider container...")
                    
                    if not dry_run:
                        en_slider = Article(
                            published_url='',
                            layout_type=da_slider.layout_type,
                            display_order=da_slider.display_order,
                            layout_data={},
                            grid_size=da_slider.grid_size,
                            section='home',
                            is_home=True,
                            language='en',
                            title='',
                            slug='',
                            k5a_url=da_slider.k5a_url,
                            site_alias='sermitsiaq',
                            instance='',
                            is_paywall=False,
                            paywall_class=''
                        )
                        db.session.add(en_slider)
                        db.session.flush()  # Get ID but don't commit yet
                        print(f"         ✅ Created EN slider container (ID: {en_slider.id})")
                
                # Translate slider content
                if not dry_run:
                    try:
                        # ⚠️ QUAN TRỌNG: Dùng Google Translate Web cho title và slider_articles titles
                        # Tạo browser instance để dịch
                        with start_browser_for_translate(headless=True) as sb_web:
                            # Translate title bằng Google Translate Web
                        if da_slider.title:
                                translated_title = translate_text_with_google_web(
                                    sb_web, 
                                    da_slider.title, 
                                    source_lang='da', 
                                    target_lang='en'
                                )
                                if translated_title:
                                    en_slider.title = translated_title
                                    print(f"         📝 Translated title (Google Translate Web): '{da_slider.title}' → '{en_slider.title}'")
                                    time.sleep(delay)
                        
                        # Translate layout_data
                        if da_slider.layout_data:
                            en_layout_data = da_slider.layout_data.copy()
                            
                                # Translate slider_title bằng Google Translate Web
                            if 'slider_title' in en_layout_data and en_layout_data['slider_title']:
                                    translated_slider_title = translate_text_with_google_web(
                                        sb_web,
                                        en_layout_data['slider_title'],
                                        source_lang='da',
                                        target_lang='en'
                                    )
                                    if translated_slider_title:
                                        en_layout_data['slider_title'] = translated_slider_title
                                        print(f"         📝 Translated slider_title (Google Translate Web): '{en_layout_data.get('slider_title')}' → '{translated_slider_title}'")
                                time.sleep(delay)
                            
                                # Translate header_link text (for job_slider) - dùng deep_translator (không phải title)
                                from deep_translator import GoogleTranslator
                                translator = GoogleTranslator(source='da', target='en')
                            if 'header_link' in en_layout_data and en_layout_data['header_link']:
                                header_link = en_layout_data['header_link']
                                if isinstance(header_link, dict) and 'text' in header_link:
                                    translated_text = translator.translate(header_link['text'])
                                    en_layout_data['header_link']['text'] = translated_text
                                    print(f"         📝 Translated header_link: '{header_link['text']}' → '{translated_text}'")
                                    time.sleep(delay)
                            
                                # Translate slider_articles titles bằng Google Translate Web
                            if 'slider_articles' in en_layout_data and isinstance(en_layout_data['slider_articles'], list):
                                translated_articles = []
                                for article in en_layout_data['slider_articles']:
                                    if isinstance(article, dict):
                                        article_copy = article.copy()
                                            # Translate title bằng Google Translate Web
                                        if 'title' in article_copy and article_copy['title']:
                                                translated_article_title = translate_text_with_google_web(
                                                    sb_web,
                                                    article_copy['title'],
                                                    source_lang='da',
                                                    target_lang='en'
                                                )
                                                if translated_article_title:
                                                    article_copy['title'] = translated_article_title
                                            time.sleep(delay)
                                            # Translate kicker if exists - dùng deep_translator (không phải title)
                                        if 'kicker' in article_copy and article_copy['kicker']:
                                            article_copy['kicker'] = translator.translate(article_copy['kicker'])
                                            time.sleep(delay)
                                        translated_articles.append(article_copy)
                                
                                en_layout_data['slider_articles'] = translated_articles
                                    print(f"         📝 Translated {len(translated_articles)} slider articles (titles via Google Translate Web)")
                            
                            en_slider.layout_data = en_layout_data
                        
                        db.session.commit()
                        stats['translated'] += 1
                        print(f"      ✅ Translated and saved EN slider container")
                        
                    except Exception as e:
                        stats['errors'] += 1
                        stats['error_list'].append({
                            'da_id': da_slider.id,
                            'error': str(e)
                        })
                        print(f"      ❌ Error translating slider: {e}")
                        db.session.rollback()
                else:
                    # Dry run
                    stats['translated'] += 1
                    print(f"      ⚠️  Would translate slider (dry run)")
            
            except Exception as e:
                stats['errors'] += 1
                stats['error_list'].append({
                    'da_id': da_slider.id if 'da_slider' in locals() else 'N/A',
                    'error': str(e)
                })
                print(f"   [{idx}/{len(da_sliders)}] ❌ Error: {e}")
                if not dry_run:
                    db.session.rollback()
                continue
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ Slider translation completed")
        print(f"{'='*60}")
        print(f"   Sliders checked: {stats['checked']}")
        print(f"   Sliders translated: {stats['translated']}")
        print(f"   Sliders skipped: {stats['skipped']}")
        print(f"   Errors: {stats['errors']}")
        if stats['error_list']:
            print(f"\n   First 5 errors:")
            for error in stats['error_list'][:5]:
                print(f"      - DA ID {error['da_id']}: {error['error']}")
        
        return stats


def create_or_update_5_articles_en(dry_run=False, delay=0.5):
    """
    Xử lý riêng cho 5_articles: Tạo/Update EN từ DA MỚI NHẤT
    
    ⚠️ LOGIC ĐẶC BIỆT:
    - 5_articles KHÔNG CÓ published_url (cả DA và EN)
    - Chỉ nên có TỐI ĐA 1 EN 5_article (dịch từ DA mới nhất)
    - Nếu có nhiều EN 5_articles → XÓA cũ, giữ/tạo mới từ DA mới nhất
    
    Args:
        dry_run: Nếu True, chỉ log không thực hiện
        delay: Delay giữa các lần translate (giây)
    
    Returns:
        dict: Statistics
    """
    print(f"\n{'='*60}")
    print(f"📦 Processing 5_articles EN (from latest DA)")
    print(f"{'='*60}")
    
    stats = {
        'da_found': 0,
        'en_found': 0,
        'en_created': 0,
        'en_updated': 0,
        'en_deleted': 0,
        'errors': 0
    }
    
    with app.app_context():
        # 1. Lấy DA 5_article MỚI NHẤT
        da_latest = Article.query.filter(
            Article.language == 'da',
            Article.layout_type == '5_articles',
            Article.section == 'home',
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).order_by(Article.created_at.desc()).first()
        
        if not da_latest:
            print("   ⚠️  No DA 5_articles found")
            return stats
        
        stats['da_found'] = 1
        print(f"   ✅ Found DA 5_article (ID: {da_latest.id})")
        print(f"      Title: {da_latest.title[:60] if da_latest.title else 'N/A'}...")
        print(f"      Created: {da_latest.created_at}")
        
        # 2. Tìm TẤT CẢ EN 5_articles hiện có
        en_articles = Article.query.filter(
            Article.language == 'en',
            Article.layout_type == '5_articles',
            Article.section == 'home',
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).order_by(Article.created_at.desc()).all()
        
        stats['en_found'] = len(en_articles)
        print(f"   📊 Found {len(en_articles)} existing EN 5_articles")
        
        # 3. Xác định action
        if len(en_articles) == 0:
            # Chưa có → CREATE
            print(f"   🌐 No EN 5_article found → Creating new one")
            
            if not dry_run:
                try:
                    en_article = translate_article(
                        da_latest,
                        target_language='en',
                        delay=delay
                    )
                    
                    if not en_article:
                        print(f"      ❌ translate_article() returned None")
                        stats['errors'] += 1
                        return stats
                    
                    # Set metadata
                    en_article.layout_type = '5_articles'
                    en_article.section = 'home'
                    en_article.is_home = da_latest.is_home
                    en_article.display_order = da_latest.display_order
                    en_article.grid_size = da_latest.grid_size
                    
                    # Copy image_data
                    if da_latest.image_data:
                        en_article.image_data = da_latest.image_data
                    
                    # Copy layout_data
                    if da_latest.layout_data:
                        en_article.layout_data = da_latest.layout_data.copy() if isinstance(da_latest.layout_data, dict) else da_latest.layout_data
                    
                    db.session.add(en_article)
                    db.session.commit()
                    
                    stats['en_created'] = 1
                    print(f"      ✅ Created EN 5_article (ID: {en_article.id})")
                except Exception as e:
                    print(f"      ❌ Error creating EN article: {e}")
                    db.session.rollback()
                    stats['errors'] += 1
            else:
                print(f"      📝 Would create EN 5_article (dry run)")
        
        elif len(en_articles) == 1:
            # Đã có 1 → UPDATE từ DA mới nhất
            en_existing = en_articles[0]
            print(f"   ♻️  Found 1 EN 5_article (ID: {en_existing.id}) → Updating from latest DA")
            
            if not dry_run:
                try:
                    updated = False
                    
                    # Update title nếu DA có title mới - dùng Google Translate Web
                    if da_latest.title:
                        print(f"      🌐 Translating title using Google Translate Web...")
                        translated_title = translate_title_with_web(
                            da_latest.title,
                            source_lang='da',
                            target_lang='en',
                            headless=True
                        )
                        if translated_title and translated_title != en_existing.title:
                            en_existing.title = translated_title
                            updated = True
                            print(f"         ✅ Translated title: '{da_latest.title}' → '{translated_title}'")
                    
                    # Update metadata
                    if en_existing.display_order != da_latest.display_order:
                        en_existing.display_order = da_latest.display_order
                        updated = True
                    
                    if en_existing.grid_size != da_latest.grid_size:
                        en_existing.grid_size = da_latest.grid_size
                        updated = True
                    
                    if en_existing.is_home != da_latest.is_home:
                        en_existing.is_home = da_latest.is_home
                        updated = True
                    
                    # Update image_data
                    if da_latest.image_data and en_existing.image_data != da_latest.image_data:
                        en_existing.image_data = da_latest.image_data
                        updated = True
                    
                    if updated:
                        db.session.commit()
                        stats['en_updated'] = 1
                        print(f"      ✅ Updated EN 5_article")
                    else:
                        print(f"      ⏭️  EN 5_article already up to date")
                except Exception as e:
                    print(f"      ❌ Error updating EN article: {e}")
                    db.session.rollback()
                    stats['errors'] += 1
            else:
                print(f"      📝 Would update EN 5_article (dry run)")
        
        else:
            # Có NHIỀU HƠN 1 → Giữ 1 mới nhất, XÓA cũ, UPDATE từ DA
            en_keep = en_articles[0]  # Mới nhất
            en_to_delete = en_articles[1:]  # Các cũ khác
            
            print(f"   ⚠️  Found {len(en_articles)} EN 5_articles (should be only 1)")
            print(f"      → Keeping EN ID {en_keep.id} (newest)")
            print(f"      → Deleting {len(en_to_delete)} old EN articles")
            
            if not dry_run:
                try:
                    # Xóa các EN cũ
                    for old_en in en_to_delete:
                        print(f"         🗑️  Deleting old EN ID {old_en.id}")
                        db.session.delete(old_en)
                    
                    stats['en_deleted'] = len(en_to_delete)
                    
                    # Update EN giữ lại từ DA mới nhất
                    updated = False
                    
                    if da_latest.title:
                        print(f"      🌐 Translating title using Google Translate Web...")
                        translated_title = translate_title_with_web(
                            da_latest.title,
                            source_lang='da',
                            target_lang='en',
                            headless=True
                        )
                        if translated_title and translated_title != en_keep.title:
                            en_keep.title = translated_title
                            updated = True
                            print(f"         ✅ Translated title: '{da_latest.title}' → '{translated_title}'")
                    
                    if en_keep.display_order != da_latest.display_order:
                        en_keep.display_order = da_latest.display_order
                        updated = True
                    
                    if en_keep.grid_size != da_latest.grid_size:
                        en_keep.grid_size = da_latest.grid_size
                        updated = True
                    
                    if da_latest.image_data:
                        en_keep.image_data = da_latest.image_data
                        updated = True
                    
                    db.session.commit()
                    
                    if updated:
                        stats['en_updated'] = 1
                        print(f"      ✅ Deleted {len(en_to_delete)} old EN, updated kept EN")
                    else:
                        print(f"      ✅ Deleted {len(en_to_delete)} old EN, kept EN already up to date")
                except Exception as e:
                    print(f"      ❌ Error cleaning up EN articles: {e}")
                    db.session.rollback()
                    stats['errors'] += 1
            else:
                print(f"      📝 Would delete {len(en_to_delete)} old EN and update kept EN (dry run)")
        
        print()
        print(f"📊 5_articles EN processing complete:")
        print(f"   DA found: {stats['da_found']}")
        print(f"   EN found: {stats['en_found']}")
        print(f"   EN created: {stats['en_created']}")
        print(f"   EN updated: {stats['en_updated']}")
        print(f"   EN deleted: {stats['en_deleted']}")
        print(f"   Errors: {stats['errors']}")
        
        return stats


def create_missing_en_articles(layout_items, language='da', dry_run=False, delay=0.5):
    """
    Check và tạo EN articles cho các DA articles có trong layout chưa có EN version
    
    Args:
        layout_items: List of layout items từ crawl (chỉ tạo EN cho articles trong layout này)
        language: Language của source articles (chỉ 'da' được support)
        dry_run: Nếu True, chỉ log không tạo
        delay: Delay giữa các lần translate (giây)
    
    Returns:
        dict: Statistics về quá trình tạo EN articles
    """
    if language != 'da':
        print(f"⚠️  Only 'da' language is supported for creating EN articles")
        return {'created': 0, 'skipped': 0, 'errors': 0}
    
    print(f"\n{'='*60}")
    print(f"🌐 Creating missing EN articles for articles in layout")
    print(f"{'='*60}")
    print(f"   Layout items: {len(layout_items)}")
    print(f"   Dry run: {dry_run}")
    
    stats = {
        'checked': 0,
        'created': 0,
        'skipped': 0,
        'urls_translated': 0,  # Số URLs đã translate cho EN articles đã tồn tại
        'errors': 0,
        'error_list': []
    }
    
    with app.app_context():
        # Lấy danh sách published_url từ layout_items (chỉ articles thông thường, không phải slider)
        layout_urls = set()
        for layout_item in layout_items:
            published_url = layout_item.get('published_url', '')
            if published_url and layout_item.get('layout_type') not in ['slider', 'job_slider']:
                layout_urls.add(published_url)
        
        print(f"   Found {len(layout_urls)} unique URLs in layout to check")
        
        # Lấy DA articles có published_url trong layout
        # ⚠️ QUAN TRỌNG: Với 1_with_list_left/right, chỉ lấy articles có section='home'
        # Vì chúng chỉ xuất hiện ở home, không nên query vào các sections khác
        # ⚠️ Chỉ lấy articles chưa bị mark deleted
        da_articles = Article.query.filter(
            Article.language == 'da',
            Article.is_home == True,
            Article.published_url.in_(layout_urls),
            # Nếu layout_type là 1_with_list_left/right, phải có section='home'
            # Nếu layout_type khác, không cần filter section
            or_(
                Article.layout_type.notin_(['1_with_list_left', '1_with_list_right']),
                Article.section == 'home'
            ),
            # Chỉ lấy articles chưa bị deleted
            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
        ).all()
        
        print(f"   Found {len(da_articles)} DA articles in layout to check (filtered: 1_with_list_left/right only in section='home')")
        
        for idx, da_article in enumerate(da_articles, 1):
            try:
                stats['checked'] += 1
                
                if not da_article.published_url:
                    print(f"   [{idx}/{len(da_articles)}] ⚠️  Skipping article {da_article.id} (no published_url)")
                    stats['skipped'] += 1
                    continue
                
                # ⚠️ QUAN TRỌNG: Với 1_with_list_left/right, chỉ tạo EN nếu DA article có section='home'
                if da_article.layout_type in ['1_with_list_left', '1_with_list_right']:
                    if da_article.section != 'home':
                        print(f"   [{idx}/{len(da_articles)}] ⚠️  Skipping {da_article.layout_type} article {da_article.id} (section='{da_article.section}', need 'home')")
                        stats['skipped'] += 1
                        continue
                
                # Check xem đã có EN version chưa
                # EN articles có published_url = DA URL (từ layout)
                # Với 1_with_list_left/right: chỉ tìm EN article có section='home'
                # ⚠️ Chỉ tìm EN article chưa bị mark deleted
                query = Article.query.filter_by(
                    published_url=da_article.published_url,
                    language='en'
                ).filter(
                    or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                )
                if da_article.layout_type in ['1_with_list_left', '1_with_list_right']:
                    query = query.filter_by(section='home')
                existing_en = query.first()
                
                if existing_en:
                    # Đã có EN version → check và translate URL nếu chưa có published_url_en
                    if not existing_en.published_url_en or existing_en.published_url_en.strip() == '':
                        # Chưa có published_url_en → translate và update
                        if not dry_run:
                            try:
                                if da_article.published_url:
                                    en_url = translate_url(da_article.published_url, delay=0.3)
                                    if en_url:
                                        existing_en.published_url_en = en_url
                                        db.session.commit()
                                        stats['urls_translated'] += 1
                                        print(f"   [{idx}/{len(da_articles)}] ✅ EN version exists, translated URL (DA ID: {da_article.id}, EN ID: {existing_en.id})")
                                        print(f"      📝 Set published_url_en: {en_url[:60]}...")
                                    else:
                                        print(f"   [{idx}/{len(da_articles)}] ⚠️  EN version exists but failed to translate URL (DA ID: {da_article.id}, EN ID: {existing_en.id})")
                                else:
                                    print(f"   [{idx}/{len(da_articles)}] ⚠️  EN version exists but DA article has no published_url (DA ID: {da_article.id}, EN ID: {existing_en.id})")
                            except Exception as e:
                                print(f"   [{idx}/{len(da_articles)}] ❌ Error translating URL for EN article {existing_en.id}: {e}")
                                db.session.rollback()
                        else:
                            print(f"   [{idx}/{len(da_articles)}] ⚠️  EN version exists, would translate URL (dry run)")
                    else:
                        # Đã có published_url_en
                        if idx <= 5 or idx % 10 == 0:
                            print(f"   [{idx}/{len(da_articles)}] ✅ EN version exists with URL (DA ID: {da_article.id}, EN ID: {existing_en.id})")
                    stats['skipped'] += 1
                    continue
                
                # Chưa có EN version → tạo mới
                print(f"   [{idx}/{len(da_articles)}] 🌐 Creating EN version for DA article {da_article.id}: '{da_article.title[:50]}...'")
                
                if not dry_run:
                    try:
                        # ⚠️ CRITICAL: Check lần cuối xem EN article đã tồn tại chưa
                        # (có thể đã được tạo bởi iteration trước trong cùng 1 lần chạy)
                        # ⚠️ Chỉ check EN article chưa bị mark deleted
                        final_check = Article.query.filter_by(
                            published_url=da_article.published_url,
                            language='en'
                        ).filter(
                            or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                        )
                        if da_article.layout_type in ['1_with_list_left', '1_with_list_right']:
                            final_check = final_check.filter_by(section='home')
                        existing_en_final = final_check.first()
                        
                        if existing_en_final:
                            print(f"      ⏭️  EN article found in final check (ID: {existing_en_final.id}), skipping creation...")
                            stats['skipped'] += 1
                            continue
                        
                        # Translate article
                        en_article = translate_article(
                            da_article,
                            target_language='en',
                            delay=delay
                        )
                        
                        if en_article:
                            # Translate URL cho EN article
                            if da_article.published_url:
                                en_url = translate_url(da_article.published_url, delay=0.3)
                                if en_url:
                                    en_article.published_url_en = en_url
                            
                            # Copy metadata từ DA article
                            en_article.display_order = da_article.display_order
                            en_article.layout_type = da_article.layout_type
                            
                            # ⚠️ QUAN TRỌNG: Giữ lại TẤT CẢ các field đã được translate từ translate_article()
                            # translate_article() đã translate: kicker_below, kicker_floating, title_parts, list_items, list_title, etc.
                            # KHÔNG copy da_article.layout_data vì sẽ ghi đè các field đã translate
                            # Chỉ merge các field metadata (row_index, article_index_in_row, total_rows) từ DA nếu chưa có
                            if en_article.layout_data and da_article.layout_data:
                                # Giữ lại en_article.layout_data đã được translate
                                # Chỉ merge các field metadata từ DA nếu chưa có trong EN
                                da_layout_data = da_article.layout_data.copy() if isinstance(da_article.layout_data, dict) else {}
                                
                                # Merge metadata fields (không ghi đè các field đã translate)
                                for key in ['row_index', 'article_index_in_row', 'total_rows', 'kicker_below_classes']:
                                    if key in da_layout_data and key not in en_article.layout_data:
                                        en_article.layout_data[key] = da_layout_data[key]
                                
                                print(f"         ✅ Preserved all translated fields (kicker_below, kicker_floating, title_parts, list_items, etc.)")
                            elif da_article.layout_data:
                                # Nếu không có layout_data đã translate, copy trực tiếp (fallback)
                                en_article.layout_data = da_article.layout_data.copy() if isinstance(da_article.layout_data, dict) else da_article.layout_data
                            
                            en_article.grid_size = da_article.grid_size
                            en_article.is_home = da_article.is_home
                            # ⚠️ QUAN TRỌNG: Copy section từ DA article
                            # (Nếu DA được tạo từ home crawl → section='home', nếu từ section pages → section=<section_name>)
                            en_article.section = da_article.section
                            
                            # Save vào database
                            db.session.add(en_article)
                            db.session.commit()
                            
                            stats['created'] += 1
                            print(f"      ✅ Created EN article (ID: {en_article.id})")
                            
                            # Delay để tránh rate limit
                            time.sleep(delay)
                        else:
                            stats['errors'] += 1
                            stats['error_list'].append({
                                'da_id': da_article.id,
                                'error': 'Translation returned None'
                            })
                            print(f"      ❌ Translation failed")
                    except Exception as e:
                        stats['errors'] += 1
                        stats['error_list'].append({
                            'da_id': da_article.id,
                            'error': str(e)
                        })
                        print(f"      ❌ Error creating EN article: {e}")
                        db.session.rollback()
                        continue
                else:
                    # Dry run
                    stats['created'] += 1
                    print(f"      ⚠️  Would create EN article (dry run)")
            
            except Exception as e:
                stats['errors'] += 1
                stats['error_list'].append({
                    'da_id': da_article.id if 'da_article' in locals() else 'N/A',
                    'error': str(e)
                })
                print(f"   [{idx}/{len(da_articles)}] ❌ Error: {e}")
                if not dry_run:
                    db.session.rollback()
                continue
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ EN articles creation completed")
        print(f"{'='*60}")
        print(f"   Articles checked: {stats['checked']}")
        print(f"   EN articles created: {stats['created']}")
        print(f"   EN articles skipped (already exist): {stats['skipped']}")
        print(f"   URLs translated for existing EN articles: {stats['urls_translated']}")
        print(f"   Errors: {stats['errors']}")
        if stats['error_list']:
            print(f"\n   First 5 errors:")
            for error in stats['error_list'][:5]:
                print(f"      - DA ID {error['da_id']}: {error['error']}")
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Link articles đã có trong DB với home layout structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Link từ file layout đã crawl
  python scripts/link_home_articles.py --layout-file home_layouts/home_layout_da_20240101_120000.json --language da
  
  # Crawl và link trực tiếp (không lưu file)
  python scripts/link_home_articles.py --crawl --language da
  
  # Dry run (chỉ log, không update)
  python scripts/link_home_articles.py --layout-file home_layouts/home_layout_da_20240101_120000.json --language da --dry-run
        """
    )
    
    parser.add_argument('--layout-file', '-f',
                       help='Path to layout JSON file (nếu không có, sẽ crawl trực tiếp)')
    parser.add_argument('--crawl', '-c', action='store_true',
                       help='Crawl layout trực tiếp thay vì load từ file')
    parser.add_argument('--language', '-l', default='da', choices=['da', 'kl', 'en'],
                       help='Language code (default: da)')
    parser.add_argument('--url', '-u',
                       help='URL của trang home (chỉ dùng khi --crawl)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run: chỉ log, không update database')
    parser.add_argument('--no-reset', action='store_true',
                       help='Không reset is_home=False trước khi link (mặc định: có reset)')
    parser.add_argument('--no-headless', action='store_true',
                       help='Chạy browser ở chế độ no-headless (chỉ dùng khi --crawl)')
    parser.add_argument('--create-en', action='store_true',
                       help='Sau khi link DA articles, check và tạo EN articles nếu chưa có')
    parser.add_argument('--no-create-en', action='store_true',
                       help='Không tạo EN articles (mặc định: tạo nếu --language=da)')
    
    args = parser.parse_args()
    
    # ⚠️ BẮT BUỘC: Luôn crawl layout mới mỗi lần chạy (không load từ file)
    # Chỉ load từ file nếu user chỉ định rõ --layout-file
    if not args.layout_file:
        # Không có --layout-file → bắt buộc crawl layout mới
        args.crawl = True
        print(f"🔄 Will crawl fresh layout (default: always crawl new layout)")
    else:
        # Có --layout-file → user muốn dùng file cụ thể (override default)
        print(f"📄 Will use specified layout file: {args.layout_file}")
    
    # Nếu language='da' và không có --no-create-en, tự động xử lý KL -> DA -> EN
    should_process_all = (
        args.language == 'da' and 
        not args.no_create_en  # Mặc định xử lý tất cả nếu không có --no-create-en
    )
    
    # Step 0: Mark old 1_with_list articles for deletion (cho tất cả languages sẽ xử lý)
    # ⚠️ QUAN TRỌNG: Mark TRƯỚC KHI crawl để crawl có thể tạo mới
    if should_process_all:
        # Mark cho cả KL, DA, EN
        for lang in ['kl', 'da', 'en']:
            print(f"\n{'='*60}")
            print(f"🗑️  Step 0: Marking old {lang.upper()} 1_with_list articles")
            print(f"{'='*60}")
            mark_list_articles_for_deletion(language=lang, dry_run=args.dry_run)
    else:
        # Chỉ mark cho language hiện tại
        print(f"\n{'='*60}")
        print(f"🗑️  Step 0: Marking old {args.language.upper()} 1_with_list articles")
        print(f"{'='*60}")
        mark_list_articles_for_deletion(language=args.language, dry_run=args.dry_run)
    
    # Step 1: Xử lý KL trước (nếu should_process_all)
    if should_process_all:
        print(f"\n{'='*60}")
        print(f"🔗 Step 1: Processing KL articles")
        print(f"{'='*60}")
        
        # Check xem có KL articles trong DB chưa
        with app.app_context():
            kl_articles_count = Article.query.filter_by(
                language='kl',
                is_home=True
            ).count()
            print(f"   📊 Found {kl_articles_count} KL articles in DB (is_home=True)")
        
        # ⚠️ BẮT BUỘC: Luôn crawl KL layout mới mỗi lần chạy (giống DA)
        # Chỉ load từ file nếu user chỉ định rõ --layout-file
        kl_layout_items = None
        
        if args.layout_file and not args.crawl:
            # Nếu có layout file DA và không có --crawl, tìm layout file KL tương ứng
            layout_path = Path(args.layout_file)
            layout_dir = layout_path.parent
            # Tìm file KL mới nhất trong cùng thư mục
            kl_files = sorted(layout_dir.glob('home_layout_kl_*.json'), reverse=True)
            if kl_files:
                kl_layout_items = load_layout_from_file(str(kl_files[0]))
                print(f"   ✅ Loaded KL layout from: {kl_files[0].name}")
        
        # Nếu không có layout file hoặc có --crawl, crawl KL layout mới
        if not kl_layout_items or args.crawl:
            if not args.dry_run:
                # Crawl KL layout để tạo articles vào DB
                print(f"   🔄 Crawling fresh KL layout...")
                kl_layout_items = crawl_home_layout(
                    home_url='https://kl.sermitsiaq.ag',
                    language='kl',
                    headless=not args.no_headless
                )
                
                # Tự động lưu KL layout file (ghi đè file cũ)
                if kl_layout_items:
                    output_file = "home_layout_kl.json"  # Tên cố định, ghi đè file cũ
                    saved_file = save_layout_to_file(
                        layout_items=kl_layout_items,
                        output_file=output_file,
                        language='kl'
                    )
                    print(f"      💾 KL layout saved to: {saved_file} (overwrites existing file)")
            else:
                print(f"   🔄 Would crawl KL layout (dry run)")
        
        if kl_layout_items:
            # ⚠️ QUAN TRỌNG: Delete old KL articles SAU KHI crawl (tạo mới), TRƯỚC KHI link
            # Để tránh có 2 articles cùng URL cùng is_home=True
            print(f"\n{'='*60}")
            print(f"🗑️  Step 1.1: Deleting old KL marked articles")
            print(f"{'='*60}")
            delete_marked_articles(language='kl', dry_run=args.dry_run)
            
            # Link KL articles
            link_articles_with_layout(
                kl_layout_items,
                language='kl',
                dry_run=args.dry_run,
                reset_first=not args.no_reset
            )
            
            # ⚠️ QUAN TRỌNG: Cleanup KL 5_articles duplicates
            print(f"\n{'='*60}")
            print(f"🧹 Cleanup: Removing duplicate KL 5_articles")
            print(f"{'='*60}")
            cleanup_5articles_duplicates(language='kl', dry_run=args.dry_run)
        else:
            print(f"   ⚠️  No KL layout found, skipping KL processing")
        
        # ⚠️ QUAN TRỌNG: Match DA và KL articles SAU KHI cả hai đã được process
        # Matching step set canonical_id cho KL articles → link với DA articles
        # Cần thiết cho language switcher DA ↔ KL
        if kl_layout_items and not args.dry_run:
            print(f"\n{'='*60}")
            print(f"🔗 Step 1.5: Matching DA and KL home articles")
            print(f"{'='*60}")
            
            with app.app_context():
                from services.article_matcher import match_and_link_articles
                
                # Get DA articles (chỉ lấy articles chưa bị mark deleted)
                da_articles = Article.query.filter_by(
                    language='da',
                    is_home=True
                ).filter(
                    or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                ).all()
                
                # Get KL articles (chỉ lấy articles chưa bị mark deleted)
                kl_articles = Article.query.filter_by(
                    language='kl',
                    is_home=True
                ).filter(
                    or_(Article.is_deleted == False, Article.is_deleted.is_(None))
                ).all()
                
                print(f"   Found {len(da_articles)} DA articles")
                print(f"   Found {len(kl_articles)} KL articles")
                
                if da_articles and kl_articles:
                    stats = match_and_link_articles(da_articles, kl_articles)
                    print(f"   ✅ Matched {stats['matched_count']} articles")
                    print(f"   ⚠️  Unmatched DA: {len(stats['unmatched_dk'])}")
                    print(f"   ⚠️  Unmatched KL: {len(stats['unmatched_kl'])}")
                else:
                    print(f"   ⚠️  No articles to match")
        elif kl_layout_items and args.dry_run:
            print(f"\n{'='*60}")
            print(f"🔗 Step 1.5: Would match DA and KL home articles (dry run)")
            print(f"{'='*60}")
    
    # Load hoặc crawl layout cho language hiện tại
    if args.crawl or not args.layout_file:
        # Crawl trực tiếp
        if not args.url:
            if args.language == 'kl':
                args.url = 'https://kl.sermitsiaq.ag'
            else:
                args.url = 'https://www.sermitsiaq.ag'
        
        print(f"\n🔄 Crawling layout structure for {args.language.upper()}...")
        layout_items = crawl_home_layout(
            home_url=args.url,
            language=args.language,
            headless=not args.no_headless
        )
        
        if not layout_items:
            print("❌ Failed to crawl layout")
            return
        
        # ⚠️ QUAN TRỌNG: Tự động lưu layout file để EN có thể dùng
        # EN dùng chung layout với DA, nên luôn lưu với language='da' cho DA layout
        # Ghi đè file cũ (tên cố định) để không tạo quá nhiều file
        if not args.dry_run:
            # Tên file cố định: home_layout_da.json, home_layout_kl.json
            output_file = f"home_layout_{args.language}.json"
            saved_file = save_layout_to_file(
                layout_items=layout_items,
                output_file=output_file,  # Tên cố định, ghi đè file cũ
                language=args.language
            )
            print(f"   💾 Layout saved to: {saved_file} (overwrites existing file)")
            if args.language == 'da':
                print(f"   ℹ️  EN will use this layout file (EN uses same layout as DA)")
    else:
        # Load từ file (chỉ khi user chỉ định rõ --layout-file)
        layout_items = load_layout_from_file(args.layout_file)
        if not layout_items:
            return
    
    # Step 2: Delete old DA articles SAU KHI crawl (tạo mới), TRƯỚC KHI link
    # ⚠️ QUAN TRỌNG: Delete TRƯỚC link để tránh có 2 articles cùng URL cùng is_home=True
    if should_process_all:
        print(f"\n{'='*60}")
        print(f"🔗 Step 2: Processing DA articles")
        print(f"{'='*60}")
        
        print(f"\n{'='*60}")
        print(f"🗑️  Step 2.1: Deleting old DA marked articles")
        print(f"{'='*60}")
        delete_marked_articles(language='da', dry_run=args.dry_run)
    else:
        # Nếu chỉ chạy cho 1 language (không phải 'all'), delete sau khi crawl
        print(f"\n{'='*60}")
        print(f"🗑️  Deleting old {args.language.upper()} marked articles")
        print(f"{'='*60}")
        delete_marked_articles(language=args.language, dry_run=args.dry_run)
    
    # Link articles với layout
    link_articles_with_layout(
        layout_items, 
        language=args.language, 
        dry_run=args.dry_run,
        reset_first=not args.no_reset  # Reset nếu không có --no-reset
    )
    
    # ⚠️ QUAN TRỌNG: Cleanup 5_articles duplicates sau khi link xong
    print(f"\n{'='*60}")
    print(f"🧹 Cleanup: Removing duplicate 5_articles")
    print(f"{'='*60}")
    cleanup_5articles_duplicates(language=args.language, dry_run=args.dry_run)
    
    # Step 3 & 4: Tạo và link EN articles (nếu should_process_all)
    # Sau khi link DA articles, check và tạo EN articles nếu chưa có
    # Chỉ tạo nếu:
    # - language='da' (chỉ tạo EN từ DA)
    # - Không có --no-create-en (mặc định: tạo EN articles)
    # Lưu ý: KL được xử lý độc lập, không tạo EN từ KL
    # Mặc định: Khi link DA articles, sẽ tự động tạo EN articles nếu chưa có
    should_create_en = (
        args.language == 'da' and 
        not args.no_create_en  # Mặc định tạo nếu không có --no-create-en
    )
    
    if should_create_en and not args.dry_run:
        step_num = "3" if should_process_all else "2"
        print(f"\n{'='*60}")
        print(f"🌐 Step {step_num}: Creating missing EN articles")
        print(f"{'='*60}")
        create_missing_en_articles(
            layout_items=layout_items,
            language=args.language,
            dry_run=args.dry_run,
            delay=0.5
        )
        
        # ⚠️ XỬ LÝ RIÊNG: 5_articles (Create/Update EN from latest DA)
        # 5_articles không có published_url, xử lý riêng với logic đặc biệt
        print(f"\n{'='*60}")
        print(f"📦 Step {step_num}.1: Processing 5_articles EN")
        print(f"{'='*60}")
        create_or_update_5_articles_en(
            dry_run=args.dry_run,
            delay=0.5
        )
        
        # ⚠️ QUAN TRỌNG: Delete old EN articles SAU KHI tạo mới, TRƯỚC KHI link
        # Để tránh có 2 articles cùng URL cùng is_home=True
        step_num_delete = f"{step_num}.1"
        print(f"\n{'='*60}")
        print(f"🗑️  Step {step_num_delete}: Deleting old EN marked articles")
        print(f"{'='*60}")
        delete_marked_articles(language='en', dry_run=args.dry_run)
        
        # Link EN articles với layout (sau khi đã tạo xong và delete old)
        step_num = "4" if should_process_all else "3"
        print(f"\n{'='*60}")
        print(f"🔗 Step {step_num}: Linking EN articles with layout")
        print(f"{'='*60}")
        link_articles_with_layout(
            layout_items,
            language='en',  # Link EN articles
            dry_run=args.dry_run,
            reset_first=not args.no_reset  # Reset EN articles trước khi link
        )
        
        # ⚠️ QUAN TRỌNG: Cleanup EN 5_articles duplicates
        print(f"\n{'='*60}")
        print(f"🧹 Cleanup: Removing duplicate EN 5_articles")
        print(f"{'='*60}")
        cleanup_5articles_duplicates(language='en', dry_run=args.dry_run)
        
        # ⚠️ QUAN TRỌNG: Translate slider containers SAU KHI EN sliders đã được tạo
        # (EN sliders được tạo trong link_articles_with_layout cho EN)
        step_num_slider = str(int(step_num) + 1) if step_num.isdigit() else "4a"
        print(f"\n{'='*60}")
        print(f"🎠 Step {step_num_slider}: Translating slider containers")
        print(f"{'='*60}")
        translate_slider_containers(
            language=args.language,
            dry_run=args.dry_run,
            delay=0.5
        )
    elif should_create_en and args.dry_run:
        step_num = "3" if should_process_all else "2"
        print(f"\n{'='*60}")
        print(f"🌐 Step {step_num}: Would create missing EN articles (dry run)")
        print(f"{'='*60}")
        create_missing_en_articles(
            layout_items=layout_items,
            language=args.language,
            dry_run=True,
            delay=0.5
        )
        
        # ⚠️ QUAN TRỌNG: Delete old EN articles SAU KHI tạo mới, TRƯỚC KHI link
        step_num_delete = f"{step_num}.1"
        print(f"\n{'='*60}")
        print(f"🗑️  Step {step_num_delete}: Would delete old EN marked articles (dry run)")
        print(f"{'='*60}")
        delete_marked_articles(language='en', dry_run=True)
        
        # Link EN articles với layout (dry run)
        step_num = "4" if should_process_all else "3"
        print(f"\n{'='*60}")
        print(f"🔗 Step {step_num}: Would link EN articles with layout (dry run)")
        print(f"{'='*60}")
        link_articles_with_layout(
            layout_items,
            language='en',
            dry_run=True,
            reset_first=not args.no_reset
        )
        
        # Translate slider containers (dry run) - SAU KHI EN sliders đã được tạo
        step_num_slider = str(int(step_num) + 1) if step_num.isdigit() else "4a"
        print(f"\n{'='*60}")
        print(f"🎠 Step {step_num_slider}: Would translate slider containers (dry run)")
        print(f"{'='*60}")
        translate_slider_containers(
            language=args.language,
            dry_run=True,
            delay=0.5
        )
    
    # Step cuối cùng: Generate sitemaps (nếu đã xử lý xong và không phải dry_run)
    # Chỉ generate khi:
    # - Không phải dry_run
    # - Đã xử lý xong (should_process_all hoặc should_create_en hoặc language='kl')
    should_generate_sitemaps = (
        not args.dry_run and
        (should_process_all or should_create_en or args.language == 'kl')
    )
    
    if should_generate_sitemaps:
        step_num = "6" if should_process_all else "6" if should_create_en else "2"  # Step 6 vì translate_slider_containers là step 5
        print(f"\n{'='*60}")
        print(f"🗺️  Step {step_num}: Generating sitemaps")
        print(f"{'='*60}")
        
        # Xác định output directory (giống như generate_sitemaps.py mặc định: current directory)
        output_dir = Path('.')
        
        # Generate sitemaps cho các ngôn ngữ đã xử lý
        languages_to_generate = []
        if should_process_all:
            # Đã xử lý KL, DA, EN
            languages_to_generate = ['kl', 'da', 'en']
        elif args.language == 'kl':
            # Chỉ xử lý KL
            languages_to_generate = ['kl']
        elif should_create_en:
            # Đã xử lý DA và EN
            languages_to_generate = ['da', 'en']
        else:
            # Chỉ xử lý language hiện tại
            languages_to_generate = [args.language]
        
        for lang in languages_to_generate:
            try:
                file_names = {
                    'en': 'sitemap.xml',
                    'da': 'sitemap-DK.xml',
                    'kl': 'sitemap-KL.xml'
                }
                output_file = output_dir / file_names.get(lang, f'sitemap-{lang.upper()}.xml')
                
                print(f"   📋 Generating sitemap for {lang.upper()}...")
                generate_sitemap(
                    language=lang,
                    output_file=str(output_file),
                    base_domain='www.sermitsiaq.com'
                )
            except Exception as e:
                print(f"   ⚠️  Error generating sitemap for {lang.upper()}: {e}")
        
        print(f"   ✅ Sitemaps generated successfully!")
    
    # ⚠️ NOTE: Old marked articles đã được deleted TRƯỚC KHI link (sau mỗi lần crawl)
    # Không cần delete lại ở đây nữa
    
    # Step cuối cùng: Check và crawl article details nếu có articles với is_temp=True
    if not args.dry_run:
        with app.app_context():
            # Đếm số articles có is_temp=True
            temp_articles_count = Article.query.filter_by(is_temp=True).count()
            
            if temp_articles_count > 0:
                print(f"\n{'='*60}")
                print(f"📄 Step Final: Crawling article details for {temp_articles_count} temp articles")
                print(f"{'='*60}")
                
                try:
                    # Import và gọi crawl_article_details_batch
                    import subprocess
                    import sys
                    
                    script_path = Path(__file__).parent / 'crawl_article_details_batch.py'
                    
                    print(f"   🔄 Running: python {script_path}")
                    
                    # Chạy script crawl_article_details_batch.py
                    result = subprocess.run(
                        [sys.executable, str(script_path), '--crawl-all', '--no-auto-translate'],
                        cwd=str(Path(__file__).parent.parent),
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        print(f"   ✅ Article details crawl completed")
                        print(f"   📋 Output:")
                        # In output (giới hạn 50 dòng cuối)
                        output_lines = result.stdout.split('\n')
                        for line in output_lines[-50:]:
                            if line.strip():
                                print(f"      {line}")
                    else:
                        print(f"   ⚠️  Article details crawl completed with warnings")
                        print(f"   📋 Error output:")
                        error_lines = result.stderr.split('\n')
                        for line in error_lines[-20:]:
                            if line.strip():
                                print(f"      {line}")
                except Exception as e:
                    print(f"   ❌ Error running crawl_article_details_batch.py: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"\n{'='*60}")
                print(f"✅ No temp articles found, skipping article details crawl")
                print(f"{'='*60}")


if __name__ == '__main__':
    main()

