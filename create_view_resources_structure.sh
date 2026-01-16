#!/bin/bash

# Script tự động tạo cấu trúc folder view-resources
# Usage: ./create_view_resources_structure.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_DIR="view-resources"

echo -e "${GREEN}📁 Creating view-resources directory structure...${NC}"
echo ""

# Tạo các thư mục
echo -e "${YELLOW}Creating directories...${NC}"

mkdir -p "$BASE_DIR/dachser2/public/sermitsiaq"
mkdir -p "$BASE_DIR/baseview/public/common/ClientAPI"
mkdir -p "$BASE_DIR/baseview/public/common/baseview"
mkdir -p "$BASE_DIR/baseview/public/common/build"
mkdir -p "$BASE_DIR/public/common"

echo -e "${GREEN}✅ Directory structure created${NC}"
echo ""

# Tạo file .gitkeep trong các thư mục rỗng
echo -e "${YELLOW}Creating .gitkeep files...${NC}"

touch "$BASE_DIR/dachser2/public/sermitsiaq/.gitkeep"
touch "$BASE_DIR/baseview/public/common/ClientAPI/.gitkeep"
touch "$BASE_DIR/baseview/public/common/baseview/.gitkeep"
touch "$BASE_DIR/baseview/public/common/build/.gitkeep"
touch "$BASE_DIR/public/common/.gitkeep"

echo -e "${GREEN}✅ .gitkeep files created${NC}"
echo ""

# Hiển thị cấu trúc
echo -e "${GREEN}📂 Directory structure:${NC}"
tree -L 4 "$BASE_DIR" 2>/dev/null || find "$BASE_DIR" -type d | sed 's|[^/]*/| |g'

echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Structure created successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Copy your logo.svg to: $BASE_DIR/dachser2/public/sermitsiaq/"
echo "   2. Copy favicons to: $BASE_DIR/dachser2/public/sermitsiaq/"
echo "   3. Copy JavaScript files to respective directories"
echo "   4. See README.md in view-resources/ for details"
echo ""

