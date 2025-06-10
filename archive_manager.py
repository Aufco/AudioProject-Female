import os
import shutil
from io_helpers import ensure_directory, log_message

def get_archive_directory(base_version):
    """
    Get the next available archive directory for a version.
    
    Args:
        base_version: Base version string (e.g., "1.21.4")
        
    Returns:
        str: Archive directory path
    """
    archive_base = "Archive"
    ensure_directory(archive_base)
    
    # Check if version directory already exists
    version_dir = os.path.join(archive_base, base_version)
    if not os.path.exists(version_dir):
        return version_dir
    
    # Find next available run number
    run_number = 1
    while True:
        version_with_run = f"{base_version}-{run_number}"
        version_dir = os.path.join(archive_base, version_with_run)
        if not os.path.exists(version_dir):
            return version_dir
        run_number += 1

def archive_run_data(version, translations_dir, reference_files_dir, ogg_dirs, log_file):
    """
    Archive the run data including translations, reference files, and relevant OGG files.
    Only archives OGG files that correspond to keys in the processed translation files.
    
    Args:
        version: Minecraft version string
        translations_dir: Path to Translations directory
        reference_files_dir: Path to Reference_Files directory
        ogg_dirs: List of OGG directory paths
        log_file: Path to log file
        
    Returns:
        str: Path to created archive directory
    """
    try:
        # Get archive directory
        archive_dir = get_archive_directory(version)
        ensure_directory(archive_dir)
        
        log_message(log_file, f"\n=== Starting Archive Process ===")
        log_message(log_file, f"Archive directory: {archive_dir}")
        
        # First, get all keys from processed translation files BEFORE moving them
        all_translation_keys = set()
        if os.path.exists(translations_dir):
            from io_helpers import load_json
            for file in os.listdir(translations_dir):
                if file.endswith('_processed.json'):
                    translation_data = load_json(os.path.join(translations_dir, file))
                    if translation_data:
                        all_translation_keys.update(translation_data.keys())
        
        log_message(log_file, f"Found {len(all_translation_keys)} unique keys across all processed translations")
        
        # Archive translations directory
        if os.path.exists(translations_dir):
            archive_translations = os.path.join(archive_dir, "Translations")
            shutil.copytree(translations_dir, archive_translations)
            log_message(log_file, f"Moved Translations to archive")
            
            # Remove original translations directory
            shutil.rmtree(translations_dir)
            log_message(log_file, f"Removed original Translations directory")
        else:
            log_message(log_file, f"Warning: Translations directory not found: {translations_dir}")
        
        # Copy reference files
        if os.path.exists(reference_files_dir):
            archive_reference = os.path.join(archive_dir, "Reference_Files")
            shutil.copytree(reference_files_dir, archive_reference)
            log_message(log_file, f"Copied Reference_Files to archive")
        else:
            log_message(log_file, f"Warning: Reference_Files directory not found: {reference_files_dir}")
        
        # Copy only relevant OGG files based on processed translations
        archived_ogg_count = 0
        total_files_copied = 0
        
        for ogg_dir in ogg_dirs:
            if os.path.exists(ogg_dir):
                archive_ogg = os.path.join(archive_dir, os.path.basename(ogg_dir))
                ensure_directory(archive_ogg)
                
                files_copied_this_dir = 0
                files_skipped_this_dir = 0
                
                # Copy only OGG files that match translation keys
                for file in os.listdir(ogg_dir):
                    if file.endswith('.ogg'):
                        # Extract key from filename (remove .ogg extension)
                        key = file[:-4]
                        
                        if key in all_translation_keys:
                            src_path = os.path.join(ogg_dir, file)
                            dst_path = os.path.join(archive_ogg, file)
                            shutil.copy2(src_path, dst_path)
                            files_copied_this_dir += 1
                        else:
                            files_skipped_this_dir += 1
                
                total_files_copied += files_copied_this_dir
                archived_ogg_count += 1
                
                log_message(log_file, f"Copied {os.path.basename(ogg_dir)}: {files_copied_this_dir} files copied, {files_skipped_this_dir} files skipped (removed from translations)")
            else:
                log_message(log_file, f"Warning: OGG directory not found: {ogg_dir}")
        
        log_message(log_file, f"=== Archive Process Complete ===")
        log_message(log_file, f"Archived {archived_ogg_count} OGG directories with {total_files_copied} total files")
        log_message(log_file, f"Archive location: {archive_dir}")
        
        return archive_dir
        
    except Exception as e:
        error_msg = f"Error during archiving: {e}"
        print(error_msg)
        log_message(log_file, error_msg)
        return None

def create_language_summary(language_stats, output_dir):
    """
    Create a summary.txt file for a language with its statistics.
    
    Args:
        language_stats: Dictionary with language statistics
        output_dir: Directory to save summary file
    """
    try:
        ensure_directory(output_dir)
        summary_file = os.path.join(output_dir, "summary.txt")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Language Processing Summary\n")
            f.write("=" * 30 + "\n\n")
            f.write(f"Total entries: {language_stats.get('total_entries', 0)}\n")
            f.write(f"WAV files made: {language_stats.get('wav_made', 0)}\n")
            f.write(f"WAV files skipped: {language_stats.get('wav_skipped', 0)}\n")
            f.write(f"WAV files failed: {language_stats.get('wav_failed', 0)}\n")
            f.write(f"OGG files made: {language_stats.get('ogg_made', 0)}\n")
            f.write(f"OGG files skipped: {language_stats.get('ogg_skipped', 0)}\n")
            f.write(f"OGG files failed: {language_stats.get('ogg_failed', 0)}\n")
            
    except Exception as e:
        print(f"Error creating language summary: {e}")

def cleanup_empty_directories():
    """
    Remove any empty WAV/OGG directories that may have been created.
    """
    try:
        current_dir = "."
        for item in os.listdir(current_dir):
            if (item.endswith("-WAV") or item.endswith("-OGG")) and os.path.isdir(item):
                if not os.listdir(item):  # Directory is empty
                    os.rmdir(item)
                    print(f"Removed empty directory: {item}")
    except Exception as e:
        print(f"Error cleaning up empty directories: {e}")

def get_existing_ogg_directories():
    """
    Get list of existing OGG directories in current directory.
    
    Returns:
        list: List of OGG directory paths
    """
    ogg_dirs = []
    try:
        current_dir = "."
        for item in os.listdir(current_dir):
            if item.endswith("-OGG") and os.path.isdir(item):
                ogg_dirs.append(item)
    except Exception as e:
        print(f"Error getting OGG directories: {e}")
    
    return ogg_dirs