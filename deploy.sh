#!/bin/bash

# Script để deploy Flask app lên VPS
# Usage: ./deploy.sh

echo "🚀 Starting Flask app deployment..."

# Tạo thư mục logs nếu chưa có
mkdir -p logs

# Kiểm tra virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Tạo thư mục logs
mkdir -p logs

echo "✅ Deployment setup complete!"
echo ""
echo "To run the app:"
echo "  Development: python app.py"
echo "  Production:  gunicorn -c gunicorn_config.py app:app"
echo ""
echo "Or use systemd service (see DEPLOY_VPS.md)"

