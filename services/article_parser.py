"""
Parser để extract article data từ HTML của sermitsiaq.ag
"""
from bs4 import BeautifulSoup
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse


def parse_title_with_highlights(title_elem):
    """
    Parse title element để extract text và các phần được highlight với màu sắc
    
    Args:
        title_elem: BeautifulSoup element của h2.headline
    
    Returns:
        dict: {
            'full_text': str,  # Full title text (plain text)
            'parts': [  # List of title parts với highlight info
                {'text': str, 'color_class': str or None},
                ...
            ]
        }
    """
    if not title_elem:
        return None
    
    try:
        # Lấy full text (plain text, không có HTML)
        full_text = title_elem.get_text(strip=False)  # Giữ newlines
        
        # Parse các parts với highlight
        parts = []
        
        # Duyệt qua tất cả children của title_elem
        for child in title_elem.children:
            if hasattr(child, 'name'):
                # Nếu là tag (span, etc.)
                if child.name == 'span':
                    # Extract color classes từ span
                    span_classes = child.get('class', [])
                    color_class = ' '.join(span_classes) if span_classes else None
                    text = child.get_text(strip=False)  # Giữ newlines
                    parts.append({
                        'text': text,
                        'color_class': color_class
                    })
                else:
                    # Tag khác, lấy text
                    text = child.get_text(strip=False)
                    if text.strip():
                        parts.append({
                            'text': text,
                            'color_class': None
                        })
            else:
                # Text node
                text = str(child).strip()
                if text:
                    parts.append({
                        'text': text,
                        'color_class': None
                    })
        
        # Nếu không có parts (không có span), tạo 1 part với full text
        if not parts:
            parts.append({
                'text': full_text,
                'color_class': None
            })
        
        return {
            'full_text': full_text.strip(),
            'parts': parts
        }
    except Exception as e:
        print(f"⚠️  Error parsing title with highlights: {e}")
        # Fallback: return plain text
        return {
            'full_text': title_elem.get_text(strip=True),
            'parts': [{'text': title_elem.get_text(strip=True), 'color_class': None}]
        }


