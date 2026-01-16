# 🧪 Test Data từ Database

## Kiểm tra data

```bash
# Test xem data có đúng không
python3 scripts/test_data.py

# Check database
python3 scripts/check_database.py
```

## Chạy Flask app để xem trên browser

```bash
# Start Flask app
python3 app.py

# Hoặc với gunicorn (production)
gunicorn -c gunicorn_config.py app:app
```

Sau đó truy cập: **http://localhost:5000/**

## Kiểm tra

1. ✅ **50 articles** được hiển thị
2. ✅ **Pattern 2-3-2-3-2-3...** đúng (hàng 1: 2 articles, hàng 2: 3 articles, ...)
3. ✅ **Hình ảnh** hiển thị đúng (từ link CDN)
4. ✅ **Title, URL, Paywall** hiển thị đúng

## Nếu không thấy data

1. Kiểm tra database connection:
```bash
python3 -c "from app import app, db; app.app_context().push(); from database import Article; print(f'Articles: {Article.query.count()}')"
```

2. Kiểm tra view có lấy data:
```python
# Trong views/article_views.py, index() function
# Đảm bảo có: articles = Article.query.order_by(Article.display_order.asc()).limit(50).all()
```

3. Check logs trong terminal khi chạy Flask app

