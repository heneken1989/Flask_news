#!/usr/bin/env python3
"""
Script để kiểm tra và xóa các ảnh thumbnail (kích thước nhỏ) để download lại với chất lượng cao
Sử dụng: python scripts/check_and_remove_thumbnails.py [--min-size-kb MIN_SIZE] [--dry-run]
"""

import sys
import os
import argparse
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  Warning: PIL/Pillow not installed. Image dimension checking will be skipped.")
    print("   Install with: pip install Pillow")

# Add flask directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article, ArticleDetail
from services.image_downloader import extract_image_id_from_url


def get_image_file_size_kb(file_path: str) -> float:
    """
    Lấy kích thước file ảnh (KB)
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / 1024.0
    except:
        return 0.0


def get_image_dimensions(file_path: str) -> tuple:
    """
    Lấy kích thước ảnh (width, height) bằng PIL
    """
    if not HAS_PIL:
        return (None, None)
    
    try:
        with Image.open(file_path) as img:
            return img.size  # (width, height)
    except Exception as e:
        return (None, None)


def is_thumbnail(file_path: str, min_size_kb: float = 50.0, min_width: int = 500) -> bool:
    """
    Kiểm tra xem ảnh có phải thumbnail không
    
    Args:
        file_path: Đường dẫn file ảnh
        min_size_kb: Kích thước tối thiểu (KB) - nếu nhỏ hơn thì là thumbnail
        min_width: Chiều rộng tối thiểu (pixels) - nếu nhỏ hơn thì là thumbnail
        
    Returns:
        True nếu là thumbnail, False nếu không
    """
    # Kiểm tra kích thước file
    size_kb = get_image_file_size_kb(file_path)
    if size_kb < min_size_kb:
        return True
    
    # Kiểm tra kích thước ảnh (width x height)
    width, height = get_image_dimensions(file_path)
    if width and width < min_width:
        return True
    
    return False


def find_image_files_in_directory(directory: str) -> list:
    """
    Tìm tất cả file ảnh trong thư mục
    """
    image_extensions = ['.webp', '.jpeg', '.jpg', '.png']
    image_files = []
    
    if not os.path.exists(directory):
        return image_files
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                file_path = os.path.join(root, file)
                image_files.append(file_path)
    
    return image_files


def find_image_files_from_database() -> dict:
    """
    Tìm tất cả file ảnh được reference trong database
    Returns: dict {image_id: file_path}
    """
    image_files = {}
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'images')
    
    # Tìm từ Article.image_data
    articles = Article.query.filter(Article.image_data.isnot(None)).all()
    for article in articles:
        if not article.image_data:
            continue
        
        import json
        if isinstance(article.image_data, str):
            try:
                image_data = json.loads(article.image_data)
            except:
                continue
        else:
            image_data = article.image_data
        
        # Extract imageId từ các URLs
        for key in ['desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg', 'fallback']:
            url = image_data.get(key)
            if url:
                image_id = extract_image_id_from_url(url)
                if image_id:
                    # Tìm file với các extension có thể có
                    for ext in ['webp', 'jpeg', 'jpg', 'png']:
                        file_path = os.path.join(save_dir, f"{image_id}.{ext}")
                        if os.path.exists(file_path) and file_path not in image_files.values():
                            image_files[image_id] = file_path
                            break
    
    # Tìm từ ArticleDetail.content_blocks
    article_details = ArticleDetail.query.filter(ArticleDetail.content_blocks.isnot(None)).all()
    for article_detail in article_details:
        if not article_detail.content_blocks:
            continue
        
        import json
        if isinstance(article_detail.content_blocks, str):
            try:
                content_blocks = json.loads(article_detail.content_blocks)
            except:
                continue
        else:
            content_blocks = article_detail.content_blocks
        
        if not isinstance(content_blocks, list):
            continue
        
        for block in content_blocks:
            if block.get('type') == 'image' and block.get('image_sources'):
                image_sources = block.get('image_sources', {})
                for key in ['desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg', 'fallback']:
                    url = image_sources.get(key)
                    if url:
                        image_id = extract_image_id_from_url(url)
                        if image_id:
                            for ext in ['webp', 'jpeg', 'jpg', 'png']:
                                file_path = os.path.join(save_dir, f"{image_id}.{ext}")
                                if os.path.exists(file_path) and file_path not in image_files.values():
                                    image_files[image_id] = file_path
                                    break
    
    return image_files


def main():
    parser = argparse.ArgumentParser(description='Kiểm tra và xóa các ảnh thumbnail (kích thước nhỏ)')
    parser.add_argument('--min-size-kb', type=float, default=50.0,
                       help='Kích thước tối thiểu (KB) - nếu nhỏ hơn thì xóa. Default: 50.0 KB')
    parser.add_argument('--min-width', type=int, default=500,
                       help='Chiều rộng tối thiểu (pixels) - nếu nhỏ hơn thì xóa. Default: 500')
    parser.add_argument('--dry-run', action='store_true',
                       help='Chỉ hiển thị, không xóa file')
    parser.add_argument('--check-all', action='store_true',
                       help='Kiểm tra tất cả file ảnh trong thư mục, không chỉ những file trong database')
    
    args = parser.parse_args()
    
    with app.app_context():
        # Setup save directory
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_dir = os.path.join(current_dir, 'static', 'uploads', 'images')
        
        print("="*80)
        print("🔍 Checking for thumbnail images...")
        print("="*80)
        print(f"   Save directory: {save_dir}")
        print(f"   Min size: {args.min_size_kb} KB")
        print(f"   Min width: {args.min_width} pixels")
        print(f"   Mode: {'DRY RUN (no deletion)' if args.dry_run else 'DELETE MODE'}")
        print()
        
        # Tìm file ảnh
        if args.check_all:
            print("📂 Scanning all image files in directory...")
            image_files = find_image_files_in_directory(save_dir)
            print(f"   Found {len(image_files)} image files")
        else:
            print("📂 Scanning image files from database...")
            image_files_dict = find_image_files_from_database()
            image_files = list(image_files_dict.values())
            print(f"   Found {len(image_files)} image files referenced in database")
        
        if not image_files:
            print("\n✅ No image files found!")
            return
        
        # Kiểm tra từng file
        thumbnails = []
        for file_path in image_files:
            if is_thumbnail(file_path, args.min_size_kb, args.min_width):
                size_kb = get_image_file_size_kb(file_path)
                width, height = get_image_dimensions(file_path)
                thumbnails.append({
                    'path': file_path,
                    'size_kb': size_kb,
                    'width': width,
                    'height': height
                })
        
        if not thumbnails:
            print("\n✅ No thumbnail images found! All images are high quality.")
            return
        
        # Hiển thị kết quả
        print(f"\n📊 Found {len(thumbnails)} thumbnail images:")
        print("-" * 80)
        total_size_kb = 0.0
        for i, thumb in enumerate(thumbnails, 1):
            file_name = os.path.basename(thumb['path'])
            size_str = f"{thumb['size_kb']:.1f} KB"
            dim_str = f"{thumb['width']}x{thumb['height']}" if thumb['width'] and thumb['height'] else "N/A"
            print(f"   [{i}/{len(thumbnails)}] {file_name}")
            print(f"       Size: {size_str}, Dimensions: {dim_str}")
            total_size_kb += thumb['size_kb']
        
        print("-" * 80)
        print(f"   Total size: {total_size_kb:.1f} KB ({total_size_kb/1024:.2f} MB)")
        print()
        
        # Xóa file nếu không phải dry-run
        if args.dry_run:
            print("🔍 DRY RUN: Would delete the above files.")
            print("   Run without --dry-run to actually delete them.")
        else:
            print(f"🗑️  Deleting {len(thumbnails)} thumbnail files...")
            deleted_count = 0
            failed_count = 0
            
            for thumb in thumbnails:
                try:
                    os.remove(thumb['path'])
                    deleted_count += 1
                    print(f"   ✅ Deleted: {os.path.basename(thumb['path'])}")
                except Exception as e:
                    failed_count += 1
                    print(f"   ⚠️  Failed to delete {os.path.basename(thumb['path'])}: {e}")
            
            print()
            print(f"✅ Deleted {deleted_count} files, {failed_count} failed")
            print()
            print("💡 Next step: Run 'python scripts/redownload_missing_images.py' to download high-quality versions")
        
        print("="*80)


if __name__ == '__main__':
    main()
