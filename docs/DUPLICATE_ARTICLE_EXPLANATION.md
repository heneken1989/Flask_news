# Giải thích: Tại sao 1 article được set `is_home = true` 2 lần?

## 📊 Vấn đề

Một article có thể xuất hiện **nhiều lần** trong layout file với các `display_order` và `layout_type` khác nhau:

### Ví dụ: Article "Mette Frederiksen"

**Lần 1 (Row chính):**
```json
{
  "published_url": "https://www.sermitsiaq.ag/samfund/mette-frederiksen-det-er-en-alvorlig-situation/2334931",
  "display_order": 20001,
  "row_index": 20,
  "layout_type": "3_articles"
}
```

**Lần 2 (NUUK slider):**
```json
{
  "published_url": "https://www.sermitsiaq.ag/samfund/mette-frederiksen-det-er-en-alvorlig-situation/2334931",
  "display_order": 23003,
  "row_index": -1,
  "layout_type": "5_articles"
}
```

## ❌ Vấn đề cũ (trước khi fix)

Khi `link_home_articles.py` chạy, nó iterate qua **TẤT CẢ** layout items theo thứ tự trong file:

```python
# Logic cũ (SAI)
for layout_item in layout_items:  # Iterate theo thứ tự trong file
    published_url = layout_item.get('published_url')
    display_order = layout_item.get('display_order')
    layout_type = layout_item.get('layout_type')
    
    # Tìm article trong DB
    article = Article.query.filter_by(published_url=published_url).first()
    
    if article:
        # Update article
        article.display_order = display_order  # ⚠️ Ghi đè lên giá trị cũ
        article.layout_type = layout_type      # ⚠️ Ghi đè lên giá trị cũ
        article.is_home = True                 # ⚠️ Set lại (không ảnh hưởng nhưng redundant)
        db.session.commit()
```

**Kết quả:**
1. **Lần 1 (Index 21)**: Update article với `display_order=20001`, `layout_type=3_articles` ✅
2. **Lần 2 (Index 29)**: Update lại article với `display_order=23003`, `layout_type=5_articles` ❌
3. **Kết quả cuối cùng**: Article có `display_order=23003` (SAI!) thay vì `20001` (ĐÚNG)

## 💡 Nguyên nhân

1. **Một article có thể xuất hiện nhiều lần trong layout:**
   - Trong **row chính** (row_index >= 0) - đây là vị trí đúng
   - Trong **NUUK slider** (row_index = -1) - đây là duplicate từ slider
   - Trong các **slider khác**

2. **Logic cũ không có cơ chế skip duplicate:**
   - Mỗi lần tìm thấy article, nó update article đó
   - Không track các URL đã được xử lý
   - Lần update cuối cùng sẽ **ghi đè** lên các lần trước

## ✅ Giải pháp đã implement

### 1. Sắp xếp layout items trước khi xử lý

```python
# Sắp xếp: ưu tiên items có row_index >= 0
layout_items_sorted = sorted(layout_items, key=lambda x: (
    x.get('row_index', -1) < 0,  # row_index < 0 sẽ ở sau
    x.get('display_order', 999999)  # Sau đó sắp xếp theo display_order
))
```

**Kết quả:**
- Items có `row_index >= 0` (rows chính) được xử lý **TRƯỚC**
- Items có `row_index < 0` (NUUK slider) được xử lý **SAU**

### 2. Track processed URLs

```python
processed_urls = set()  # Track các URL đã được xử lý

for layout_item in layout_items_sorted:
    published_url = layout_item.get('published_url')
    row_index = layout_item.get('row_index', -1)
    
    # ⚠️ QUAN TRỌNG: Skip duplicate URLs
    if published_url in processed_urls:
        if row_index < 0:
            # URL đã được xử lý và layout item này có row_index < 0
            # → SKIP (đây là duplicate từ NUUK slider)
            print(f"⏭️  Skipping duplicate URL (row_index={row_index})")
            continue
        else:
            # URL đã được xử lý nhưng layout item này có row_index >= 0
            # → RE-PROCESS (ưu tiên row chính)
            print(f"🔄 Re-processing URL with better row_index (row_index={row_index})")
            processed_urls.remove(published_url)  # Remove để xử lý lại
    
    # ... xử lý article ...
    
    # Mark URL as processed
    processed_urls.add(published_url)
```

**Logic:**
- Nếu URL đã được xử lý và layout item có `row_index < 0` → **SKIP**
- Nếu URL đã được xử lý nhưng layout item có `row_index >= 0` → **RE-PROCESS** (ưu tiên row chính)

### 3. Kết quả

**Trước khi fix:**
```
Article "Mette Frederiksen":
  - display_order: 23003 (SAI - từ NUUK slider)
  - layout_type: 5_articles (SAI)
  - is_home: True
```

**Sau khi fix:**
```
Article "Mette Frederiksen":
  - display_order: 20001 (ĐÚNG - từ row 20)
  - layout_type: 3_articles (ĐÚNG)
  - is_home: True
```

## 📝 Tóm tắt

**Vấn đề:** Một article xuất hiện nhiều lần trong layout file → bị update nhiều lần → giá trị cuối cùng ghi đè lên giá trị đúng.

**Giải pháp:**
1. Sắp xếp layout items: ưu tiên `row_index >= 0` trước
2. Track processed URLs: skip duplicate URLs từ NUUK slider
3. Kết quả: Article chỉ được update 1 lần với giá trị đúng

## 🔍 Debug tips

Để kiểm tra xem một article có xuất hiện nhiều lần trong layout:

```python
import json
from pathlib import Path

layout_file = Path('scripts/home_layouts/home_layout_da.json')
with open(layout_file, 'r', encoding='utf-8') as f:
    layout_data = json.load(f)
    layout_items = layout_data.get('layout_items', [])

# Tìm article theo URL
url = "https://www.sermitsiaq.ag/samfund/mette-frederiksen-det-er-en-alvorlig-situation/2334931"
items = [item for item in layout_items if item.get('published_url') == url]

print(f"Article xuất hiện {len(items)} lần:")
for item in items:
    print(f"  - display_order: {item.get('display_order')}, row_index: {item.get('row_index')}, layout_type: {item.get('layout_type')}")
```

