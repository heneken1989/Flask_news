"""
Script để tạo test article detail để kiểm tra xem đã fix duplicate chưa
Giữ nguyên article cũ, tạo test version với URL khác

Usage:
    python flask/scripts/re_crawl_article.py --url "https://www.sermitsiaq.ag/..."
"""
import sys
import os
import argparse
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article, ArticleDetail
from scripts.crawl_article_details_batch import crawl_article_detail

def create_test_url(url):
    """
    Tạo test URL từ URL gốc bằng cách thêm -test vào trước phần cuối
    
    Args:
        url: URL gốc
        
    Returns:
        Test URL
    """
    # Thêm -test trước phần cuối của URL (trước số ID hoặc trước dấu / cuối)
    # Ví dụ: https://www.sermitsiaq.ag/.../2335959 -> https://www.sermitsiaq.ag/.../2335959-test
    if url.endswith('/'):
        test_url = url.rstrip('/') + '-test'
    else:
        test_url = url + '-test'
    return test_url

def re_crawl_article(url, language='da', headless=True, download_images=True):
    """
    Tạo test article detail để kiểm tra duplicate (giữ nguyên article cũ)
    
    Args:
        url: URL của article cần crawl lại
        language: Language code
        headless: Run browser in headless mode
        download_images: Download images nếu True
    """
    with app.app_context():
        print(f"\n🔍 Creating test article for: {url}")
        print(f"   Language: {language}")
        
        # Tạo test URL
        test_url = create_test_url(url)
        print(f"\n   📋 Test URL: {test_url}")
        
        # Kiểm tra xem đã có test article detail chưa
        existing_test = ArticleDetail.query.filter_by(published_url=test_url).first()
        
        if existing_test:
            print(f"\n   ⚠️  Test ArticleDetail already exists:")
            print(f"      ID: {existing_test.id}")
            print(f"      Language: {existing_test.language}")
            print(f"      Blocks: {len(existing_test.content_blocks) if existing_test.content_blocks else 0}")
            
            # Xóa test article detail cũ để tạo lại
            print(f"\n   🗑️  Deleting old test ArticleDetail...")
            db.session.delete(existing_test)
            db.session.commit()
            print(f"      ✅ Deleted test ArticleDetail ID {existing_test.id}")
        
        # Tìm Article gốc
        article = Article.query.filter_by(published_url=url).first()
        if not article:
            print(f"\n   ⚠️  Article not found with URL: {url}")
            print(f"   ℹ️  Will crawl anyway...")
        
        # Crawl với test URL (nhưng crawl từ URL gốc)
        print(f"\n   🚀 Crawling article detail (from original URL, saving as test)...")
        
        # Crawl từ URL gốc
        result = crawl_article_detail(
            url=url,  # Crawl từ URL gốc
            language=language,
            headless=headless,
            download_images=download_images
        )
        
        if result:
            # Thay đổi published_url thành test URL
            print(f"\n   🔄 Changing published_url to test URL...")
            result.published_url = test_url
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(result, 'published_url')
            db.session.commit()
            
            print(f"\n   ✅ Successfully created test article!")
            print(f"      ArticleDetail ID: {result.id}")
            print(f"      Published URL: {result.published_url}")
            print(f"      Blocks: {len(result.content_blocks) if result.content_blocks else 0}")
            
            # Kiểm tra duplicate
            print(f"\n   🔍 Checking for duplicates...")
            from scripts.check_duplicate_paragraphs import find_duplicate_paragraphs_in_article
            duplicates = find_duplicate_paragraphs_in_article(result)
            
            if duplicates:
                print(f"\n   ⚠️  Found {len(duplicates)} duplicate pairs:")
                for dup in duplicates:
                    print(f"      - Block {dup['block1_index']} vs Block {dup['block2_index']} (similarity: {dup['similarity']:.2%})")
                    print(f"        Block {dup['block1_index']}: {dup['block1_text'][:100]}...")
                    print(f"        Block {dup['block2_index']}: {dup['block2_text'][:100]}...")
            else:
                print(f"\n   ✅ No duplicates found!")
            
            print(f"\n   📝 Test article URL: {test_url}")
            print(f"   📝 Original article URL: {url}")
        else:
            print(f"\n   ❌ Failed to crawl article detail")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Re-crawl một article để test fix duplicate')
    parser.add_argument('--url', type=str, required=True, help='URL của article cần crawl lại')
    parser.add_argument('--language', '-l', choices=['da', 'kl', 'en'], default='da',
                        help='Language code (default: da)')
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in no-headless mode')
    parser.add_argument('--no-download-images', action='store_true',
                        help='Tắt download images')
    
    args = parser.parse_args()
    
    re_crawl_article(
        url=args.url,
        language=args.language,
        headless=not args.no_headless,
        download_images=not args.no_download_images
    )
