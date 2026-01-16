# 🔄 Restart Service trên VPS

## Service Name
```
flask-nococo
```

## Các lệnh restart

### 1. **Restart service** (recommended)
```bash
sudo systemctl restart flask-nococo
```

### 2. **Reload service** (nếu chỉ thay đổi code, không thay đổi config)
```bash
sudo systemctl reload flask-nococo
```

### 3. **Stop và Start lại**
```bash
sudo systemctl stop flask-nococo
sudo systemctl start flask-nococo
```

## Kiểm tra status

### **Xem status**
```bash
sudo systemctl status flask-nococo
```

### **Xem logs real-time**
```bash
sudo journalctl -u flask-nococo -f
```

### **Xem logs gần đây**
```bash
sudo journalctl -u flask-nococo -n 50
```

## Sau khi update code

### **Workflow đầy đủ:**
```bash
# 1. SSH vào VPS
ssh root@your-vps-ip

# 2. Pull code mới (nếu dùng Git)
cd /var/www/flask/nococo
sudo -u www-data git pull origin main

# 3. Install dependencies mới (nếu có)
cd /var/www/flask/nococo
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart service
sudo systemctl restart flask-nococo

# 5. Kiểm tra status
sudo systemctl status flask-nococo
```

## Troubleshooting

### **Service không start**
```bash
# Xem logs chi tiết
sudo journalctl -u flask-nococo -n 100

# Kiểm tra config
sudo systemctl cat flask-nococo

# Test chạy thủ công
cd /var/www/flask/nococo
source venv/bin/activate
gunicorn -c gunicorn_config.py app:app
```

### **Service bị crash liên tục**
```bash
# Xem logs
sudo journalctl -u flask-nococo -n 100

# Kiểm tra database connection
cd /var/www/flask/nococo
source venv/bin/activate
python3 -c "from app import app, db; app.app_context().push(); print('✅ DB OK')"

# Kiểm tra permissions
ls -la /var/www/flask/nococo
```

## Quick Commands

```bash
# Restart
sudo systemctl restart flask-nococo

# Status
sudo systemctl status flask-nococo

# Logs
sudo journalctl -u flask-nococo -f

# Enable (auto-start on boot)
sudo systemctl enable flask-nococo

# Disable (không auto-start)
sudo systemctl disable flask-nococo
```