def extract_grid_size_from_classes(article_classes):
    """
    Extract grid size từ article classes (large-5, large-6, large-7, etc.)
    
    Args:
        article_classes: List of class strings hoặc string
    
    Returns:
        int: Grid size (5, 6, 7, 8, 4, 12, etc.) hoặc None
    """
    try:
        if isinstance(article_classes, str):
            class_str = article_classes
        else:
            class_str = ' '.join(article_classes) if article_classes else ''
        
        # Tìm pattern large-X trong class string
        import re
        match = re.search(r'large-(\d+)', class_str)
        if match:
            return int(match.group(1))
        return None
    except:
        return None


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
        
        # Title với highlights
        title_elem = article_element.find('h2', class_='headline')
        title_data = parse_title_with_highlights(title_elem) if title_elem else None
        if not title_data or not title_data['full_text']:
            return None
        
        title = title_data['full_text']  # Plain text cho backward compatibility
        title_parts = title_data['parts']  # Parts với highlight info
        
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
        
        # Extract kicker floating (text màu xanh trên hình ảnh)
        kicker_floating = None
        floating_text_elem = article_element.find('div', class_='floatingText')
        if floating_text_elem:
            kicker_elem = floating_text_elem.find('div', class_=lambda x: x and 'kicker' in x and 'floating' in x)
            if kicker_elem:
                kicker_floating = kicker_elem.get_text(strip=True)
        
        # Extract kicker below (text nằm giữa media và headline, ví dụ "OPDATERET")
        kicker_below = None
        kicker_below_classes = None
        # Tìm div với class "kicker below" trong article element
        kicker_below_elem = article_element.find('div', class_=lambda x: x and 'kicker' in x and 'below' in x)
        if kicker_below_elem:
            kicker_below = kicker_below_elem.get_text(strip=True)
            # Lấy classes của kicker below để giữ nguyên styling
            kicker_below_classes = ' '.join(kicker_below_elem.get('class', []))
        
        # Image data
        image_data = parse_article_image(article_element, base_url)
        
        # Extract slug từ URL
        slug = extract_slug_from_url(url)
        
        # Extract article ID từ URL (nếu có)
        article_id = extract_article_id_from_url(url)
        
        # Extract grid size từ classes
        article_classes = article_element.get('class', [])
        grid_size = extract_grid_size_from_classes(article_classes)
        
        return {
            'element_guid': element_guid,
            'title': title,
            'title_parts': title_parts,  # Parts với highlight info
            'slug': slug,
            'url': url,
            'k5a_url': k5a_url,
            'section': section,
            'site_alias': site_alias,
            'instance': instance,
            'published_date': published_date,
            'is_paywall': is_paywall,
            'paywall_class': paywall_class,
            'kicker_floating': kicker_floating,
            'kicker_below': kicker_below,  # Kicker below (ví dụ "OPDATERET")
            'kicker_below_classes': kicker_below_classes,  # Classes của kicker below
            'image_data': image_data,
            'article_id': article_id,
            'grid_size': grid_size,  # Lưu grid size từ HTML
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


def detect_layout_type_from_element(article_elem, row_elem=None):
    """
    Detect layout_type từ article element và row structure
    
    Args:
        article_elem: BeautifulSoup element của article
        row_elem: BeautifulSoup element của row chứa article (optional)
    
    Returns:
        str: Layout type ('1_full', '2_articles', '3_articles', '1_special_bg', etc.)
    """
    try:
        # Check article classes để xác định grid size
        article_classes = article_elem.get('class', [])
        article_class_str = ' '.join(article_classes) if article_classes else ''
        
        # Check special background (nhưng không return ngay, vì có thể là 2_articles với bg-black)
        content_div = article_elem.find('div', class_='content')
        has_special_bg = False
        if content_div:
            content_classes = content_div.get('class', [])
            content_class_str = ' '.join(content_classes) if content_classes else ''
            if 'bg-black' in content_class_str:
                has_special_bg = True
        
        # Nếu có row_elem, check số lượng articles trong row để xác định layout
        if row_elem:
            # Lọc chỉ lấy elements có name (bỏ qua text nodes, comments, etc.)
            row_children = [child for child in row_elem.children 
                           if hasattr(child, 'name') and child.name is not None]
            
            # Đếm số articles trong row
            articles_in_row = [child for child in row_children if child.name == 'article']
            
            # Check xem có list bên cạnh không
            list_elem = row_elem.find('div', class_='articlesByTag')
            if not list_elem:
                list_elem = row_elem.find('div', class_='toplist')
            
            if list_elem:
                # Có list trong row - check vị trí
                article_index = None
                list_index = None
                
                for idx, child in enumerate(row_children):
                    if child.name == 'article':
                        if child == article_elem or child.get('data-element-guid') == article_elem.get('data-element-guid'):
                            article_index = idx
                    elif child.name == 'div':
                        child_classes = child.get('class', [])
                        if 'articlesByTag' in child_classes or 'toplist' in child_classes:
                            list_index = idx
                
                if article_index is not None and list_index is not None:
                    if list_index < article_index:
                        return '1_with_list_left'
                    else:
                        return '1_with_list_right'
            
            # Nếu có 2 articles trong row, đó là 2_articles (bất kể grid size)
            if len(articles_in_row) == 2:
                return '2_articles'
            # Nếu có 3 articles trong row, đó là 3_articles
            elif len(articles_in_row) == 3:
                return '3_articles'
        
        # Check grid size từ classes (fallback nếu không có row_elem)
        if 'large-12' in article_class_str:
            # Full width - có thể là 1_full
            return '1_full'
        elif 'large-6' in article_class_str or 'large-5' in article_class_str or 'large-7' in article_class_str or 'large-8' in article_class_str:
            # 2 per row (với các tỷ lệ khác nhau: 6+6, 5+7, 8+4, etc.)
            return '2_articles'
        elif 'large-4' in article_class_str:
            # 3 per row
            return '3_articles'
        
        # Nếu có special bg và không phải 2_articles, return 1_special_bg
        if has_special_bg:
            return '1_special_bg'
        
        # Default
        return '1_full'
    except:
        return '1_full'  # Default fallback


def parse_articles_from_html(html_content, base_url='https://www.sermitsiaq.ag', is_home=False):
    """
    Parse tất cả articles từ HTML content
    
    Args:
        html_content: HTML content string
        base_url: Base URL để resolve relative URLs
        is_home: Nếu True, sẽ detect layout_type từ HTML structure
    
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
            rows = []
        else:
            article_elements = page_content.find_all('article', attrs={'data-element-guid': True})
            # Tìm rows nếu là home page
            if is_home:
                rows = page_content.find_all('div', class_='row')
            else:
                rows = []
        
        print(f"📰 Found {len(article_elements)} article elements")
        
        for article_elem in article_elements:
            article_data = parse_article_element(article_elem, base_url)
            if article_data:
                # Nếu là home page, detect layout_type
                if is_home:
                    # Tìm row chứa article này
                    row_elem = None
                    for row in rows:
                        if article_elem in row.find_all('article'):
                            row_elem = row
                            break
                    
                    layout_type = detect_layout_type_from_element(article_elem, row_elem)
                    article_data['layout_type'] = layout_type
                    
                    # Detect layout_data nếu có
                    layout_data = {}
                    
                    # Thêm kicker_floating vào layout_data nếu có (cho tất cả layout types)
                    if article_data.get('kicker_floating'):
                        layout_data['kicker_floating'] = article_data['kicker_floating']
                    
                    # Thêm kicker_below vào layout_data nếu có (cho tất cả layout types)
                    if article_data.get('kicker_below'):
                        layout_data['kicker_below'] = article_data['kicker_below']
                        layout_data['kicker_below_classes'] = article_data.get('kicker_below_classes', 'kicker below primary color_mobile_primary')
                    
                    # Thêm title_parts vào layout_data nếu có highlights (cho tất cả layout types)
                    if article_data.get('title_parts'):
                        layout_data['title_parts'] = article_data['title_parts']
                    
                    # Check và lưu has_bg_black nếu article có bg-black (cho tất cả layout types)
                    content_div = article_elem.find('div', class_='content')
                    if content_div:
                        content_classes = content_div.get('class', [])
                        content_class_str = ' '.join(content_classes) if content_classes else ''
                        if 'bg-black' in content_class_str:
                            layout_data['has_bg_black'] = True
                            # Lưu tất cả classes của content div để giữ nguyên styling
                            layout_data['content_classes'] = content_class_str
                    
                    if layout_type == '1_special_bg':
                        # Check kicker
                        kicker_elem = article_elem.find('div', class_='kicker')
                        if kicker_elem:
                            layout_data['kicker'] = kicker_elem.get_text(strip=True)
                    elif layout_type in ['1_with_list_left', '1_with_list_right']:
                        # Parse list items từ row
                        if row_elem:
                            # Tìm list element (có thể là articlesByTag hoặc toplist)
                            list_elem = row_elem.find('div', class_='articlesByTag')
                            if not list_elem:
                                list_elem = row_elem.find('div', class_='toplist')
                            
                            if list_elem:
                                # Extract list title - có thể là h3 với class headline hoặc không
                                list_title_elem = list_elem.find('h3')
                                if list_title_elem:
                                    layout_data['list_title'] = list_title_elem.get_text(strip=True)
                                
                                # Extract list items
                                list_items = []
                                # Tìm trong ul.toplist-results hoặc ul thông thường
                                ul_elem = list_elem.find('ul', class_='toplist-results')
                                if not ul_elem:
                                    ul_elem = list_elem.find('ul')
                                
                                if ul_elem:
                                    for li in ul_elem.find_all('li'):
                                        link = li.find('a')
                                        if link:
                                            # Tìm title - có thể là h4 với class abt-title hoặc h4 thông thường
                                            # Title có thể nằm trong link hoặc trong li
                                            title_elem = link.find('h4', class_='abt-title')
                                            if not title_elem:
                                                title_elem = link.find('h4')
                                            if not title_elem:
                                                # Fallback: tìm trong li
                                                title_elem = li.find('h4', class_='abt-title')
                                            if not title_elem:
                                                title_elem = li.find('h4')
                                            
                                            if title_elem:
                                                title = title_elem.get_text(strip=True)
                                                url = link.get('href', '')
                                                if title and url:
                                                    list_items.append({
                                                        'title': title,
                                                        'url': url
                                                    })
                                
                                if list_items:
                                    layout_data['list_items'] = list_items
                    
                    if layout_data:
                        article_data['layout_data'] = layout_data
                
                articles.append(article_data)
        
        print(f"✅ Successfully parsed {len(articles)} articles")
        
    except Exception as e:
        print(f"❌ Error parsing HTML: {e}")
        import traceback
        traceback.print_exc()
    
    return articles

