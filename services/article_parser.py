"""
Parser để extract article data từ HTML của sermitsiaq.ag
"""
from bs4 import BeautifulSoup
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse


def parse_article_element(article_element, base_url='https://www.sermitsiaq.ag'):
    """
    Parse một article element từ HTML để extract data
    
    Args:
        article_element: BeautifulSoup element của article
        base_url: Base URL để resolve relative URLs
    
    Returns:
        dict: Article data hoặc None nếu không parse được
    """
    try:
        # Lấy element_guid từ data-element-guid attribute
        element_guid = article_element.get('data-element-guid', '')
        if not element_guid:
            return None
        
        # Lấy instance và site_alias
        instance = article_element.get('data-instance', '')
        site_alias = article_element.get('data-site-alias', 'sermitsiaq')
        section = article_element.get('data-section', '')
        
        # Tìm link chính của article
        link_elem = article_element.find('a', itemprop='url')
        if not link_elem:
            return None
        
        # URL và k5a_url
        url = link_elem.get('href', '')
        k5a_url = link_elem.get('data-k5a-url', url)
        
        # Resolve relative URLs
        if url and not url.startswith('http'):
            url = urljoin(base_url, url)
        if k5a_url and not k5a_url.startswith('http'):
            k5a_url = urljoin(base_url, k5a_url)
        
        # Title
        title_elem = article_element.find('h2', class_='headline')
        title = title_elem.get_text(strip=True) if title_elem else ''
        if not title:
            return None
        
        # Published date
        time_elem = article_element.find('time', itemprop='datePublished')
        published_date = None
        if time_elem:
            datetime_str = time_elem.get('datetime', '')
            if datetime_str:
                try:
                    # Parse ISO format: 2026-01-15T20:29:57+01:00
                    published_date = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                except:
                    pass
        
        # Paywall check
        paywall_elem = article_element.find('div', class_='paywallLabel')
        is_paywall = paywall_elem is not None
        paywall_class = 'paywall' if is_paywall else ''
        
        # Image data
        image_data = parse_article_image(article_element, base_url)
        
        # Extract slug từ URL
        slug = extract_slug_from_url(url)
        
        # Extract article ID từ URL (nếu có)
        article_id = extract_article_id_from_url(url)
        
        return {
            'element_guid': element_guid,
            'title': title,
            'slug': slug,
            'url': url,
            'k5a_url': k5a_url,
            'section': section,
            'site_alias': site_alias,
            'instance': instance,
            'published_date': published_date,
            'is_paywall': is_paywall,
            'paywall_class': paywall_class,
            'image_data': image_data,
            'article_id': article_id,
        }
    except Exception as e:
        print(f"⚠️  Error parsing article element: {e}")
        return None


def parse_article_image(article_element, base_url='https://www.sermitsiaq.ag'):
    """
    Parse image data từ article element
    
    Args:
        article_element: BeautifulSoup element của article
        base_url: Base URL để resolve relative URLs
    
    Returns:
        dict: Image data
    """
    image_data = {}
    
    try:
        # Tìm figure element
        figure = article_element.find('figure')
        if not figure:
            return image_data
        
        # Lấy element_guid của image
        image_element_guid = figure.get('data-element-guid', '')
        if image_element_guid:
            image_data['element_guid'] = image_element_guid
        
        # Tìm picture element
        picture = figure.find('picture')
        if not picture:
            # Fallback: tìm img trực tiếp
            img = figure.find('img')
            if img:
                src = img.get('src', '')
                if src and not src.startswith('http'):
                    src = urljoin(base_url, src)
                image_data['fallback'] = src
                image_data['desktop_webp'] = src
                image_data['desktop_jpeg'] = src
                image_data['mobile_webp'] = src
                image_data['mobile_jpeg'] = src
                image_data['alt'] = img.get('alt', '')
                image_data['title'] = img.get('title', '')
                image_data['desktop_width'] = img.get('width', '524')
                image_data['desktop_height'] = img.get('height', '341')
                image_data['mobile_width'] = img.get('width', '480')
                image_data['mobile_height'] = img.get('height', '312')
            return image_data
        
        # Parse source elements
        sources = picture.find_all('source')
        for source in sources:
            srcset = source.get('srcset', '')
            media = source.get('media', '')
            img_type = source.get('type', '')
            
            if not srcset:
                continue
            
            # Resolve relative URLs
            if not srcset.startswith('http'):
                srcset = urljoin(base_url, srcset)
            
            # Determine image type
            if 'webp' in img_type:
                if 'min-width: 768px' in media or 'min-width: 768' in media:
                    image_data['desktop_webp'] = srcset
                elif 'max-width: 767px' in media or 'max-width: 767' in media:
                    image_data['mobile_webp'] = srcset
            elif 'jpeg' in img_type or 'jpg' in img_type:
                if 'min-width: 768px' in media or 'min-width: 768' in media:
                    image_data['desktop_jpeg'] = srcset
                elif 'max-width: 767px' in media or 'max-width: 767' in media:
                    image_data['mobile_jpeg'] = srcset
        
        # Fallback img
        img = picture.find('img')
        if img:
            src = img.get('src', '')
            if src and not src.startswith('http'):
                src = urljoin(base_url, src)
            image_data['fallback'] = src
            image_data['alt'] = img.get('alt', '')
            image_data['title'] = img.get('title', '')
            image_data['desktop_width'] = img.get('width', '524')
            image_data['desktop_height'] = img.get('height', '341')
            image_data['mobile_width'] = img.get('width', '480')
            image_data['mobile_height'] = img.get('height', '312')
        
    except Exception as e:
        print(f"⚠️  Error parsing image: {e}")
    
    return image_data


def extract_slug_from_url(url):
    """
    Extract slug từ URL
    Ví dụ: https://www.sermitsiaq.ag/erhverv/article-slug/2329217 -> article-slug
    """
    if not url:
        return ''
    
    try:
        # Parse URL
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Split path
        parts = path.split('/')
        if len(parts) >= 2:
            # Lấy phần trước số ID
            slug = parts[-2] if parts[-1].isdigit() else parts[-1]
            return slug
        return ''
    except:
        return ''


def extract_article_id_from_url(url):
    """
    Extract article ID từ URL
    Ví dụ: https://www.sermitsiaq.ag/erhverv/article-slug/2329217 -> 2329217
    """
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        parts = path.split('/')
        
        # Lấy số cuối cùng trong path
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None
    except:
        return None


def parse_articles_from_html(html_content, base_url='https://www.sermitsiaq.ag'):
    """
    Parse tất cả articles từ HTML content
    
    Args:
        html_content: HTML content string
        base_url: Base URL để resolve relative URLs
    
    Returns:
        list: List of article dictionaries
    """
    articles = []
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Tìm tất cả article elements
        # Selector: article[data-element-guid] trong .page-content
        page_content = soup.find('div', class_='page-content')
        if not page_content:
            # Fallback: tìm tất cả articles
            article_elements = soup.find_all('article', attrs={'data-element-guid': True})
        else:
            article_elements = page_content.find_all('article', attrs={'data-element-guid': True})
        
        print(f"📰 Found {len(article_elements)} article elements")
        
        for article_elem in article_elements:
            article_data = parse_article_element(article_elem, base_url)
            if article_data:
                articles.append(article_data)
        
        print(f"✅ Successfully parsed {len(articles)} articles")
        
    except Exception as e:
        print(f"❌ Error parsing HTML: {e}")
        import traceback
        traceback.print_exc()
    
    return articles

