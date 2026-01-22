"""
Script để dịch URL từ DA sang EN cho bảng articles
Dịch slug trong URL từ tiếng Đan Mạch sang tiếng Anh và lưu vào cột published_url_en

Usage:
    python scripts/translate_article_urls.py
    python scripts/translate_article_urls.py --limit 10
    python scripts/translate_article_urls.py --language en
"""
import sys
import os
import argparse
import re
from urllib.parse import urlparse, urlunparse
from deep_translator import GoogleTranslator
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, Article


def extract_slug_from_url(url: str) -> str:
    """
    Extract slug từ URL
    Ví dụ: https://www.sermitsiaq.ag/samfund/hercules-fly-landede-i-nuuk-onsdag/2330773
    -> hercules-fly-landede-i-nuuk-onsdag
    """
    if not url:
        return None
    
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Path format: section/slug/article_id
    # Lấy phần slug (phần giữa section và article_id)
    parts = path.split('/')
    if len(parts) >= 3:
        # Bỏ qua phần đầu (section) và phần cuối (article_id)
        slug = '/'.join(parts[1:-1])
        return slug
    
    return None


def translate_slug(da_slug: str, delay: float = 0.3) -> str:
    """
    Dịch slug từ DA sang EN
    Ví dụ: "hercules-fly-landede-i-nuuk-onsdag" -> "hercules-aircraft-landed-in-nuuk-wednesday"
    
    Args:
        da_slug: Slug tiếng Đan Mạch
        delay: Delay giữa các lần translate (giây)
        
    Returns:
        Slug tiếng Anh
    """
    if not da_slug:
        return None
    
    try:
        # Thay dấu gạch ngang bằng khoảng trắng để dịch
        words = da_slug.replace('-', ' ')
        
        # Dịch
        translator = GoogleTranslator(source='da', target='en')
        translated = translator.translate(words)
        
        time.sleep(delay)  # Delay để tránh rate limit
        
        # Chuyển lại thành slug (lowercase, thay khoảng trắng bằng dấu gạch ngang)
        en_slug = translated.lower().strip()
        en_slug = re.sub(r'[^\w\s-]', '', en_slug)  # Loại bỏ ký tự đặc biệt
        en_slug = re.sub(r'\s+', '-', en_slug)  # Thay khoảng trắng bằng dấu gạch ngang
        en_slug = re.sub(r'-+', '-', en_slug)  # Loại bỏ dấu gạch ngang trùng lặp
        
        return en_slug
    except Exception as e:
        print(f"      ⚠️  Translation error: {e}")
        return None


# Section name mapping từ DA sang EN
SECTION_MAPPING = {
    'samfund': 'society',
    'erhverv': 'business',
    'kultur': 'culture',
    'sport': 'sport',  # Giữ nguyên
    'podcasti': 'podcast',
    'politik': 'politics',
    'indland': 'domestic',
    'udland': 'international',
    'sundhed': 'health',
    'uddannelse': 'education',
    'nuuk': 'nuuk'  # Giữ nguyên (tên địa danh)
}


def translate_section(da_section: str) -> str:
    """
    Dịch section name từ DA sang EN
    
    Args:
        da_section: Section name tiếng Đan Mạch
        
    Returns:
        Section name tiếng Anh
    """
    # Kiểm tra mapping trước
    if da_section.lower() in SECTION_MAPPING:
        return SECTION_MAPPING[da_section.lower()]
    
    # Nếu không có trong mapping, thử dịch bằng Google Translator
    try:
        translator = GoogleTranslator(source='da', target='en')
        translated = translator.translate(da_section)
        time.sleep(0.3)  # Delay để tránh rate limit
        
        # Chuyển thành lowercase và slug format
        en_section = translated.lower().strip()
        en_section = re.sub(r'[^\w\s-]', '', en_section)  # Loại bỏ ký tự đặc biệt
        en_section = re.sub(r'\s+', '-', en_section)  # Thay khoảng trắng bằng dấu gạch ngang
        
        return en_section
    except Exception as e:
        print(f"      ⚠️  Translation error for section '{da_section}': {e}")
        # Fallback: giữ nguyên nếu không dịch được
        return da_section.lower()


