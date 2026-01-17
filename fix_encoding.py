"""Script to fix encoding of settings.py"""
import sys

settings_file = r"c:\Users\lipef\OneDrive\Desktop\web-scraping-finep\config\settings.py"

try:
    # Read with UTF-16-LE encoding
    with open(settings_file, 'r', encoding='utf-16-le') as f:
        content = f.read()
    
    # Write back as UTF-8 without BOM
    with open(settings_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ File successfully converted from UTF-16 LE to UTF-8")
    print(f"✓ File: {settings_file}")
    
    # Verify the file can now be imported
    sys.path.insert(0, r'c:\Users\lipef\OneDrive\Desktop\web-scraping-finep\config')
    import settings
    print("✓ File can be imported without errors")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
