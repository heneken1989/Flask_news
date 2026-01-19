"""
Script test để kiểm tra trang login có input nào không
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seleniumbase import SB

LOGIN_URL = "https://www.sermitsiaq.ag/login"
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')

def handle_cookie_popup(sb):
    """Xử lý cookie consent popup"""
    try:
        sb.sleep(2)  # Đợi popup xuất hiện
        
        # Tìm và click button "ACCEPTER ALLE"
        buttons = sb.execute_script("""
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || buttons[i].innerText;
                if (text.includes('ACCEPTER') || text.includes('Accepter') || 
                    text.includes('ACCEPT') || text.includes('Accept')) {
                    return buttons[i];
                }
            }
            return null;
        """)
        
        if buttons:
            sb.execute_script("arguments[0].click();", buttons)
            print("✅ Accepted cookie consent popup")
            sb.sleep(3)
            return True
        return False
    except Exception as e:
        print(f"⚠️  Cookie popup handling: {e}")
        return False

def test_login_page():
    """Test trang login để tìm các input elements"""
    print("🔍 Testing login page...")
    print(f"   URL: {LOGIN_URL}")
    
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    with SB(uc=True, headless=False, user_data_dir=USER_DATA_DIR) as sb:
        try:
            # Mở trang login
            print("\n📄 Opening login page...")
            sb.open(LOGIN_URL)
            sb.sleep(3)
            
            # Xử lý cookie popup
            print("\n🍪 Handling cookie popup...")
            handle_cookie_popup(sb)
            sb.sleep(2)
            
            # Chụp màn hình
            screenshot_path = os.path.join(USER_DATA_DIR, 'test_login_page.png')
            sb.save_screenshot(screenshot_path)
            print(f"\n📸 Screenshot saved: {screenshot_path}")
            
            # Tìm tất cả input elements
            print("\n🔍 Finding all input elements...")
            
            # Method 1: Tìm bằng CSS selector
            print("\n--- Method 1: CSS Selector ---")
            try:
                inputs = sb.find_elements('input', timeout=5)
                print(f"   Found {len(inputs)} input elements:")
                for i, inp in enumerate(inputs, 1):
                    try:
                        input_id = inp.get_attribute('id') or 'no-id'
                        input_name = inp.get_attribute('name') or 'no-name'
                        input_type = inp.get_attribute('type') or 'no-type'
                        input_placeholder = inp.get_attribute('placeholder') or 'no-placeholder'
                        is_visible = inp.is_displayed()
                        print(f"   {i}. ID: {input_id}, Name: {input_name}, Type: {input_type}")
                        print(f"      Placeholder: {input_placeholder}, Visible: {is_visible}")
                    except Exception as e:
                        print(f"   {i}. Error reading input: {e}")
            except Exception as e:
                print(f"   ❌ Error finding inputs: {e}")
            
            # Method 2: Tìm bằng JavaScript
            print("\n--- Method 2: JavaScript ---")
            try:
                inputs_info = sb.execute_script("""
                    var inputs = document.querySelectorAll('input');
                    var result = [];
                    for (var i = 0; i < inputs.length; i++) {
                        var inp = inputs[i];
                        result.push({
                            id: inp.id || 'no-id',
                            name: inp.name || 'no-name',
                            type: inp.type || 'no-type',
                            placeholder: inp.placeholder || 'no-placeholder',
                            visible: inp.offsetParent !== null,
                            className: inp.className || 'no-class'
                        });
                    }
                    return result;
                """)
                print(f"   Found {len(inputs_info)} input elements:")
                for i, inp_info in enumerate(inputs_info, 1):
                    print(f"   {i}. ID: {inp_info['id']}, Name: {inp_info['name']}, Type: {inp_info['type']}")
                    print(f"      Placeholder: {inp_info['placeholder']}, Visible: {inp_info['visible']}")
                    print(f"      Class: {inp_info['className']}")
            except Exception as e:
                print(f"   ❌ Error with JavaScript: {e}")
            
            # Method 3: Tìm cụ thể #id_subscriber
            print("\n--- Method 3: Find #id_subscriber specifically ---")
            try:
                subscriber = sb.find_element('#id_subscriber', timeout=5)
                print(f"   ✅ Found #id_subscriber!")
                print(f"      ID: {subscriber.get_attribute('id')}")
                print(f"      Name: {subscriber.get_attribute('name')}")
                print(f"      Type: {subscriber.get_attribute('type')}")
                print(f"      Visible: {subscriber.is_displayed()}")
            except Exception as e:
                print(f"   ❌ Could not find #id_subscriber: {e}")
            
            # Method 4: Tìm bằng name attribute
            print("\n--- Method 4: Find by name='subscriber' ---")
            try:
                subscriber = sb.find_element('input[name="subscriber"]', timeout=5)
                print(f"   ✅ Found input[name='subscriber']!")
                print(f"      ID: {subscriber.get_attribute('id')}")
                print(f"      Visible: {subscriber.is_displayed()}")
            except Exception as e:
                print(f"   ❌ Could not find input[name='subscriber']: {e}")
            
            # Method 5: Tìm form và các input trong form
            print("\n--- Method 5: Find form and inputs in form ---")
            try:
                forms = sb.find_elements('form', timeout=5)
                print(f"   Found {len(forms)} form elements:")
                for i, form in enumerate(forms, 1):
                    try:
                        form_action = form.get_attribute('action') or 'no-action'
                        form_method = form.get_attribute('method') or 'no-method'
                        print(f"   Form {i}: action={form_action}, method={form_method}")
                        
                        # Tìm inputs trong form này
                        form_inputs = form.find_elements('input')
                        print(f"      Contains {len(form_inputs)} input elements:")
                        for j, inp in enumerate(form_inputs, 1):
                            inp_id = inp.get_attribute('id') or 'no-id'
                            inp_name = inp.get_attribute('name') or 'no-name'
                            inp_type = inp.get_attribute('type') or 'no-type'
                            print(f"         {j}. ID: {inp_id}, Name: {inp_name}, Type: {inp_type}")
                    except Exception as e:
                        print(f"   Error reading form {i}: {e}")
            except Exception as e:
                print(f"   ❌ Error finding forms: {e}")
            
            # Method 6: Kiểm tra iframe
            print("\n--- Method 6: Check for iframes ---")
            try:
                iframes = sb.execute_script("""
                    return document.querySelectorAll('iframe');
                """)
                print(f"   Found {len(iframes)} iframe(s)")
                for i, iframe in enumerate(iframes, 1):
                    try:
                        iframe_src = sb.execute_script("""
                            var iframes = document.querySelectorAll('iframe');
                            return iframes[arguments[0]].src;
                        """, i-1)
                        iframe_id = sb.execute_script("""
                            var iframes = document.querySelectorAll('iframe');
                            return iframes[arguments[0]].id || 'no-id';
                        """, i-1)
                        print(f"   Iframe {i}: src={iframe_src}, id={iframe_id}")
                        
                        # Thử switch vào iframe và tìm input
                        try:
                            # Thử switch bằng index
                            sb.switch_to_frame(i-1)
                            sb.sleep(2)  # Đợi iframe load
                            
                            iframe_inputs = sb.execute_script("""
                                var inputs = document.querySelectorAll('input');
                                var result = [];
                                for (var i = 0; i < inputs.length; i++) {
                                    var inp = inputs[i];
                                    result.push({
                                        id: inp.id || 'no-id',
                                        name: inp.name || 'no-name',
                                        type: inp.type || 'no-type',
                                        placeholder: inp.placeholder || 'no-placeholder',
                                        visible: inp.offsetParent !== null
                                    });
                                }
                                return result;
                            """)
                            if iframe_inputs:
                                print(f"      ✅ Found {len(iframe_inputs)} input(s) in iframe:")
                                for inp in iframe_inputs:
                                    print(f"         - ID: {inp['id']}, Name: {inp['name']}, Type: {inp['type']}")
                                    print(f"           Placeholder: {inp['placeholder']}, Visible: {inp['visible']}")
                                    
                                    # Kiểm tra xem có phải subscriber input không
                                    if 'subscriber' in inp['id'].lower() or 'subscriber' in inp['name'].lower():
                                        print(f"           🎯 THIS IS THE SUBSCRIBER INPUT!")
                            
                            # Kiểm tra form trong iframe
                            forms_in_iframe = sb.execute_script("""
                                var forms = document.querySelectorAll('form');
                                return forms.length;
                            """)
                            if forms_in_iframe > 0:
                                print(f"      ✅ Found {forms_in_iframe} form(s) in iframe")
                            
                            sb.switch_to_default_content()
                        except Exception as e:
                            print(f"      ⚠️  Could not access iframe: {e}")
                            try:
                                sb.switch_to_default_content()
                            except:
                                pass
                    except Exception as e:
                        print(f"   Error checking iframe {i}: {e}")
            except Exception as e:
                print(f"   ❌ Error finding iframes: {e}")
            
            # Method 7: Đợi lâu hơn và kiểm tra lại
            print("\n--- Method 7: Wait longer and check again ---")
            print("   Waiting 5 more seconds for dynamic content...")
            sb.sleep(5)
            
            try:
                inputs_info = sb.execute_script("""
                    var inputs = document.querySelectorAll('input');
                    var result = [];
                    for (var i = 0; i < inputs.length; i++) {
                        var inp = inputs[i];
                        result.push({
                            id: inp.id || 'no-id',
                            name: inp.name || 'no-name',
                            type: inp.type || 'no-type',
                            placeholder: inp.placeholder || 'no-placeholder',
                            visible: inp.offsetParent !== null
                        });
                    }
                    return result;
                """)
                print(f"   Found {len(inputs_info)} input elements after waiting:")
                for i, inp_info in enumerate(inputs_info, 1):
                    if 'subscriber' in inp_info['id'].lower() or 'subscriber' in inp_info['name'].lower():
                        print(f"   ✅ {i}. ID: {inp_info['id']}, Name: {inp_info['name']}, Type: {inp_info['type']}")
                        print(f"      Placeholder: {inp_info['placeholder']}, Visible: {inp_info['visible']}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Method 8: Get page source để kiểm tra
            print("\n--- Method 8: Check page source ---")
            try:
                page_source = sb.get_page_source()
                if 'id_subscriber' in page_source:
                    print("   ✅ Found 'id_subscriber' in page source")
                    # Tìm vị trí trong source
                    idx = page_source.find('id_subscriber')
                    snippet = page_source[max(0, idx-100):idx+200]
                    print(f"   Snippet: ...{snippet}...")
                else:
                    print("   ❌ 'id_subscriber' NOT found in page source")
                
                if 'name="subscriber"' in page_source:
                    print("   ✅ Found 'name=\"subscriber\"' in page source")
                else:
                    print("   ❌ 'name=\"subscriber\"' NOT found in page source")
                
                # Kiểm tra xem có iframe trong source
                if 'iframe' in page_source.lower():
                    print("   ✅ Found 'iframe' in page source")
                    # Tìm các iframe
                    import re
                    iframe_pattern = r'<iframe[^>]*>'
                    iframes_in_source = re.findall(iframe_pattern, page_source, re.IGNORECASE)
                    print(f"   Found {len(iframes_in_source)} iframe tag(s) in source:")
                    for iframe_tag in iframes_in_source[:3]:  # Chỉ hiển thị 3 đầu tiên
                        print(f"      {iframe_tag[:100]}...")
            except Exception as e:
                print(f"   ❌ Error checking page source: {e}")
            
            # Method 9: Thử switch vào iframe có chứa form login (iframe 0 - đã tìm thấy ở trên)
            print("\n--- Method 9: Switch to iframe 0 (where login form was found) ---")
            try:
                print("   Switching to iframe 0...")
                sb.switch_to_frame(0)
                sb.sleep(3)  # Đợi iframe load
                
                # Tìm input trong iframe
                subscriber_input = sb.execute_script("""
                    var input = document.querySelector('#id_subscriber') || 
                               document.querySelector('input[name="subscriber"]');
                    if (input) {
                        return {
                            id: input.id,
                            name: input.name,
                            type: input.type,
                            placeholder: input.placeholder,
                            visible: input.offsetParent !== null
                        };
                    }
                    return null;
                """)
                
                if subscriber_input:
                    print(f"   ✅ Found subscriber input in iframe 0!")
                    print(f"      ID: {subscriber_input['id']}")
                    print(f"      Name: {subscriber_input['name']}")
                    print(f"      Type: {subscriber_input['type']}")
                    print(f"      Placeholder: {subscriber_input['placeholder']}")
                    print(f"      Visible: {subscriber_input['visible']}")
                    
                    # Thử tìm password input
                    password_input = sb.execute_script("""
                        var input = document.querySelector('#id_password') || 
                                   document.querySelector('input[name="password"]');
                        if (input) {
                            return {
                                id: input.id,
                                name: input.name,
                                type: input.type
                            };
                        }
                        return null;
                    """)
                    if password_input:
                        print(f"   ✅ Found password input!")
                        print(f"      ID: {password_input['id']}, Name: {password_input['name']}")
                    
                    # Thử tìm submit button
                    submit_button = sb.execute_script("""
                        var btn = document.querySelector('button[type="submit"]') ||
                                 document.querySelector('input[type="submit"]');
                        if (btn) {
                            return {
                                type: btn.type,
                                text: btn.textContent || btn.value || 'no-text'
                            };
                        }
                        return null;
                    """)
                    if submit_button:
                        print(f"   ✅ Found submit button!")
                        print(f"      Type: {submit_button['type']}, Text: {submit_button['text']}")
                else:
                    print("   ❌ Subscriber input not found in iframe 0")
                
                sb.switch_to_default_content()
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
                try:
                    sb.switch_to_default_content()
                except:
                    pass
            
            # Method 10: Thử switch vào iteras-iframe1 (đợi visible)
            print("\n--- Method 10: Switch to iteras-iframe1 (wait for visible) ---")
            try:
                # Đợi iframe visible
                print("   Waiting for iteras-iframe1 to become visible...")
                sb.wait_for_element('iframe[name="iteras-iframe1"]', timeout=15)
                sb.sleep(2)
                
                # Tìm iframe index
                iframe_index = sb.execute_script("""
                    var iframes = document.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {
                        if (iframes[i].name === 'iteras-iframe1' || 
                            iframes[i].classList.contains('iteras-iframe')) {
                            return i;
                        }
                    }
                    return -1;
                """)
                
                if iframe_index >= 0:
                    print(f"   ✅ Found iteras-iframe1 at index {iframe_index}")
                    sb.switch_to_frame(iframe_index)
                    sb.sleep(3)
                    
                    # Tìm input trong iframe
                    subscriber_input = sb.execute_script("""
                        var input = document.querySelector('#id_subscriber') || 
                                   document.querySelector('input[name="subscriber"]');
                        if (input) {
                            return {
                                id: input.id,
                                name: input.name,
                                type: input.type,
                                placeholder: input.placeholder,
                                visible: input.offsetParent !== null
                            };
                        }
                        return null;
                    """)
                    
                    if subscriber_input:
                        print(f"   ✅ Found subscriber input in iteras-iframe1!")
                        print(f"      ID: {subscriber_input['id']}")
                        print(f"      Name: {subscriber_input['name']}")
                        print(f"      Type: {subscriber_input['type']}")
                        print(f"      Placeholder: {subscriber_input['placeholder']}")
                        print(f"      Visible: {subscriber_input['visible']}")
                    else:
                        print("   ❌ Subscriber input not found in iteras-iframe1")
                    
                    sb.switch_to_default_content()
                else:
                    print("   ❌ iteras-iframe1 not found")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                try:
                    sb.switch_to_default_content()
                except:
                    pass
            
            print("\n✅ Test completed!")
            print(f"📸 Check screenshot: {screenshot_path}")
            print("\n⏸️  Browser will stay open for 10 seconds for inspection...")
            sb.sleep(10)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_login_page()

