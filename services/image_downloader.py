"""
Service để download và lưu images từ website gốc về domain của chúng ta
"""
import os
import re
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional
import hashlib


def extract_image_id_from_url(url: str) -> Optional[str]:
    """
    Extract imageId từ URL
    
    Args:
        url: Image URL
        
    Returns:
        imageId (str) hoặc None
    """
    if not url:
        return None
    
    # Tìm imageId trong query string
    match = re.search(r'[?&]imageId=(\d+)', url)
    if match:
        return match.group(1)
    
    # Hoặc extract từ path (ví dụ: /2333823.webp)
    match = re.search(r'/(\d+)\.(webp|jpg|jpeg|png)', url)
    if match:
        return match.group(1)
    
    return None


def download_image(image_url: str, save_dir: str, image_id: str = None, format: str = 'webp') -> Optional[str]:
    """
    Download image từ URL và lưu vào thư mục
    
    Args:
        image_url: URL của image cần download
        save_dir: Thư mục để lưu image
        image_id: Image ID (nếu có, dùng làm tên file)
        format: Format của image (webp, jpeg, jpg, png)
        
    Returns:
        Path tương đối của image đã lưu (ví dụ: /static/uploads/images/2333823.webp) hoặc None nếu lỗi
    """
    if not image_url:
        return None
    
    try:
        # Extract imageId nếu chưa có
        if not image_id:
            image_id = extract_image_id_from_url(image_url)
        
        # Nếu không có imageId, dùng hash của URL
        if not image_id:
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            image_id = f"img_{url_hash}"
        
        # Tạo tên file
        file_name = f"{image_id}.{format}"
        
        # Tạo thư mục nếu chưa có
        os.makedirs(save_dir, exist_ok=True)
        
        # Tạo full file path
        file_path = os.path.join(save_dir, file_name)
        
        # Check nếu file đã tồn tại, skip download
        if os.path.exists(file_path):
            print(f"      ⏭️  Image already exists, skipping download: {file_name}")
            # Tạo relative path để dùng trong URL
            relative_path = file_path.replace(os.path.dirname(os.path.dirname(os.path.dirname(save_dir))), '')
            relative_path = relative_path.replace('\\', '/')  # Windows path fix
            if not relative_path.startswith('/'):
                relative_path = '/' + relative_path
            return relative_path
        
        # Download image
        response = requests.get(image_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Lưu file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Tạo relative path để dùng trong URL
        # Giả sử save_dir là flask/static/uploads/images
        # Relative path sẽ là /static/uploads/images/{file_name}
        relative_path = file_path.replace(os.path.dirname(os.path.dirname(os.path.dirname(save_dir))), '')
        relative_path = relative_path.replace('\\', '/')  # Windows path fix
        if not relative_path.startswith('/'):
            relative_path = '/' + relative_path
        
        return relative_path
        
    except Exception as e:
        print(f"      ⚠️  Error downloading image {image_url}: {e}")
        return None


def download_and_update_image_data(image_data: Dict, base_url: str = 'https://www.sermitsiaq.com', 
                                   save_dir: str = None, download_all_formats: bool = False) -> Dict:
    """
    Download images từ image_data và cập nhật với URLs mới
    
    Args:
        image_data: Dict chứa image data (desktop_webp, desktop_jpeg, mobile_webp, mobile_jpeg, fallback)
        base_url: Base URL của domain (ví dụ: https://www.sermitsiaq.com)
        save_dir: Thư mục để lưu images (default: flask/static/uploads/images)
        download_all_formats: Nếu True, download tất cả formats. Nếu False, chỉ download desktop_webp và fallback
        
    Returns:
        Updated image_data với URLs mới
    """
    if not image_data:
        return image_data
    
    # Default save directory
    if not save_dir:
        # Lấy thư mục flask/static/uploads/images
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_dir = os.path.join(current_dir, 'static', 'uploads', 'images')
    
    # Extract imageId từ bất kỳ URL nào
    image_id = None
    for key in ['desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg', 'fallback']:
        if image_data.get(key):
            image_id = extract_image_id_from_url(image_data[key])
            if image_id:
                break
    
    if not image_id:
        print(f"      ⚠️  Could not extract imageId from image_data, keeping original URLs")
        # Vẫn đảm bảo tất cả keys có giá trị (fallback chain)
        updated_data = image_data.copy()
        
        # Đảm bảo tất cả các keys quan trọng đều có giá trị
        # Nếu không có desktop_webp, dùng fallback
        if not updated_data.get('desktop_webp') and updated_data.get('fallback'):
            updated_data['desktop_webp'] = updated_data['fallback']
        
        # Nếu không có fallback, dùng desktop_webp
        if not updated_data.get('fallback') and updated_data.get('desktop_webp'):
            updated_data['fallback'] = updated_data['desktop_webp']
        
        # Đảm bảo desktop_jpeg, mobile_webp, mobile_jpeg có giá trị
        if updated_data.get('desktop_webp'):
            if not updated_data.get('desktop_jpeg'):
                updated_data['desktop_jpeg'] = updated_data['desktop_webp']
            if not updated_data.get('mobile_webp'):
                updated_data['mobile_webp'] = updated_data['desktop_webp']
            if not updated_data.get('mobile_jpeg'):
                updated_data['mobile_jpeg'] = updated_data['desktop_webp']
        elif updated_data.get('fallback'):
            # Nếu không có desktop_webp, dùng fallback cho tất cả
            updated_data['desktop_webp'] = updated_data['fallback']
            updated_data['desktop_jpeg'] = updated_data['fallback']
            updated_data['mobile_webp'] = updated_data['fallback']
            updated_data['mobile_jpeg'] = updated_data['fallback']
        
        return updated_data
    
    updated_data = image_data.copy()
    
    # Download và cập nhật URLs
    if download_all_formats:
        # Download tất cả formats
        formats_to_download = [
            ('desktop_webp', 'webp'),
            ('desktop_jpeg', 'jpeg'),
            ('mobile_webp', 'webp'),
            ('mobile_jpeg', 'jpeg'),
            ('fallback', 'webp')
        ]
    else:
        # Chỉ download desktop_webp và fallback
        formats_to_download = [
            ('desktop_webp', 'webp'),
            ('fallback', 'webp')
        ]
    
    for key, format_type in formats_to_download:
        if image_data.get(key):
            original_url = image_data[key]
            
            # Kiểm tra xem URL đã có .com domain chưa
            if isinstance(original_url, str) and 'sermitsiaq.com' in original_url:
                # Đã có .com domain, giữ nguyên
                updated_data[key] = original_url
                print(f"      ℹ️  {key} already has .com domain, keeping: {original_url[:80]}...")
            else:
                # Chưa có .com domain, download
                relative_path = download_image(original_url, save_dir, image_id, format_type)
                
                if relative_path:
                    # Tạo full URL
                    new_url = f"{base_url}{relative_path}"
                    updated_data[key] = new_url
                    print(f"      ✅ Downloaded {key}: {new_url}")
                else:
                    # Giữ nguyên URL gốc nếu download lỗi (fallback về URL từ trang gốc)
                    print(f"      ⚠️  Failed to download {key}, keeping original URL: {original_url[:80]}...")
                    # Đảm bảo vẫn giữ URL gốc
                    updated_data[key] = original_url
        else:
            # Nếu key không có trong image_data, tìm fallback từ các keys khác
            # Ưu tiên: fallback > desktop_webp > desktop_jpeg > mobile_webp > mobile_jpeg
            fallback_keys = ['fallback', 'desktop_webp', 'desktop_jpeg', 'mobile_webp', 'mobile_jpeg']
            for fb_key in fallback_keys:
                if image_data.get(fb_key) and fb_key != key:
                    updated_data[key] = image_data[fb_key]
                    print(f"      ℹ️  Using {fb_key} as fallback for {key}: {image_data[fb_key]}")
                    break
    
    # Đảm bảo tất cả các keys quan trọng đều có giá trị (fallback chain)
    # Nếu không có desktop_webp, dùng fallback
    if not updated_data.get('desktop_webp') and updated_data.get('fallback'):
        updated_data['desktop_webp'] = updated_data['fallback']
        print(f"      ℹ️  Using fallback for desktop_webp: {updated_data['fallback']}")
    
    # Nếu không có fallback, dùng desktop_webp
    if not updated_data.get('fallback') and updated_data.get('desktop_webp'):
        updated_data['fallback'] = updated_data['desktop_webp']
        print(f"      ℹ️  Using desktop_webp for fallback: {updated_data['desktop_webp']}")
    
    # Nếu không download all formats, copy URLs từ desktop_webp cho các format khác
    # Chỉ copy nếu desktop_webp đã được download (có chứa domain của chúng ta)
    if not download_all_formats:
        # Luôn đảm bảo có desktop_jpeg, mobile_webp, mobile_jpeg
        if updated_data.get('desktop_webp'):
            # Copy desktop_webp cho desktop_jpeg nếu chưa có
            if not updated_data.get('desktop_jpeg'):
                updated_data['desktop_jpeg'] = updated_data['desktop_webp']
            
            # Copy desktop_webp cho mobile nếu chưa có
            if not updated_data.get('mobile_webp'):
                updated_data['mobile_webp'] = updated_data['desktop_webp']
            if not updated_data.get('mobile_jpeg'):
                updated_data['mobile_jpeg'] = updated_data['desktop_webp']
        elif updated_data.get('fallback'):
            # Nếu không có desktop_webp, dùng fallback cho tất cả
            updated_data['desktop_webp'] = updated_data['fallback']
            updated_data['desktop_jpeg'] = updated_data['fallback']
            updated_data['mobile_webp'] = updated_data['fallback']
            updated_data['mobile_jpeg'] = updated_data['fallback']
    
    return updated_data

