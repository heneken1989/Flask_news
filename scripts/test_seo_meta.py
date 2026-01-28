#!/usr/bin/env python3
"""
Script để test SEO meta tags của website
Usage: python test_seo_meta.py <url>
"""

import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def test_seo_meta(url, expected_title=None, expected_description=None):
    """
    Test SEO meta tags của một URL
    """
    print(f"\n{'='*60}")
    print(f"🔍 Testing SEO for: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        errors = []
        warnings = []
        
        # Test title
        title = soup.find('title')
        if title:
            title_text = title.text.strip()
            print(f"✅ Title: {title_text[:80]}...")
            if expected_title and expected_title.lower() not in title_text.lower():
                warnings.append(f"Title không khớp với expected: {expected_title}")
            if len(title_text) > 60:
                warnings.append(f"Title quá dài ({len(title_text)} chars, nên < 60)")
        else:
            errors.append("Không tìm thấy <title> tag")
        
        # Test meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '').strip()
            print(f"✅ Meta Description: {desc[:80]}...")
            if len(desc) > 160:
                warnings.append(f"Description quá dài ({len(desc)} chars, nên < 160)")
            if len(desc) < 50:
                warnings.append(f"Description quá ngắn ({len(desc)} chars, nên > 50)")
            if expected_description and expected_description.lower() not in desc.lower():
                warnings.append(f"Description không khớp với expected")
        else:
            errors.append("Không tìm thấy meta description")
        
        # Test og:title
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if og_title:
            og_title_text = og_title.get('content', '').strip()
            print(f"✅ OG Title: {og_title_text[:80]}...")
            if title and title_text != og_title_text:
                warnings.append("og:title khác với <title>")
        else:
            errors.append("Không tìm thấy og:title")
        
        # Test og:description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            print(f"✅ OG Description: {og_desc.get('content', '')[:80]}...")
        else:
            errors.append("Không tìm thấy og:description")
        
        # Test og:image
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image:
            img_url = og_image.get('content', '').strip()
            print(f"✅ OG Image: {img_url[:80]}...")
            # Check if image URL is accessible
            if img_url.startswith('http'):
                try:
                    img_response = requests.head(img_url, timeout=5, allow_redirects=True)
                    if img_response.status_code == 200:
                        print(f"   ✅ Image accessible")
                        # Check image dimensions
                        content_type = img_response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            print(f"   ✅ Image type: {content_type}")
                    else:
                        warnings.append(f"Image không accessible (status: {img_response.status_code})")
                except:
                    warnings.append("Không thể check image accessibility")
            elif img_url.startswith('/'):
                # Relative URL - check if it exists
                full_img_url = urljoin(url, img_url)
                try:
                    img_response = requests.head(full_img_url, timeout=5)
                    if img_response.status_code == 200:
                        print(f"   ✅ Image accessible at {full_img_url}")
                    else:
                        warnings.append(f"Image không accessible (status: {img_response.status_code})")
                except:
                    warnings.append("Không thể check image accessibility")
        else:
            errors.append("Không tìm thấy og:image")
        
        # Test og:url
        og_url = soup.find('meta', attrs={'property': 'og:url'})
        if og_url:
            print(f"✅ OG URL: {og_url.get('content', '')}")
        else:
            warnings.append("Không tìm thấy og:url")
        
        # Test canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            canonical_url = canonical.get('href', '').strip()
            print(f"✅ Canonical: {canonical_url}")
            if canonical_url != url:
                warnings.append(f"Canonical URL khác với current URL")
        else:
            errors.append("Không tìm thấy canonical URL")
        
        # Test hreflang
        hreflangs = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
        if hreflangs:
            print(f"✅ Hreflang tags ({len(hreflangs)}):")
            for hreflang in hreflangs:
                lang = hreflang.get('hreflang')
                href = hreflang.get('href', '')
                print(f"   - {lang}: {href}")  # Hiển thị full URL
        else:
            warnings.append("Không tìm thấy hreflang tags")
        
        # Test structured data
        json_ld_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        if json_ld_scripts:
            import json
            print(f"✅ Structured Data ({len(json_ld_scripts)} script(s)):")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for schema in data:
                            schema_type = schema.get('@type', 'Unknown')
                            print(f"   - {schema_type}")
                    else:
                        schema_type = data.get('@type', 'Unknown')
                        print(f"   - {schema_type}")
                except json.JSONDecodeError as e:
                    errors.append(f"Structured data không parse được: {e}")
        else:
            errors.append("Không tìm thấy structured data (JSON-LD)")
        
        # Summary
        print(f"\n{'='*60}")
        if errors:
            print(f"❌ ERRORS ({len(errors)}):")
            for error in errors:
                print(f"   - {error}")
        if warnings:
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"   - {warning}")
        if not errors and not warnings:
            print("✅ All checks passed!")
        print(f"{'='*60}\n")
        
        return len(errors) == 0
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Không thể fetch URL: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_seo_meta.py <url>")
        print("Example: python test_seo_meta.py http://localhost:5000/")
        sys.exit(1)
    
    url = sys.argv[1]
    test_seo_meta(url)

