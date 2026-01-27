#!/usr/bin/env python3
"""
Script để kiểm tra trạng thái Chrome trên VPS
- Kiểm tra Chrome processes đang chạy
- Kiểm tra Chrome binary location
- Kiểm tra Chrome version
- Kiểm tra dependencies
"""

import subprocess
import os
import sys

def check_chrome_processes():
    """Kiểm tra Chrome processes đang chạy"""
    print("=" * 60)
    print("1. Checking Chrome/Chromium processes...")
    print("=" * 60)
    
    try:
        # Tìm tất cả Chrome/Chromium processes
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        chrome_processes = []
        for line in result.stdout.split('\n'):
            if any(keyword in line.lower() for keyword in ['chrome', 'chromium', 'chromedriver']):
                chrome_processes.append(line)
        
        if chrome_processes:
            print(f"⚠️  Found {len(chrome_processes)} Chrome/Chromium processes:")
            for proc in chrome_processes:
                print(f"   {proc}")
            
            # Lấy PID
            pids = []
            for proc in chrome_processes:
                parts = proc.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids.append(pid)
                    except:
                        pass
            
            if pids:
                print(f"\n   PIDs: {', '.join(map(str, pids))}")
                print(f"\n   💡 To kill all Chrome processes:")
                print(f"      sudo kill -9 {' '.join(map(str, pids))}")
        else:
            print("✅ No Chrome/Chromium processes running")
        
        return chrome_processes
        
    except Exception as e:
        print(f"❌ Error checking processes: {e}")
        return []


def check_chrome_binary():
    """Kiểm tra Chrome binary location"""
    print("\n" + "=" * 60)
    print("2. Checking Chrome/Chromium binary location...")
    print("=" * 60)
    
    possible_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/snap/bin/chromium',
        '/usr/bin/google-chrome-stable',
        '/opt/google/chrome/chrome',
    ]
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            found_paths.append(path)
            # Check if executable
            if os.access(path, os.X_OK):
                print(f"✅ Found executable: {path}")
                # Get version
                try:
                    result = subprocess.run(
                        [path, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        print(f"   Version: {result.stdout.strip()}")
                except:
                    pass
            else:
                print(f"⚠️  Found but not executable: {path}")
    
    if not found_paths:
        print("❌ Chrome/Chromium binary not found in common locations")
        print("\n   💡 To install Chrome:")
        print("      sudo apt-get update")
        print("      sudo apt-get install -y chromium-browser")
        print("   Or:")
        print("      sudo apt-get install -y google-chrome-stable")
    
    return found_paths


def check_chrome_dependencies():
    """Kiểm tra Chrome dependencies"""
    print("\n" + "=" * 60)
    print("3. Checking Chrome dependencies...")
    print("=" * 60)
    
    required_libs = [
        'libnss3.so',
        'libatk-1.0.so',
        'libatk-bridge-2.0.so',
        'libcups.so',
        'libdrm.so',
        'libxkbcommon.so',
        'libxcomposite.so',
        'libxdamage.so',
        'libxfixes.so',
        'libxrandr.so',
        'libgbm.so',
        'libasound.so',
    ]
    
    missing_libs = []
    for lib in required_libs:
        result = subprocess.run(
            ['ldconfig', '-p'],
            capture_output=True,
            text=True
        )
        if lib in result.stdout:
            print(f"✅ {lib}")
        else:
            print(f"❌ {lib} - MISSING")
            missing_libs.append(lib)
    
    if missing_libs:
        print(f"\n⚠️  Missing {len(missing_libs)} libraries")
        print("   💡 To install dependencies:")
        print("      sudo apt-get install -y \\")
        print("        libnss3 \\")
        print("        libatk1.0-0 \\")
        print("        libatk-bridge2.0-0 \\")
        print("        libcups2 \\")
        print("        libdrm2 \\")
        print("        libxkbcommon0 \\")
        print("        libxcomposite1 \\")
        print("        libxdamage1 \\")
        print("        libxfixes3 \\")
        print("        libxrandr2 \\")
        print("        libgbm1 \\")
        print("        libasound2")
    
    return missing_libs


def check_user_data_dir():
    """Kiểm tra user_data_dir"""
    print("\n" + "=" * 60)
    print("4. Checking user_data_dir...")
    print("=" * 60)
    
    user_data_dir = "/var/www/flask/nococo/user_data"
    
    if os.path.exists(user_data_dir):
        print(f"✅ user_data_dir exists: {user_data_dir}")
        
        # Check permissions
        stat_info = os.stat(user_data_dir)
        print(f"   Owner: {stat_info.st_uid}")
        print(f"   Group: {stat_info.st_gid}")
        print(f"   Permissions: {oct(stat_info.st_mode)}")
        
        # Check if writable
        if os.access(user_data_dir, os.W_OK):
            print("   ✅ Writable")
        else:
            print("   ❌ Not writable")
        
        # Count files
        try:
            file_count = sum(len(files) for _, _, files in os.walk(user_data_dir))
            print(f"   Files: {file_count}")
        except:
            pass
    else:
        print(f"ℹ️  user_data_dir does not exist: {user_data_dir}")
        print("   (Will be created on first run)")


def check_display():
    """Kiểm tra DISPLAY variable"""
    print("\n" + "=" * 60)
    print("5. Checking DISPLAY environment...")
    print("=" * 60)
    
    display = os.environ.get('DISPLAY')
    if display:
        print(f"⚠️  DISPLAY is set: {display}")
        print("   (Should be unset for headless mode)")
    else:
        print("✅ DISPLAY is not set (good for headless)")


def main():
    print("\n" + "=" * 60)
    print("Chrome/Chromium Status Check on VPS")
    print("=" * 60 + "\n")
    
    processes = check_chrome_processes()
    binaries = check_chrome_binary()
    missing_libs = check_chrome_dependencies()
    check_user_data_dir()
    check_display()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if processes:
        print("⚠️  Chrome processes are running - may cause conflicts")
        print("   Recommendation: Kill existing processes before running crawler")
    
    if not binaries:
        print("❌ Chrome/Chromium binary not found")
        print("   Recommendation: Install Chrome/Chromium")
    
    if missing_libs:
        print(f"⚠️  Missing {len(missing_libs)} required libraries")
        print("   Recommendation: Install missing dependencies")
    
    if not processes and binaries and not missing_libs:
        print("✅ All checks passed!")
        print("   Chrome should be able to start")
    
    print()


if __name__ == '__main__':
    main()

