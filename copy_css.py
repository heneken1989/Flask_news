#!/usr/bin/env python3
"""
Script to copy CSS files from frontend1 to flask-article-project
"""
import shutil
import os
from pathlib import Path

# Paths
source_dir = Path(__file__).parent.parent / 'frontend1' / 'src' / 'views' / 'FaceRecpush' / 'css'
target_dir = Path(__file__).parent / 'static' / 'css'

# Create target directory if it doesn't exist
target_dir.mkdir(parents=True, exist_ok=True)

# CSS files to copy
css_files = ['grid.css', 'main.css', 'colors.css', 'print.css', 'foundation-icons.css', 'sermitsiaq.css']
font_files = ['foundation-icons.ttf', 'foundation-icons.woff']

print(f"Copying CSS files from {source_dir} to {target_dir}...")

# Copy CSS files
for css_file in css_files:
    source_file = source_dir / css_file
    target_file = target_dir / css_file
    if source_file.exists():
        shutil.copy2(source_file, target_file)
        print(f"✓ Copied {css_file}")
    else:
        print(f"✗ {css_file} not found")

# Copy font files
for font_file in font_files:
    source_file = source_dir / font_file
    target_file = target_dir / font_file
    if source_file.exists():
        shutil.copy2(source_file, target_file)
        print(f"✓ Copied {font_file}")
    else:
        print(f"✗ {font_file} not found")

print("\nDone!")

