# Home Processing - Final Implementation

## ✅ Quyết định: Dùng `link_home_articles.py` thay vì `process_home()`

### Lý do

**Option 2 đã được chọn vì:**

1. **Loại bỏ duplicate:**
   - `process_home()` và `link_home_articles.py` có nhiều logic trùng lặp
   - Giữ 1 cách duy nhất để process home → dễ maintain

2. **Linh hoạt hơn:**
   - `link_home_articles.py` có dry-run mode
   - Có options để crawl hoặc chỉ link
   - Có thể chạy standalone khi cần

3. **Đầy đủ chức năng:**
   - Crawl home layout (DA và KL)
   - Link articles với layout
   - Match DA ↔ KL (set `canonical_id`) ← ✅ Đã thêm
   - Create missing EN articles
   - Generate sitemaps

### Changes

#### 1. `crawl_sections_multi_language.py`

**Commented `process_home()` calls:**

```python
# Line ~765: args.section == 'home'
if args.section == 'home':
    print("⏭️  Skipping process_home() - will use link_home_articles.py instead")
    print("ℹ️  Home articles will be processed after article details crawl")
    # [COMMENTED] process_home()

# Line ~795: args.section == 'all'
# Then process home last
print("⏭️  Skipping process_home() - will use link_home_articles.py instead")
# [COMMENTED] process_home()
```

**Kept and clarified subprocess:**

```python
# Line ~857-883
# ⚠️ QUAN TRỌNG: Chạy link_home_articles.py để process home articles
# Đây là cách CHÍNH để process home (thay thế process_home())
print("🏠 Processing home articles with link_home_articles.py")
subprocess.run([sys.executable, str(script_path)])
```

#### 2. `link_home_articles.py`

**Already has matching step:**

```python
# Step 1.5: Matching DA and KL home articles
da_articles = Article.query.filter_by(language='da', is_home=True).all()
kl_articles = Article.query.filter_by(language='kl', is_home=True).all()
stats = match_and_link_articles(da_articles, kl_articles)
```

### Flow sau khi optimize

```
crawl_sections_multi_language.py
├── Process sections (erhverv, samfund, kultur, sport, podcasti)
│   ├── crawl_danish_section()
│   ├── crawl_greenlandic_section()
│   ├── match_dk_kl_section_articles()
│   └── translate_dk_section_to_en()
│
├── [SKIPPED] process_home()  ← Không dùng nữa
│
├── Crawl article details (subprocess)
│   └── crawl_article_details_batch.py
│
└── Process home (subprocess)  ← Cách CHÍNH để process home
    └── link_home_articles.py
        ├── Step 0: Crawl home layout (DA)
        ├── Step 1: Process DA home articles
        ├── Step 1.1: Crawl home layout (KL)
        ├── Step 1.2: Process KL home articles
        ├── Step 1.5: Match DA ↔ KL ← ✅ Set canonical_id
        ├── Step 2: Create missing EN articles
        └── Step 3: Generate sitemaps
```

### Khi nào dùng mỗi script?

#### `crawl_sections_multi_language.py` (Main workflow)
```bash
# Crawl tất cả (sections + home)
python crawl_sections_multi_language.py --section all

# Chỉ sections (skip home)
python crawl_sections_multi_language.py --section sections

# Chỉ home
python crawl_sections_multi_language.py --section home
```

#### `link_home_articles.py` (Standalone khi cần)
```bash
# Refresh layout sau khi layout thay đổi
python link_home_articles.py

# Dry-run (không commit DB)
python link_home_articles.py --dry-run

# Chỉ link (không crawl layout)
python link_home_articles.py --skip-crawl-layout
```

### Benefits

✅ **Loại bỏ duplicate logic**
- Không còn 2 cách để process home

✅ **Linh hoạt hơn**
- `link_home_articles.py` có nhiều options hơn
- Có thể chạy standalone khi cần

✅ **Dễ maintain**
- Chỉ cần maintain 1 nơi
- Logic rõ ràng hơn

✅ **Đầy đủ chức năng**
- Có matching step (set `canonical_id`)
- Language switcher DA ↔ KL hoạt động
- Generate sitemaps

### Estimated Time Savings

- Không tiết kiệm thời gian chạy (vẫn phải crawl layout)
- Nhưng code đơn giản hơn, dễ maintain hơn
- Linh hoạt hơn khi cần refresh layout

---

## 🎯 Kết luận

**Option 2 là lựa chọn tốt nhất:**
- Loại bỏ duplicate
- Linh hoạt
- Đầy đủ chức năng
- Dễ maintain

**`link_home_articles.py` là cách CHÍNH để process home articles.**

