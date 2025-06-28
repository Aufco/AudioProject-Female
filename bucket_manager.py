import os
from google.cloud import storage
from io_helpers import ensure_directory, log_message

class BucketManager:
    def __init__(self, bucket_name, log_file):
        """
        Initialize bucket manager for Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            log_file: Path to log file
        """
        self.bucket_name = bucket_name
        self.log_file = log_file
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def upload_file(self, local_path, bucket_path):
        """
        Upload a file to the bucket.
        
        Args:
            local_path: Local file path
            bucket_path: Path in bucket
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(bucket_path)
            blob.upload_from_filename(local_path)
            return True
        except Exception as e:
            error_msg = f"Error uploading {local_path} to bucket: {e}"
            print(error_msg)
            log_message(self.log_file, error_msg)
            return False
    
    def list_files(self, prefix=""):
        """
        List files in bucket with given prefix.
        
        Args:
            prefix: Prefix to filter files
            
        Returns:
            list: List of file names
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            error_msg = f"Error listing files in bucket with prefix '{prefix}': {e}"
            print(error_msg)
            log_message(self.log_file, error_msg)
            return []
    
    def delete_file(self, bucket_path):
        """
        Delete a file from the bucket.
        
        Args:
            bucket_path: Path in bucket
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(bucket_path)
            blob.delete()
            return True
        except Exception as e:
            error_msg = f"Error deleting {bucket_path} from bucket: {e}"
            print(error_msg)
            log_message(self.log_file, error_msg)
            return False

def transfer_existing_audio_to_bucket(bucket_manager, log_file):
    """
    Transfer all existing WAV and OGG files from local directories to bucket.
    
    Args:
        bucket_manager: BucketManager instance
        log_file: Path to log file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_message(log_file, "\n=== Transferring Existing Audio Files to Bucket ===")
        
        transferred_count = 0
        failed_count = 0
        directories_to_cleanup = []
        
        # Find all WAV and OGG directories
        current_dir = "."
        for item in os.listdir(current_dir):
            if (item.endswith("-WAV") or item.endswith("-OGG")) and os.path.isdir(item):
                directory_path = os.path.join(current_dir, item)
                directories_to_cleanup.append(directory_path)
                
                # Extract language code from directory name and use existing bucket structure
                bucket_prefix = f"AudioProject-Female/{item}/"
                
                log_message(log_file, f"Processing directory: {item}")
                
                # Transfer all audio files
                for file in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, file)
                    
                    # Skip summary.txt files - we don't want these in the bucket
                    if file == "summary.txt":
                        log_message(log_file, f"Skipping summary.txt file: {file_path}")
                        continue
                    
                    # Only transfer audio files
                    if file.endswith(('.wav', '.ogg')):
                        bucket_path = bucket_prefix + file
                        
                        if bucket_manager.upload_file(file_path, bucket_path):
                            transferred_count += 1
                            log_message(log_file, f"Transferred: {file_path} -> {bucket_path}")
                        else:
                            failed_count += 1
                            log_message(log_file, f"Failed to transfer: {file_path}")
        
        log_message(log_file, f"Transfer complete: {transferred_count} files transferred, {failed_count} failed")
        
        return transferred_count > 0 or failed_count == 0
        
    except Exception as e:
        error_msg = f"Error during audio file transfer: {e}"
        print(error_msg)
        log_message(log_file, error_msg)
        return False

