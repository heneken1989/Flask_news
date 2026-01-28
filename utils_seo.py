"""
SEO utility functions for generating meta tags
"""
from flask import request, url_for
from urllib.parse import urlparse, urlunparse
from datetime import datetime


def get_seo_meta(article=None, page_type='home', language='da', section=None, title=None, description=None, image_url=None):
    """
    Generate SEO meta tags dictionary for templates
    
    Args:
        article: Article object (optional)
        page_type: 'home', 'article', 'section'
        language: 'da', 'kl', 'en'
        section: Section name (optional)
        title: Custom title (optional, overrides article.title)
        description: Custom description (optional, overrides article.excerpt)
        image_url: Custom image URL (optional, overrides article.image_data)
    
    Returns:
        dict with SEO meta tags
    """
    base_url = request.url_root.rstrip('/')
    current_url = request.url
    
    # Default values
    seo_title = "Sermitsiaq - Grønlands største nyhedssite"
    seo_description = "Sermitsiaq er Grønlands største nyhedssite med nyheder, debat og kultur."
    seo_image = f"{base_url}/static/images/default-og-image.jpg"
    seo_url = current_url
    seo_type = "website"
    
    # Language locale mapping
    locale_map = {
        'da': 'da_DK',
        'kl': 'kl_GL', 
        'en': 'en_US'
    }
    og_locale = locale_map.get(language, 'da_DK')
    
    # Override với custom title/description nếu có (cho section page hoặc custom)
    if title:
        seo_title = title
    if description:
        seo_description = description[:160] if description else seo_description  # Limit to 160 chars
    
    # Get data from article if provided
    if article:
        # Title - chỉ override nếu chưa có custom title
        if not title:
            seo_title = article.title or seo_title
        
        # Description - chỉ override nếu chưa có custom description
        if not description:
            desc = article.excerpt or seo_description
            seo_description = desc[:160] if desc else seo_description  # Limit to 160 chars
        
        # Image - lấy từ image_data (JSON field)
        # Ưu tiên image URLs với domain .com (đã được download về server của chúng ta)
        if not image_url and article.image_data:
            img_data = article.image_data
            # image_data có thể là dict hoặc string (JSON)
            if isinstance(img_data, str):
                import json
                try:
                    img_data = json.loads(img_data)
                except:
                    img_data = None
            
            if isinstance(img_data, dict):
                image_keys = ['desktop_jpeg', 'desktop_webp', 'fallback', 'mobile_jpeg', 'mobile_webp']
                
                # Ưu tiên 1: Tìm image với domain .com (đã được download)
                for key in image_keys:
                    url = img_data.get(key)
                    if url and 'sermitsiaq.com' in url:
                        image_url = url
                        break
                
                # Ưu tiên 2: Nếu không có .com, lấy bất kỳ image nào (có thể là .ag)
                if not image_url:
                    image_url = (
                        img_data.get('desktop_jpeg') or 
                        img_data.get('desktop_webp') or 
                        img_data.get('fallback') or 
                        img_data.get('mobile_jpeg') or
                        img_data.get('mobile_webp')
                    )
        
        if image_url:
            # Nếu image URL có domain .ag, convert sang .com (nếu có thể)
            # Nhưng ưu tiên giữ nguyên nếu đã là .com
            if 'sermitsiaq.ag' in image_url and 'sermitsiaq.com' not in image_url:
                # Có thể convert .ag sang .com nếu cần, nhưng tốt nhất là dùng .com từ DB
                pass  # Giữ nguyên .ag nếu không có .com
            elif image_url.startswith('/'):
                # Relative path - tạo absolute URL
                image_url = f"{base_url}{image_url}"
            elif not image_url.startswith('http'):
                # Không có protocol - thêm base_url
                image_url = f"{base_url}/{image_url}"
            seo_image = image_url
        
        # Canonical URL - dùng URL hiện tại của request (current_url) thay vì published_url từ DB
        # Điều này đảm bảo canonical URL đúng với URL đang xem
        # (Ví dụ: nếu đang xem /society/... thì canonical là /society/..., không phải /samfund/...)
        seo_url = current_url  # Dùng request.url (URL hiện tại)
        
        # Type
        seo_type = "article"
        
        # Article-specific meta
        published_time = None
        modified_time = None
        if article.published_date:
            published_time = article.published_date.isoformat() + 'Z'
        if article.updated_at:
            modified_time = article.updated_at.isoformat() + 'Z'
        
        # Author
        author = None
        if article.layout_data and isinstance(article.layout_data, dict):
            author = article.layout_data.get('author')
        
        # Tags
        tags = []
        if article.layout_data and isinstance(article.layout_data, dict):
            tags = article.layout_data.get('tags', [])
    
    # Generate hreflang URLs
    hreflang_urls = {}
    if article and article.published_url:
        # Find translations
        from database import Article
        translations = []
        
        # If article has canonical_id, find all translations
        if article.canonical_id:
            canonical = Article.query.get(article.canonical_id)
            if canonical:
                translations = Article.query.filter(
                    (Article.id == canonical.id) | 
                    (Article.canonical_id == canonical.id)
                ).all()
        else:
            # Find all translations of this article
            translations = Article.query.filter(
                (Article.id == article.id) | 
                (Article.canonical_id == article.id)
            ).all()
        
        # Build hreflang URLs
        # Ưu tiên published_url_en cho EN articles
        # Convert domain từ .ag sang .com và đảm bảo URL đúng format
        for trans in translations:
            url_to_use = None
            if trans.language == 'en' and trans.published_url_en:
                url_to_use = trans.published_url_en
            elif trans.published_url:
                url_to_use = trans.published_url
            
            if url_to_use:
                # Parse URL để lấy path
                parsed = urlparse(url_to_use)
                path_only = parsed.path  # Lấy path (ví dụ: /samfund/...)
                
                # Convert domain từ .ag sang .com
                # Tạo full URL với domain .com
                hreflang_urls[trans.language] = urlunparse((
                    'https',  # Luôn dùng https
                    'www.sermitsiaq.com',  # Domain .com
                    path_only,  # Giữ nguyên path
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
    
    # Build meta dict
    meta = {
        'title': seo_title,
        'description': seo_description,
        'image': seo_image,
        'url': seo_url,
        'type': seo_type,
        'locale': og_locale,
        'language': language,
        'hreflang_urls': hreflang_urls,
    }
    
    # Article-specific
    if article:
        meta['published_time'] = published_time
        meta['modified_time'] = modified_time
        meta['author'] = author
        meta['tags'] = tags
        meta['section'] = article.section or section
    
    return meta


def get_structured_data(article=None, page_type='home', language='da'):
    """
    Generate JSON-LD structured data
    
    Args:
        article: Article object (optional)
        page_type: 'home', 'article', 'section'
        language: 'da', 'kl', 'en'
    
    Returns:
        list of structured data dicts
    """
    base_url = request.url_root.rstrip('/')
    current_url = request.url  # URL hiện tại của request
    structured_data = []
    
    if page_type == 'article' and article:
        # NewsArticle schema
        article_data = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": article.title or "",
            "description": article.excerpt or "",  # Lấy từ DB: article.excerpt
            "image": [],
            "datePublished": article.published_date.isoformat() + 'Z' if article.published_date else None,
            "dateModified": article.updated_at.isoformat() + 'Z' if article.updated_at else (article.published_date.isoformat() + 'Z' if article.published_date else None),
        }
        
        # Add image - lấy từ image_data (JSON field)
        if article.image_data:
            img_data = article.image_data
            # image_data có thể là dict hoặc string (JSON)
            if isinstance(img_data, str):
                import json
                try:
                    img_data = json.loads(img_data)
                except:
                    img_data = None
            
            if isinstance(img_data, dict):
                image_keys = ['desktop_jpeg', 'desktop_webp', 'fallback', 'mobile_jpeg', 'mobile_webp']
                
                # Ưu tiên 1: Tìm image với domain .com (đã được download)
                img_url = None
                for key in image_keys:
                    url = img_data.get(key)
                    if url and 'sermitsiaq.com' in url:
                        img_url = url
                        break
                
                # Ưu tiên 2: Nếu không có .com, lấy bất kỳ image nào (có thể là .ag)
                if not img_url:
                    for key in image_keys:
                        if img_data.get(key):
                            img_url = img_data[key]
                            break
                
                if img_url:
                    # Nếu là relative path, tạo absolute URL
                    if img_url.startswith('/'):
                        img_url = f"{base_url}{img_url}"
                    elif not img_url.startswith('http'):
                        img_url = f"{base_url}/{img_url}"
                    article_data['image'].append(img_url)
        
        # Add author
        if article.layout_data and isinstance(article.layout_data, dict):
            author = article.layout_data.get('author')
            if author:
                article_data['author'] = {
                    "@type": "Person",
                    "name": author
                }
        
        # Add publisher
        article_data['publisher'] = {
            "@type": "Organization",
            "name": "Sermitsiaq",
            "logo": {
                "@type": "ImageObject",
                "url": f"{base_url}/static/images/logo.png"
            }
        }
        
        # Add URL - dùng URL hiện tại của request (current_url) cho canonical
        # Ưu tiên published_url_en nếu article là EN và có published_url_en
        url_to_use = None
        if article.language == 'en' and article.published_url_en:
            url_to_use = article.published_url_en
        elif article.published_url:
            url_to_use = article.published_url
        
        if url_to_use:
            # Convert domain từ .ag sang .com
            if 'sermitsiaq.ag' in url_to_use:
                url_to_use = url_to_use.replace('sermitsiaq.ag', 'sermitsiaq.com')
            
            if url_to_use.startswith('http'):
                article_data['mainEntityOfPage'] = {"@id": url_to_use}
            else:
                parsed = urlparse(url_to_use)
                article_data['mainEntityOfPage'] = {
                    "@id": urlunparse((
                        request.scheme,
                        request.host,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment
                    ))
                }
        else:
            # Fallback: dùng current_url (URL hiện tại của request)
            article_data['mainEntityOfPage'] = {"@id": request.url}
        
        structured_data.append(article_data)
    
    # WebSite schema (always add)
    website_data = {
        "@context": "http://schema.org",
        "@type": "WebSite",
        "name": "Sermitsiaq",
        "url": base_url,
        "inLanguage": language
    }
    structured_data.append(website_data)
    
    return structured_data

