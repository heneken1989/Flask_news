#!/bin/bash

# Script setup PostgreSQL cho Flask app trên VPS
# Usage: sudo ./setup_postgresql.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Kiểm tra quyền root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Thông tin cấu hình
DB_NAME="flask_news"
DB_USER="flask_user"
DB_PASSWORD=""
FLASK_DIR="/var/www/flask/nococo"

echo -e "${GREEN}🗄️  Setting up PostgreSQL for Flask app${NC}"
echo ""

# Bước 1: Install PostgreSQL
echo -e "${YELLOW}[1/5] Installing PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    apt-get update
    apt-get install -y postgresql postgresql-contrib
    echo -e "${GREEN}✅ PostgreSQL installed${NC}"
else
    echo -e "${GREEN}✅ PostgreSQL already installed${NC}"
fi
echo ""

# Bước 2: Start PostgreSQL service
echo -e "${YELLOW}[2/5] Starting PostgreSQL service...${NC}"
systemctl start postgresql
systemctl enable postgresql
echo -e "${GREEN}✅ PostgreSQL service started${NC}"
echo ""

# Bước 3: Generate secure password
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo -e "${YELLOW}Generated password: ${DB_PASSWORD}${NC}"
    echo -e "${RED}⚠️  SAVE THIS PASSWORD! You'll need it for DATABASE_URL${NC}"
    echo ""
fi

# Bước 4: Create database and user
echo -e "${YELLOW}[3/5] Creating database and user...${NC}"
sudo -u postgres psql <<EOF
-- Create database
CREATE DATABASE $DB_NAME;

-- Create user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

-- Exit
\q
EOF

echo -e "${GREEN}✅ Database and user created${NC}"
echo ""

# Bước 5: Configure PostgreSQL for remote/local access
echo -e "${YELLOW}[4/5] Configuring PostgreSQL...${NC}"

# Backup original config
if [ ! -f /etc/postgresql/*/main/pg_hba.conf.bak ]; then
    cp /etc/postgresql/*/main/pg_hba.conf /etc/postgresql/*/main/pg_hba.conf.bak
fi

# Allow local connections (already default, but ensure it's there)
if ! grep -q "local.*all.*all.*md5" /etc/postgresql/*/main/pg_hba.conf; then
    echo "local   all             all                                     md5" >> /etc/postgresql/*/main/pg_hba.conf
fi

# Restart PostgreSQL
systemctl restart postgresql
echo -e "${GREEN}✅ PostgreSQL configured${NC}"
echo ""

# Bước 6: Create .env file for Flask app
echo -e "${YELLOW}[5/5] Creating .env file for Flask app...${NC}"
if [ -d "$FLASK_DIR" ]; then
    ENV_FILE="$FLASK_DIR/.env"
    cat > "$ENV_FILE" <<EOF
# PostgreSQL Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME

# Flask Configuration
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=$(openssl rand -hex 32)
EOF
    chown www-data:www-data "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo -e "${GREEN}✅ .env file created at $ENV_FILE${NC}"
    echo ""
    echo -e "${YELLOW}📝 Database credentials saved to: $ENV_FILE${NC}"
    echo -e "${YELLOW}   DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME${NC}"
else
    echo -e "${RED}⚠️  Flask directory not found: $FLASK_DIR${NC}"
    echo -e "${YELLOW}   Please create .env file manually with:${NC}"
    echo -e "${YELLOW}   DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME${NC}"
fi
echo ""

# Bước 7: Test connection
echo -e "${YELLOW}[6/6] Testing database connection...${NC}"
sudo -u postgres psql -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database connection successful${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}✅ PostgreSQL setup completed!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Update app.py to use DATABASE_URL from .env"
echo "2. Install Python dependencies: pip install -r requirements.txt"
echo "3. Run migrations: python3 -c 'from app import app, db; app.app_context().push(); db.create_all()'"
echo "4. Start crawling articles and save to database"
echo ""

