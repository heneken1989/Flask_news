# 🔗 Test URLs

Danh sách các URL để test các pages trong Flask app.

## 🚀 Chạy Flask App

```bash
cd /Users/hien/Desktop/Projects/GC_HRAI/flask
python app.py
```

App sẽ chạy tại: **http://localhost:5000**

---

## 📋 Test URLs

### **1. Home Page (Original)**
```
http://localhost:5000/
```
- Template: `1.html` (original)
- Hiển thị: Full page với header, footer, content từ file gốc

### **2. Article Page (Original)**
```
http://localhost:5000/article
http://localhost:5000/article/123
```
- Template: `1.html` (original)
- Hiển thị: Article detail page

### **3. Front Page với Articles Grid (TEST)**
```
http://localhost:5000/test
http://localhost:5000/test/front
```
- Template: `front_page.html` (mới)
- Hiển thị: Front page với articles grid layout
- Data: Mock articles (2 articles đầu: 2 per row, 3 articles sau: 3 per row)

### **4. View Resources (Local Development)**
```
http://localhost:5000/view-resources/dachser2/public/sermitsiaq/logo.svg
http://localhost:5000/view-resources/baseview/public/common/ClientAPI/index.js
```
- Serve: Files từ `view-resources/` directory
- Trên VPS: Nginx sẽ serve trực tiếp

---

## 🧪 Test Scenarios

### **Test 1: Articles Grid - 2 per row**
1. Vào: `http://localhost:5000/test`
2. Kiểm tra: 2 articles đầu hiển thị 2 per row (large-6)
3. Kiểm tra: CSS styling match với HTML gốc

### **Test 2: Articles Grid - 3 per row**
1. Vào: `http://localhost:5000/test`
2. Kiểm tra: 3 articles sau hiển thị 3 per row (large-4)
3. Kiểm tra: Grid layout đúng

### **Test 3: Header & Footer**
1. Vào: `http://localhost:5000/test`
2. Kiểm tra: Header hiển thị đúng
3. Kiểm tra: Footer hiển thị đúng
4. Kiểm tra: Logo load được từ `/view-resources/`

### **Test 4: Paywall Labels**
1. Vào: `http://localhost:5000/test`
2. Kiểm tra: Articles có `is_paywall: True` hiển thị paywall label
3. Kiểm tra: Class `paywallLabel  ` có 2 spaces cuối

### **Test 5: Images**
1. Vào: `http://localhost:5000/test`
2. Kiểm tra: Images load được
3. Kiểm tra: Responsive images (desktop/mobile) hoạt động
4. Kiểm tra: Picture element với multiple sources

---

## 🔧 Customize Test Data

Để thay đổi test data, edit `views/article_views.py` function `test_front_page()`:

```python
@article_view_bp.route('/test')
def test_front_page():
    mock_articles = [
        # Thêm/sửa articles ở đây
    ]
    return render_template('front_page.html', articles=mock_articles, ...)
```

---

## 📝 Notes

- **Route `/test`** chỉ dùng để test, không dùng cho production
- **Mock data** trong `test_front_page()` sẽ được thay bằng API call sau
- **CSS** sẽ tự động load từ `static/css/` directory
- **View resources** được serve qua Flask route `/view-resources/` khi chạy local

---

## ✅ Checklist Test

- [ ] Home page (`/`) load được
- [ ] Test page (`/test`) load được
- [ ] Articles hiển thị đúng grid layout
- [ ] Header hiển thị đúng
- [ ] Footer hiển thị đúng
- [ ] Logo load được
- [ ] Images load được
- [ ] Paywall labels hiển thị đúng
- [ ] CSS styling match với HTML gốc
- [ ] Responsive images hoạt động

