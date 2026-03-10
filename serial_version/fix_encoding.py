#!/usr/bin/env python3
"""
Fix encoding issues by replacing Unicode characters with ASCII equivalents
"""

import re
import os
from pathlib import Path

def fix_unicode_in_file(file_path):
    """Replace Unicode characters with ASCII equivalents"""
    
    unicode_map = {
        '✅': 'SUCCESS',
        '❌': 'FAILED',
        '🚀': 'STARTING',
        '⚡': 'RUNNING',
        '📊': 'RESULTS',
        '📁': 'FOLDER',
        '⚙️': 'SETTINGS',
        '🔧': 'TOOLS',
        '🗂️': 'MAPPING',
        '🔄': 'REFRESH',
        '🏭': 'PDK'
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace Unicode characters
        for unicode_char, ascii_replacement in unicode_map.items():
            content = content.replace(unicode_char, ascii_replacement)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed encoding in: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_all_files():
    """Fix encoding in all Python files"""
    
    files_to_fix = [
        'subprocess_cli.py',
        'batch_processor.py',
        'test_batch.py',
        'subprocess_gui.py'
    ]
    
    current_dir = Path(__file__).parent
    
    for filename in files_to_fix:
        file_path = current_dir / filename
        if file_path.exists():
            fix_unicode_in_file(file_path)
        else:
            print(f"File not found: {filename}")

if __name__ == "__main__":
    print("Fixing Unicode encoding issues...")
    fix_all_files()
    print("Encoding fix complete!")