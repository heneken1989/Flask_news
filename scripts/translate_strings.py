#!/usr/bin/env python3
"""
Script để tự động dịch strings trong file .po bằng Google Translate
Sử dụng: python scripts/translate_strings.py
"""

import os
import sys
import re
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("❌ Error: deep-translator not installed")
    print("   Run: pip install deep-translator")
    sys.exit(1)

# Language mapping - Google Translate supported languages
LANG_MAP = {
    'en': 'en',  # English
    'da': 'da',  # Danish
    # 'kl': 'kl',  # Greenlandic - NOT supported by Google Translate
}

# Languages not supported by Google Translate (need manual translation)
UNSUPPORTED_LANGUAGES = ['kl']  # Greenlandic

# Translation service - chỉ dùng deep_translator (đã loại bỏ googletrans)

def parse_po_file(po_file_path):
    """Parse .po file và extract msgid/msgstr pairs (skip metadata)"""
    entries = []
    current_entry = None
    in_msgid = False
    in_msgstr = False
    header_passed = False
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        original_line = line
        line = line.rstrip()
        
        # Skip comments and empty lines (but track when we pass header)
        if line.startswith('#') or not line.strip():
            if line.startswith('#') and 'POT-Creation-Date' in line:
                header_passed = True
            continue
        
        # Start of new entry (only after header)
        if line.startswith('msgid '):
            # Save previous entry
            if current_entry and current_entry.get('msgid'):
                entries.append(current_entry)
            
            # Start new entry
            current_entry = {
                'msgid': '',
                'msgstr': '',
                'fuzzy': False,
                'original_lines': []
            }
            in_msgid = True
            in_msgstr = False
            
            # Extract msgid
            msgid = line[6:].strip()
            if msgid.startswith('"') and msgid.endswith('"'):
                current_entry['msgid'] = msgid[1:-1]
                current_entry['original_lines'].append(original_line)
            elif msgid == '""':
                # Empty msgid (header metadata) - skip
                current_entry = None
                in_msgid = False
                continue
        
        # Continue msgid (multi-line)
        elif in_msgid and line.startswith('"') and line.endswith('"'):
            if current_entry:
                current_entry['msgid'] += line[1:-1]
                current_entry['original_lines'].append(original_line)
        
        # msgstr
        elif line.startswith('msgstr '):
            if current_entry:
                in_msgid = False
                in_msgstr = True
                msgstr = line[7:].strip()
                if msgstr.startswith('"') and msgstr.endswith('"'):
                    current_entry['msgstr'] = msgstr[1:-1]
                elif msgstr == '""':
                    current_entry['msgstr'] = ''
                current_entry['original_lines'].append(original_line)
        
        # Continue msgstr (multi-line)
        elif in_msgstr and line.startswith('"') and line.endswith('"'):
            if current_entry:
                current_entry['msgstr'] += line[1:-1]
                current_entry['original_lines'].append(original_line)
        
        # Check for fuzzy flag
        elif line.startswith('#, fuzzy'):
            if current_entry:
                current_entry['fuzzy'] = True
    
    # Save last entry
    if current_entry and current_entry.get('msgid'):
        entries.append(current_entry)
    
    return entries

def translate_text(text, source_lang='da', target_lang='en'):
    """Translate text using Google Translate"""
    if not text or not text.strip():
        return text
    
    # Check if language is supported
    if target_lang in UNSUPPORTED_LANGUAGES:
        print(f"   ⚠️  Language '{target_lang}' not supported by Google Translate")
        return text
    
    try:
        # Chỉ dùng deep_translator (đã loại bỏ googletrans)
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"   ⚠️  Translation error: {e}")
        return text

