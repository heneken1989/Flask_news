# Git Conflict Resolution trên VPS

## Lỗi: pathspec did not match any file(s) known to git

Lỗi này có nghĩa là files không có trong git repository. Hãy chạy các lệnh sau:

```bash
# 1. Kiểm tra git status
git status

# 2. Nếu files là untracked (chưa được add vào git), có 2 cách:

# Cách A: Xóa files nếu không cần
rm copy_css.py deploy.sh

# Cách B: Add files vào git nếu cần giữ
git add copy_css.py deploy.sh
git commit -m "Add copy_css.py and deploy.sh"

# 3. Nếu files đã bị xóa trong git nhưng vẫn còn local:
git rm copy_css.py deploy.sh
git commit -m "Remove copy_css.py and deploy.sh"

# 4. Sau đó pull lại
git pull origin main

# 5. Pop stash
git stash pop
```

## Nếu vẫn còn conflict sau khi pull:

```bash
# Xem files nào đang conflict
git status

# Resolve từng file
git checkout --theirs <file>
# hoặc
git checkout --ours <file>

# Add và commit
git add .
git commit -m "Resolve merge conflicts"

# Pull lại
git pull origin main
```

