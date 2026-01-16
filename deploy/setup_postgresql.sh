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
-- Drop database if exists (for re-run)
DROP DATABASE IF EXISTS $DB_NAME;

-- Drop user if exists (for re-run)
DROP USER IF EXISTS $DB_USER;

-- Create database
CREATE DATABASE $DB_NAME;

-- Create user with CREATEDB privilege (for flexibility)
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD' CREATEDB;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME

-- Grant all privileges on schema
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER SCHEMA public OWNER TO $DB_USER;

-- Grant privileges on all existing tables (if any)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO $DB_USER;

-- Make user superuser for maximum flexibility (optional, can remove if security concern)
-- ALTER USER $DB_USER WITH SUPERUSER;

-- Exit
\q
EOF

echo -e "${GREEN}✅ Database and user created${NC}"
echo ""

# Bước 5: Configure PostgreSQL for easy access
echo -e "${YELLOW}[4/5] Configuring PostgreSQL for easy access...${NC}"

# Find PostgreSQL version and config directory
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
PG_CONF_DIR="/etc/postgresql/${PG_VERSION}/main"
PG_HBA_FILE="${PG_CONF_DIR}/pg_hba.conf"

if [ ! -d "$PG_CONF_DIR" ]; then
    # Try alternative path
    PG_CONF_DIR=$(find /etc/postgresql -name "main" -type d | head -1)
    PG_HBA_FILE="${PG_CONF_DIR}/pg_hba.conf"
fi

if [ -f "$PG_HBA_FILE" ]; then
    # Backup original config
    if [ ! -f "${PG_HBA_FILE}.bak" ]; then
        cp "$PG_HBA_FILE" "${PG_HBA_FILE}.bak"
        echo -e "${GREEN}✅ Backed up pg_hba.conf${NC}"
    fi
    
    # Configure pg_hba.conf for easy local access
    # Allow all local connections with password (md5)
    if ! grep -q "^# Easy access for Flask and crawl scripts" "$PG_HBA_FILE"; then
        cat >> "$PG_HBA_FILE" <<EOF

# Easy access for Flask and crawl scripts
# Allow all local connections with password authentication
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF
        echo -e "${GREEN}✅ Updated pg_hba.conf for easy access${NC}"
    else
        echo -e "${YELLOW}⚠️  pg_hba.conf already configured${NC}"
    fi
    
    # Restart PostgreSQL
    systemctl restart postgresql
    echo -e "${GREEN}✅ PostgreSQL configured and restarted${NC}"
else
    echo -e "${RED}⚠️  Could not find pg_hba.conf at $PG_HBA_FILE${NC}"
    echo -e "${YELLOW}   Please configure manually${NC}"
fi
echo ""

# Bước 6: Create .env file and connection info file
echo -e "${YELLOW}[5/5] Creating .env file and connection info...${NC}"

# Create connection info file (readable by all users)
CONN_INFO_FILE="/tmp/flask_db_connection.txt"
cat > "$CONN_INFO_FILE" <<EOF
# PostgreSQL Database Connection Info
# This file contains database credentials for Flask app and crawl scripts
# You can source this file or copy DATABASE_URL to your .env file

DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME

# Connection details:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# For Python scripts:
# import os
# os.environ['DATABASE_URL'] = 'postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME'

# For command line:
# psql -h localhost -U $DB_USER -d $DB_NAME
EOF

chmod 644 "$CONN_INFO_FILE"
echo -e "${GREEN}✅ Connection info saved to: $CONN_INFO_FILE${NC}"
echo ""

# Create .env file in Flask directory (if exists)
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
    # Make readable by www-data and current user
    chown www-data:www-data "$ENV_FILE" 2>/dev/null || chown $(whoami):$(whoami) "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    echo -e "${GREEN}✅ .env file created at $ENV_FILE${NC}"
else
    echo -e "${YELLOW}⚠️  Flask directory not found: $FLASK_DIR${NC}"
    echo -e "${YELLOW}   Create .env file manually with content from: $CONN_INFO_FILE${NC}"
fi
echo ""

# Display connection info
echo -e "${GREEN}📝 Database Connection Information:${NC}"
echo -e "${YELLOW}   DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME${NC}"
echo -e "${YELLOW}   Full info saved to: $CONN_INFO_FILE${NC}"
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
echo -e "${YELLOW}📋 Connection Examples:${NC}"
echo ""
echo -e "${YELLOW}1. From Python script (crawl script):${NC}"
echo "   import os"
echo "   os.environ['DATABASE_URL'] = 'postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME'"
echo ""
echo -e "${YELLOW}2. From command line:${NC}"
echo "   PGPASSWORD='$DB_PASSWORD' psql -h localhost -U $DB_USER -d $DB_NAME"
echo ""
echo -e "${YELLOW}3. From Flask app:${NC}"
echo "   DATABASE_URL is already in .env file"
echo ""
echo -e "${YELLOW}4. Test connection:${NC}"
echo "   python3 -c \"from app import app, db; app.app_context().push(); print('✅ Connected!')\""
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Install Python dependencies: pip install -r requirements.txt"
echo "2. Run init_database.py: python3 deploy/init_database.py"
echo "3. Start crawling articles and save to database"
echo ""