def cleanup_local_directories(log_file):
    """
    Delete all local WAV and OGG directories and their contents.
    
    Args:
        log_file: Path to log file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import shutil
        
        log_message(log_file, "\n=== Cleaning Up Local Audio Directories ===")
        
        deleted_count = 0
        failed_count = 0
        
        # Find and delete all WAV and OGG directories
        current_dir = "."
        for item in os.listdir(current_dir):
            if (item.endswith("-WAV") or item.endswith("-OGG")) and os.path.isdir(item):
                directory_path = os.path.join(current_dir, item)
                
                try:
                    shutil.rmtree(directory_path)
                    deleted_count += 1
                    log_message(log_file, f"Deleted directory: {directory_path}")
                except Exception as e:
                    failed_count += 1
                    log_message(log_file, f"Failed to delete directory {directory_path}: {e}")
        
        log_message(log_file, f"Cleanup complete: {deleted_count} directories deleted, {failed_count} failed")
        
        return failed_count == 0
        
    except Exception as e:
        error_msg = f"Error during directory cleanup: {e}"
        print(error_msg)
        log_message(log_file, error_msg)
        return False

def create_bucket_file_logs(bucket_manager, log_file):
    """
    Create .txt files listing all audio files in the bucket for each language.
    
    Args:
        bucket_manager: BucketManager instance
        log_file: Path to log file
        
    Returns:
        dict: Dictionary mapping language codes to their file lists
    """
    try:
        log_message(log_file, "\n=== Creating Bucket File Logs ===")
        
        # Get all files in bucket
        all_files = bucket_manager.list_files()
        
        # Group files by language and format
        language_files = {}
        
        for file_path in all_files:
            # Expected format: AudioProject-Female/voice-name-female-FORMAT/filename.ext
            parts = file_path.split('/')
            if len(parts) >= 3 and parts[0] == 'AudioProject-Female':
                directory_name = parts[1]  # e.g., "af-ZA-Standard-A-female-OGG"
                filename = parts[2]
                
                # Extract voice name and format from directory name
                if directory_name.endswith('-female-WAV'):
                    voice_name = directory_name.replace('-female-WAV', '')
                    format_type = 'WAV'
                elif directory_name.endswith('-female-OGG'):
                    voice_name = directory_name.replace('-female-OGG', '')
                    format_type = 'OGG'
                else:
                    continue
                
                if voice_name not in language_files:
                    language_files[voice_name] = {'WAV': [], 'OGG': []}
                
                language_files[voice_name][format_type].append(filename)
        
        # Create log files for each language
        logs_dir = "BucketLogs"
        ensure_directory(logs_dir)
        
        for voice_name, formats in language_files.items():
            for format_type, files in formats.items():
                if files:  # Only create log if there are files
                    log_filename = f"{voice_name}_{format_type}_files.txt"
                    log_path = os.path.join(logs_dir, log_filename)
                    
                    with open(log_path, 'w', encoding='utf-8') as f:
                        f.write(f"Bucket Files Log - {voice_name} {format_type}\n")
                        f.write("=" * 40 + "\n\n")
                        f.write(f"Total files: {len(files)}\n\n")
                        
                        for filename in sorted(files):
                            f.write(f"{filename}\n")
                    
                    log_message(log_file, f"Created bucket log: {log_path} ({len(files)} files)")
        
        log_message(log_file, f"Bucket logging complete: {len(language_files)} languages processed")
        
        return language_files
        
    except Exception as e:
        error_msg = f"Error creating bucket file logs: {e}"
        print(error_msg)
        log_message(log_file, error_msg)
        return {}

def check_file_exists_in_bucket(bucket_manager, voice_name, format_type, filename):
    """
    Check if a specific audio file exists in the bucket.
    
    Args:
        bucket_manager: BucketManager instance
        voice_name: Voice name (e.g., af-ZA-Standard-A)
        format_type: WAV or OGG
        filename: Name of the file
        
    Returns:
        bool: True if file exists, False otherwise
    """
    bucket_path = f"AudioProject-Female/{voice_name}-female-{format_type}/{filename}"
    
    try:
        blob = bucket_manager.bucket.blob(bucket_path)
        return blob.exists()
    except Exception as e:
        print(f"Error checking file existence in bucket: {e}")
        return False

def get_existing_bucket_files(bucket_manager, voice_name):
    """
    OPTIMIZED: Get all existing WAV and OGG files from bucket in batch operations.
    
    Args:
        bucket_manager: BucketManager instance
        voice_name: Voice name (e.g., af-ZA-Standard-A)
        
    Returns:
        tuple: (set of WAV filenames, set of OGG filenames)
    """
    wav_files = set()
    ogg_files = set()
    
    try:
        # Batch fetch WAV files
        wav_prefix = f"AudioProject-Female/{voice_name}-female-WAV/"
        wav_blobs = bucket_manager.bucket.list_blobs(prefix=wav_prefix)
        for blob in wav_blobs:
            filename = blob.name.split('/')[-1]
            if filename.endswith('.wav'):
                wav_files.add(filename)
        
        # Batch fetch OGG files
        ogg_prefix = f"AudioProject-Female/{voice_name}-female-OGG/"
        ogg_blobs = bucket_manager.bucket.list_blobs(prefix=ogg_prefix)
        for blob in ogg_blobs:
            filename = blob.name.split('/')[-1]
            if filename.endswith('.ogg'):
                ogg_files.add(filename)
                
    except Exception as e:
        print(f"Error batch checking bucket files: {e}")
        
    return wav_files, ogg_files

def transfer_generated_files_to_bucket(bucket_manager, wav_dir, ogg_dir, voice_name, log_file):
    """
    Transfer newly generated WAV and OGG files to bucket and clean up local directories.
    
    Args:
        bucket_manager: BucketManager instance
        wav_dir: Local WAV directory path
        ogg_dir: Local OGG directory path
        voice_name: Voice name (e.g., af-ZA-Standard-A)
        log_file: Path to log file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import shutil
        
        log_message(log_file, f"\n=== Transferring Generated Files to Bucket - {voice_name} ===")
        
        transferred_count = 0
        failed_count = 0
        
        # Transfer WAV files
        if os.path.exists(wav_dir):
            with os.scandir(wav_dir) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    file = entry.name
                    if file.endswith('.wav'):
                        local_path = os.path.join(wav_dir, file)
                        bucket_path = f"AudioProject-Female/{voice_name}-female-WAV/{file}"
                        
                        if bucket_manager.upload_file(local_path, bucket_path):
                            transferred_count += 1
                            log_message(log_file, f"Transferred WAV: {file}")
                        else:
                            failed_count += 1
            
            # Delete WAV directory
            shutil.rmtree(wav_dir)
            log_message(log_file, f"Deleted local WAV directory: {wav_dir}")
        
        # Transfer OGG files (excluding summary.txt)
        if os.path.exists(ogg_dir):
            with os.scandir(ogg_dir) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    file = entry.name
                    if file.endswith('.ogg'):
                        local_path = os.path.join(ogg_dir, file)
                        bucket_path = f"AudioProject-Female/{voice_name}-female-OGG/{file}"
                        
                        if bucket_manager.upload_file(local_path, bucket_path):
                            transferred_count += 1
                            log_message(log_file, f"Transferred OGG: {file}")
                        else:
                            failed_count += 1
                    elif file == "summary.txt":
                        log_message(log_file, f"Skipping summary.txt during transfer")
            
            # Delete OGG directory
            shutil.rmtree(ogg_dir)
            log_message(log_file, f"Deleted local OGG directory: {ogg_dir}")
        
        log_message(log_file, f"Transfer complete for {voice_name}: {transferred_count} files transferred, {failed_count} failed")
        
        return failed_count == 0
        
    except Exception as e:
        error_msg = f"Error transferring generated files for {voice_name}: {e}"
        print(error_msg)
        log_message(log_file, error_msg)
        return False