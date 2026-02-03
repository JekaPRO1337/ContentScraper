import os
import zipfile
import re
import shutil

# Directories to completely ignore
EXCLUDE_DIRS = {
    '.git', '__pycache__', 'venv', '.agent', '.gemini', 'brain', 'website', '.pytest_cache'
}

# File patterns to ignore
EXCLUDE_FILE_PATTERNS = [
    r'\.session$',
    r'database\.db$',
    r'sniffer_log\.html$',
    r'\.zip$',
    r'\.pyc$',
]

def scrub_config(content):
    """Replace sensitive values with placeholders in config.py content."""
    content = re.sub(r"(API_ID\s*=\s*)['\"].*?['\"]", r"\1'YOUR_API_ID_HERE'", content)
    content = re.sub(r"(API_HASH\s*=\s*)['\"].*?['\"]", r"\1'YOUR_API_HASH_HERE'", content)
    content = re.sub(r"(BOT_TOKEN\s*=\s*)['\"].*?['\"]", r"\1'YOUR_BOT_TOKEN_HERE'", content)
    content = re.sub(r"(ADMIN_ID\s*=\s*)['\"].*?['\"]", r"\1'YOUR_TELEGRAM_ID_HERE'", content)
    content = re.sub(r"(SNIFFER_LICENSE\s*=\s*)['\"].*?['\"]", r"\1'YOUR_LICENSE_KEY_HERE'", content)
    return content

def create_zip(source_dir, output_zip):
    if os.path.exists(output_zip):
        print(f"Deleting old archive: {output_zip}")
        os.remove(output_zip)
        
    print(f"Creating archive: {output_zip}")
    
    added_files = []
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to prevent descending into excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            relative_root = os.path.relpath(root, source_dir)
            if relative_root != "." and any(part in EXCLUDE_DIRS for part in relative_root.split(os.sep)):
                continue

            for file in files:
                if any(re.search(p, file) for p in EXCLUDE_FILE_PATTERNS):
                    continue
                
                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, source_dir)
                
                # Final guard against anything inside 'website'
                if archive_path.startswith("website") or "website" in archive_path.split(os.sep):
                    continue

                if file == 'config.py' and root == source_dir:
                    print(f"  Scrubbing {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    scrubbed_content = scrub_config(content)
                    zipf.writestr(archive_path, scrubbed_content.encode('utf-8'))
                else:
                    try:
                        zipf.write(file_path, archive_path)
                    except Exception as e:
                        print(f"  Error adding {archive_path}: {e}")
                added_files.append(archive_path)

    print(f"Successfully created {output_zip} with {len(added_files)} files.")
    
    # Verification
    print("Archive contents:")
    for f in sorted(added_files):
        print(f"  - {f}")
    
    if any("website" in f.lower() for f in added_files):
        print("ERROR: Website folder detected in archive!")
    else:
        print("Verification OK: No website folder in archive.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, "website", "content-scraper-premium.zip")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    create_zip(current_dir, output_path)
