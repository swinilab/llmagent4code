#!/usr/bin/env python3
import os
import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace from app. with from oms_backend.app.
    new_content = content.replace('from app.', 'from oms_backend.app.')
    # Also replace import app. (though unlikely)
    new_content = new_content.replace('import app.', 'import oms_backend.app.')
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed: {filepath}")
    else:
        print(f"No change: {filepath}")

def main():
    root = 'oms_backend/app'
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                fix_file(filepath)

if __name__ == '__main__':
    main()