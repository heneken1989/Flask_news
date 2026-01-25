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
from scripts.crawl_home_layout import crawl_home_layout
from services.translation_service import translate_article
from scripts.translate_article_urls import translate_url
import time


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
    
    stats = {
        'total_items': len(layout_items),
        'articles_found': 0,
        'articles_updated': 0,
        'articles_not_found': 0,
        'sliders_processed': 0,
        'errors': []
    }
    
    with app.app_context():
        # Bước 1: Reset tất cả is_home=False cho language này (nếu reset_first=True)
        if reset_first and not dry_run:
            print(f"\n🔄 Resetting is_home=False for all articles (language: {language})...")
            reset_count = Article.query.filter_by(
                language=language,
                is_home=True
            ).update({'is_home': False}, synchronize_session=False)
            db.session.commit()
            print(f"   ✅ Reset {reset_count} articles (is_home=False)")
        elif reset_first and dry_run:
            reset_count = Article.query.filter_by(
                language=language,
                is_home=True
            ).count()
            print(f"\n🔄 Would reset {reset_count} articles (is_home=False) - dry run")
        
        # Pre-fetch tất cả articles của language này để lookup nhanh
        print(f"\n📚 Pre-fetching articles for language '{language}'...")
        all_articles = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
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
        
        # Process từng layout item
        print(f"\n🔄 Processing layout items...")
        updated_article_ids = set()
        
        for idx, layout_item in enumerate(layout_items, 1):
            try:
                published_url = layout_item.get('published_url', '')
                layout_type = layout_item.get('layout_type', '')
                display_order = layout_item.get('display_order', 0)
                
                # Xử lý slider containers đặc biệt
                if layout_type in ['slider', 'job_slider']:
                    stats['sliders_processed'] += 1
                    print(f"   [{idx}/{len(layout_items)}] Processing slider: {layout_type} (display_order={display_order})")
                    
                    # Với slider, tìm hoặc tạo slider container article
                    # Slider container không có published_url, dùng (layout_type, display_order) làm key
                    existing_slider = Article.query.filter_by(
                        section='home',
                        is_home=True,
                        language=language,
                        layout_type=layout_type,
                        display_order=display_order
                    ).first()
                    
                    if existing_slider:
                        # Update existing slider container
                        if not dry_run:
                            existing_slider.display_order = display_order
                            existing_slider.layout_type = layout_type
                            existing_slider.layout_data = layout_item.get('layout_data', {})
                            existing_slider.grid_size = layout_item.get('grid_size', 6)
                            existing_slider.is_home = True
                            # Slider containers có thể có section='home' vì chúng không thuộc tag nào
                            existing_slider.section = 'home'
                            
                            if existing_slider.id not in updated_article_ids:
                                updated_article_ids.add(existing_slider.id)
                                stats['articles_updated'] += 1
                                db.session.commit()
                        
                        print(f"      ✅ Updated slider container (ID: {existing_slider.id})")
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
                    
                    # Link các articles trong slider
                    slider_articles = layout_item.get('slider_articles', [])
                    for slider_article in slider_articles:
                        slider_url = slider_article.get('published_url', '')
                        if slider_url and slider_url in articles_map:
                            # Tìm article phù hợp (cùng language)
                            for article in articles_map[slider_url]:
                                if article.language == language:
                                    # Update article để link với home
                                    # ⚠️ QUAN TRỌNG: Chỉ update is_home=True, KHÔNG update section
                                    if not dry_run:
                                        article.is_home = True
                                        # KHÔNG update section - giữ nguyên section gốc
                                        # Note: display_order của articles trong slider
                                        # được lưu trong layout_data của slider container
                                        if article.id not in updated_article_ids:
                                            updated_article_ids.add(article.id)
                                            stats['articles_updated'] += 1
                                            db.session.commit()
                                    stats['articles_found'] += 1
                                    print(f"         ✅ Linked article in slider: {slider_url[:60]}... (ID: {article.id})")
                                    break
                            else:
                                print(f"         ⚠️  Article in slider not found for language '{language}': {slider_url[:60]}...")
                        elif slider_url:
                            print(f"         ⚠️  Article in slider not found in DB: {slider_url[:60]}...")
                    
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
                matched_article = None
                
                if published_url in articles_map:
                    # Tìm article cùng language
                    # Với EN: tìm EN article có published_url = DA URL (từ layout)
                    # Với DA: tìm DA article có published_url = DA URL (từ layout)
                    for article in articles_map[published_url]:
                        if article.language == language:
                            matched_article = article
                            break
                    
                    # Nếu không tìm thấy và language='en', thử tìm bằng cách khác
                    if not matched_article and language == 'en':
                        # Tìm DA article trước
                        da_article = None
                        for article in articles_map[published_url]:
                            if article.language == 'da':
                                da_article = article
                                break
                        
                        if da_article:
                            # Tìm EN version từ DA article
                            # Cách 1: Tìm bằng canonical_id (EN có canonical_id = DA.id)
                            en_article = Article.query.filter_by(
                                canonical_id=da_article.id,
                                language='en'
                            ).first()
                            
                            if en_article:
                                matched_article = en_article
                                print(f"      🔍 Found EN article via canonical_id (DA ID: {da_article.id}, EN ID: {en_article.id})")
                                print(f"         EN published_url: {en_article.published_url[:60] if en_article.published_url else 'N/A'}...")
                                print(f"         EN published_url_en: {en_article.published_url_en[:60] if en_article.published_url_en else 'N/A'}...")
                    
                    if matched_article:
                        stats['articles_found'] += 1
                        
                        # Update metadata
                        # ⚠️ QUAN TRỌNG: Chỉ update is_home=True, KHÔNG update section
                        # Để articles vẫn hiển thị được ở các tag/section khác
                        if not dry_run:
                            matched_article.display_order = display_order
                            matched_article.layout_type = layout_type
                            
                            # Merge layout_data (giữ lại data cũ nếu có)
                            existing_layout_data = matched_article.layout_data or {}
                            new_layout_data = {
                                'row_index': layout_item.get('row_index', -1),
                                'article_index_in_row': layout_item.get('article_index_in_row', -1),
                                'total_rows': layout_item.get('total_rows', 0)
                            }
                            
                            # Merge với data từ layout_item nếu có (NHƯNG không ghi đè list_items và list_title)
                            if layout_item.get('layout_data'):
                                layout_item_data = layout_item['layout_data'].copy()
                                # Bỏ qua list_items và list_title từ layout_item['layout_data']
                                # vì chúng ta sẽ set riêng từ layout_item.get('list_items')
                                layout_item_data.pop('list_items', None)
                                layout_item_data.pop('list_title', None)
                                new_layout_data.update(layout_item_data)
                            
                            # Thêm list_items và list_title cho 1_with_list_left/right (SAU KHI merge)
                            # Đảm bảo list_items và list_title không bị ghi đè
                            if layout_type in ['1_with_list_left', '1_with_list_right']:
                                if list_title:
                                    new_layout_data['list_title'] = list_title
                                if list_items:
                                    new_layout_data['list_items'] = list_items
                            
                            # Merge với existing data
                            # Với list_items và list_title: ưu tiên giá trị mới nếu có, nếu không giữ lại existing
                            # Với các field khác: update bình thường
                            for key, value in new_layout_data.items():
                                if key in ['list_items', 'list_title']:
                                    # Chỉ update nếu có giá trị mới (không rỗng)
                                    if value:
                                        existing_layout_data[key] = value
                                    # Nếu không có giá trị mới, giữ lại existing (nếu có)
                                else:
                                    # Với các field khác, update bình thường
                                    existing_layout_data[key] = value
                            
                            matched_article.layout_data = existing_layout_data
                            
                            matched_article.grid_size = layout_item.get('grid_size', 6)
                            matched_article.is_home = True
                            # ⚠️ KHÔNG update section='home' - giữ nguyên section gốc (samfund, sport, etc.)
                            # Để articles vẫn hiển thị được ở các tag/section khác
                            
                            if matched_article.id not in updated_article_ids:
                                updated_article_ids.add(matched_article.id)
                                stats['articles_updated'] += 1
                                db.session.commit()
                        
                        print(f"      ✅ Updated article (ID: {matched_article.id})")
                        
                        # Log list items nếu có
                        if list_items:
                            print(f"         📋 List items saved: {len(list_items)} items")
                    else:
                        print(f"      ⚠️  Article found but language mismatch (need '{language}')")
                        stats['articles_not_found'] += 1
                else:
                    print(f"      ⚠️  Article not found in DB: {published_url[:60]}...")
                    stats['articles_not_found'] += 1
                    stats['errors'].append({
                        'url': published_url,
                        'reason': 'not_found_in_db'
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
        if stats['errors']:
            print(f"   Errors: {len(stats['errors'])}")
            print(f"\n   First 5 errors:")
            for error in stats['errors'][:5]:
                print(f"      - {error}")
        
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
        da_articles = Article.query.filter(
            Article.language == 'da',
            Article.is_home == True,
            Article.published_url.in_(layout_urls)
        ).all()
        
        print(f"   Found {len(da_articles)} DA articles in layout to check")
        
        for idx, da_article in enumerate(da_articles, 1):
            try:
                stats['checked'] += 1
                
                if not da_article.published_url:
                    print(f"   [{idx}/{len(da_articles)}] ⚠️  Skipping article {da_article.id} (no published_url)")
                    stats['skipped'] += 1
                    continue
                
                # Check xem đã có EN version chưa
                # EN articles có published_url = DA URL (từ layout)
                existing_en = Article.query.filter_by(
                    published_url=da_article.published_url,
                    language='en'
                ).first()
                
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
                            en_article.layout_data = da_article.layout_data  # Copy layout_data (bao gồm list_items)
                            en_article.grid_size = da_article.grid_size
                            en_article.is_home = da_article.is_home
                            en_article.section = da_article.section  # Giữ nguyên section gốc
                            
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
    
    # Load hoặc crawl layout
    if args.crawl or not args.layout_file:
        # Crawl trực tiếp
        if not args.url:
            if args.language == 'kl':
                args.url = 'https://kl.sermitsiaq.ag'
            else:
                args.url = 'https://www.sermitsiaq.ag'
        
        print(f"🔄 Crawling layout structure...")
        layout_items = crawl_home_layout(
            home_url=args.url,
            language=args.language,
            headless=not args.no_headless
        )
        
        if not layout_items:
            print("❌ Failed to crawl layout")
            return
    else:
        # Load từ file
        layout_items = load_layout_from_file(args.layout_file)
        if not layout_items:
            return
    
    # Link articles với layout
    link_articles_with_layout(
        layout_items, 
        language=args.language, 
        dry_run=args.dry_run,
        reset_first=not args.no_reset  # Reset nếu không có --no-reset
    )
    
    # Sau khi link DA articles, check và tạo EN articles nếu chưa có
    # Chỉ tạo nếu:
    # - language='da' (chỉ tạo EN từ DA)
    # - Không có --no-create-en (mặc định: tạo EN articles)
    # Mặc định: Khi link DA articles, sẽ tự động tạo EN articles nếu chưa có
    should_create_en = (
        args.language == 'da' and 
        not args.no_create_en  # Mặc định tạo nếu không có --no-create-en
    )
    
    if should_create_en and not args.dry_run:
        print(f"\n{'='*60}")
        print(f"🌐 Step 2: Creating missing EN articles")
        print(f"{'='*60}")
        create_missing_en_articles(
            layout_items=layout_items,
            language=args.language,
            dry_run=args.dry_run,
            delay=0.5
        )
        
        # Step 3: Link EN articles với layout (sau khi đã tạo xong)
        print(f"\n{'='*60}")
        print(f"🔗 Step 3: Linking EN articles with layout")
        print(f"{'='*60}")
        link_articles_with_layout(
            layout_items,
            language='en',  # Link EN articles
            dry_run=args.dry_run,
            reset_first=not args.no_reset  # Reset EN articles trước khi link
        )
    elif should_create_en and args.dry_run:
        print(f"\n{'='*60}")
        print(f"🌐 Would create missing EN articles (dry run)")
        print(f"{'='*60}")
        create_missing_en_articles(
            layout_items=layout_items,
            language=args.language,
            dry_run=True,
            delay=0.5
        )
        
        # Step 3: Link EN articles với layout (dry run)
        print(f"\n{'='*60}")
        print(f"🔗 Would link EN articles with layout (dry run)")
        print(f"{'='*60}")
        link_articles_with_layout(
            layout_items,
            language='en',
            dry_run=True,
            reset_first=not args.no_reset
        )


if __name__ == '__main__':
    main()

