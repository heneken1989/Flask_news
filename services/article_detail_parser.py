"""
Service để parse và lưu structured article detail content vào database
"""
from bs4 import BeautifulSoup
from database import db, ArticleDetail
from typing import List, Dict, Optional
from datetime import datetime
import json
import re


class ArticleDetailParser:
    """
    Parse HTML content thành structured blocks cho article detail
    """
    
    @staticmethod
    def parse_html_content(html_content: str) -> List[Dict]:
        """
        Parse HTML content thành list of blocks theo đúng thứ tự
        
        Args:
            html_content: Raw HTML content từ bodytext
            
        Returns:
            List of block dictionaries
        """
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        blocks = []
        order = 0
        
        # Parse article meta FIRST (bylines and dates) - thường nằm trong articleHeader
        # Tìm trong toàn bộ soup
        meta_div = soup.find('div', class_='meta')
        if meta_div:
            # Parse meta bất kể nằm ở đâu
            meta_block = ArticleDetailParser._parse_article_meta(meta_div, order)
            if meta_block:
                blocks.append(meta_block)
                order += 1
        
        # Parse subtitle (h2.subtitle) và header image caption từ articleHeader - nếu có
        # Subtitle và header image caption thường nằm trong articleHeader, không phải bodytext
        article_header = soup.find('div', class_='articleHeader')
        if not article_header:
            # Try alternative: find by class containing 'articleHeader'
            article_header = soup.find('div', class_=lambda x: x and 'articleHeader' in ' '.join(x) if isinstance(x, list) else 'articleHeader' in str(x))
        
        if article_header:
            # Parse title (h1.headline.mainTitle) - ưu tiên cao nhất
            title_elem = article_header.find('h1', class_='headline')
            if not title_elem:
                # Try alternative: find h1 with mainTitle class
                title_elem = article_header.find('h1', class_='mainTitle')
            if not title_elem:
                # Try finding any h1 in articleHeader
                title_elem = article_header.find('h1')
            
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text:
                    blocks.append({
                        'type': 'title',
                        'order': order,
                        'level': 'h1',
                        'html': str(title_elem),
                        'text': title_text,
                        'classes': title_elem.get('class', [])
                    })
                    order += 1
            
            # Parse subtitle - tìm h2 với class chứa 'subtitle'
            subtitle_elem = None
            # Try exact match first (BeautifulSoup tự động handle spaces trong class)
            subtitle_elem = article_header.find('h2', class_='subtitle')
            # If not found, try finding all h2 and check if any has subtitle in class
            if not subtitle_elem:
                h2_elements = article_header.find_all('h2')
                for h2 in h2_elements:
                    classes = h2.get('class', [])
                    # Handle both list and string class attributes
                    if isinstance(classes, list):
                        class_list = [str(c).strip() for c in classes if c]
                    else:
                        class_list = [str(classes).strip()] if classes else []
                    
                    if 'subtitle' in class_list:
                        subtitle_elem = h2
                        break
            
            if subtitle_elem:
                subtitle_text = subtitle_elem.get_text(strip=True)
                if subtitle_text:
                    blocks.append({
                        'type': 'subtitle',
                        'order': order,
                        'level': 'h2',
                        'html': str(subtitle_elem),
                        'text': subtitle_text,
                        'classes': subtitle_elem.get('class', [])
                    })
                    order += 1
            
            # Parse header image caption từ articleHeader
            # Caption có thể nằm sau figure.headerImage hoặc trong div.caption
            header_caption_div = article_header.find('div', class_='caption')
            if header_caption_div:
                caption_elem = header_caption_div.find('figcaption', itemprop='caption')
                author_elem = header_caption_div.find('figcaption', itemprop='author')
                
                caption_text = ''
                author_text = ''
                
                if caption_elem:
                    caption_text = caption_elem.get_text(strip=True)
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    # Remove "Foto: " or "Assi: " prefix if exists (case insensitive)
                    # "Assi: " is Greenlandic for "Foto: " (Photo)
                    if author_text.lower().startswith('foto: '):
                        author_text = author_text[6:].strip()
                    elif author_text.lower().startswith('foto:'):
                        author_text = author_text[5:].strip()
                    elif author_text.lower().startswith('assi: '):
                        author_text = author_text[6:].strip()
                    elif author_text.lower().startswith('assi:'):
                        author_text = author_text[5:].strip()
                
                # Nếu có caption hoặc author, tạo một block đặc biệt để lưu header image caption
                if caption_text or author_text:
                    blocks.append({
                        'type': 'header_image_caption',
                        'order': order,
                        'caption': caption_text,
                        'author': author_text,
                        'html': str(header_caption_div)
                    })
                    order += 1
        
        # Find bodytext container
        bodytext = soup.find('div', class_='bodytext')
        if not bodytext:
            bodytext = soup
        
        # Parse intro section (nếu có)
        intro_div = bodytext.find('div', class_='intro')
        if intro_div:
            intro_blocks = ArticleDetailParser._parse_intro(intro_div, order)
            blocks.extend(intro_blocks)
            order += len(intro_blocks)
        
        # Parse content-text section - QUAN TRỌNG: giữ nguyên thứ tự các elements
        content_div = bodytext.find('div', class_='content-text')
        if content_div:
            # Parse tất cả children theo đúng thứ tự
            content_blocks = ArticleDetailParser._parse_content_text_ordered(content_div, order)
            blocks.extend(content_blocks)
            order += len(content_blocks)
        elif not intro_div:
            # If no intro/content-text, parse all elements
            generic_blocks = ArticleDetailParser._parse_generic_content(bodytext, order)
            blocks.extend(generic_blocks)
        
        # Parse paywall offers section (outside bodytext)
        offers_div = soup.find('div', class_='iteras-offers')
        if offers_div:
            offer_block = ArticleDetailParser._parse_paywall_offers(offers_div, order)
            if offer_block:
                blocks.append(offer_block)
        
        # Parse article footer tags (outside bodytext)
        footer_div = soup.find('div', class_='articleFooter')
        if footer_div:
            tags_block = ArticleDetailParser._parse_article_footer_tags(footer_div, order)
            if tags_block:
                blocks.append(tags_block)
        
        return blocks
    
    @staticmethod
    def _parse_intro(intro_div, start_order: int) -> List[Dict]:
        """Parse intro section"""
        blocks = []
        order = start_order
        
        for element in intro_div.children:
            if not hasattr(element, 'name'):
                continue
            
            if element.name == 'p':
                blocks.append({
                    'type': 'paragraph',
                    'order': order,
                    'html': str(element),
                    'text': element.get_text(),
                    'classes': element.get('class', [])
                })
                order += 1
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                blocks.append({
                    'type': 'heading',
                    'order': order,
                    'level': element.name,
                    'html': str(element),
                    'text': element.get_text(),
                    'classes': element.get('class', [])
                })
                order += 1
        
        return blocks
    
    @staticmethod
    def _parse_content_text_ordered(content_div, start_order: int) -> List[Dict]:
        """
        Parse content-text section theo đúng thứ tự các elements
        Giữ nguyên thứ tự: paragraphs, headings, images, ads xen kẽ nhau
        """
        blocks = []
        order = start_order
        
        # Duyệt qua tất cả children theo đúng thứ tự
        for element in content_div.children:
            if not hasattr(element, 'name') or element.name is None:
                continue
            
            # Paragraph
            if element.name == 'p':
                blocks.append({
                    'type': 'paragraph',
                    'order': order,
                    'html': str(element),
                    'text': element.get_text(),
                    'classes': element.get('class', [])
                })
                order += 1
            
            # Heading
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                blocks.append({
                    'type': 'heading',
                    'order': order,
                    'level': element.name,
                    'html': str(element),
                    'text': element.get_text(),
                    'classes': element.get('class', [])
                })
                order += 1
            
            # Image/Figure
            elif element.name == 'figure':
                image_block = ArticleDetailParser._parse_figure(element, order)
                if image_block:
                    blocks.append(image_block)
                    order += 1
            
            # Google Ad
            elif element.name == 'div' and 'google-ad' in element.get('class', []):
                ad_block = ArticleDetailParser._parse_ad(element, order)
                if ad_block:
                    blocks.append(ad_block)
                    order += 1
        
        return blocks
    
    @staticmethod
    def _parse_content_text(content_div, start_order: int) -> List[Dict]:
        """Parse content-text section (legacy method, redirects to ordered version)"""
        return ArticleDetailParser._parse_content_text_ordered(content_div, start_order)
    
    @staticmethod
    def _parse_generic_content(container, start_order: int) -> List[Dict]:
        """Parse generic content (fallback)"""
        blocks = []
        order = start_order
        
        for element in container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'figure', 'div'], recursive=False):
            if element.name == 'p':
                blocks.append({
                    'type': 'paragraph',
                    'order': order,
                    'html': str(element),
                    'text': element.get_text(),
                    'classes': element.get('class', [])
                })
                order += 1
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                blocks.append({
                    'type': 'heading',
                    'order': order,
                    'level': element.name,
                    'html': str(element),
                    'text': element.get_text(),
                    'classes': element.get('class', [])
                })
                order += 1
            elif element.name == 'figure':
                image_block = ArticleDetailParser._parse_figure(element, order)
                if image_block:
                    blocks.append(image_block)
                    order += 1
            elif element.name == 'div' and 'google-ad' in element.get('class', []):
                ad_block = ArticleDetailParser._parse_ad(element, order)
                if ad_block:
                    blocks.append(ad_block)
                    order += 1
        
        return blocks
    
    @staticmethod
    def _parse_figure(figure_element, order: int) -> Optional[Dict]:
        """Parse figure/image element"""
        element_guid = figure_element.get('data-element-guid', '')
        img = figure_element.find('img')
        picture = figure_element.find('picture')
        caption_div = figure_element.find('div', class_='caption')
        
        if not img and not picture:
            return None
        
        # Extract image sources
        image_sources = {}
        if picture:
            sources = picture.find_all('source')
            for source in sources:
                media = source.get('media', '')
                srcset = source.get('srcset', '')
                img_type = source.get('type', '')
                
                if 'min-width: 768px' in media:
                    if 'webp' in img_type:
                        image_sources['desktop_webp'] = srcset
                    elif 'jpeg' in img_type:
                        image_sources['desktop_jpeg'] = srcset
                elif 'max-width: 767px' in media:
                    if 'webp' in img_type:
                        image_sources['mobile_webp'] = srcset
                    elif 'jpeg' in img_type:
                        image_sources['mobile_jpeg'] = srcset
        
        # Get img tag
        img_tag = picture.find('img') if picture else img
        if img_tag:
            image_sources['fallback'] = img_tag.get('src', '')
            image_sources['alt'] = img_tag.get('alt', '')
            image_sources['title'] = img_tag.get('title', '')
            image_sources['width'] = img_tag.get('width', '')
            image_sources['height'] = img_tag.get('height', '')
        
        # Extract caption
        caption = ''
        author = ''
        if caption_div:
            caption_elem = caption_div.find('figcaption', itemprop='caption')
            author_elem = caption_div.find('figcaption', itemprop='author')
            if caption_elem:
                caption = caption_elem.get_text(strip=True)
            if author_elem:
                author = author_elem.get_text(strip=True)
        
        # Get figure classes
        figure_classes = figure_element.get('class', [])
        float_class = ''
        if 'desktop-floatLeft' in figure_classes or 'mobile-floatLeft' in figure_classes:
            float_class = 'floatLeft'
        elif 'desktop-floatRight' in figure_classes or 'mobile-floatRight' in figure_classes:
            float_class = 'floatRight'
        
        return {
            'type': 'image',
            'order': order,
            'element_guid': element_guid,
            'image_sources': image_sources,
            'caption': caption,
            'author': author,
            'float_class': float_class,
            'classes': figure_classes,
            'html': str(figure_element)
        }
    
    @staticmethod
    def _parse_ad(ad_element, order: int) -> Optional[Dict]:
        """Parse Google Ad element"""
        element_guid = ad_element.get('data-element-guid', '')
        ad_id = ad_element.find('div', class_='adunit')
        ad_id = ad_id.get('id', '') if ad_id else ''
        
        return {
            'type': 'ad',
            'order': order,
            'element_guid': element_guid,
            'ad_id': ad_id,
            'classes': ad_element.get('class', []),
            'html': str(ad_element)
        }
    
    @staticmethod
    def _parse_paywall_offers(offers_div, order: int) -> Optional[Dict]:
        """Parse paywall offers section"""
        offers = []
        offer_list = offers_div.find('div', class_='offer-list')
        
        if offer_list:
            for offer_div in offer_list.find_all('div', class_='offer'):
                offer_name = offer_div.find('h3', class_='offer-name')
                offer_pros = offer_div.find('ul', class_='offer-pros')
                offer_cta = offer_div.find('a', class_='offer-cta')
                
                pros = []
                if offer_pros:
                    for li in offer_pros.find_all('li'):
                        span = li.find('span')
                        if span:
                            pros.append(span.get_text(strip=True))
                
                offers.append({
                    'name': offer_name.get_text(strip=True) if offer_name else '',
                    'pros': pros,
                    'cta_text': offer_cta.get_text(strip=True) if offer_cta else '',
                    'cta_url': offer_cta.get('href', '') if offer_cta else ''
                })
        
        description = offers_div.find('p', class_='offer-description')
        
        return {
            'type': 'paywall_offer',
            'order': order,
            'offers': offers,
            'description': description.get_text(strip=True) if description else '',
            'html': str(offers_div)
        }
    
    @staticmethod
    def _parse_article_footer_tags(footer_div, order: int) -> Optional[Dict]:
        """Parse article footer tags section"""
        element_guid = footer_div.get('data-element-guid', '')
        tags_span = footer_div.find('span', class_='tags')
        
        if not tags_span:
            return None
        
        tags = []
        for tag_link in tags_span.find_all('a'):
            tag_text = tag_link.get_text(strip=True)
            tag_url = tag_link.get('href', '')
            tags.append({
                'text': tag_text,
                'url': tag_url
            })
        
        return {
            'type': 'article_footer_tags',
            'order': order,
            'element_guid': element_guid,
            'tags': tags,
            'html': str(footer_div)
        }
    
    @staticmethod
    def _parse_article_meta(meta_div, order: int) -> Optional[Dict]:
        """Parse article meta section (bylines and dates)"""
        element_guid = meta_div.get('data-element-guid', '')
        
        # Parse bylines
        bylines = []
        bylines_div = meta_div.find('div', class_='bylines')
        if bylines_div:
            for byline_div in bylines_div.find_all('div', class_='byline'):
                byline_guid = byline_div.get('data-element-guid', '')
                
                # Get author image
                author_image = None
                figure = byline_div.find('figure')
                if figure:
                    img = figure.find('img')
                    if img:
                        author_image = {
                            'src': img.get('src', ''),
                            'alt': img.get('alt', ''),
                            'width': img.get('width', ''),
                            'height': img.get('height', '')
                        }
                
                # Get author name
                name_address = byline_div.find('address', class_='name')
                firstname = ''
                lastname = ''
                fullname = ''
                description = ''
                author_url = None
                
                if name_address:
                    # Try to find name spans
                    firstname_elem = name_address.find('span', class_='firstname')
                    lastname_elem = name_address.find('span', class_='lastname')
                    description_elem = name_address.find('span', class_='description')
                    
                    if firstname_elem:
                        firstname = firstname_elem.get_text(strip=True)
                    if lastname_elem:
                        lastname = lastname_elem.get_text(strip=True)
                    if description_elem:
                        description = description_elem.get_text(strip=True)
                    
                    # Get full name from itemprop="name" - có thể có nhiều spans với itemprop="name"
                    name_spans = name_address.find_all('span', itemprop='name')
                    if name_spans:
                        # Lấy span đầu tiên có itemprop="name"
                        fullname = name_spans[0].get_text(strip=True)
                    # Fallback: combine firstname + lastname nếu không có fullname
                    if not fullname and (firstname or lastname):
                        fullname = f"{firstname} {lastname}".strip()
                    
                    # Get author URL if exists
                    author_link = name_address.find('a', rel='author')
                    if author_link:
                        author_url = author_link.get('href', '')
                
                bylines.append({
                    'element_guid': byline_guid,
                    'author_image': author_image,
                    'firstname': firstname,
                    'lastname': lastname,
                    'fullname': fullname,
                    'description': description,
                    'author_url': author_url
                })
        
        # Parse dates
        dates = {}
        dates_div = meta_div.find('div', class_='dates')
        if dates_div:
            # Tìm span có class datePublished (có thể là dateGroup datePublished)
            # BeautifulSoup find với multiple classes
            date_published = dates_div.find('span', class_=lambda x: x and 'datePublished' in x)
            if not date_published:
                # Try to find span with dateGroup class
                date_published = dates_div.find('span', class_='dateGroup')
            
            if date_published:
                date_label = date_published.find('span', class_='dateLabel')
                time_elem = date_published.find('time')
                
                if time_elem:
                    dates['published'] = {
                        'label': date_label.get_text(strip=True) if date_label else '',
                        'datetime': time_elem.get('datetime', ''),
                        'title': time_elem.get('title', ''),
                        'text': time_elem.get_text(strip=True)
                    }
        

        if bylines or dates:
            return {
                'type': 'article_meta',
                'order': order,
                'element_guid': element_guid,
                'bylines': bylines,
                'dates': dates,
                'html': str(meta_div)
            }
        return None
    
    @staticmethod
    def save_article_detail(published_url: str, html_content: str, language: str = 'en', element_guid: str = None) -> ArticleDetail:
        """
        Parse và lưu article detail vào database
        
        Args:
            published_url: URL của article (link với articles.published_url)
            html_content: Raw HTML content
            language: Language code
            element_guid: Element GUID từ HTML gốc
            
        Returns:
            ArticleDetail object
        """
        # Parse content
        blocks = ArticleDetailParser.parse_html_content(html_content)
        
        # Find existing by both published_url AND language (vì unique constraint là (published_url, language))
        article_detail = ArticleDetail.query.filter_by(
            published_url=published_url,
            language=language
        ).first()
        
        if article_detail:
            # Update existing
            article_detail.content_blocks = blocks
            if element_guid:
                article_detail.element_guid = element_guid
            article_detail.updated_at = datetime.utcnow()
        else:
            # Create new
            article_detail = ArticleDetail(
                published_url=published_url,
                content_blocks=blocks,
                language=language,
                element_guid=element_guid
            )
            db.session.add(article_detail)
        
        db.session.commit()
        return article_detail
    
    @staticmethod
    def convert_url_between_languages(url: str, target_language: str) -> str:
        """
        Chuyển đổi URL giữa các ngôn ngữ:
        - KL → DA/EN: Loại bỏ 'kl.' (kl.sermitsiaq.ag → www.sermitsiaq.ag)
        - DA/EN → KL: Thêm 'kl.' (www.sermitsiaq.ag → kl.sermitsiaq.ag)
        
        Args:
            url: URL gốc
            target_language: Language code ('da', 'kl', 'en')
            
        Returns:
            URL đã chuyển đổi
        """
        if not url:
            return url
        
        # Xác định URL hiện tại là KL hay DA/EN
        is_kl_url = 'kl.sermitsiaq.ag' in url or 'kl.sermitsiaq.gl' in url
        
        if target_language == 'kl':
            # Chuyển sang KL: thêm 'kl.'
            if not is_kl_url:
                # Chỉ replace nếu chưa có 'kl.'
                # Ưu tiên replace 'www.' trước, sau đó mới replace domain không có 'www.'
                if 'www.sermitsiaq.ag' in url:
                    url = url.replace('www.sermitsiaq.ag', 'kl.sermitsiaq.ag')
                elif 'www.sermitsiaq.gl' in url:
                    url = url.replace('www.sermitsiaq.gl', 'kl.sermitsiaq.gl')
                elif 'sermitsiaq.ag' in url and 'kl.sermitsiaq.ag' not in url:
                    # Chỉ replace nếu chưa có 'kl.' trong URL
                    url = url.replace('sermitsiaq.ag', 'kl.sermitsiaq.ag', 1)
                elif 'sermitsiaq.gl' in url and 'kl.sermitsiaq.gl' not in url:
                    url = url.replace('sermitsiaq.gl', 'kl.sermitsiaq.gl', 1)
        else:
            # Chuyển sang DA/EN: loại bỏ 'kl.'
            if is_kl_url:
                url = url.replace('kl.sermitsiaq.ag', 'www.sermitsiaq.ag')
                url = url.replace('kl.sermitsiaq.gl', 'www.sermitsiaq.gl')
        
        return url
    
    @staticmethod
    def get_article_detail(published_url: str, language: str = None) -> Optional[ArticleDetail]:
        """
        Get article detail by published_url and optionally language
        Tự động chuyển đổi URL giữa các ngôn ngữ nếu không tìm thấy
        
        Args:
            published_url: URL của article
            language: Language code ('da', 'kl', 'en'). If None, returns first match
            
        Returns:
            ArticleDetail object or None
        """
        # Ưu tiên 1: Tìm với URL và language chính xác
        query = ArticleDetail.query.filter_by(published_url=published_url)
        if language:
            query = query.filter_by(language=language)
        article_detail = query.first()
        
        if article_detail:
            return article_detail
        
        # Ưu tiên 2: Nếu không tìm thấy và có language, thử chuyển đổi URL
        if language:
            converted_url = ArticleDetailParser.convert_url_between_languages(published_url, language)
            if converted_url != published_url:
                query = ArticleDetail.query.filter_by(published_url=converted_url)
                query = query.filter_by(language=language)
                article_detail = query.first()
                if article_detail:
                    return article_detail
        
        # Ưu tiên 3: Fallback về DA nếu không tìm thấy
        if language and language != 'da':
            # Thử với URL gốc và language='da'
            query = ArticleDetail.query.filter_by(published_url=published_url)
            query = query.filter_by(language='da')
            article_detail = query.first()
            if article_detail:
                return article_detail
            
            # Thử với URL đã chuyển đổi và language='da'
            converted_url = ArticleDetailParser.convert_url_between_languages(published_url, 'da')
            if converted_url != published_url:
                query = ArticleDetail.query.filter_by(published_url=converted_url)
                query = query.filter_by(language='da')
                article_detail = query.first()
                if article_detail:
                    return article_detail
        
        # Nếu không có language, trả về bất kỳ match nào
        if not language:
            return ArticleDetail.query.filter_by(published_url=published_url).first()
        
        return None
    
    @staticmethod
    def extract_image_id_from_article(article) -> Optional[str]:
        """
        Extract imageId từ Article.image_data
        
        Args:
            article: Article object
            
        Returns:
            imageId string hoặc None
        """
        if not article or not article.image_data:
            return None
        
        image_data = article.image_data
        if isinstance(image_data, str):
            import json
            try:
                image_data = json.loads(image_data)
            except:
                return None
        
        # Tìm imageId trong các URL fields
        url_fields = ['desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg', 'fallback']
        for field in url_fields:
            url = image_data.get(field, '')
            if url and 'imageId=' in url:
                # Extract imageId từ URL: imageId=2329158
                match = re.search(r'imageId=(\d+)', url)
                if match:
                    return match.group(1)
        
        return None
    
    @staticmethod
    def find_article_detail_by_image_id(image_id: str, language: str) -> Optional[ArticleDetail]:
        """
        Tìm ArticleDetail qua imageId bằng cách:
        1. Tìm tất cả Article có cùng imageId trong image_data
        2. Lấy published_url của Article đó
        3. Tìm ArticleDetail với published_url và language
        
        Args:
            image_id: Image ID (ví dụ: "2329158")
            language: Language code ('da', 'kl', 'en')
            
        Returns:
            ArticleDetail object hoặc None
        """
        if not image_id:
            return None
        
        from database import Article
        
        # Tìm tất cả Article có imageId này trong image_data
        # Query tất cả articles và filter trong Python (vì JSON field query phức tạp)
        all_articles = Article.query.all()
        
        for article in all_articles:
            if not article.image_data:
                continue
            
            image_data = article.image_data
            if isinstance(image_data, str):
                import json
                try:
                    image_data = json.loads(image_data)
                except:
                    continue
            
            # Kiểm tra imageId trong image_data
            url_fields = ['desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg', 'fallback']
            for field in url_fields:
                url = image_data.get(field, '')
                if url and f'imageId={image_id}' in url:
                    # Tìm thấy article có cùng imageId
                    # Tìm ArticleDetail với published_url của article này và language
                    if article.published_url:
                        article_detail = ArticleDetail.query.filter_by(
                            published_url=article.published_url,
                            language=language
                        ).first()
                        if article_detail:
                            return article_detail
        
        return None
    
    @staticmethod
    def get_article_detail_by_article(article, language: str = None) -> Optional[ArticleDetail]:
        """
        Get article detail from Article object
        Sử dụng imageId mapping nếu không tìm thấy qua URL
        
        Args:
            article: Article object
            language: Language code ('da', 'kl', 'en'). If None, uses article.language
            
        Returns:
            ArticleDetail object or None
        """
        if not article or not article.published_url:
            return None
        
        # Sử dụng language từ article nếu không được cung cấp
        if language is None:
            language = article.language
        
        # Extract imageId một lần để dùng nhiều lần
        image_id = ArticleDetailParser.extract_image_id_from_article(article)
        
        # Ưu tiên 1: Tìm với published_url và language (bao gồm URL conversion, KHÔNG fallback DA)
        # Tạm thời disable fallback trong get_article_detail bằng cách gọi trực tiếp query
        query = ArticleDetail.query.filter_by(published_url=article.published_url)
        if language:
            query = query.filter_by(language=language)
        article_detail = query.first()
        
        if article_detail:
            return article_detail
        
        # Thử URL conversion
        if language:
            converted_url = ArticleDetailParser.convert_url_between_languages(article.published_url, language)
            if converted_url != article.published_url:
                query = ArticleDetail.query.filter_by(published_url=converted_url)
                query = query.filter_by(language=language)
                article_detail = query.first()
                if article_detail:
                    return article_detail
        
        # Ưu tiên 2: Nếu không tìm thấy, thử mapping qua imageId với target language
        if image_id:
            article_detail = ArticleDetailParser.find_article_detail_by_image_id(image_id, language)
            if article_detail:
                return article_detail
        
        # Ưu tiên 3: Fallback về DA nếu không tìm thấy
        if language != 'da':
            # Thử URL gốc với DA
            query = ArticleDetail.query.filter_by(published_url=article.published_url, language='da')
            article_detail = query.first()
            if article_detail:
                return article_detail
            
            # Thử URL conversion với DA
            converted_url = ArticleDetailParser.convert_url_between_languages(article.published_url, 'da')
            if converted_url != article.published_url:
                query = ArticleDetail.query.filter_by(published_url=converted_url, language='da')
                article_detail = query.first()
                if article_detail:
                    return article_detail
            
            # Thử imageId với DA
            if image_id:
                article_detail = ArticleDetailParser.find_article_detail_by_image_id(image_id, 'da')
                if article_detail:
                    return article_detail
        
        return None


