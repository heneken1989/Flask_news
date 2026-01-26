# Crawler Service Setup Guide

Hướng dẫn setup systemd service để chạy `crawl_sections_multi_language.py` tự động mỗi giờ trên VPS Linux.

## 📋 Yêu cầu

- Linux VPS (Ubuntu/Debian/CentOS)
- Python virtual environment đã được setup
- PostgreSQL đã được cấu hình
- Quyền root hoặc sudo

## 🚀 Cách 1: Sử dụng Setup Script (Khuyến nghị)

### Bước 1: Chỉnh sửa paths trong script (nếu cần)

Mở file `setup_crawler_service.sh` và chỉnh sửa các biến nếu cần:

```bash
# Nếu user/group khác www-data
export SERVICE_USER="your_user"
export SERVICE_GROUP="your_group"

# Nếu venv ở vị trí khác
export VENV_PATH="/path/to/your/venv"
```

### Bước 2: Chạy setup script

```bash
cd /path/to/GC_HRAI/flask/deploy
sudo bash setup_crawler_service.sh
```

## 🔧 Cách 2: Setup Thủ Công

### Bước 1: Copy service files

```bash
sudo cp deploy/crawl_sections.service /etc/systemd/system/
sudo cp deploy/crawl_sections.timer /etc/systemd/system/
```

### Bước 2: Chỉnh sửa paths trong service file

```bash
sudo nano /etc/systemd/system/crawl_sections.service
```

Cập nhật các paths:
- `WorkingDirectory`: Đường dẫn đến thư mục `flask`
- `ExecStart`: Đường dẫn đến Python venv và script
- `User` và `Group`: User/group để chạy service

### Bước 3: Reload và enable

```bash
sudo systemctl daemon-reload
sudo systemctl enable crawl_sections.timer
sudo systemctl start crawl_sections.timer
```

## 📊 Kiểm tra Service

### Xem timer status

```bash
systemctl status crawl_sections.timer
```

### Xem service logs

```bash
# Xem logs real-time
journalctl -u crawl_sections.service -f

# Xem logs của lần chạy gần nhất
journalctl -u crawl_sections.service -n 100

# Xem logs của hôm nay
journalctl -u crawl_sections.service --since today
```

### Xem lịch chạy

```bash
systemctl list-timers crawl_sections.timer
```

## 🎮 Quản lý Service

### Chạy thủ công (không đợi timer)

```bash
sudo systemctl start crawl_sections.service
```

### Dừng timer (ngừng chạy tự động)

```bash
sudo systemctl stop crawl_sections.timer
```

### Bật lại timer

```bash
sudo systemctl start crawl_sections.timer
```

### Tắt hoàn toàn (disable)

```bash
sudo systemctl disable crawl_sections.timer
sudo systemctl stop crawl_sections.timer
```

### Xóa service (nếu không cần nữa)

```bash
sudo systemctl disable crawl_sections.timer
sudo systemctl stop crawl_sections.timer
sudo rm /etc/systemd/system/crawl_sections.service
sudo rm /etc/systemd/system/crawl_sections.timer
sudo systemctl daemon-reload
```

## ⚙️ Tùy chỉnh Schedule

Nếu muốn chạy với tần suất khác, chỉnh sửa `crawl_sections.timer`:

```ini
[Timer]
# Chạy mỗi 30 phút
OnCalendar=*:0/30

# Chạy mỗi 2 giờ
OnCalendar=0/2:00

# Chạy vào 8h sáng và 8h tối mỗi ngày
OnCalendar=08:00,20:00

# Chạy vào 9h sáng mỗi ngày
OnCalendar=09:00
```

Sau khi chỉnh sửa:

```bash
sudo systemctl daemon-reload
sudo systemctl restart crawl_sections.timer
```

## 🔍 Troubleshooting

### Service không chạy

1. Kiểm tra logs:
   ```bash
   journalctl -u crawl_sections.service -n 50
   ```

2. Kiểm tra paths trong service file:
   ```bash
   sudo systemctl cat crawl_sections.service
   ```

3. Test chạy thủ công:
   ```bash
   sudo systemctl start crawl_sections.service
   journalctl -u crawl_sections.service -f
   ```

### Permission errors

Đảm bảo user trong service file có quyền:
- Đọc/ghi database
- Đọc/ghi files trong project directory
- Chạy Python script

### Database connection errors

Kiểm tra PostgreSQL đang chạy:
```bash
sudo systemctl status postgresql
```

## 📝 Alternative: Cron Job

Nếu không muốn dùng systemd, có thể dùng cron:

```bash
# Mở crontab
crontab -e

# Thêm dòng sau (chạy mỗi giờ)
0 * * * * cd /path/to/GC_HRAI/flask && /path/to/venv/bin/python scripts/crawl_sections_multi_language.py --section all >> /var/log/crawl_sections.log 2>&1
```

## 🎯 Lưu ý

- Service sẽ chạy với user `www-data` (hoặc user bạn chỉ định)
- Đảm bảo user này có quyền truy cập database và files
- Logs được lưu trong systemd journal (dùng `journalctl` để xem)
- Timer có random delay 0-300 giây để tránh load spike

