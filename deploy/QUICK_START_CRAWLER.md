# 🚀 Hướng Dẫn Nhanh: Chạy Crawler Mỗi Giờ

## Cách 1: Sử dụng Setup Script (Khuyến nghị - Tự động)

### Bước 1: Chạy setup script

```bash
cd /path/to/GC_HRAI/flask/deploy
sudo bash setup_crawler_service.sh
```

Script sẽ tự động:
- ✅ Kiểm tra và cài Chrome/Chromium nếu chưa có
- ✅ Tự động detect paths (venv, project directory)
- ✅ Copy service files vào `/etc/systemd/system/`
- ✅ Enable và start timer
- ✅ Hiển thị status

### Bước 2: Kiểm tra đã chạy thành công

```bash
# Xem timer status
systemctl status crawl_sections.timer

# Xem lịch chạy tiếp theo
systemctl list-timers crawl_sections.timer

# Xem logs
journalctl -u crawl_sections.service -f
```

## Cách 2: Setup Thủ Công

### Bước 1: Copy service files

```bash
cd /path/to/GC_HRAI/flask/deploy
sudo cp crawl_sections.service /etc/systemd/system/
sudo cp crawl_sections.timer /etc/systemd/system/
```

### Bước 2: Chỉnh sửa paths trong service file

```bash
sudo nano /etc/systemd/system/crawl_sections.service
```

Cập nhật các paths:
- `WorkingDirectory=/path/to/GC_HRAI/flask` → Đường dẫn thực tế đến thư mục `flask`
- `ExecStart=/path/to/venv/bin/python ...` → Đường dẫn thực tế đến Python venv
- `User=www-data` → User của bạn (nếu khác)
- `Group=www-data` → Group của bạn (nếu khác)

### Bước 3: Reload và enable

```bash
sudo systemctl daemon-reload
sudo systemctl enable crawl_sections.timer
sudo systemctl start crawl_sections.timer
```

## 📊 Kiểm Tra Service

### Xem timer status
```bash
systemctl status crawl_sections.timer
```

### Xem logs real-time
```bash
journalctl -u crawl_sections.service -f
```

### Xem logs của lần chạy gần nhất
```bash
journalctl -u crawl_sections.service -n 100
```

### Xem lịch chạy tiếp theo
```bash
systemctl list-timers crawl_sections.timer
```

## 🎮 Quản Lý Service

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

## ⚙️ Tùy Chỉnh Schedule

Nếu muốn chạy với tần suất khác, chỉnh sửa `crawl_sections.timer`:

```bash
sudo nano /etc/systemd/system/crawl_sections.timer
```

Các tùy chọn:

```ini
[Timer]
# Chạy mỗi giờ (mặc định)
OnCalendar=hourly

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

### Lỗi "Chrome not found"

Chạy script cài Chrome:
```bash
cd /path/to/GC_HRAI/flask/deploy
sudo bash install_chrome.sh
```

### Permission errors

Đảm bảo user trong service file có quyền:
- Đọc/ghi database
- Đọc/ghi files trong project directory
- Chạy Python script

## 📝 Alternative: Cron Job

Nếu không muốn dùng systemd, có thể dùng cron:

```bash
# Mở crontab
crontab -e

# Thêm dòng sau (chạy mỗi giờ)
0 * * * * cd /path/to/GC_HRAI/flask && /path/to/venv/bin/python scripts/crawl_sections_multi_language.py --section all >> /var/log/crawl_sections.log 2>&1
```

Xem file `cron_example.txt` để biết thêm các tùy chọn schedule khác.

## ✅ Sau Khi Setup

Service sẽ tự động:
1. ✅ Chạy `crawl_sections_multi_language.py --section all` mỗi giờ
2. ✅ Crawl tất cả sections (erhverv, samfund, kultur, sport, podcasti) và home
3. ✅ Tự động crawl article details sau khi crawl sections
4. ✅ Tự động chạy `link_home_articles.py` sau khi crawl details

## 📊 Kiểm Tra Kết Quả

```bash
# Xem logs của lần chạy gần nhất
journalctl -u crawl_sections.service -n 200

# Xem logs của hôm nay
journalctl -u crawl_sections.service --since today

# Xem logs real-time khi service đang chạy
journalctl -u crawl_sections.service -f
```

