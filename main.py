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
from archive_manager import archive_run_data, get_existing_ogg_directories, create_language_summary
# Import will be done dynamically when needed

# Configuration
TRANSLATIONS_ORIGINAL_DIR = "Translations_Original"
TRANSLATIONS_DIR = "Translations"
REFERENCE_FILES_DIR = "Reference_Files"
LOGS_DIR = "Logs"
LOG_FILE = os.path.join(LOGS_DIR, "log.txt")
SCRIPTS_DIR = "Scripts"

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
            
            # Generate audio
            translation_path = os.path.join(TRANSLATIONS_DIR, translation_file)
            stats = generate_audio_for_language(
                translation_path,
                voice_info,
                wav_dir,
                ogg_dir,
                LOG_FILE
            )
            
            if stats:
                processed_languages += 1
                
                # Update overall stats
                overall_stats['total_wav_made'] += stats['wav_made']
                overall_stats['total_wav_skipped'] += stats['wav_skipped']
                overall_stats['total_ogg_made'] += stats['ogg_made']
                overall_stats['total_ogg_skipped'] += stats['ogg_skipped']
                
                # Create language summary
                create_language_summary(stats, ogg_dir)
                
                # Print language summary
                print(f"Language summary for {voice_info['in_game_code']}:")
                print(f"  Total entries: {stats['total_entries']}")
                print(f"  WAV made: {stats['wav_made']}, skipped: {stats['wav_skipped']}")
                print(f"  OGG made: {stats['ogg_made']}, skipped: {stats['ogg_skipped']}")
                
                # Log language summary
                log_message(LOG_FILE, f"Language {voice_info['in_game_code']} completed:")
                log_message(LOG_FILE, f"  WAV made: {stats['wav_made']}, skipped: {stats['wav_skipped']}")
                log_message(LOG_FILE, f"  OGG made: {stats['ogg_made']}, skipped: {stats['ogg_skipped']}")
                
            else:
                print(f"Failed to process {voice_info['in_game_code']}")
                failed_languages += 1
        
        # Archive and cleanup
        print(f"\nArchiving results...")
        log_message(LOG_FILE, f"\n=== Starting Archive Process ===")
        
        # Get all existing OGG directories (including ones from previous runs)
        all_ogg_dirs = get_existing_ogg_directories()
        
        archive_dir = archive_run_data(
            version,
            TRANSLATIONS_DIR,
            REFERENCE_FILES_DIR,
            all_ogg_dirs,
            LOG_FILE
        )
        
        if archive_dir:
            print(f" Results archived to: {archive_dir}")
        else:
            print("Warning: Archiving failed")
        
        # Final summary
        print(f"\n" + "=" * 50)
        print(f"RUN COMPLETE")
        print(f"Version: {version}")
        print(f"Languages processed: {processed_languages}")
        print(f"Languages failed: {failed_languages}")
        print(f"Total WAV files made: {overall_stats['total_wav_made']}")
        print(f"Total OGG files made: {overall_stats['total_ogg_made']}")
        if archive_dir:
            print(f"Archive location: {archive_dir}")
        print(f"=" * 50)
        
        # Log final summary
        log_message(LOG_FILE, f"\n=== RUN SUMMARY ===")
        log_message(LOG_FILE, f"Version: {version}")
        log_message(LOG_FILE, f"Languages processed: {processed_languages}")
        log_message(LOG_FILE, f"Languages failed: {failed_languages}")
        log_message(LOG_FILE, f"Total WAV files made: {overall_stats['total_wav_made']}")
        log_message(LOG_FILE, f"Total OGG files made: {overall_stats['total_ogg_made']}")
        if archive_dir:
            log_message(LOG_FILE, f"Archive location: {archive_dir}")
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