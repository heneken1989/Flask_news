"""
Script để generate 3 sitemap riêng cho 3 ngôn ngữ:
- sitemap.xml (EN)
- sitemap-DK.xml (DA)
- sitemap-KL.xml (KL)

Usage:
    python scripts/generate_sitemaps.py
    python scripts/generate_sitemaps.py --output-dir /path/to/output
"""
import sys
import os
import argparse
import re
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import xml.etree.ElementTree as ET

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article


def extract_image_id_from_image_data(image_data):
    """
    Extract imageId từ image_data để tạo URL image
    Có thể lấy từ:
    1. URL image có chứa imageId (ví dụ: ?imageId=2333823)
    2. element_guid (nếu có)
    
    Args:
        image_data: dict chứa image data
        
    Returns:
        imageId (str) hoặc None
    """
    if not image_data:
        return None
    
    # Thử extract từ URL image
    image_urls = [
        image_data.get('desktop_webp'),
        image_data.get('desktop_jpeg'),
        image_data.get('mobile_webp'),
        image_data.get('mobile_jpeg'),
        image_data.get('fallback')
    ]
    
    for url in image_urls:
        if not url:
            continue
        
        # Tìm imageId trong URL
        match = re.search(r'[?&]imageId=(\d+)', url)
        if match:
            return match.group(1)
        
        # Hoặc extract từ path (ví dụ: /2333823.webp)
        match = re.search(r'/(\d+)\.(webp|jpg|jpeg)', url)
        if match:
            return match.group(1)
    
    # Fallback: thử dùng element_guid nếu có (nhưng không chắc chắn)
    # element_guid thường là UUID, không phải imageId
    # return image_data.get('element_guid')
    
    return None


