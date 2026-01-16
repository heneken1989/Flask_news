#!/usr/bin/env python3
"""
Script để tách header và footer từ 1.html
"""

def extract_header_footer():
    input_file = 'templates/1.html'
    
    # Đọc file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Tìm vị trí header và footer
    header_start = None
    header_end = None
    footer_start = None
    footer_end = None
    
    for i, line in enumerate(lines, 1):
        if '<header class="pageElement pageHeader">' in line:
            header_start = i - 1  # 0-based index
        if '</header>' in line and header_start is not None:
            header_end = i
        if '<footer class="page">' in line:
            footer_start = i - 1
        if '</footer>' in line and footer_start is not None:
            footer_end = i
    
    # Extract header
    if header_start and header_end:
        header_content = ''.join(lines[header_start:header_end])
        with open('templates/partials/header.html', 'w', encoding='utf-8') as f:
            f.write(header_content)
        print(f"✅ Header extracted: lines {header_start+1}-{header_end}")
    
    # Extract footer
    if footer_start and footer_end:
        footer_content = ''.join(lines[footer_start:footer_end])
        with open('templates/partials/footer.html', 'w', encoding='utf-8') as f:
            f.write(footer_content)
        print(f"✅ Footer extracted: lines {footer_start+1}-{footer_end}")
    
    # Extract head section (từ đầu đến </head>)
    head_end = None
    for i, line in enumerate(lines):
        if '</head>' in line:
            head_end = i + 1
            break
    
    if head_end:
        head_content = ''.join(lines[0:head_end])
        with open('templates/partials/head.html', 'w', encoding='utf-8') as f:
            f.write(head_content)
        print(f"✅ Head extracted: lines 1-{head_end}")

if __name__ == '__main__':
    extract_header_footer()

