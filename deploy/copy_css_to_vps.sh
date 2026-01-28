#!/bin/bash

# Copy CSS và template files lên VPS
# Usage: ./copy_css_to_vps.sh

cd /Users/hien/Desktop/Projects/GC_HRAI

# Copy file CSS mới
scp flask/static/css/article_images.css root@31.97.111.177:/var/www/flask/nococo/static/css/

# Copy template head.html (đã thêm import CSS)
scp flask/templates/partials/head.html root@31.97.111.177:/var/www/flask/nococo/templates/partials/

# Copy template main_body.html (đã thêm class row-articles)
scp flask/templates/partials/main_body.html root@31.97.111.177:/var/www/flask/nococo/templates/partials/

# Copy grid.scss (nếu cần compile trên VPS)
scp flask/static/css/components/grid.scss root@31.97.111.177:/var/www/flask/nococo/static/css/components/

echo "✅ All files copied successfully!"