def get_article_url(article, language='en', base_domain='www.sermitsiaq.com'):
    """
    Lấy URL của article theo ngôn ngữ
    
    Args:
        article: Article object
        language: Language code ('en', 'da', 'kl')
        base_domain: Domain để tạo URL (default: www.sermitsiaq.com)
        
    Returns:
        Full URL string
    """
    url_to_use = None
    
    if language == 'en' and article.published_url_en:
        url_to_use = article.published_url_en
    elif article.published_url:
        url_to_use = article.published_url
    else:
        return None
    
    if not url_to_use:
        return None
    
    # Parse URL để lấy path
    parsed = urlparse(url_to_use)
    path_only = parsed.path
    
    # Tạo URL mới với domain mới
    new_url = urlunparse((
        'https',
        base_domain,
        path_only,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    
    return new_url


def format_lastmod(published_date):
    """
    Format published_date thành format: 2026-01-22T00:00+01:00
    
    Args:
        published_date: datetime object hoặc string
        
    Returns:
        Formatted date string
    """
    if not published_date:
        return None
    
    if isinstance(published_date, datetime):
        # Format: 2026-01-22T00:00+01:00
        return published_date.strftime('%Y-%m-%dT00:00+01:00')
    else:
        # Nếu là string, thử parse
        try:
            if isinstance(published_date, str):
                # Thử parse ISO format
                dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%dT00:00+01:00')
        except:
            pass
        
        # Fallback: lấy 10 ký tự đầu (YYYY-MM-DD)
        date_str = str(published_date)[:10]
        if len(date_str) == 10:
            return f"{date_str}T00:00+01:00"
    
    return None


def generate_sitemap(language='en', output_file=None, base_domain='www.sermitsiaq.com'):
    """
    Generate sitemap.xml cho một ngôn ngữ
    
    Args:
        language: Language code ('en', 'da', 'kl')
        output_file: Path to output file (None = return XML string)
        base_domain: Domain để tạo URL (default: sermitsiaq.com)
        
    Returns:
        XML string nếu output_file=None, hoặc None nếu write to file
    """
    with app.app_context():
        # Query articles theo language
        articles = Article.query.filter_by(
            language=language,
            is_temp=False
        ).filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
        ).order_by(
            Article.published_date.desc().nullslast()
        ).all()
        
        print(f"\n📋 Generating sitemap for {language.upper()}...")
        print(f"   Found {len(articles)} articles")
        
        # Create XML root
        root = ET.Element('urlset')
        root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        root.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
        
        url_count = 0
        image_count = 0
        
        for article in articles:
            # Get article URL
            article_url = get_article_url(article, language=language, base_domain=base_domain)
            if not article_url:
                continue
            
            # Create url element
            url_elem = ET.SubElement(root, 'url')
            
            # Loc
            loc_elem = ET.SubElement(url_elem, 'loc')
            loc_elem.text = article_url
            
            # Lastmod
            lastmod = format_lastmod(article.published_date)
            if lastmod:
                lastmod_elem = ET.SubElement(url_elem, 'lastmod')
                lastmod_elem.text = lastmod
            
            # Image - Ưu tiên lấy link từ domain của chúng ta
            if article.image_data:
                image_url = None
                
                # Ưu tiên 1: Kiểm tra xem có URL từ domain của chúng ta không
                # Check theo thứ tự: desktop_webp, fallback, desktop_jpeg, mobile_webp, mobile_jpeg
                for key in ['desktop_webp', 'fallback', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg']:
                    url = article.image_data.get(key)
                    if url:
                        # Check xem có phải URL từ domain của chúng ta không
                        # (chứa sermitsiaq.com và static/uploads/images, hoặc không chứa image.sermitsiaq.ag)
                        if ('sermitsiaq.com' in url and 'static/uploads/images' in url) or \
                           ('sermitsiaq.com' in url and 'image.sermitsiaq.ag' not in url):
                            # Đây là URL từ domain của chúng ta
                            image_url = url
                            break
                
                # Ưu tiên 2: Nếu không có URL từ domain của chúng ta, dùng URL từ trang gốc
                if not image_url:
                    image_id = extract_image_id_from_image_data(article.image_data)
                    if image_id:
                        # Fallback về URL gốc từ image.sermitsiaq.ag
                        image_url = f'https://image.sermitsiaq.ag?imageId={image_id}&format=webp&width=1200'
                
                if image_url:
                    image_elem = ET.SubElement(url_elem, 'image:image')
                    image_loc_elem = ET.SubElement(image_elem, 'image:loc')
                    image_loc_elem.text = image_url
                    image_count += 1
            
            url_count += 1
        
        print(f"   ✅ Generated {url_count} URLs, {image_count} images")
        
        # Create XML string
        ET.indent(root, space='  ')
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        
        # Write to file or return
        if output_file:
            with open(output_file, 'wb') as f:
                f.write(xml_str)
            print(f"   💾 Saved to: {output_file}")
            return None
        else:
            return xml_str


def main():
    parser = argparse.ArgumentParser(
        description='Generate sitemap.xml files for 3 languages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all 3 sitemaps in current directory
  python scripts/generate_sitemaps.py
  
  # Generate to specific output directory
  python scripts/generate_sitemaps.py --output-dir /path/to/output
  
  # Generate only one language
  python scripts/generate_sitemaps.py --language en
        """
    )
    
    parser.add_argument('--output-dir', '-o', default='.',
                        help='Output directory for sitemap files (default: current directory)')
    parser.add_argument('--language', '-l', choices=['en', 'da', 'kl'],
                        help='Generate sitemap for specific language only')
    parser.add_argument('--domain', '-d', default='www.sermitsiaq.com',
                        help='Base domain for URLs (default: www.sermitsiaq.com)')
    
    args = parser.parse_args()
    
    # Create output directory if not exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    languages = [args.language] if args.language else ['en', 'da', 'kl']
    file_names = {
        'en': 'sitemap.xml',
        'da': 'sitemap-DK.xml',
        'kl': 'sitemap-KL.xml'
    }
    
    for lang in languages:
        output_file = os.path.join(args.output_dir, file_names[lang])
        generate_sitemap(
            language=lang,
            output_file=output_file,
            base_domain=args.domain
        )
    
    print(f"\n{'='*60}")
    print(f"✅ All sitemaps generated successfully!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()

