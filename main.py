#!/usr/bin/env python3
"""
Minecraft Audio Project - Main Script
Converts Minecraft translation files to audio using Google Text-to-Speech.
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

# Import our modules
from io_helpers import log_message, ensure_directory
from preprocess_translations import preprocess_all_translations  
from voice_selector import match_languages_to_voices
from audio_generator import generate_audio_for_language, create_audio_directories
from bucket_manager import (BucketManager, transfer_existing_audio_to_bucket, 
                           cleanup_local_directories, create_bucket_file_logs,
                           transfer_generated_files_to_bucket)

# Configuration
TRANSLATIONS_ORIGINAL_DIR = "Translations_Original"
TRANSLATIONS_DIR = "Translations"
REFERENCE_FILES_DIR = "Reference_Files"
LOGS_DIR = "Logs"
LOG_FILE = os.path.join(LOGS_DIR, "log.txt")
SCRIPTS_DIR = "Scripts"
BUCKET_NAME = "myproject-461901-bucket"

def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")
    
    # Check ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(" ffmpeg found")
        else:
            print(" ffmpeg not working properly")
            return False
    except FileNotFoundError:
        print(" ffmpeg not found in PATH")
        print("Please install ffmpeg and ensure it's in your PATH")
        return False
    
    # Check Google Cloud credentials
    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        print(" Google Cloud Text-to-Speech client initialized")
    except Exception as e:
        print(f" Google Cloud TTS error: {e}")
        print("Please ensure your Google Cloud credentials are properly configured")
        return False
    
    return True

def get_minecraft_version():
    """Get Minecraft version with run number handling."""
    version = "1.21.4"  # Default version
    
    # Check if this version was already archived
    base_archive_dir = os.path.join("Archive", version)
    if os.path.exists(base_archive_dir):
        # Find next available run number
        run_number = 1
        while True:
            version_with_run = f"{version}-{run_number}"
            archive_dir = os.path.join("Archive", version_with_run)
            if not os.path.exists(archive_dir):
                print(f"Version {version} already exists. Using run version: {version_with_run}")
                return version_with_run
            run_number += 1
    
    return version

def initialize_logging(version):
    """Initialize logging for the run."""
    ensure_directory(LOGS_DIR)
    
    # Clear/create log file
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("")
    
    # Add header
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message(LOG_FILE, "=" * 60)
    log_message(LOG_FILE, f"Minecraft Audio Project - Run Started")
    log_message(LOG_FILE, f"Version: {version}")
    log_message(LOG_FILE, f"Timestamp: {timestamp}")
    log_message(LOG_FILE, "=" * 60)

def fetch_google_voices():
    """Fetch Google voices and handle quota errors."""
    print("\nFetching Google voices...")
    log_message(LOG_FILE, "\n=== Fetching Google Voices ===")
    
    try:
        # Run the voice fetching script
        result = subprocess.run([
            sys.executable, 
            os.path.join(SCRIPTS_DIR, "Google-tts_supported_voices.py")
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            error_msg = f"Error fetching voices: {result.stderr}"
            print(error_msg)
            log_message(LOG_FILE, error_msg)
            
            # Check for quota error
            if "quota" in result.stderr.lower() or "exceeded" in result.stderr.lower():
                print("Google API quota exhausted. Please try again later.")
                return False
            
            return False
        
        print(" Google voices fetched successfully")
        log_message(LOG_FILE, "Google voices fetched successfully")
        return True
        
    except Exception as e:
        error_msg = f"Error running voice fetch script: {e}"
        print(error_msg)
        log_message(LOG_FILE, error_msg)
        return False

def main():
    """Main execution function."""
    print("Minecraft Audio Project")
    print("=" * 40)
    
    try:
        # Get Minecraft version
        version = get_minecraft_version()
        print(f"Processing version: {version}")
        
        # Initialize logging
        initialize_logging(version)
        
        # Check dependencies
        if not check_dependencies():
            print("Dependency check failed. Please resolve the issues above.")
            return 1
        
        # Fetch Google voices
        if not fetch_google_voices():
            print("Failed to fetch Google voices. Exiting.")
            return 1
        
        # Preprocess translation files
        print("\nPreprocessing translation files...")
        log_message(LOG_FILE, "\n=== Starting Translation Preprocessing ===")
        
        reference_file = os.path.join(REFERENCE_FILES_DIR, "en_us_processed.json")
        if not os.path.exists(reference_file):
            print(f"Error: Reference file not found: {reference_file}")
            return 1
        
        preprocessing_stats = preprocess_all_translations(
            TRANSLATIONS_ORIGINAL_DIR,
            TRANSLATIONS_DIR, 
            reference_file,
            LOG_FILE
        )
        
        if not preprocessing_stats:
            print("Failed to preprocess translations. Exiting.")
            return 1
        
        print(f" Preprocessed {preprocessing_stats['files_processed']} language files")
        
        # Match languages to voices
        print("\nMatching languages to Google voices...")
        log_message(LOG_FILE, "\n=== Matching Languages to Voices ===")
        
        html_table_file = os.path.join(REFERENCE_FILES_DIR, "Minecraft_languages_table.html")
        google_voices_file = os.path.join(REFERENCE_FILES_DIR, "Google-tts-supported-languages.json")
        
        language_voice_mapping = match_languages_to_voices(
            TRANSLATIONS_DIR,
            html_table_file,
            google_voices_file
        )
        
        if not language_voice_mapping:
            print("No languages could be matched to Google voices. Exiting.")
            return 1
        
        print(f" Matched {len(language_voice_mapping)} languages to voices")
        
        # Create language table CSV
        print("\nCreating language table CSV...")
        from voice_selector import create_language_table_csv, parse_minecraft_language_table
        from io_helpers import load_json
        
        language_mapping = parse_minecraft_language_table(html_table_file)
        google_voices = load_json(google_voices_file)
        create_language_table_csv(language_voice_mapping, language_mapping, google_voices)
        
        # Initialize bucket manager
        print("\nInitializing bucket manager...")
        log_message(LOG_FILE, "\n=== Initializing Bucket Manager ===")
        
        try:
            bucket_manager = BucketManager(BUCKET_NAME, LOG_FILE)
            print(f" Connected to bucket: {BUCKET_NAME}")
            log_message(LOG_FILE, f"Connected to bucket: {BUCKET_NAME}")
        except Exception as e:
            print(f"Failed to initialize bucket manager: {e}")
            log_message(LOG_FILE, f"Failed to initialize bucket manager: {e}")
            return 1
        
        # Step 1: Transfer existing audio files to bucket and cleanup
        print("\nTransferring existing audio files to bucket...")
        if transfer_existing_audio_to_bucket(bucket_manager, LOG_FILE):
            print(" Transfer completed successfully")
            
            # Step 2: Delete local directories
            print("\nCleaning up local audio directories...")
            if cleanup_local_directories(LOG_FILE):
                print(" Cleanup completed successfully")
            else:
                print("Warning: Some directories could not be cleaned up")
        else:
            print("Warning: Transfer failed or no files to transfer")
        
        # Step 3: Create bucket file logs for reference
        print("\nCreating bucket file logs...")
        create_bucket_file_logs(bucket_manager, LOG_FILE)
        
        # Generate audio for each language
        print("\nGenerating audio files...")
        log_message(LOG_FILE, "\n=== Starting Audio Generation ===")
        
        total_languages = len(language_voice_mapping)
        processed_languages = 0
        failed_languages = 0
        overall_stats = {
            'total_wav_made': 0,
            'total_wav_skipped': 0,
            'total_ogg_made': 0,
            'total_ogg_skipped': 0
        }
        
        ogg_directories = []
        
        for translation_file, voice_info in language_voice_mapping.items():
            print(f"\nProcessing {voice_info['in_game_code']} ({processed_languages + 1}/{total_languages})")
            log_message(LOG_FILE, f"\n--- Processing {voice_info['in_game_code']} ---")
            
            # Create audio directories
            wav_dir, ogg_dir = create_audio_directories(voice_info)
            if not wav_dir or not ogg_dir:
                print(f"Failed to create directories for {voice_info['in_game_code']}")
                failed_languages += 1
                continue
            
            ogg_directories.append(ogg_dir)
            
            # Generate audio with bucket checking
            translation_path = os.path.join(TRANSLATIONS_DIR, translation_file)
            stats = generate_audio_for_language(
                translation_path,
                voice_info,
                wav_dir,
                ogg_dir,
                LOG_FILE,
                bucket_manager=bucket_manager
            )
            
            if stats:
                processed_languages += 1
                
                # Update overall stats
                overall_stats['total_wav_made'] += stats['wav_made']
                overall_stats['total_wav_skipped'] += stats['wav_skipped']
                overall_stats['total_ogg_made'] += stats['ogg_made']
                overall_stats['total_ogg_skipped'] += stats['ogg_skipped']
                
                # Print language summary
                print(f"Language summary for {voice_info['in_game_code']}:")
                print(f"  Total entries: {stats['total_entries']}")
                print(f"  WAV made: {stats['wav_made']}, skipped: {stats['wav_skipped']}")
                print(f"  OGG made: {stats['ogg_made']}, skipped: {stats['ogg_skipped']}")
                
                # Log language summary
                log_message(LOG_FILE, f"Language {voice_info['in_game_code']} completed:")
                log_message(LOG_FILE, f"  WAV made: {stats['wav_made']}, skipped: {stats['wav_skipped']}")
                log_message(LOG_FILE, f"  OGG made: {stats['ogg_made']}, skipped: {stats['ogg_skipped']}")
                
                # Transfer generated files to bucket and cleanup
                voice_name, _ = voice_info['voices'][0]
                if transfer_generated_files_to_bucket(bucket_manager, wav_dir, ogg_dir, voice_name, LOG_FILE):
                    print(f"  Files transferred to bucket and cleaned up")
                else:
                    print(f"  Warning: Failed to transfer some files to bucket")
                
            else:
                print(f"Failed to process {voice_info['in_game_code']}")
                failed_languages += 1
        
        # Final bucket file logs update
        print(f"\nUpdating bucket file logs...")
        log_message(LOG_FILE, f"\n=== Updating Final Bucket Logs ===")
        
        create_bucket_file_logs(bucket_manager, LOG_FILE)
        
        
        
        # Final summary
        print(f"\n" + "=" * 50)
        print(f"RUN COMPLETE")
        print(f"Version: {version}")
        print(f"Languages processed: {processed_languages}")
        print(f"Languages failed: {failed_languages}")
        print(f"Total WAV files made: {overall_stats['total_wav_made']}")
        print(f"Total OGG files made: {overall_stats['total_ogg_made']}")
        print(f"Bucket: {BUCKET_NAME}")
        print(f"=" * 50)
        
        # Log final summary
        log_message(LOG_FILE, f"\n=== RUN SUMMARY ===")
        log_message(LOG_FILE, f"Version: {version}")
        log_message(LOG_FILE, f"Languages processed: {processed_languages}")
        log_message(LOG_FILE, f"Languages failed: {failed_languages}")
        log_message(LOG_FILE, f"Total WAV files made: {overall_stats['total_wav_made']}")
        log_message(LOG_FILE, f"Total OGG files made: {overall_stats['total_ogg_made']}")
        log_message(LOG_FILE, f"Bucket: {BUCKET_NAME}")
        log_message(LOG_FILE, f"Run completed successfully")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        log_message(LOG_FILE, "Process interrupted by user")
        return 1
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        log_message(LOG_FILE, error_msg)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)