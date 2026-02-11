#!/usr/bin/env python3
"""
Script để download lại images cho các articles bị mất hình ảnh
Sử dụng: python scripts/redownload_missing_images.py [--section SECTION] [--language LANG] [--limit N]
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add flask directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article, ArticleDetail
from services.image_downloader import download_and_update_image_data, extract_image_id_from_url


def check_image_file_exists(image_url: str, save_dir: str) -> bool:
    """
    Kiểm tra xem file image đã tồn tại chưa dựa trên URL
    """
    if not image_url:
        return False
    
    # Extract imageId từ URL
    image_id = extract_image_id_from_url(image_url)
    if not image_id:
        return False
    
    # Check các format có thể có
    for ext in ['webp', 'jpeg', 'jpg', 'png']:
        file_path = os.path.join(save_dir, f"{image_id}.{ext}")
        if os.path.exists(file_path):
            return True
    
    return False


def process_article_images(article: Article, save_dir: str, download_all: bool = True) -> bool:
    """
    Process và download lại images cho một article
    Returns: True nếu có download, False nếu không cần
    """
    if not article.image_data:
        return False
    
    # Parse image_data (có thể là dict hoặc JSON string)
    img_data = article.image_data
    if isinstance(img_data, str):
        try:
            img_data = json.loads(img_data)
        except:
            return False
    
    if not isinstance(img_data, dict) or len(img_data) == 0:
        return False
    
    # Kiểm tra xem có image nào cần download không
    needs_download = False
    image_urls_to_check = [
        img_data.get('desktop_webp'),
        img_data.get('desktop_jpeg'),
        img_data.get('mobile_webp'),
        img_data.get('mobile_jpeg'),
        img_data.get('fallback')
    ]
    
    for url in image_urls_to_check:
        if url and not check_image_file_exists(url, save_dir):
            needs_download = True
            break
    
    if not needs_download:
        return False
    
    # Download lại images
    print(f"   📥 Downloading images for article ID {article.id}: {article.title[:60]}...")
    try:
        updated_image_data = download_and_update_image_data(
            img_data,
            base_url='https://www.sermitsiaq.com',
            download_all_formats=download_all
        )
        
        # Update database
        article.image_data = updated_image_data
        db.session.commit()
        print(f"   ✅ Updated images for article ID {article.id}")
        return True
    except Exception as e:
        print(f"   ⚠️  Error downloading images for article ID {article.id}: {e}")
        db.session.rollback()
        return False


def process_article_detail_images(article_detail: ArticleDetail, save_dir: str, download_all: bool = True) -> bool:
    """
    Process và download lại images trong content_blocks của ArticleDetail
    Returns: True nếu có download, False nếu không cần
    """
    if not article_detail.content_blocks:
        return False
    
    content_blocks = article_detail.content_blocks
    if isinstance(content_blocks, str):
        try:
            content_blocks = json.loads(content_blocks)
        except:
            return False
    
    if not isinstance(content_blocks, list):
        return False
    
    needs_download = False
    updated = False
    
    # Tìm tất cả image blocks
    for block in content_blocks:
        if block.get('type') == 'image' and block.get('image_sources'):
            image_sources = block.get('image_sources', {})
            
            # Kiểm tra xem có image nào cần download không
            image_urls_to_check = [
                image_sources.get('desktop_webp'),
                image_sources.get('desktop_jpeg'),
                image_sources.get('mobile_webp'),
                image_sources.get('mobile_jpeg'),
                image_sources.get('fallback')
            ]
            
            for url in image_urls_to_check:
                if url and not check_image_file_exists(url, save_dir):
                    needs_download = True
                    break
            
            if needs_download:
                print(f"   📥 Downloading images for article_detail ID {article_detail.id} (block #{block.get('order', '?')})...")
                try:
                    updated_image_sources = download_and_update_image_data(
                        image_sources,
                        base_url='https://www.sermitsiaq.com',
                        download_all_formats=download_all
                    )
                    
                    # Update block
                    block['image_sources'] = updated_image_sources
                    updated = True
                    print(f"   ✅ Updated images for article_detail ID {article_detail.id} (block #{block.get('order', '?')})")
                except Exception as e:
                    print(f"   ⚠️  Error downloading images for article_detail ID {article_detail.id}: {e}")
    
    if updated:
        # Update database
        article_detail.content_blocks = content_blocks
        db.session.commit()
        return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description='Download lại images cho articles bị mất hình ảnh')
    parser.add_argument('--section', type=str, help='Filter theo section (erhverv, samfund, kultur, sport, etc.)')
    parser.add_argument('--language', type=str, default='da', help='Filter theo language (da, kl, en). Default: da')
    parser.add_argument('--limit', type=int, help='Giới hạn số lượng articles (để test)')
    parser.add_argument('--download-all-formats', action='store_true', 
                       help='Download tất cả formats (desktop_webp, desktop_jpeg, mobile_webp, mobile_jpeg). Default: chỉ desktop_webp và fallback')
    parser.add_argument('--articles-only', action='store_true', 
                       help='Chỉ process articles, không process article_details')
    parser.add_argument('--details-only', action='store_true', 
                       help='Chỉ process article_details, không process articles')
    
    args = parser.parse_args()
    
    with app.app_context():
        # Setup save directory
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_dir = os.path.join(current_dir, 'static', 'uploads', 'images')
        os.makedirs(save_dir, exist_ok=True)
        
        print("="*80)
        print("🔄 Starting image re-download process...")
        print("="*80)
        print(f"   Save directory: {save_dir}")
        print(f"   Section filter: {args.section or 'All'}")
        print(f"   Language filter: {args.language}")
        print(f"   Download all formats: {args.download_all_formats}")
        print(f"   Limit: {args.limit or 'No limit'}")
        print()
        
        # Process Articles
        if not args.details_only:
            print("📄 Processing Articles...")
            query = Article.query.filter(Article.image_data.isnot(None))
            
            if args.section:
                query = query.filter(Article.section == args.section)
            
            if args.language:
                query = query.filter(Article.language == args.language)
            
            if args.limit:
                query = query.limit(args.limit)
            
            articles = query.all()
            print(f"   Found {len(articles)} articles with image_data")
            
            downloaded_count = 0
            for i, article in enumerate(articles, 1):
                print(f"\n[{i}/{len(articles)}] Article ID {article.id}: {article.title[:60]}...")
                if process_article_images(article, save_dir, download_all=args.download_all_formats):
                    downloaded_count += 1
            
            print(f"\n✅ Processed {len(articles)} articles, downloaded images for {downloaded_count} articles")
        
        # Process ArticleDetails
        if not args.articles_only:
            print("\n" + "="*80)
            print("📄 Processing ArticleDetails...")
            query = ArticleDetail.query.filter(ArticleDetail.content_blocks.isnot(None))
            
            if args.language:
                query = query.filter(ArticleDetail.language == args.language)
            
            if args.limit:
                query = query.limit(args.limit)
            
            article_details = query.all()
            print(f"   Found {len(article_details)} article_details with content_blocks")
            
            downloaded_count = 0
            for i, article_detail in enumerate(article_details, 1):
                print(f"\n[{i}/{len(article_details)}] ArticleDetail ID {article_detail.id}: {article_detail.published_url[:60]}...")
                if process_article_detail_images(article_detail, save_dir, download_all=args.download_all_formats):
                    downloaded_count += 1
            
            print(f"\n✅ Processed {len(article_details)} article_details, downloaded images for {downloaded_count} article_details")
        
        print("\n" + "="*80)
        print("✅ Image re-download process completed!")
        print("="*80)


if __name__ == '__main__':
    main()