def translate_url(da_url: str, delay: float = 0.3) -> str:
    """
    Dịch URL từ DA sang EN (bao gồm cả section và slug)
    Ví dụ: 
    https://www.sermitsiaq.ag/erhverv/greenland-committee-invited-to-avannaata-qimussersua/2329146
    -> https://www.sermitsiaq.ag/business/greenland-committee-invited-to-avannaata-qimussersua/2329146
    
    Args:
        da_url: URL tiếng Đan Mạch
        delay: Delay giữa các lần translate (giây)
        
    Returns:
        URL tiếng Anh
    """
    if not da_url:
        return None
    
    try:
        parsed = urlparse(da_url)
        path = parsed.path.strip('/')
        
        # Path format: section/slug/article_id
        parts = path.split('/')
        if len(parts) >= 3:
            da_section = parts[0]
            slug = '/'.join(parts[1:-1])
            article_id = parts[-1]
            
            # Dịch section
            en_section = translate_section(da_section)
            
            # Dịch slug
            en_slug = translate_slug(slug, delay=delay)
            if not en_slug:
                return None
            
            # Tạo path mới với section và slug đã dịch
            new_path = f'/{en_section}/{en_slug}/{article_id}'
            
            # Tạo URL mới
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                new_path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            return new_url
        else:
            # Không đúng format, trả về None
            return None
            
    except Exception as e:
        print(f"      ⚠️  Error translating URL: {e}")
        return None


def translate_article_urls(language='en', limit=None, delay=0.3, force=False):
    """
    Dịch URL từ DA sang EN cho tất cả articles
    
    Args:
        language: Language code để filter (chỉ dịch cho articles có language này)
        limit: Giới hạn số lượng articles
        delay: Delay giữa các lần translate (giây)
        force: Nếu True, dịch lại cả các articles đã có published_url_en
    """
    with app.app_context():
        # Lấy tất cả articles có published_url
        query = Article.query.filter(
            Article.published_url.isnot(None),
            Article.published_url != ''
        )
        
        # Nếu không force, chỉ lấy articles chưa có published_url_en
        if not force:
            query = query.filter(
                (Article.published_url_en.is_(None) | (Article.published_url_en == ''))
            )
        
        # Filter theo language nếu có
        if language:
            query = query.filter_by(language=language)
        
        # Loại bỏ www.sjob.gl
        query = query.filter(~Article.published_url.contains('www.sjob.gl'))
        
        # Order by id
        query = query.order_by(Article.id)
        
        # Limit
        if limit:
            query = query.limit(limit)
        
        articles = query.all()
        
        if not articles:
            if force:
                print("\n✅ Không có articles nào để dịch lại!")
            else:
                print("\n✅ Không có articles nào cần dịch URL!")
            return
        
        if force:
            print(f"\n🔄 Bắt đầu dịch lại URL cho {len(articles)} articles (force mode)...\n")
        else:
            print(f"\n🌐 Bắt đầu dịch URL cho {len(articles)} articles...\n")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for i, article in enumerate(articles, 1):
            print(f"\n[{i}/{len(articles)}] Article ID: {article.id}")
            print(f"   DA URL: {article.published_url[:70]}...")
            
            try:
                # Dịch URL
                en_url = translate_url(article.published_url, delay=delay)
                
                if en_url:
                    article.published_url_en = en_url
                    db.session.commit()
                    print(f"   ✅ EN URL: {en_url[:70]}...")
                    success_count += 1
                else:
                    print(f"   ⏭️  Skipped - Could not translate URL")
                    skip_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                fail_count += 1
        
        print(f"\n{'='*60}")
        print(f"✅ Hoàn thành dịch URL!")
        print(f"   Success: {success_count}/{len(articles)}")
        print(f"   Skipped: {skip_count}/{len(articles)}")
        print(f"   Failed: {fail_count}/{len(articles)}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Dịch URL từ DA sang EN cho bảng articles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dịch tất cả articles chưa có published_url_en
  python scripts/translate_article_urls.py
  
  # Dịch giới hạn số lượng
  python scripts/translate_article_urls.py --limit 10
  
  # Dịch chỉ cho articles có language='en'
  python scripts/translate_article_urls.py --language en
  
  # Delay giữa các lần translate (mặc định: 0.3s)
  python scripts/translate_article_urls.py --delay 0.5
  
  # Dịch lại cả các articles đã có published_url_en (force mode)
  python scripts/translate_article_urls.py --force
        """
    )
    
    parser.add_argument('--language', '-l', default='en',
                        help='Language code để filter (default: en)')
    parser.add_argument('--limit', '-n', type=int,
                        help='Giới hạn số lượng articles')
    parser.add_argument('--delay', '-d', type=float, default=0.3,
                        help='Delay giữa các lần translate (seconds, default: 0.3)')
    parser.add_argument('--force', action='store_true',
                        help='Dịch lại cả các articles đã có published_url_en')
    
    args = parser.parse_args()
    
    translate_article_urls(
        language=args.language,
        limit=args.limit,
        delay=args.delay,
        force=args.force
    )


if __name__ == '__main__':
    main()

