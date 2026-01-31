
import zipfile
import os

def create_distribution():
    include_files = [
        'main.py',
        'config.py',
        'database.py',
        'sniffer.py',
        'install.bat',
        'requirements.txt',
        'bot_icon.png',
        'README.md',
        'ffmpeg.exe'
    ]
    include_dirs = ['utils', 'handlers', 'website']
    target_zip = 'website/public/content-scraper-premium.zip'
    
    if os.path.exists(target_zip):
        os.remove(target_zip)
    os.makedirs(os.path.dirname(target_zip), exist_ok=True)
    
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in include_files:
            if os.path.exists(filename):
                zipf.write(filename, filename)
            else:
                print(f"Warning: {filename} not found!")

        for directory in include_dirs:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    if '__pycache__' in root or '.git' in root: continue
                    for file in files:
                        if file.endswith('.zip') or file == '.env' or file.endswith('.session') or file.endswith('.db'): continue
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, os.getcwd())
                        zipf.write(file_path, rel_path)
    print("Archive rebuilt!")

if __name__ == "__main__":
    create_distribution()
