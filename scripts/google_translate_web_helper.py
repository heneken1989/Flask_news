"""
Helper functions cho Google Translate Web (tích hợp từ test_translate_article_web.py)
Được sử dụng trong crawl_article_details_batch.py
"""
import re
import time
from bs4 import BeautifulSoup


def translate_text_with_google_web(sb, text, source_lang='da', target_lang='en', max_retries=3):
    """
    Dịch text sử dụng Google Translate Web (browser automation)
    
    Args:
        sb: SeleniumBase instance
        text: Text cần dịch
        source_lang: Source language code ('da', 'en', 'kl', etc.)
        target_lang: Target language code ('en', 'da', etc.)
        max_retries: Số lần retry nếu lỗi
    
    Returns:
        Translated text hoặc None nếu lỗi
    """
    if not text or not text.strip():
        return text
    
    try:
        # Mở Google Translate
        translate_url = f"https://translate.google.com/?sl={source_lang}&tl={target_lang}&op=translate"
        sb.open(translate_url)
        sb.sleep(2)  # Đợi trang load
        
        # Xử lý cookie consent nếu có
        try:
            accept_buttons = sb.find_elements('button', timeout=3)
            for btn in accept_buttons:
                btn_text = btn.text.lower()
                if 'accept' in btn_text or 'agree' in btn_text or 'got it' in btn_text:
                    sb.click(btn)
                    sb.sleep(1)
                    break
        except:
            pass
        
        # Tìm textarea input
        input_found = False
        textarea_selector = None
        
        for attempt in range(max_retries):
            try:
                selectors = [
                    'textarea[aria-label*="Source"]',
                    'textarea[aria-label*="source"]',
                    'textarea[aria-label*="Text"]',
                    'textarea[aria-label*="text"]',
                    'textarea.cSNK3d',
                    'textarea[jsname="BJE2fc"]',
                    'textarea',
                ]
                
                # Tìm selector nào hoạt động
                for selector in selectors:
                    try:
                        textarea_elem = sb.find_element(selector, timeout=2)
                        if textarea_elem:
                            textarea_selector = selector
                            input_found = True
                            break
                    except:
                        continue
                
                # Thử xpath nếu chưa tìm thấy
                if not textarea_selector:
                    try:
                        textarea_elem = sb.find_element('//textarea', timeout=2)
                        if textarea_elem:
                            textarea_selector = '//textarea'
                            input_found = True
                    except:
                        pass
                
                if textarea_selector and input_found:
                    # Clear và nhập text (sử dụng selector string)
                    sb.clear(textarea_selector)
                    sb.sleep(0.5)
                    
                    # Giới hạn text nếu quá dài
                    if len(text) > 5000:
                        text_to_translate = text[:5000]
                        print(f"      ⚠️  Text too long ({len(text)} chars), truncating to 5000 chars")
                    else:
                        text_to_translate = text
                    
                    # Click vào textarea để focus
                    try:
                        sb.click(textarea_selector)
                        sb.sleep(0.5)
                    except:
                        pass
                    
                    # Với text dài (> 500 chars), sử dụng JavaScript để set value trực tiếp
                    if len(text_to_translate) > 500:
                        try:
                            # Sử dụng JavaScript để set value (nhanh hơn và đáng tin cậy hơn)
                            sb.execute_script(f"""
                                var textarea = document.querySelector('{textarea_selector.replace("'", "\\'")}') || 
                                               document.evaluate('{textarea_selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                if (textarea) {{
                                    textarea.value = {repr(text_to_translate)};
                                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                }}
                            """)
                            sb.sleep(1)
                            
                            # Kiểm tra xem text đã được paste chưa
                            try:
                                actual_text = sb.execute_script(f"""
                                    var textarea = document.querySelector('{textarea_selector.replace("'", "\\'")}') || 
                                                   document.evaluate('{textarea_selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                    return textarea ? textarea.value : '';
                                """)
                                if actual_text and len(actual_text) > len(text_to_translate) * 0.8:
                                    print(f"      ✅ Text pasted successfully via JavaScript ({len(actual_text)} chars)")
                                else:
                                    # Fallback: dùng type
                                    print(f"      ⚠️  JavaScript paste may have failed, trying type() method...")
                                    sb.type(textarea_selector, text_to_translate)
                            except:
                                # Fallback: dùng type
                                sb.type(textarea_selector, text_to_translate)
                        except Exception as e:
                            print(f"      ⚠️  JavaScript paste failed: {e}, using type() method...")
                            sb.type(textarea_selector, text_to_translate)
                    else:
                        # Với text ngắn, dùng type bình thường
                        sb.type(textarea_selector, text_to_translate)
                    
                    # Debug: Hiển thị text đã paste
                    print(f"      📋 Pasted text into Google Translate (length: {len(text_to_translate)} chars)")
                    print(f"      📝 First 300 chars: {text_to_translate[:300]}...")
                    if len(text_to_translate) > 300:
                        print(f"      📝 Last 100 chars: ...{text_to_translate[-100:]}")
                    
                    # Kiểm tra xem text đã được paste vào textarea chưa
                    try:
                        sb.sleep(1)
                        actual_text = sb.execute_script(f"""
                            var textarea = document.querySelector('{textarea_selector.replace("'", "\\'")}') || 
                                           document.evaluate('{textarea_selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            return textarea ? textarea.value : '';
                        """)
                        if actual_text:
                            print(f"      ✅ Verified: Text in textarea ({len(actual_text)} chars)")
                        else:
                            print(f"      ⚠️  Warning: Textarea appears empty after paste!")
                    except:
                        pass
                    
                    # Đợi Google Translate xử lý thêm
                    sb.sleep(3)
                    
                    # Đợi kết quả dịch - cần đợi lâu hơn để Google Translate xử lý hết text
                    print(f"      ⏳ Waiting for Google Translate to process...")
                    sb.sleep(5)  # Đợi thêm để Google Translate xử lý hết text dài
                    
                    # Đợi kết quả dịch - cải thiện logic để lấy TOÀN BỘ text
                    translated_text = None
                    wait_time = 0
                    max_wait = 20  # Tăng thời gian đợi lên 20 giây
                    
                    while wait_time < max_wait:
                        try:
                            # Cách 1: Lấy từ page source (toàn bộ HTML) - cách tốt nhất
                            page_source = sb.get_page_source()
                            soup = BeautifulSoup(page_source, 'html.parser')
                            
                            # Helper function để check xem element có phải là alternative/hidden translation không
                            def is_alternative_or_hidden(elem):
                                """Check xem element có phải là alternative translation hoặc hidden không"""
                                # Check aria-hidden
                                if elem.get('aria-hidden') == 'true':
                                    return True
                                
                                # Check parent elements - nếu có parent là alternative translation container
                                parent = elem.parent
                                max_depth = 5  # Giới hạn độ sâu để tránh loop vô hạn
                                depth = 0
                                while parent and depth < max_depth:
                                    parent_class = parent.get('class', [])
                                    if isinstance(parent_class, list):
                                        parent_class = ' '.join(parent_class)
                                    
                                    # Loại bỏ các containers của alternative translations
                                    if 'NWlwsb' in parent_class or 'WtlSJf' in parent_class:
                                        return True
                                    if 'xss4Ef' in parent_class or 'FWYOhf' in parent_class:
                                        return True
                                    if parent.get('jsname') == 'HyaQwf':  # Alternative translations container
                                        return True
                                    
                                    parent = parent.parent
                                    depth += 1
                                
                                # Check class của chính element
                                elem_class = elem.get('class', [])
                                if isinstance(elem_class, list):
                                    elem_class = ' '.join(elem_class)
                                if 'WtlSJf' in elem_class or 'xss4Ef' in elem_class or 'FWYOhf' in elem_class:
                                    return True
                                
                                return False
                            
                            # Ưu tiên: Tìm TẤT CẢ main visible results (jsname="W297wb" hoặc jsname="jqKxS")
                            # Google Translate có thể hiển thị kết quả dài trong nhiều spans, cần gộp lại
                            main_result_parts = []
                            min_text_length = 1 if len(text_to_translate) < 50 else 5
                            
                            try:
                                # Tìm TẤT CẢ main result spans (visible)
                                main_spans = soup.find_all('span', {'jsname': 'W297wb'})
                                for span in main_spans:
                                    # Chỉ lấy nếu không phải alternative/hidden
                                    if not is_alternative_or_hidden(span):
                                        text_content = span.get_text(separator=' ', strip=True)
                                        if text_content and len(text_content) >= min_text_length:
                                            # Loại bỏ text UI
                                            if 'Không tải được' not in text_content and 'Thử lại' not in text_content:
                                                # Loại bỏ duplicate (check nếu text đã có trong parts)
                                                is_duplicate = False
                                                for existing in main_result_parts:
                                                    # Nếu text này là substring của text đã có hoặc ngược lại
                                                    if text_content in existing or existing in text_content:
                                                        if len(text_content) <= len(existing):
                                                            is_duplicate = True
                                                            break
                                                        else:
                                                            # Nếu text mới dài hơn, thay thế text cũ
                                                            main_result_parts.remove(existing)
                                                            break
                                                
                                                if not is_duplicate:
                                                    main_result_parts.append(text_content)
                                
                                # Nếu không tìm thấy spans, thử tìm main result divs
                                if not main_result_parts:
                                    main_divs = soup.find_all('div', {'jsname': 'jqKxS'})
                                    for div in main_divs:
                                        if not is_alternative_or_hidden(div):
                                            text_content = div.get_text(separator=' ', strip=True)
                                            if text_content and len(text_content) >= min_text_length:
                                                if 'Không tải được' not in text_content and 'Thử lại' not in text_content:
                                                    is_duplicate = False
                                                    for existing in main_result_parts:
                                                        if text_content in existing or existing in text_content:
                                                            if len(text_content) <= len(existing):
                                                                is_duplicate = True
                                                                break
                                                            else:
                                                                main_result_parts.remove(existing)
                                                                break
                                                        
                                                        if not is_duplicate:
                                                            main_result_parts.append(text_content)
                            except:
                                pass
                            
                            # Nếu tìm thấy main results, gộp lại
                            if main_result_parts:
                                # Gộp tất cả parts lại
                                # QUAN TRỌNG: KHÔNG loại bỏ separators ở đây - để giữ lại cho việc tách blocks sau
                                combined_text = ' '.join(main_result_parts)
                                
                                # Chỉ loại bỏ text UI, KHÔNG loại bỏ separators
                                combined_text = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', combined_text, flags=re.IGNORECASE)
                                # Normalize whitespace nhưng giữ separators
                                combined_text = ' '.join(combined_text.split())
                                
                                if len(combined_text) >= min_text_length:
                                    translated_text = combined_text
                                    print(f"      ✅ Found {len(main_result_parts)} main visible parts, combined: {len(translated_text)} chars")
                                    break
                            
                            # Fallback: Tìm từ các selectors khác nhưng loại bỏ alternative/hidden
                            all_translated_parts = []
                            
                            # Thử tìm từ lang attribute nhưng chỉ lấy visible elements
                            try:
                                lang_elements = soup.find_all(['span', 'div'], lang=target_lang)
                                for elem in lang_elements:
                                    # Loại bỏ alternative/hidden translations
                                    if is_alternative_or_hidden(elem):
                                        continue
                                    
                                    text_content = elem.get_text(separator=' ', strip=True)
                                    if text_content and len(text_content) >= min_text_length:
                                        # Loại bỏ text UI
                                        if 'Không tải được' in text_content or 'Thử lại' in text_content:
                                            continue
                                        
                                        # Loại bỏ duplicate (check nếu text đã có trong parts)
                                        is_duplicate = False
                                        for existing in all_translated_parts:
                                            # Nếu text này là substring của text đã có hoặc ngược lại
                                            if text_content in existing or existing in text_content:
                                                if len(text_content) <= len(existing):
                                                    is_duplicate = True
                                                    break
                                                else:
                                                    # Nếu text mới dài hơn, thay thế text cũ
                                                    all_translated_parts.remove(existing)
                                                    break
                                        
                                        if not is_duplicate:
                                            all_translated_parts.append(text_content)
                            except:
                                pass
                            
                            # Thử các selectors khác
                            selectors_to_try = [
                                ('span', {'data-language-to': target_lang}),
                                ('span', {'class': 'VIiyi'}),
                                ('div', {'class': 'VIiyi'}),
                            ]
                            
                            for tag, attrs in selectors_to_try:
                                elements = soup.find_all(tag, attrs)
                                for elem in elements:
                                    # Loại bỏ alternative/hidden translations
                                    if is_alternative_or_hidden(elem):
                                        continue
                                    
                                    text_content = elem.get_text(separator=' ', strip=True)
                                    if text_content and len(text_content) >= min_text_length:
                                        # Loại bỏ text UI
                                        if 'Không tải được' in text_content or 'Thử lại' in text_content:
                                            continue
                                        
                                        # Loại bỏ duplicate
                                        is_duplicate = False
                                        for existing in all_translated_parts:
                                            if text_content in existing or existing in text_content:
                                                if len(text_content) <= len(existing):
                                                    is_duplicate = True
                                                    break
                                                else:
                                                    all_translated_parts.remove(existing)
                                                    break
                                        
                                        if not is_duplicate:
                                            all_translated_parts.append(text_content)
                            
                            # Nếu tìm thấy nhiều parts, GỘP TẤT CẢ lại (không chỉ lấy phần lớn nhất)
                            if all_translated_parts:
                                # Gộp tất cả parts lại
                                # QUAN TRỌNG: KHÔNG loại bỏ separators ở đây - để giữ lại cho việc tách blocks sau
                                combined_text = ' '.join(all_translated_parts)
                                
                                # Chỉ loại bỏ text UI, KHÔNG loại bỏ separators
                                combined_text = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', combined_text, flags=re.IGNORECASE)
                                # Normalize whitespace nhưng giữ separators
                                combined_text = ' '.join(combined_text.split())
                                
                                min_combined_length = 1 if len(text_to_translate) < 50 else 10
                                if combined_text and len(combined_text) >= min_combined_length:
                                    translated_text = combined_text
                                    print(f"      ✅ Found {len(all_translated_parts)} visible parts, combined: {len(translated_text)} chars")
                                    break
                            
                            # Kiểm tra xem đã có đủ text chưa
                            # Với text ngắn (< 50 chars), chỉ cần có text là đủ
                            # Với text dài, cần ít nhất 30% input
                            min_required = len(text_to_translate) * 0.3 if len(text_to_translate) > 50 else 1
                            
                            if translated_text and len(translated_text) >= min_required:
                                break
                            
                            sb.sleep(1)
                            wait_time += 1
                            
                        except Exception as e:
                            print(f"      ⚠️  Error getting translation: {e}")
                            sb.sleep(1)
                            wait_time += 1
                            continue
                    
                    if translated_text and translated_text.strip():
                        translated_text = translated_text.strip()
                        # Loại bỏ "PM" hoặc "AM" ở cuối
                        translated_text = re.sub(r'\s*(PM|AM)$', '', translated_text, flags=re.IGNORECASE)
                        print(f"      ✅ Final translated text: {len(translated_text)} chars (input: {len(text_to_translate)} chars)")
                        return translated_text
                    else:
                        # Nếu không lấy được kết quả, thử cách khác: scroll và tìm lại
                        print(f"      ⚠️  Could not get translated text after {max_wait} seconds, trying alternative method...")
                        
                        # Thử scroll xuống để xem toàn bộ kết quả
                        try:
                            sb.scroll_to_bottom()
                            sb.sleep(2)
                            
                            # Thử lấy lại từ page source sau khi scroll
                            page_source = sb.get_page_source()
                            soup = BeautifulSoup(page_source, 'html.parser')
                            
                            # Helper function để check xem element có phải là alternative/hidden translation không
                            def is_alternative_or_hidden(elem):
                                """Check xem element có phải là alternative translation hoặc hidden không"""
                                if elem.get('aria-hidden') == 'true':
                                    return True
                                
                                parent = elem.parent
                                max_depth = 5
                                depth = 0
                                while parent and depth < max_depth:
                                    parent_class = parent.get('class', [])
                                    if isinstance(parent_class, list):
                                        parent_class = ' '.join(parent_class)
                                    
                                    if 'NWlwsb' in parent_class or 'WtlSJf' in parent_class:
                                        return True
                                    if 'xss4Ef' in parent_class or 'FWYOhf' in parent_class:
                                        return True
                                    if parent.get('jsname') == 'HyaQwf':
                                        return True
                                    
                                    parent = parent.parent
                                    depth += 1
                                
                                elem_class = elem.get('class', [])
                                if isinstance(elem_class, list):
                                    elem_class = ' '.join(elem_class)
                                if 'WtlSJf' in elem_class or 'xss4Ef' in elem_class or 'FWYOhf' in elem_class:
                                    return True
                                
                                return False
                            
                            # Tìm tất cả text có lang attribute = target_lang nhưng chỉ lấy visible
                            all_texts = []
                            for elem in soup.find_all(['span', 'div'], lang=target_lang):
                                # Loại bỏ alternative/hidden translations
                                if is_alternative_or_hidden(elem):
                                    continue
                                
                                text = elem.get_text(separator=' ', strip=True)
                                # Loại bỏ text UI
                                if 'Không tải được' in text or 'Thử lại' in text:
                                    continue
                                
                                if text and len(text) > 2:
                                    all_texts.append(text)
                            
                            if all_texts:
                                # Gộp TẤT CẢ texts lại (không chỉ lấy text lớn nhất)
                                # QUAN TRỌNG: KHÔNG loại bỏ separators ở đây - để giữ lại cho việc tách blocks sau
                                combined_text = ' '.join(all_texts)
                                
                                # Chỉ loại bỏ text UI, KHÔNG loại bỏ separators
                                combined_text = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', combined_text, flags=re.IGNORECASE)
                                # Normalize whitespace nhưng giữ separators
                                combined_text = ' '.join(combined_text.split())
                                
                                if combined_text:
                                    translated_text = combined_text.strip()
                                    translated_text = re.sub(r'\s*(PM|AM)$', '', translated_text, flags=re.IGNORECASE)
                                    print(f"      ✅ Found {len(all_texts)} visible texts, combined: {len(translated_text)} chars")
                                    return translated_text
                        except Exception as e:
                            print(f"      ⚠️  Alternative method also failed: {e}")
                        
                        # Nếu vẫn không được, với text ngắn có thể giữ nguyên hoặc retry
                        if len(text_to_translate) < 50:
                            print(f"      ⚠️  Text too short ({len(text_to_translate)} chars), may not show translation. Keeping original or retrying...")
                            if attempt < max_retries - 1:
                                print(f"      🔄 Retrying... ({attempt + 1}/{max_retries})")
                                sb.sleep(2)
                                continue
                            # Với text rất ngắn, có thể giữ nguyên
                            return text_to_translate
                        else:
                            if attempt < max_retries - 1:
                                print(f"      🔄 Retrying... ({attempt + 1}/{max_retries})")
                                sb.sleep(2)
                                continue
                            return None
                
            except Exception as e:
                print(f"      ⚠️  Error in translation attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"      🔄 Retrying... ({attempt + 1}/{max_retries})")
                    sb.sleep(2)
                    sb.open(translate_url)
                    sb.sleep(2)
                    continue
                else:
                    return None
        
        if not input_found:
            print(f"      ❌ Could not find input textarea after {max_retries} attempts")
            return None
        
    except Exception as e:
        print(f"      ❌ Error with Google Translate Web: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return None
def translate_content_blocks_with_web(sb, content_blocks, source_lang='da', target_lang='en', delay=2.0, batch_size=5):
    """
    Dịch content_blocks sử dụng Google Translate Web (gom các block lại để dịch hiệu quả hơn)
    
    Args:
        sb: SeleniumBase instance
        content_blocks: List of content blocks
        source_lang: Source language code
        target_lang: Target language code
        delay: Delay giữa các lần translate (giây)
        batch_size: Số lượng blocks gom lại để dịch cùng lúc
        
    Returns:
        Translated content blocks
    """
    if not content_blocks:
        return []
    
    # Separator để tách các blocks sau khi dịch
    # Sử dụng format (*N*) để đánh dấu block index, giúp map chính xác hơn
    # Ví dụ: (*0*), (*1*), (*2*) để biết đây là block 0, 1, 2
    def get_block_separator(block_index):
        """Tạo separator với block index"""
        return f"\n(*{block_index}*)\n"
    
    BLOCK_SEPARATOR_PATTERN = r'\(\*(\d+)\*\)'  # Pattern để tìm (*N*)
    
    translated_blocks = []
    text_blocks_to_translate = []  # Lưu index và text của các blocks cần dịch
    
    # Bước 1: Gom các text blocks lại (KHÔNG bao gồm caption - sẽ dịch riêng)
    print(f"   📦 Grouping text blocks for batch translation...")
    for idx, block in enumerate(content_blocks):
        block_text = None
        
        # Lấy text từ block (KHÔNG lấy caption - sẽ dịch riêng)
        if block.get('type') in ['kicker', 'paragraph', 'heading', 'intro', 'subtitle', 'title']:
            if block.get('text'):
                block_text = block['text']
            elif block.get('html'):
                # Extract text từ HTML
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(block['html'], 'html.parser')
                    block_text = soup.get_text(separator=' ', strip=False)
                except:
                    pass
        
        if block_text and block_text.strip():
            text_blocks_to_translate.append({
                'index': idx,
                'block': block,
                'text': block_text.strip()
            })
    
    print(f"   📝 Found {len(text_blocks_to_translate)} text blocks to translate")
    
    # Bước 2: Dịch theo batch
    # Google Translate Web giới hạn thực tế: Rất nghiêm ngặt, có thể cắt text ngay cả với ~1500 ký tự
    # Giảm xuống rất thấp để tránh bị cắt text
    # Google Translate Web limits:
    # - Không login: ~5000 ký tự, ~1000 từ
    # - Có login: ~10000-15000 ký tự, ~2000-3000 từ
    # Với logic lấy kết quả đã cải thiện (lấy tất cả elements), có thể tăng giới hạn
    MAX_CHARS_PER_BATCH = 3000  # Giới hạn: 3000 ký tự (tăng từ 1000 vì logic đã tốt hơn)
    MAX_WORDS_PER_BATCH = 600   # Giới hạn: 600 từ (tăng từ 200 vì logic đã tốt hơn)
    
    if text_blocks_to_translate:
        translated_texts = {}
        
        # Tạo batches dựa trên số ký tự/số từ thay vì số lượng blocks cố định
        current_batch = []
        current_batch_chars = 0
        current_batch_words = 0
        batch_number = 1
        total_batches = 0
        
        # Tính tổng số batches cần thiết
        temp_batches = []
        temp_batch = []
        temp_chars = 0
        temp_words = 0
        for item in text_blocks_to_translate:
            text = item['text']
            text_chars = len(text)
            text_words = len(text.split())
            
            # Tính toán separator size (ước lượng cho block index lớn nhất)
            estimated_separator_size = len(get_block_separator(len(text_blocks_to_translate)))
            
            # Nếu thêm block này vượt quá giới hạn, tạo batch mới
            if (temp_chars + text_chars + estimated_separator_size > MAX_CHARS_PER_BATCH or 
                temp_words + text_words > MAX_WORDS_PER_BATCH) and temp_batch:
                temp_batches.append(temp_batch)
                temp_batch = []
                temp_chars = 0
                temp_words = 0
            
            temp_batch.append(item)
            temp_chars += text_chars + estimated_separator_size
            temp_words += text_words
        
        if temp_batch:
            temp_batches.append(temp_batch)
        
        total_batches = len(temp_batches)
        
        # Dịch từng batch
        for batch in temp_batches:
            print(f"   🌐 Translating batch {batch_number}/{total_batches} ({len(batch)} blocks)...")
            
            # Gom text của batch lại với separator có block index
            batch_texts = []
            for i, item in enumerate(batch):
                # Thêm separator với block index trước mỗi block (trừ block đầu tiên)
                if i > 0:
                    batch_texts.append(get_block_separator(item['index']))
                batch_texts.append(item['text'])
            combined_text = ''.join(batch_texts)
            
            # Đếm số ký tự và số từ
            batch_chars = len(combined_text)
            batch_words = len(combined_text.split())
            print(f"      📊 Batch stats: {batch_chars:,} characters, {batch_words:,} words")
            
            # Debug: Hiển thị các blocks trong batch
            print(f"      📋 Blocks in this batch:")
            for i, item in enumerate(batch, 1):
                block_preview = item['text'][:100] + ('...' if len(item['text']) > 100 else '')
                # Highlight nếu là block có thể bị miss (như "Grønlandsudvalget inviteret til Avannaata Qimussersua")
                if 'Grønlandsudvalget' in item['text'] or 'Avannaata' in item['text'] or 'inviteret' in item['text']:
                    print(f"         {i}. Block {item['index']} ⚠️ (may be missed): {block_preview}")
                else:
                    print(f"         {i}. Block {item['index']}: {block_preview}")
            
            # Debug: Hiển thị separator trong combined text
            import re
            separator_matches = re.findall(BLOCK_SEPARATOR_PATTERN, combined_text)
            expected_separators = len(batch) - 1
            print(f"      🔍 Separator count in combined text: {len(separator_matches)} (expected: {expected_separators})")
            if len(separator_matches) != expected_separators:
                print(f"      ⚠️  Warning: Separator count mismatch!")
            if separator_matches:
                print(f"      🔍 Block indices in separators: {separator_matches}")
            print(f"      🔍 Combined text preview (first 400 chars): {combined_text[:400]}...")
            if len(combined_text) > 400:
                print(f"      🔍 Combined text preview (last 200 chars): ...{combined_text[-200:]}")
            
            # Cảnh báo nếu vượt quá giới hạn
            if batch_chars > MAX_CHARS_PER_BATCH:
                print(f"      ⚠️  Warning: Batch exceeds character limit ({batch_chars} > {MAX_CHARS_PER_BATCH})")
            if batch_words > MAX_WORDS_PER_BATCH:
                print(f"      ⚠️  Warning: Batch exceeds word limit ({batch_words} > {MAX_WORDS_PER_BATCH})")
            
            # Dịch toàn bộ batch
            translated_combined = None
            translated_batch = None
            separator_pattern = None
            
            try:
                translated_combined = translate_text_with_google_web(sb, combined_text, source_lang, target_lang)
                if translated_combined:
                    translated_chars = len(translated_combined)
                    translated_words = len(translated_combined.split())
                    input_chars = len(combined_text)
                    input_words = len(combined_text.split())
                    
                    print(f"      ✅ Translated: {translated_chars:,} characters, {translated_words:,} words")
                    
                    # Debug: In toàn bộ kết quả dịch để kiểm tra
                    print(f"\n      🔍 ========== FULL TRANSLATION RESULT ==========")
                    print(f"      Length: {len(translated_combined)} characters")
                    print(f"      Full text:\n{translated_combined}")
                    print(f"      ============================================\n")
                    
                    # Kiểm tra xem Google Translate có cắt text không
                    # Nếu translated text quá ngắn (< 70% input), có thể bị cắt
                    # Hoặc nếu text kết thúc đột ngột (không có dấu chấm câu ở cuối)
                    should_translate_individually = False
                    reason = ""
                    
                    text_ratio = translated_chars / input_chars if input_chars > 0 else 0
                    ends_properly = translated_combined.strip().endswith(('.', '!', '?', ':', ';'))
                    
                    print(f"      🔍 Text ratio: {text_ratio*100:.1f}% ({translated_chars}/{input_chars})")
                    print(f"      🔍 Ends properly: {ends_properly} (last 30 chars: '{translated_combined[-30:]}')")
                    
                    # Phát hiện text bị cắt: ratio < 70% HOẶC (không kết thúc đúng và ratio < 90%)
                    if text_ratio < 0.7:
                        should_translate_individually = True
                        reason = f"translated text too short ({translated_chars} vs {input_chars} input, {text_ratio*100:.1f}%)"
                        print(f"      ⚠️  Text truncated detected: ratio {text_ratio*100:.1f}% < 70%")
                    elif not ends_properly and text_ratio < 0.9:
                        # Text có thể bị cắt nếu không kết thúc đúng cách và ratio < 90%
                        should_translate_individually = True
                        reason = f"translated text may be truncated (ends with '{translated_combined[-30:]}', ratio: {text_ratio*100:.1f}%)"
                        print(f"      ⚠️  Text may be truncated: ends improperly and ratio {text_ratio*100:.1f}% < 90%")
                    else:
                        print(f"      ✅ Text ratio OK: {text_ratio*100:.1f}%")
                    
                    # Tách lại thành các blocks để kiểm tra
                    # Nếu chỉ có 1 block, không cần tìm separator
                    if len(batch) == 1:
                        print(f"      ℹ️  Single block in batch, no separator needed")
                        translated_batch = [translated_combined.strip()]
                        should_translate_individually = False
                    else:
                        # Tìm các separator với format (*N*) để map chính xác block index
                        import re
                        
                        # Loại bỏ text UI trước khi tìm separator
                        cleaned_translated = translated_combined
                        cleaned_translated = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', cleaned_translated, flags=re.IGNORECASE)
                        
                        separator_matches = list(re.finditer(BLOCK_SEPARATOR_PATTERN, cleaned_translated))
                        
                        if separator_matches:
                            # Tạo dict: {position: block_index}
                            separator_info = {}
                            for match in separator_matches:
                                pos = match.start()
                                block_idx = int(match.group(1))
                                separator_info[pos] = block_idx
                            
                            # Sắp xếp theo position
                            separator_positions = sorted(separator_info.keys())
                            print(f"      🔍 Found {len(separator_positions)} separators with block indices")
                            
                            # Debug: Hiển thị block indices
                            block_indices_found = [separator_info[pos] for pos in separator_positions]
                            print(f"      🔍 Block indices in separators: {block_indices_found}")
                            
                            # Sử dụng cleaned_translated cho việc split
                            translated_combined = cleaned_translated
                        else:
                            separator_positions = []
                            print(f"      ⚠️  No separators with format (*N*) found in translated text")
                            
                            # Debug: Kiểm tra xem separators có trong text không (có thể bị Google Translate loại bỏ)
                            debug_separator_check = re.search(r'\(\*\d+\*\)', translated_combined)
                            if debug_separator_check:
                                print(f"      🔍 Debug: Found separator pattern in text at position {debug_separator_check.start()}")
                            else:
                                print(f"      🔍 Debug: Separator pattern (*N*) NOT found in translated text")
                                print(f"      🔍 Debug: First 200 chars of translated: '{translated_combined[:200]}'")
                                # Kiểm tra xem có pattern tương tự không
                                similar_patterns = re.findall(r'\([^)]*\d+[^)]*\)', translated_combined)
                                if similar_patterns:
                                    print(f"      🔍 Debug: Found similar patterns: {similar_patterns[:5]}")
                    
                    # Lưu thông tin block index cho mỗi separator
                    separator_block_map = {}  # {position: block_index}
                    if separator_positions:
                        # Extract block index từ separator pattern
                        import re
                        for pos in separator_positions:
                            # Tìm pattern (*N*) tại vị trí pos
                            match = re.search(BLOCK_SEPARATOR_PATTERN, translated_combined[max(0, pos-10):pos+20])
                            if match:
                                block_idx = int(match.group(1))
                                separator_block_map[pos] = block_idx
                        
                        # Loại bỏ các separator quá gần nhau (< 30 chars) - có thể là duplicate
                        filtered_positions = []
                        filtered_map = {}
                        for pos in separator_positions:
                            if not filtered_positions or pos - filtered_positions[-1] >= 30:
                                filtered_positions.append(pos)
                                if pos in separator_block_map:
                                    filtered_map[pos] = separator_block_map[pos]
                            else:
                                # Nếu quá gần, giữ lại vị trí đầu tiên
                                pass
                        
                        separator_positions = filtered_positions
                        separator_block_map = filtered_map
                        
                        # Chỉ lấy số lượng separator cần thiết (len(batch) - 1)
                        expected_separators = len(batch) - 1
                        if len(separator_positions) > expected_separators:
                            # Ưu tiên các separator có block index khớp với batch
                            batch_indices = {item['index'] for item in batch}
                            # Sắp xếp lại: ưu tiên separator có block index trong batch
                            prioritized = []
                            others = []
                            for pos in separator_positions:
                                if pos in separator_block_map and separator_block_map[pos] in batch_indices:
                                    prioritized.append(pos)
                                else:
                                    others.append(pos)
                            separator_positions = (prioritized + others)[:expected_separators]
                            # Cập nhật lại map
                            separator_block_map = {pos: separator_block_map[pos] for pos in separator_positions if pos in separator_block_map}
                            print(f"      ⚠️  Found {len(separator_positions)} separators but only need {expected_separators}, taking first {expected_separators}")
                        elif len(separator_positions) < expected_separators:
                            print(f"      ⚠️  Found only {len(separator_positions)} separators but need {expected_separators}")
                    
                    print(f"      🔍 Total separator positions (after filtering): {len(separator_positions)}")
                    if separator_block_map:
                        print(f"      🔍 Block indices map: {separator_block_map}")
                    
                    if separator_positions:
                        # Split tại các vị trí separator và map với block index
                        # Tìm tất cả separators với block indices
                        import re
                        all_separators = list(re.finditer(BLOCK_SEPARATOR_PATTERN, translated_combined))
                        
                        parts_map = {}  # {block_index: translated_text}
                        
                        if all_separators:
                            # Lấy text trước separator đầu tiên (block đầu tiên trong batch)
                            first_sep = all_separators[0]
                            first_text = translated_combined[:first_sep.start()].strip()
                            # Loại bỏ text UI và normalize
                            first_text = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', first_text, flags=re.IGNORECASE)
                            first_text = re.sub(BLOCK_SEPARATOR_PATTERN, '', first_text)  # Loại bỏ separator nếu có
                            first_text = ' '.join(first_text.split())
                            if first_text and len(batch) > 0:
                                parts_map[batch[0]['index']] = first_text
                            
                            # Lấy text giữa các separators
                            for i in range(len(all_separators)):
                                current_sep = all_separators[i]
                                block_idx = int(current_sep.group(1))
                                
                                # Tìm separator tiếp theo
                                if i + 1 < len(all_separators):
                                    next_sep = all_separators[i + 1]
                                    text_between = translated_combined[current_sep.end():next_sep.start()].strip()
                                else:
                                    # Lấy text sau separator cuối cùng
                                    text_between = translated_combined[current_sep.end():].strip()
                                
                                # Loại bỏ text UI, separator, và normalize
                                text_between = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', text_between, flags=re.IGNORECASE)
                                text_between = re.sub(BLOCK_SEPARATOR_PATTERN, '', text_between)  # Loại bỏ separator nếu có
                                text_between = ' '.join(text_between.split())
                                
                                if text_between:
                                    # Kiểm tra duplicate
                                    is_duplicate = False
                                    if parts_map:
                                        for prev_idx, prev_part in parts_map.items():
                                            if len(prev_part) > 50 and len(text_between) > 50:
                                                # So sánh 100 ký tự đầu
                                                if prev_part[:100] == text_between[:100]:
                                                    is_duplicate = True
                                                    break
                                    
                                    if not is_duplicate:
                                        # Map với block index từ separator
                                        parts_map[block_idx] = text_between
                        else:
                            # Không tìm thấy separator, lấy toàn bộ text làm block đầu tiên
                            cleaned_text = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', translated_combined, flags=re.IGNORECASE)
                            cleaned_text = re.sub(BLOCK_SEPARATOR_PATTERN, '', cleaned_text)
                            cleaned_text = ' '.join(cleaned_text.split())
                            if cleaned_text and len(batch) > 0:
                                parts_map[batch[0]['index']] = cleaned_text
                        
                        # Chuyển parts_map thành list theo thứ tự batch
                        parts = []
                        for item in batch:
                            if item['index'] in parts_map:
                                parts.append(parts_map[item['index']])
                            else:
                                # Nếu không tìm thấy, thêm empty string
                                parts.append('')
                                print(f"      ⚠️  Block {item['index']} not found in split results")
                        
                        # Luôn lưu lại parts đã split được (dù có đủ hay không)
                        translated_batch = parts
                        
                        # Debug: Hiển thị kết quả split chi tiết
                        print(f"\n      🔍 ========== SPLIT RESULTS ==========")
                        print(f"      Total parts found: {len(parts)}")
                        print(f"      Expected: {len(batch)}")
                        print(f"      Separator positions: {separator_positions}")
                        for i, part in enumerate(parts, 1):
                            print(f"\n      Part {i} ({len(part)} chars):")
                            print(f"      {part}")
                            print(f"      ---")
                        print(f"      ======================================\n")
                        
                        if len(parts) >= len(batch):
                            print(f"      ✅ Separator found, split into {len(translated_batch)} parts (expected {len(batch)})")
                        else:
                            print(f"      ⚠️  Separator found but only {len(parts)} parts (expected {len(batch)})")
                            print(f"      ⚠️  Google Translate may have merged some blocks or truncated the text")
                            print(f"      🔍 Missing {len(batch) - len(parts)} blocks")
                    else:
                        print(f"      ⚠️  Separator pattern (*N*) not found in translated text")
                    
                    # Debug: Hiển thị kết quả split
                    if translated_batch:
                        print(f"      🔍 Split results:")
                        for i, part in enumerate(translated_batch, 1):
                            part_preview = part[:80] + ('...' if len(part) > 80 else '')
                            print(f"         Part {i} ({len(part)} chars): {part_preview}")
                    else:
                        # Debug: Nếu vẫn không tìm thấy separator
                        print(f"      🔍 Debug: Checking for separators in translated text...")
                        print(f"      🔍 First 300 chars: {repr(translated_combined[:300])}")
                        print(f"      🔍 Contains '***': {'***' in translated_combined}")
                        print(f"      🔍 Count of '***': {translated_combined.count('***')}")
                        # Hiển thị tất cả các vị trí có ***
                        star_positions = []
                        i = 0
                        while i < len(translated_combined):
                            if translated_combined[i:i+3] == '***':
                                star_positions.append(i)
                                i += 3
                            else:
                                i += 1
                        print(f"      🔍 Positions of '***': {star_positions[:10]}")  # Hiển thị 10 vị trí đầu
                    
                    # Chỉ kiểm tra nếu không phải single block (đã xử lý ở trên)
                    if len(batch) > 1:
                        if translated_batch:
                            # Nếu số parts ít hơn số blocks gốc, cần dịch lại các blocks còn thiếu
                            if len(translated_batch) < len(batch):
                                should_translate_individually = True
                                reason = f"missing blocks after split ({len(translated_batch)} parts vs {len(batch)} expected)"
                            else:
                                # Đủ parts, không cần dịch lại
                                should_translate_individually = False
                        else:
                            should_translate_individually = True
                            reason = "separator not found in translated text"
                            print(f"      🔍 Debug: First 200 chars of translated: {repr(translated_combined[:200])}")
                    
                    # Xử lý kết quả dịch
                    if should_translate_individually:
                        # Có vấn đề: một số blocks bị thiếu hoặc không tìm thấy separator
                        print(f"      ⚠️  Warning: {reason}")
                        
                        # Nếu đã có một số parts từ batch translation, sử dụng chúng
                        if translated_batch and len(translated_batch) > 0:
                            print(f"\n      📝 ========== USING PARTS FROM BATCH ==========")
                            print(f"      Using {len(translated_batch)} parts from batch translation...")
                            print(f"      Total blocks in batch: {len(batch)}")
                            print(f"      Missing blocks: {len(batch) - len(translated_batch)}")
                            
                            # Debug: Hiển thị tất cả blocks trong batch
                            print(f"\n      🔍 All blocks in batch:")
                            for i, item in enumerate(batch):
                                print(f"         {i+1}. Block {item['index']}: {item['text'][:60]}...")
                            
                            # Map các parts đã có vào các blocks tương ứng
                            print(f"\n      🔍 Mapping parts to blocks:")
                            for i, item in enumerate(batch):
                                if i < len(translated_batch):
                                    translated_texts[item['index']] = translated_batch[i].strip()
                                    print(f"      ✅ Block {item['index']} -> Part {i+1} ({len(translated_batch[i])} chars)")
                                    print(f"         Original: {item['text'][:60]}...")
                                    print(f"         Translated: {translated_batch[i][:60]}...")
                                else:
                                    # Dịch lại các blocks còn thiếu
                                    print(f"      🔄 Block {item['index']} missing, re-translating individually...")
                                    print(f"         Original text: {item['text'][:100]}...")
                                    individual_translation = translate_text_with_google_web(sb, item['text'], source_lang, target_lang)
                                    if individual_translation:
                                        translated_texts[item['index']] = individual_translation.strip()
                                        print(f"         ✅ Translated: {individual_translation[:100]}...")
                                        time.sleep(delay)
                                    else:
                                        translated_texts[item['index']] = item['text']  # Giữ nguyên nếu lỗi
                                        print(f"         ⚠️  Translation failed, keeping original")
                            print(f"      ============================================\n")
                            print(f"      ============================================\n")
                        else:
                            # Không có parts nào, dịch lại tất cả từng block riêng
                            print(f"      ⚠️  Google Translate may have truncated the text. Translating blocks individually...")
                            for item in batch:
                                print(f"      🔄 Re-translating block {item['index']} individually...")
                                individual_translation = translate_text_with_google_web(sb, item['text'], source_lang, target_lang)
                                if individual_translation:
                                    translated_texts[item['index']] = individual_translation.strip()
                                    time.sleep(delay)
                                else:
                                    translated_texts[item['index']] = item['text']  # Giữ nguyên nếu lỗi
                    else:
                        # Tất cả đều OK, map lại vào từng block
                        print(f"      ✅ All blocks translated successfully in batch")
                        for i, item in enumerate(batch):
                            if i < len(translated_batch):
                                translated_texts[item['index']] = translated_batch[i].strip()
                            else:
                                # Nếu không đủ (trường hợp này không nên xảy ra nếu logic trên đúng)
                                print(f"      ⚠️  Block {item['index']} missing from batch, translating individually...")
                                individual_translation = translate_text_with_google_web(sb, item['text'], source_lang, target_lang)
                                if individual_translation:
                                    translated_texts[item['index']] = individual_translation.strip()
                                    time.sleep(delay)
                                else:
                                    translated_texts[item['index']] = item['text']  # Giữ nguyên nếu lỗi
                else:
                    # Nếu dịch lỗi, dịch lại từng block riêng
                    print(f"      ❌ Batch translation failed, translating blocks individually...")
                    for item in batch:
                        print(f"      🔄 Translating block {item['index']} individually...")
                        individual_translation = translate_text_with_google_web(sb, item['text'], source_lang, target_lang)
                        if individual_translation:
                            translated_texts[item['index']] = individual_translation.strip()
                            time.sleep(delay)
                        else:
                            translated_texts[item['index']] = item['text']  # Giữ nguyên nếu lỗi
                
                time.sleep(delay)
            except Exception as e:
                print(f"      ⚠️  Error translating batch: {e}")
                # Nếu lỗi, giữ nguyên text gốc
                for item in batch:
                    translated_texts[item['index']] = item['text']
            
            # Debug: Pause sau khi dịch xong batch để user có thể kiểm tra
            print(f"\n      ⏸️  Batch {batch_number}/{total_batches} completed!")
            print(f"      📊 Summary:")
            print(f"         - Input: {batch_chars:,} chars, {batch_words:,} words")
            if translated_combined:
                print(f"         - Output: {len(translated_combined):,} chars, {len(translated_combined.split()):,} words")
                # Kiểm tra xem có translated_batch không
                if translated_batch:
                    print(f"         - Split into: {len(translated_batch)} parts (expected: {len(batch)})")
                    if len(translated_batch) < len(batch):
                        print(f"         - ⚠️  Missing {len(batch) - len(translated_batch)} blocks!")
                print(f"      🔍 Translated text preview (first 300 chars):")
                print(f"         {translated_combined[:300]}...")
                if len(translated_combined) > 300:
                    print(f"      🔍 Translated text preview (last 200 chars):")
                    print(f"         ...{translated_combined[-200:]}")
            else:
                print(f"         - ⚠️  Translation failed!")
            # Auto-continue to next batch (no pause needed)
            print(f"\n      ✅ Batch completed, continuing to next batch...")
            
            batch_number += 1
    
    # Bước 2.5: Gom dates và captions thành batch để dịch cùng nhau
    print(f"   📦 Grouping dates and captions for batch translation...")
    dates_and_captions_to_translate = []
    
    for idx, block in enumerate(content_blocks):
        # Gom captions
        if block.get('type') in ['image', 'header_image_caption']:
            if block.get('caption'):
                dates_and_captions_to_translate.append({
                    'index': idx,
                    'block': block,
                    'text': block['caption'],
                    'field': 'caption',
                    'type': 'caption'
                })
        
        # Gom dates từ article_meta
        if block.get('type') == 'article_meta':
            if block.get('dates'):
                for date_type, date_info in block.get('dates', {}).items():
                    # Dịch label
                    if date_info.get('label'):
                        dates_and_captions_to_translate.append({
                            'index': idx,
                            'block': block,
                            'text': date_info['label'],
                            'field': f'dates.{date_type}.label',
                            'type': 'date_label',
                            'date_type': date_type
                        })
                    # Dịch title
                    if date_info.get('title'):
                        dates_and_captions_to_translate.append({
                            'index': idx,
                            'block': block,
                            'text': date_info['title'],
                            'field': f'dates.{date_type}.title',
                            'type': 'date_title',
                            'date_type': date_type
                        })
                    # Dịch text
                    if date_info.get('text'):
                        dates_and_captions_to_translate.append({
                            'index': idx,
                            'block': block,
                            'text': date_info['text'],
                            'field': f'dates.{date_type}.text',
                            'type': 'date_text',
                            'date_type': date_type
                        })
    
    # Dịch dates và captions theo batch
    dates_and_captions_translated = {}
    if dates_and_captions_to_translate:
        print(f"   📝 Found {len(dates_and_captions_to_translate)} dates/captions to translate")
        
        # Tạo batches cho dates và captions
        MAX_CHARS_PER_BATCH = 3000
        MAX_WORDS_PER_BATCH = 600
        
        current_batch = []
        current_batch_chars = 0
        current_batch_words = 0
        batch_number = 1
        batch_start_idx = 0  # Index bắt đầu của batch hiện tại trong dates_and_captions_to_translate
        
        for item_idx, item in enumerate(dates_and_captions_to_translate):
            text = item['text']
            text_chars = len(text)
            text_words = len(text.split())
            
            estimated_separator_size = len(get_block_separator(item_idx))
            
            if (current_batch_chars + text_chars + estimated_separator_size > MAX_CHARS_PER_BATCH or 
                current_batch_words + text_words > MAX_WORDS_PER_BATCH) and current_batch:
                # Dịch batch hiện tại
                batch_texts = []
                for i, batch_item in enumerate(current_batch):
                    if i > 0:
                        # Sử dụng index trong danh sách dates_and_captions_to_translate
                        batch_item_idx = batch_start_idx + i
                        batch_texts.append(get_block_separator(batch_item_idx))
                    batch_texts.append(batch_item['text'])
                combined_text = ''.join(batch_texts)
                print(f"      🔄 Translating dates/captions batch {batch_number} ({len(current_batch)} items, {len(combined_text)} chars)...")
                translated_combined = translate_text_with_google_web(sb, combined_text, source_lang, target_lang)
                if translated_combined:
                    # Tách lại thành các items
                    import re
                    BLOCK_SEPARATOR_PATTERN = r'\(\*(\d+)\*\)'
                    separator_matches = list(re.finditer(BLOCK_SEPARATOR_PATTERN, translated_combined))
                    
                    if separator_matches:
                        # Có separators, tách theo separators
                        parts = []
                        last_end = 0
                        for match in separator_matches:
                            part = translated_combined[last_end:match.start()].strip()
                            part = re.sub(BLOCK_SEPARATOR_PATTERN, '', part)
                            part = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', part, flags=re.IGNORECASE)
                            part = ' '.join(part.split())
                            if part:
                                parts.append(part)
                            last_end = match.end()
                        
                        # Lấy phần cuối
                        last_part = translated_combined[last_end:].strip()
                        last_part = re.sub(BLOCK_SEPARATOR_PATTERN, '', last_part)
                        last_part = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', last_part, flags=re.IGNORECASE)
                        last_part = ' '.join(last_part.split())
                        if last_part:
                            parts.append(last_part)
                        
                        # Map về các items trong batch dựa trên separator indices
                        # Tạo map từ separator index sang batch item
                        separator_to_batch_map = {}
                        for i, batch_item in enumerate(current_batch):
                            item_idx_in_list = batch_start_idx + i
                            separator_to_batch_map[item_idx_in_list] = (batch_item['index'], batch_item['field'])
                        
                        # Map parts dựa trên separator indices
                        parts_map = {}
                        if separator_matches:
                            # Lấy text trước separator đầu tiên
                            first_sep = separator_matches[0]
                            first_item_idx = int(first_sep.group(1))
                            first_text = translated_combined[:first_sep.start()].strip()
                            first_text = re.sub(BLOCK_SEPARATOR_PATTERN, '', first_text)
                            first_text = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', first_text, flags=re.IGNORECASE)
                            first_text = ' '.join(first_text.split())
                            if first_text and first_item_idx in separator_to_batch_map:
                                parts_map[separator_to_batch_map[first_item_idx]] = first_text
                            
                            # Lấy text giữa các separators
                            for i in range(len(separator_matches)):
                                current_sep = separator_matches[i]
                                current_item_idx = int(current_sep.group(1))
                                
                                if i + 1 < len(separator_matches):
                                    next_sep = separator_matches[i + 1]
                                    text_between = translated_combined[current_sep.end():next_sep.start()].strip()
                                else:
                                    text_between = translated_combined[current_sep.end():].strip()
                                
                                text_between = re.sub(BLOCK_SEPARATOR_PATTERN, '', text_between)
                                text_between = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', text_between, flags=re.IGNORECASE)
                                text_between = ' '.join(text_between.split())
                                
                                if text_between and current_item_idx in separator_to_batch_map:
                                    parts_map[separator_to_batch_map[current_item_idx]] = text_between
                        
                        # Cập nhật vào dates_and_captions_translated
                        for batch_item in current_batch:
                            key = (batch_item['index'], batch_item['field'])
                            if key in parts_map:
                                dates_and_captions_translated[key] = parts_map[key]
                            else:
                                dates_and_captions_translated[key] = batch_item['text']
                    else:
                        # Không có separators, chia đều hoặc lấy toàn bộ cho item đầu tiên
                        if len(current_batch) == 1:
                            cleaned = re.sub(BLOCK_SEPARATOR_PATTERN, '', translated_combined)
                            cleaned = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', cleaned, flags=re.IGNORECASE)
                            cleaned = ' '.join(cleaned.split())
                            dates_and_captions_translated[(current_batch[0]['index'], current_batch[0]['field'])] = cleaned
                        else:
                            # Chia đều (fallback)
                            for batch_item in current_batch:
                                dates_and_captions_translated[(batch_item['index'], batch_item['field'])] = batch_item['text']
                    
                    time.sleep(delay)
                
                # Reset batch
                batch_start_idx = item_idx  # Cập nhật start index cho batch tiếp theo
                current_batch = []
                current_batch_chars = 0
                current_batch_words = 0
                batch_number += 1
            
            current_batch.append(item)
            current_batch_chars += text_chars + estimated_separator_size
            current_batch_words += text_words
        
        # Dịch batch cuối cùng
        if current_batch:
            batch_texts = []
            for i, batch_item in enumerate(current_batch):
                if i > 0:
                    # Sử dụng index trong danh sách dates_and_captions_to_translate
                    batch_item_idx = batch_start_idx + i
                    batch_texts.append(get_block_separator(batch_item_idx))
                batch_texts.append(batch_item['text'])
            combined_text = ''.join(batch_texts)
            
            print(f"      🔄 Translating dates/captions batch {batch_number} ({len(current_batch)} items, {len(combined_text)} chars)...")
            translated_combined = translate_text_with_google_web(sb, combined_text, source_lang, target_lang)
            
            if translated_combined:
                import re
                BLOCK_SEPARATOR_PATTERN = r'\(\*(\d+)\*\)'
                separator_matches = list(re.finditer(BLOCK_SEPARATOR_PATTERN, translated_combined))
                
                if separator_matches:
                    parts = []
                    last_end = 0
                    for match in separator_matches:
                        part = translated_combined[last_end:match.start()].strip()
                        part = re.sub(BLOCK_SEPARATOR_PATTERN, '', part)
                        part = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', part, flags=re.IGNORECASE)
                        part = ' '.join(part.split())
                        if part:
                            parts.append(part)
                        last_end = match.end()
                    
                    last_part = translated_combined[last_end:].strip()
                    last_part = re.sub(BLOCK_SEPARATOR_PATTERN, '', last_part)
                    last_part = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', last_part, flags=re.IGNORECASE)
                    last_part = ' '.join(last_part.split())
                    if last_part:
                        parts.append(last_part)
                    
                    for i, batch_item in enumerate(current_batch):
                        if i < len(parts):
                            dates_and_captions_translated[(batch_item['index'], batch_item['field'])] = parts[i]
                        else:
                            dates_and_captions_translated[(batch_item['index'], batch_item['field'])] = batch_item['text']
                else:
                    if len(current_batch) == 1:
                        cleaned = re.sub(BLOCK_SEPARATOR_PATTERN, '', translated_combined)
                        cleaned = re.sub(r'Không tải được bản thay thế\s*Thử lại', '', cleaned, flags=re.IGNORECASE)
                        cleaned = ' '.join(cleaned.split())
                        dates_and_captions_translated[(current_batch[0]['index'], current_batch[0]['field'])] = cleaned
                    else:
                        for batch_item in current_batch:
                            dates_and_captions_translated[(batch_item['index'], batch_item['field'])] = batch_item['text']
                
                time.sleep(delay)
    
    # Bước 3: Tạo translated blocks
    print(f"   🔄 Creating translated blocks...")
    for idx, block in enumerate(content_blocks):
        translated_block = block.copy()
        
        # Xử lý text blocks đã dịch (chỉ text blocks, không phải caption)
        if idx in translated_texts:
            translated_text = translated_texts[idx]
            
            # Kiểm tra xem có phải text gốc không (nếu giống nhau thì có thể chưa được dịch)
            original_text = None
            if block.get('text'):
                original_text = block['text']
            elif block.get('html'):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(block['html'], 'html.parser')
                    original_text = soup.get_text(separator=' ', strip=True)
                except:
                    pass
            
            # Nếu translated_text giống với original_text, có thể chưa được dịch
            if original_text and translated_text.strip() == original_text.strip():
                print(f"      ⚠️  Block {idx} translation same as original, may not be translated")
                # Thử dịch lại riêng
                try:
                    retranslated = translate_text_with_google_web(sb, original_text, source_lang, target_lang)
                    if retranslated and retranslated.strip() != original_text.strip():
                        translated_text = retranslated.strip()
                        time.sleep(delay)
                except:
                    pass
            
            # Viết hoa chữ đầu câu nếu chưa viết hoa
            if translated_text and translated_text[0].islower():
                translated_text = translated_text[0].upper() + translated_text[1:]
            
            # Fix duplicate words
            translated_text = re.sub(r'\b(\w+)\s+\1\b', r'\1', translated_text, flags=re.IGNORECASE)
            
            # Cập nhật text field
            if block.get('text'):
                translated_block['text'] = translated_text
            
            # Cập nhật HTML nếu có
            if block.get('html'):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(block['html'], 'html.parser')
                    
                    # Thay thế text trong HTML
                    text_nodes = soup.find_all(string=True)
                    first_text_node = None
                    
                    for text_node in text_nodes:
                        if text_node.strip():
                            if first_text_node is None:
                                first_text_node = text_node
                                text_node.replace_with(translated_text)
                            else:
                                text_node.replace_with('')
                    
                    translated_html = str(soup)
                    translated_block['html'] = translated_html
                    
                    # Cập nhật text field từ HTML
                    try:
                        soup = BeautifulSoup(translated_html, 'html.parser')
                        extracted_text = soup.get_text(separator=' ', strip=True)
                        extracted_text = re.sub(r'(,)([A-Za-z])', r'\1 \2', extracted_text)
                        extracted_text = re.sub(r'\b(\w+)\s+\1\b', r'\1', extracted_text, flags=re.IGNORECASE)
                        if block.get('text'):
                            translated_block['text'] = extracted_text
                    except:
                        pass
                except Exception as e:
                    print(f"      ⚠️  Error updating HTML for block {idx}: {e}")
        else:
            # Block không có trong translated_texts - có thể là block không có text hoặc bị bỏ sót
            # Kiểm tra xem có text không
            block_text = None
            if block.get('text'):
                block_text = block['text']
            elif block.get('html'):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(block['html'], 'html.parser')
                    block_text = soup.get_text(separator=' ', strip=True)
                except:
                    pass
            
            # Nếu có text nhưng không được dịch, cảnh báo
            if block_text and block_text.strip() and block.get('type') in ['kicker', 'paragraph', 'heading', 'intro', 'subtitle', 'title']:
                print(f"      ⚠️  Block {idx} (type: {block.get('type')}) has text but was not translated!")
                # Thử dịch ngay
                try:
                    translated_text = translate_text_with_google_web(sb, block_text.strip(), source_lang, target_lang)
                    if translated_text:
                        # Viết hoa chữ đầu câu
                        if translated_text[0].islower():
                            translated_text = translated_text[0].upper() + translated_text[1:]
                        # Fix duplicate words
                        translated_text = re.sub(r'\b(\w+)\s+\1\b', r'\1', translated_text, flags=re.IGNORECASE)
                        
                        if block.get('text'):
                            translated_block['text'] = translated_text
                        
                        if block.get('html'):
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(block['html'], 'html.parser')
                                text_nodes = soup.find_all(string=True)
                                first_text_node = None
                                for text_node in text_nodes:
                                    if text_node.strip():
                                        if first_text_node is None:
                                            first_text_node = text_node
                                            text_node.replace_with(translated_text)
                                        else:
                                            text_node.replace_with('')
                                translated_block['html'] = str(soup)
                            except:
                                pass
                        time.sleep(delay)
                except Exception as e:
                    print(f"      ⚠️  Error translating missed block {idx}: {e}")
        
        # Cập nhật caption từ batch translation
        if block.get('type') in ['image', 'header_image_caption']:
            if block.get('caption'):
                key = (idx, 'caption')
                if key in dates_and_captions_translated:
                    translated_caption = dates_and_captions_translated[key]
                    # Viết hoa chữ đầu câu nếu chưa viết hoa
                    if translated_caption and translated_caption[0].islower():
                        translated_caption = translated_caption[0].upper() + translated_caption[1:]
                    # Fix duplicate words
                    translated_caption = re.sub(r'\b(\w+)\s+\1\b', r'\1', translated_caption, flags=re.IGNORECASE)
                    translated_block['caption'] = translated_caption
                    print(f"      ✅ Updated caption from batch: {len(translated_caption)} chars")
                else:
                    # Fallback: dịch riêng nếu không có trong batch
                    try:
                        print(f"      🔄 Translating caption for block {idx} (not in batch)...")
                        translated_caption = translate_text_with_google_web(sb, block['caption'], source_lang, target_lang)
                        if translated_caption:
                            if translated_caption[0].islower():
                                translated_caption = translated_caption[0].upper() + translated_caption[1:]
                            translated_caption = re.sub(r'\b(\w+)\s+\1\b', r'\1', translated_caption, flags=re.IGNORECASE)
                            translated_block['caption'] = translated_caption
                            time.sleep(delay)
                        else:
                            translated_block['caption'] = block['caption']
                    except Exception as e:
                        print(f"      ⚠️  Error translating caption for block {idx}: {e}")
                        translated_block['caption'] = block['caption']
        
        # Cập nhật dates từ batch translation
        if block.get('type') == 'article_meta':
            if block.get('dates'):
                translated_dates = {}
                for date_type, date_info in block.get('dates', {}).items():
                    translated_date_info = date_info.copy()
                    
                    # Lấy từ batch translation
                    if date_info.get('label'):
                        key = (idx, f'dates.{date_type}.label')
                        if key in dates_and_captions_translated:
                            translated_date_info['label'] = dates_and_captions_translated[key]
                        else:
                            translated_date_info['label'] = date_info['label']
                    
                    if date_info.get('title'):
                        key = (idx, f'dates.{date_type}.title')
                        if key in dates_and_captions_translated:
                            translated_title = dates_and_captions_translated[key]
                            translated_title = re.sub(r'\s*(PM|AM)$', '', translated_title, flags=re.IGNORECASE)
                            translated_date_info['title'] = translated_title
                        else:
                            translated_date_info['title'] = date_info['title']
                    
                    if date_info.get('text'):
                        key = (idx, f'dates.{date_type}.text')
                        if key in dates_and_captions_translated:
                            translated_text = dates_and_captions_translated[key]
                            translated_text = re.sub(r'\s*(PM|AM)$', '', translated_text, flags=re.IGNORECASE)
                            translated_date_info['text'] = translated_text
                        else:
                            translated_date_info['text'] = date_info['text']
                    
                    # Giữ nguyên datetime
                    if date_info.get('datetime'):
                        translated_date_info['datetime'] = date_info['datetime']
                    
                    translated_dates[date_type] = translated_date_info
                
                translated_block['dates'] = translated_dates
        
        # Giữ nguyên các block khác
        translated_blocks.append(translated_block)
    
    return translated_blocks
