# ✅ Class Names Verification

Kiểm tra tất cả class names trong template phải match 100% với HTML gốc.

## 📋 Class Names từ HTML gốc (2.html dòng 1257-1339)

### **Article Element**
```html
<article class="column paywall small-12 large-6 small-abs-12 large-abs-6 " 
         data-site-alias="sermitsiaq" 
         data-section="erhverv" 
         data-instance="100090" 
         itemscope>
```
**Classes:** `column`, `paywall`, `small-12`, `large-6`, `small-abs-12`, `large-abs-6` + **space cuối**

### **Content Div**
```html
<div class="content" style="">
```
**Classes:** `content`

### **Link**
```html
<a itemprop="url" class="" href="..." data-k5a-url="..." rel="">
```
**Classes:** `""` (empty class attribute)

### **Media Div**
```html
<div class="media ">
```
**Classes:** `media` + **space cuối**

### **Figure**
```html
<figure data-element-guid="..." class="" >
```
**Classes:** `""` (empty class attribute)

### **Image Container**
```html
<div class="img fullwidthTarget">
```
**Classes:** `img`, `fullwidthTarget`

### **Floating Text**
```html
<div class="floatingText">
    <div class="labels">
    </div>
</div>
```
**Classes:** `floatingText`, `labels`

### **Paywall Label**
```html
<div class="paywallLabel  "><span class="fi-plus"></span> </div>
```
**Classes:** `paywallLabel` + **2 spaces cuối**

### **Headline**
```html
<h2 itemprop="headline" class="headline t38" style="">
```
**Classes:** `headline`, `t38`

## ✅ Template Match Checklist

- [x] `column` - Match
- [x] `paywall` - Match (conditional)
- [x] `small-12` - Match
- [x] `large-6` / `large-4` - Match (dynamic)
- [x] `small-abs-12` - Match
- [x] `large-abs-6` / `large-abs-4` - Match (dynamic)
- [x] Space cuối trong article class - Match
- [x] `content` - Match
- [x] Empty class trong `<a>` - Match
- [x] `media ` với space cuối - Match
- [x] Empty class trong `<figure>` - Match
- [x] `img` - Match
- [x] `fullwidthTarget` - Match
- [x] `floatingText` - Match
- [x] `labels` - Match
- [x] `paywallLabel  ` với 2 spaces - Match
- [x] `headline` - Match
- [x] `t38` - Match

## 🔍 Lưu ý

1. **Khoảng trắng cuối class** rất quan trọng vì CSS có thể dùng attribute selector
2. **Empty class attributes** (`class=""`) cần giữ nguyên
3. **Format indentation** nên match để dễ debug
4. **Tất cả data attributes** phải có đầy đủ

