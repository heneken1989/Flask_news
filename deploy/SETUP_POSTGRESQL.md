# 🗄️ Hướng dẫn Setup PostgreSQL trên VPS

## Cách 1: Dùng Script Tự Động (Khuyến nghị)

### Bước 1: Upload script lên VPS
```bash
# Từ máy local
scp flask/deploy/setup_postgresql.sh root@your-vps:/tmp/
```

### Bước 2: Chạy script trên VPS
```bash
# SSH vào VPS
ssh root@your-vps

# Chạy script
chmod +x /tmp/setup_postgresql.sh
sudo /tmp/setup_postgresql.sh
```

Script sẽ tự động:
- ✅ Install PostgreSQL
- ✅ Tạo database `flask_news`
- ✅ Tạo user `flask_user` với password ngẫu nhiên
- ✅ Cấu hình permissions
- ✅ Tạo file `.env` với DATABASE_URL

**⚠️ Lưu ý:** Script sẽ hiển thị password được generate. Hãy lưu lại!

---

## Cách 2: Setup Thủ Công

### Bước 1: Install PostgreSQL
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
```

### Bước 2: Start PostgreSQL
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Bước 3: Tạo Database và User
```bash
sudo -u postgres psql
```

Trong PostgreSQL shell:
```sql
-- Tạo database
CREATE DATABASE flask_news;

-- Tạo user
CREATE USER flask_user WITH PASSWORD 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE flask_news TO flask_user;

-- Connect to database
\c flask_news

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO flask_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO flask_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO flask_user;

-- Exit
\q
```

### Bước 4: Tạo file .env
```bash
cd /var/www/flask/nococo
nano .env
```

Thêm vào file:
```env
DATABASE_URL=postgresql://flask_user:your_secure_password_here@localhost/flask_news
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=your_secret_key_here
```

Lưu file và set permissions:
```bash
chown www-data:www-data .env
chmod 600 .env
```

---

## Bước 5: Khởi tạo Database Tables

### Cách 1: Dùng script Python
```bash
cd /var/www/flask/nococo
python3 deploy/init_database.py
```

### Cách 2: Dùng Python shell
```bash
cd /var/www/flask/nococo
python3
```

```python
from app import app, db
from database import Article, Category, CrawlLog

with app.app_context():
    db.create_all()
    print("✅ Tables created!")
```

---

## Kiểm tra kết nối

```bash
# Test connection từ command line
sudo -u postgres psql -d flask_news -c "SELECT version();"

# Hoặc test từ Python
python3 -c "from app import app, db; app.app_context().push(); print('✅ Connected!')"
```

---

## Troubleshooting

### Lỗi: "password authentication failed"
```bash
# Kiểm tra pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Đảm bảo có dòng:
local   all             all                                     md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Lỗi: "permission denied"
```bash
# Kiểm tra user có quyền truy cập database
sudo -u postgres psql -d flask_news -c "\du"

# Nếu cần, grant lại quyền
sudo -u postgres psql -d flask_news -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO flask_user;"
```

### Lỗi: "module 'psycopg2' not found"
```bash
# Install psycopg2
pip3 install psycopg2-binary

# Hoặc nếu dùng virtualenv
source venv/bin/activate
pip install psycopg2-binary
```

---

## Backup Database

```bash
# Backup
sudo -u postgres pg_dump flask_news > backup_$(date +%Y%m%d).sql

# Restore
sudo -u postgres psql flask_news < backup_20250116.sql
```

---

## Security Notes

1. **Đổi password mặc định** của user `postgres`:
```bash
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'new_secure_password';
```

2. **Chỉ cho phép local connections** (mặc định đã an toàn)

3. **Backup .env file** - chứa password database

4. **Không commit .env** vào Git

