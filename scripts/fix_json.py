#!/usr/bin/env python3
"""
JSON Fixer for MASTER.json
Diagnoses and fixes JSON syntax errors
"""

import json
import sys
import os

def fix_master_json():
    filepath = 'data/MASTER.json'
    
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found")
        return False
    
    # Read the file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return False
    
    print(f"File length: {len(content)} characters")
    print(f"Lines: {len(content.splitlines())}")
    
    # Look for common corruption patterns
    if '}#' in content:
        print("FOUND: Extra text after closing brace")
        clean_content = content.split('}#')[0] + '}'
        print("Removing extra text...")
    else:
        clean_content = content.strip()
    
    # Try to parse as JSON
    try:
        data = json.loads(clean_content)
        print("SUCCESS: JSON is valid!")
        print(f"Contains: {len(data.get('recipes', []))} recipes, {len(data.get('ingredients', []))} ingredients, {len(data.get('entries', []))} entries")
        
        # Write back properly formatted
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Fixed and reformatted {filepath}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"JSON ERROR at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"Error position: character {e.pos}")
        
        # Show context around error
        lines = clean_content.splitlines()
        error_line = e.lineno - 1
        
        print("\nContext around error:")
        start = max(0, error_line - 2)
        end = min(len(lines), error_line + 3)
        
        for i in range(start, end):
            marker = " --> " if i == error_line else "     "
            print(f"{marker}{i+1:4d}: {lines[i]}")
        
        return False
    
    except Exception as e:
        print(f"OTHER ERROR: {e}")
        return False

if __name__ == "__main__":
    success = fix_master_json()
    sys.exit(0 if success else 1)