def update_po_file(po_file_path, source_lang='da', target_lang='en'):
    """Update .po file với translations"""
    print(f"📝 Processing: {po_file_path}")
    print(f"   Source: {source_lang} → Target: {target_lang}")
    
    # Check if language is supported
    if target_lang in UNSUPPORTED_LANGUAGES:
        print(f"   ⚠️  Language '{target_lang}' is not supported by Google Translate")
        print(f"   Please translate manually or use a different translation service")
        return 0
    
    # Parse entries
    entries = parse_po_file(po_file_path)
    
    if not entries:
        print(f"   ℹ️  No translatable strings found (only metadata)")
        return 0
    
    print(f"   Found {len(entries)} translatable strings")
    
    translated_count = 0
    skipped_count = 0
    
    # Create translation map
    translation_map = {}
    
    for entry in entries:
        msgid = entry['msgid']
        msgstr = entry['msgstr']
        
        # Skip nếu đã có translation (và không phải fuzzy) hoặc msgid rỗng
        if not msgid or not msgid.strip():
            skipped_count += 1
            continue
        
        if msgstr and msgstr.strip() and not entry['fuzzy']:
            skipped_count += 1
            continue
        
        # Translate
        print(f"   Translating: '{msgid[:60]}...'")
        translated = translate_text(msgid, source_lang, target_lang)
        
        if translated and translated != msgid and translated.strip():
            translation_map[msgid] = translated
            translated_count += 1
        else:
            skipped_count += 1
        
        # Rate limiting
        time.sleep(0.5)  # Avoid hitting rate limits
    
    # Read original file and update msgstr lines
    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    output_lines = []
    current_msgid = ''
    in_msgid = False
    in_msgstr = False
    msgstr_start_idx = None
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Detect msgid
        if line_stripped.startswith('msgid '):
            in_msgid = True
            in_msgstr = False
            msgid_content = line_stripped[6:].strip()
            if msgid_content.startswith('"') and msgid_content.endswith('"'):
                current_msgid = msgid_content[1:-1]
            elif msgid_content == '""':
                current_msgid = ''
            else:
                current_msgid = ''
            output_lines.append(line)
            i += 1
        
        # Continue msgid (multi-line)
        elif in_msgid and line_stripped.startswith('"') and line_stripped.endswith('"'):
            if current_msgid:
                current_msgid += line_stripped[1:-1]
            else:
                current_msgid = line_stripped[1:-1]
            output_lines.append(line)
            i += 1
        
        # Detect msgstr
        elif line_stripped.startswith('msgstr '):
            in_msgid = False
            in_msgstr = True
            msgstr_start_idx = len(output_lines)
            
            # Check if we have translation for this msgid
            if current_msgid in translation_map:
                translated = translation_map[current_msgid]
                output_lines.append(f'msgstr "{translated}"\n')
            else:
                output_lines.append(line)
            i += 1
        
        # Continue msgstr (multi-line) - skip if we replaced it
        elif in_msgstr and line_stripped.startswith('"') and line_stripped.endswith('"'):
            # Only keep if we didn't replace msgstr
            if current_msgid not in translation_map:
                output_lines.append(line)
            i += 1
        
        # End of entry
        elif line_stripped == '' and in_msgstr:
            in_msgstr = False
            output_lines.append(line)
            i += 1
        
        # Regular line
        else:
            output_lines.append(line)
            i += 1
    
    # Write updated file
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
    
    print(f"   ✅ Translated: {translated_count}, Skipped: {skipped_count}")
    return translated_count

def main():
    """Main function"""
    translations_dir = Path(__file__).parent.parent / 'translations'
    
    if not translations_dir.exists():
        print(f"❌ Translations directory not found: {translations_dir}")
        print("   Run './scripts/setup_i18n.sh' first to create translation files")
        return
    
    # Check if messages.pot exists (need to extract strings first)
    pot_file = Path(__file__).parent.parent / 'messages.pot'
    if not pot_file.exists():
        print(f"⚠️  messages.pot not found. Extracting strings first...")
        print(f"   Run: pybabel extract -F babel.cfg -k _ -o messages.pot .")
        print(f"   Then run: pybabel update -i messages.pot -d translations")
        return
    
    # Source language (Danish)
    source_lang = 'da'
    
    # Target languages (only supported ones)
    target_langs = ['en']  # Only English is supported by Google Translate
    
    # Check for unsupported languages
    unsupported_files = []
    for lang in ['kl']:  # Greenlandic
        po_file = translations_dir / lang / 'LC_MESSAGES' / 'messages.po'
        if po_file.exists():
            unsupported_files.append((lang, po_file))
    
    # Translate supported languages
    for target_lang in target_langs:
        po_file = translations_dir / target_lang / 'LC_MESSAGES' / 'messages.po'
        
        if not po_file.exists():
            print(f"⚠️  File not found: {po_file}")
            print(f"   Run: pybabel init -i messages.pot -d translations -l {target_lang}")
            continue
        
        print(f"\n🌐 Translating to {target_lang}...")
        translated = update_po_file(po_file, source_lang, target_lang)
        
        if translated == 0:
            print(f"   ℹ️  No strings to translate. Make sure you have:")
            print(f"      1. Added _('...') in your code/templates")
            print(f"      2. Run: pybabel extract -F babel.cfg -k _ -o messages.pot .")
            print(f"      3. Run: pybabel update -i messages.pot -d translations")
    
    # Warn about unsupported languages
    if unsupported_files:
        print(f"\n⚠️  Unsupported languages (need manual translation):")
        for lang, po_file in unsupported_files:
            print(f"   - {lang} ({po_file})")
        print(f"   Google Translate does not support these languages.")
        print(f"   Please translate manually or use a different service.")
    
    print("\n✅ Translation complete!")
    print("   Next step: Run 'pybabel compile -d translations' to compile translations")

if __name__ == '__main__':
    main()

