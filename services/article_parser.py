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


def parse_slider_item(slider_item_elem, base_url='https://www.sermitsiaq.ag'):
    """
    Parse một article item trong slider
    
    Args:
        slider_item_elem: BeautifulSoup element của li.scroll-item
        base_url: Base URL để resolve relative URLs
    
    Returns:
        dict: Article data trong slider
    """
    try:
        link = slider_item_elem.find('a')
        if not link:
            print(f"    ⚠️  Slider item has no <a> tag")
            return None
        
        url = link.get('href', '')
        if not url:
            print(f"    ⚠️  Slider item has no href")
            return None
        
        if url and not url.startswith('http'):
            url = urljoin(base_url, url)
        
        # Parse image - figure nằm trong <a>
        image_data = {}
        figure = link.find('figure')  # Tìm figure trong <a>, không phải trong <li>
        if figure:
            img = figure.find('img')
            if img:
                img_src = img.get('src', '')
                if img_src and not img_src.startswith('http'):
                    img_src = urljoin(base_url, img_src)
                image_data['src'] = img_src
                image_data['alt'] = img.get('alt', '')
                image_data['width'] = img.get('width', '265')
                image_data['height'] = img.get('height', '159')
        
        # Parse paywall - có thể nằm trong figure (trong <a>) hoặc ngoài <li>
        is_paywall = False
        paywall_in_figure = figure.find('div', class_='paywallLabel') if figure else None
        paywall_in_link = link.find('div', class_='paywallLabel')  # Có thể nằm trong <a> nhưng ngoài figure
        paywall_outside = slider_item_elem.find('div', class_='paywallLabel')  # Hoặc ngoài <a>
        is_paywall = paywall_in_figure is not None or paywall_in_link is not None or paywall_outside is not None
        
        # Parse title và kicker - text-container nằm trong <a>
        text_container = link.find('div', class_='text-container')  # Tìm trong <a>, không phải trong <li>
        title = ''
        kicker = ''
        
        if text_container:
            # Title là h3
            h3 = text_container.find('h3')
            if h3:
                title = h3.get_text(strip=True)
            
            # Kicker là h4 (có thể không có)
            h4 = text_container.find('h4')
            if h4:
                kicker = h4.get_text(strip=True)
        
        # Parse section
        section = slider_item_elem.get('data-section', '')
        
        # Luôn trả về kết quả, ngay cả khi thiếu title (có thể có trường hợp đặc biệt)
        result = {
            'url': url,
            'title': title,
            'kicker': kicker,
            'image': image_data,
            'is_paywall': is_paywall,
            'section': section
        }
        
        return result
    except Exception as e:
        print(f"⚠️  Error parsing slider item: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_slider(slider_elem, base_url='https://www.sermitsiaq.ag'):
    """
    Parse một slider (articlescroller) element
    
    Args:
        slider_elem: BeautifulSoup element của div.articlescroller
        base_url: Base URL để resolve relative URLs
    
    Returns:
        dict: Slider data với layout_type='slider' và layout_data chứa slider info
    """
    try:
        element_guid = slider_elem.get('data-element-guid', '')
        slider_id = slider_elem.get('id', '')
        
        # Parse slider title và header link (cho JOB slider)
        title_elem = slider_elem.find('h2', class_='articlescroller-header')
        slider_title = ''
        header_link = None
        if title_elem:
            # Check xem có link trong header không (JOB slider)
            link_elem = title_elem.find('a')
            if link_elem:
                header_link = {
                    'url': link_elem.get('href', ''),
                    'text': link_elem.get_text(strip=True)
                }
                slider_title = header_link['text']
            else:
                # Title có thể có span bên trong
                span = title_elem.find('span')
                if span:
                    slider_title = span.get_text(strip=True)
                else:
                    slider_title = title_elem.get_text(strip=True)
        
        # Parse các articles trong slider
        # Tìm ul.scroll-container - có thể nằm trong .inner.content
        inner_content = slider_elem.find('div', class_='inner')
        if not inner_content:
            inner_content = slider_elem
        
        scroll_container = inner_content.find('ul', class_=lambda x: x and 'scroll-container' in x)
        if not scroll_container:
            # Fallback: tìm bất kỳ ul nào có class chứa 'scroll'
            scroll_container = inner_content.find('ul', class_=lambda x: x and 'scroll' in str(x).lower())
        
        # Check xem có nav buttons không
        has_nav = inner_content.find('nav') is not None
        
        # Check xem có phải slider NUUK không (source_nuuk class hoặc count_5)
        slider_classes = slider_elem.get('class', [])
        is_nuuk_slider = 'source_nuuk' in slider_classes
        
        # Check xem có phải JOB slider không (source_job-dk, source_feed_random_kl_jobs, hoặc source_job)
        is_job_slider = (
            'source_job-dk' in slider_classes or 
            'source_feed_random_kl_jobs' in slider_classes or
            'source_job' in str(slider_classes)
        )
        
        # Parse các class đặc biệt cho JOB slider
        extra_classes = []
        if 'bg-custom-2' in slider_classes:
            extra_classes.append('bg-custom-2')
        if 'color_mobile_bg-custom-2' in slider_classes:
            extra_classes.append('color_mobile_bg-custom-2')
        if 'hasContentPadding' in slider_classes:
            extra_classes.append('hasContentPadding')
        if 'mobile-hasContentPadding' in slider_classes:
            extra_classes.append('mobile-hasContentPadding')
        if 'layout-align-centered' in slider_classes:
            extra_classes.append('layout-align-centered')
        
        # Parse header classes cho JOB (lưu tất cả classes từ header)
        header_classes = []
        if title_elem:
            title_classes = title_elem.get('class', [])
            # Lưu tất cả classes từ header để giữ nguyên styling
            header_classes = title_classes.copy() if title_classes else []
        
        # Check count class từ scroll-container
        scroll_container_classes = scroll_container.get('class', []) if scroll_container else []
        count_class = None
        for cls in scroll_container_classes:
            if cls.startswith('count_'):
                count_class = cls
                count_num = cls.replace('count_', '')
                if count_num == '5':
                    is_nuuk_slider = True
                break
        
        slider_articles = []
        
        if scroll_container:
            # Tìm tất cả li.scroll-item - có thể có nhiều class, nên dùng lambda
            items = scroll_container.find_all('li', class_=lambda x: x and 'scroll-item' in x)
            print(f"  🎠 Found {len(items)} items in slider '{slider_title}'")
            
            for idx, item in enumerate(items):
                article_data = parse_slider_item(item, base_url)
                if article_data:
                    article_data['position'] = idx  # Thứ tự trong slider
                    slider_articles.append(article_data)
                else:
                    print(f"    ⚠️  Failed to parse slider item {idx}")
            
            print(f"  ✅ Successfully parsed {len(slider_articles)}/{len(items)} slider items")
        else:
            print(f"  ⚠️  No scroll-container found in slider")
            # Debug: in ra cấu trúc HTML để kiểm tra
            print(f"  🔍 Slider HTML structure:")
            print(f"     - Has inner div: {inner_content is not None}")
            if inner_content:
                all_uls = inner_content.find_all('ul')
                print(f"     - Found {len(all_uls)} ul elements")
                for ul_idx, ul in enumerate(all_uls):
                    ul_classes = ul.get('class', [])
                    print(f"       UL {ul_idx}: classes = {ul_classes}")
        
        # Xác định items_per_view và source class
        if is_nuuk_slider:
            items_per_view = 5
            source_class = 'source_nuuk'
        elif is_job_slider:
            items_per_view = 4
            # Xác định source_class dựa trên class thực tế
            if 'source_feed_random_kl_jobs' in slider_classes:
                source_class = 'source_feed_random_kl_jobs'
            elif 'source_job-dk' in slider_classes:
                source_class = 'source_job-dk'
            else:
                source_class = 'source_job'  # Fallback
        else:
            items_per_view = 4
            source_class = 'source_nyheder'
        
        # Set layout_type dựa vào loại slider
        if is_job_slider:
            layout_type = 'job_slider'
        else:
            layout_type = 'slider'
        
        # Build layout_data - giống hệt cho cả slider và job_slider
        layout_data = {
            'slider_title': slider_title,
            'slider_articles': slider_articles,
            'slider_id': slider_id,
            'has_nav': has_nav,
            'items_per_view': items_per_view,
            'source_class': source_class
        }
        
        # Chỉ thêm các fields đặc biệt nếu là job_slider (để template biết cách render)
        if is_job_slider:
            layout_data['header_link'] = header_link
            layout_data['extra_classes'] = extra_classes
            layout_data['header_classes'] = header_classes
        
        return {
            'element_guid': element_guid,
            'slider_id': slider_id,
            'layout_type': layout_type,  # 'slider' hoặc 'job_slider'
            'title': slider_title or 'Slider',  # Fallback title
            'url': '',  # Slider không có URL riêng
            'section': 'home',
            'layout_data': layout_data,
            'is_home': True
        }
    except Exception as e:
        print(f"⚠️  Error parsing slider: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_nuuk_articles(nuuk_elem, base_url='https://www.sermitsiaq.ag', row_index=0):
    """
    Parse NUUK articlescroller thành một container với layout_type='5_articles'
    Giống như parse_slider(), nhưng với layout_type='5_articles' và items_per_view=5
    
    Args:
        nuuk_elem: BeautifulSoup element của div.articlescroller.source_nuuk
        base_url: Base URL để resolve relative URLs
        row_index: Index của row để tính display_order
    
    Returns:
        dict: Container dictionary với layout_type='5_articles' và layout_data chứa slider info
    """
    try:
        element_guid = nuuk_elem.get('data-element-guid', '')
        slider_id = nuuk_elem.get('id', '')
        
        # Detect source_class từ classes của element
        slider_classes = nuuk_elem.get('class', [])
        if 'source_nuuk_kl' in slider_classes:
            source_class = 'source_nuuk_kl'
        else:
            source_class = 'source_nuuk'
        
        # Parse slider title
        title_elem = nuuk_elem.find('h2', class_='articlescroller-header')
        slider_title = ''
        if title_elem:
            span = title_elem.find('span')
            if span:
                slider_title = span.get_text(strip=True)
            else:
                slider_title = title_elem.get_text(strip=True)
        
        # Tìm scroll-container và các items
        inner_content = nuuk_elem.find('div', class_='inner')
        if not inner_content:
            inner_content = nuuk_elem
        
        scroll_container = inner_content.find('ul', class_=lambda x: x and 'scroll-container' in x)
        if not scroll_container:
            print(f"  ⚠️  NUUK: No scroll-container found")
            return None
        
        # Check xem có nav buttons không
        has_nav = inner_content.find('nav') is not None
        
        items = scroll_container.find_all('li', class_=lambda x: x and 'scroll-item' in x)
        print(f"  🏙️  NUUK ({source_class}): Found {len(items)} items")
        
        # Parse các articles trong slider
        slider_articles = []
        for idx, item in enumerate(items):
            article_data = parse_slider_item(item, base_url)
            if article_data:
                article_data['position'] = idx  # Thứ tự trong slider
                slider_articles.append(article_data)
        
        print(f"  ✅ NUUK ({source_class}): Successfully parsed {len(slider_articles)}/{len(items)} slider items")
        
        # Build layout_data - giống như parse_slider()
        layout_data = {
            'slider_title': slider_title,
            'slider_articles': slider_articles,
            'slider_id': slider_id,
            'has_nav': has_nav,
            'items_per_view': 5,  # NUUK luôn có 5 items
            'source_class': source_class
        }
        
        # Trả về container dict (giống parse_slider())
        return {
            'element_guid': element_guid,
            'slider_id': slider_id,
            'layout_type': '5_articles',  # Layout type đặc biệt cho NUUK
            'title': slider_title or 'NUUK Articles',  # Fallback title
            'url': '',  # Container không có URL riêng
            'section': 'home',
            'layout_data': layout_data,
            'is_home': True
        }
        
    except Exception as e:
        print(f"  ❌ Error parsing NUUK articles: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_articles_from_html(html_content, base_url='https://www.sermitsiaq.ag', is_home=False):
    """
    Parse tất cả articles từ HTML content
    
    Args:
        html_content: HTML content string
        base_url: Base URL để resolve relative URLs
        is_home: Nếu True, sẽ detect layout_type từ HTML structure và parse sliders
    
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
        
        # Nếu là home page, parse theo thứ tự rows để giữ đúng thứ tự
        if is_home and page_content:
            total_rows = len(rows)
            print(f"📐 Home page structure: {total_rows} rows found")
            
            # Parse theo thứ tự rows để giữ đúng thứ tự
            for row_idx, row in enumerate(rows):
                print(f"   📐 Processing row {row_idx + 1}/{total_rows}")
                # Check xem row có chứa slider không - tìm div có class chứa 'articlescroller'
                slider_elem = row.find('div', class_=lambda x: x and 'articlescroller' in x)
                if slider_elem:
                    # Check xem có phải NUUK không (source_nuuk hoặc source_nuuk_kl class)
                    slider_classes = slider_elem.get('class', [])
                    is_nuuk = 'source_nuuk' in slider_classes or 'source_nuuk_kl' in slider_classes
                    
                    if is_nuuk:
                        # Parse NUUK như một container (giống slider)
                        nuuk_container = parse_nuuk_articles(slider_elem, base_url, row_idx)
                        if nuuk_container:
                            nuuk_container['display_order'] = row_idx * 1000  # Đặt display_order dựa trên vị trí row
                            nuuk_container['row_index'] = row_idx  # Lưu row_index
                            nuuk_container['total_rows'] = total_rows  # Lưu tổng số rows
                            articles.append(nuuk_container)
                            slider_title = nuuk_container.get('layout_data', {}).get('slider_title', 'Untitled')
                            slider_articles_count = len(nuuk_container.get('layout_data', {}).get('slider_articles', []))
                            print(f"🏙️  Parsed NUUK container '{slider_title}': {slider_articles_count} articles")
                    else:
                        # Parse như slider thông thường
                        slider_data = parse_slider(slider_elem, base_url)
                        if slider_data:
                            slider_data['display_order'] = row_idx * 1000  # Đặt display_order dựa trên vị trí row
                            slider_data['row_index'] = row_idx  # Lưu row_index
                            slider_data['total_rows'] = total_rows  # Lưu tổng số rows
                            articles.append(slider_data)
                            slider_title = slider_data.get('layout_data', {}).get('slider_title', 'Untitled')
                            slider_articles_count = len(slider_data.get('layout_data', {}).get('slider_articles', []))
                            print(f"🎠 Parsed slider '{slider_title}': {slider_articles_count} articles")
                
                # Parse articles trong row này
                row_articles = row.find_all('article', attrs={'data-element-guid': True})
                total_articles_in_row = len(row_articles)
                
                print(f"      📐 Row {row_idx + 1} has {total_articles_in_row} articles")
                
                for article_idx, article_elem in enumerate(row_articles):
                    # Chỉ parse nếu article này chưa được parse (tránh duplicate)
                    if article_elem in article_elements:
                        article_data = parse_article_element(article_elem, base_url)
                        if article_data:
                            # Lưu thông tin chi tiết về row
                            article_data['display_order'] = row_idx * 1000 + article_idx  # Đặt display_order
                            article_data['row_index'] = row_idx  # Lưu row_index để biết article thuộc hàng nào
                            article_data['article_index_in_row'] = article_idx  # Lưu vị trí trong row
                            article_data['total_rows'] = total_rows  # Lưu tổng số rows
                            
                            # Detect layout_type từ "dạng" thực sự của article (CSS classes và row structure)
                            # detect_layout_type_from_element sẽ check:
                            # - CSS classes (large-4 = 3_articles, large-6 = 2_articles, large-12 = 1_full)
                            # - Số lượng articles trong row (nếu có row_elem)
                            # - Có list bên cạnh không (1_with_list_left/right)
                            layout_type = detect_layout_type_from_element(article_elem, row)
                            article_data['layout_type'] = layout_type
                            
                            # Log thông tin chi tiết về "dạng" và hàng
                            article_classes = article_elem.get('class', [])
                            class_str = ' '.join(article_classes) if article_classes else 'no-classes'
                            # Extract grid size classes để log
                            grid_classes = [c for c in article_classes if 'large-' in c]
                            grid_str = ', '.join(grid_classes) if grid_classes else 'no-grid'
                            print(f"      📰 Article {article_idx + 1}/{total_articles_in_row} in row {row_idx + 1}: display_order={article_data['display_order']}, layout_type={layout_type}, grid={grid_str}, title={article_data.get('title', 'N/A')[:40]}")
                            
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
                            
                            # Check và lưu background colors nếu article có bg-* (cho tất cả layout types)
                            content_div = article_elem.find('div', class_='content')
                            if content_div:
                                content_classes = content_div.get('class', [])
                                content_class_str = ' '.join(content_classes) if content_classes else ''
                                # Check bất kỳ background color nào (bg-black, bg-secondary, bg-primary, etc.)
                                has_bg_color = any(cls.startswith('bg-') for cls in content_classes)
                                if has_bg_color:
                                    layout_data['has_bg_color'] = True
                                    # Giữ lại has_bg_black cho backward compatibility
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
                                # Tìm list element (có thể là articlesByTag hoặc toplist)
                                list_elem = row.find('div', class_='articlesByTag')
                                if not list_elem:
                                    list_elem = row.find('div', class_='toplist')
                                
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
        else:
            # Không phải home page, parse articles như bình thường (không có layout detection)
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

