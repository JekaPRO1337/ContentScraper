import os
import zipfile
import re
import shutil

# Files and directories to exclude from the zip
EXCLUDE_PATTERNS = [
    r'\.git',
    r'\.session$',
    r'database\.db$',
    r'sniffer_log\.html$',
    r'__pycache__',
    r'\.zip$',
    r'\.pyc$',
    r'\.pytest_cache',
    r'venv',
    r'\.agent',
    r'\.gemini',
    r'brain',
]

def scrub_config(content):
    """Replace sensitive values with placeholders in config.py content."""
    # Pattern to match API_ID = 'value' or API_ID = "value" or API_ID = value
    content = re.sub(r"(API_ID\s*=\s*)['\"].*?['\"]", r"\1'YOUR_API_ID_HERE'", content)
    content = re.sub(r"(API_HASH\s*=\s*)['\"].*?['\"]", r"\1'YOUR_API_HASH_HERE'", content)
    content = re.sub(r"(BOT_TOKEN\s*=\s*)['\"].*?['\"]", r"\1'YOUR_BOT_TOKEN_HERE'", content)
    content = re.sub(r"(ADMIN_ID\s*=\s*)['\"].*?['\"]", r"\1'YOUR_TELEGRAM_ID_HERE'", content)
    return content

def create_zip(source_dir, output_zip):
    print(f"Creating archive: {output_zip}")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude directories
            dirs[:] = [d for d in dirs if not any(re.search(p, d) for p in EXCLUDE_PATTERNS)]
            
            for file in files:
                # Exclude files
                if any(re.search(p, file) for p in EXCLUDE_PATTERNS):
                    continue
                
                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, source_dir)
                
                # Special handling for config.py
                if file == 'config.py' and root == source_dir:
                    print(f"  Scrubbing {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    scrubbed_content = scrub_config(content)
                    zipf.writestr(archive_path, scrubbed_content.encode('utf-8'))
                else:
                    # zipf.write(file_path, archive_path)
                    try:
                        zipf.write(file_path, archive_path)
                    except Exception as e:
                        print(f"  Error adding {archive_path}: {e}")

    print(f"Successfully created {output_zip}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, "website", "content-scraper-premium.zip")
    
    # Ensure website directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    create_zip(current_dir, output_path)
