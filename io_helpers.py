import os
import json
from tqdm import tqdm
from pathlib import Path

def ensure_directory(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def load_json(file_path):
    """Load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        return None

def save_json(data, file_path):
    """Save data to JSON file with proper formatting."""
    ensure_directory(os.path.dirname(file_path))
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")
        return False

def create_progress_bar(total, description="Processing"):
    """Create a tqdm progress bar."""
    return tqdm(total=total, desc=description, unit="items")

def get_files_in_directory(directory, extension=None):
    """Get all files in directory, optionally filtered by extension."""
    if not os.path.exists(directory):
        return []
    
    files = []
    for file in os.listdir(directory):
        if extension is None or file.endswith(extension):
            files.append(os.path.join(directory, file))
    return files

def log_message(log_file, message, timestamp=True):
    """Append message to log file with optional timestamp."""
    import datetime
    
    # Only ensure directory if log_file has a directory component
    log_dir = os.path.dirname(log_file)
    if log_dir:
        ensure_directory(log_dir)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        if timestamp:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {message}\n")
        else:
            f.write(f"{message}\n")