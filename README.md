# Minecraft Audio Project - Female Voices

This project generates female voice audio files for all Minecraft in-game text using Google Text-to-Speech (TTS), with cloud storage management and intelligent file processing.

## Project Overview

The system processes Minecraft translation files, matches them to Google TTS voices, generates WAV and OGG audio files, and manages them in Google Cloud Storage. It uses batch operations for efficient file existence checking and only generates missing audio files.

## Processing Flow (using af_za as example)

### 1. Preprocessing
- Loads `af_za.json` from `Translations_Original/`
- Filters entries against `en_us_processed.json` reference (2747 entries)
- Saves processed file as `af_za_processed.json` in `Translations/`

### 2. Voice Matching
- Parses `Minecraft_languages_table.html` to map `af_za` → `af-ZA` (Google language code)
- Matches against `Google-tts-supported-languages.json` to find `af-ZA-Standard-A` (female voice)
- Creates language-to-voice mapping for audio generation

### 3. Bucket Management
- Transfers any existing local audio files to Google Cloud Storage
- Cleans up local directories to save disk space
- Creates fresh bucket logs for all 40 matched languages

### 4. Audio Generation
- Batch-checks existing files in bucket using `list_blobs()` for fast O(1) lookups
- Generates WAV files using Google TTS for missing entries only
- Converts WAV to OGG format using ffmpeg
- Transfers new files to bucket and cleans up locally

### 5. Logging
- Updates bucket file logs with current file inventory
- Generates comprehensive run statistics

## Directory and File Structure

### Directories
- **`BucketLogs/`** - Contains inventory files of audio files stored in Google Cloud Storage bucket
- **`Reference_Files/`** - Contains reference data files needed for processing and voice matching
- **`Translations/`** - Processed translation JSON files filtered to match reference entries
- **`Translations_Original/`** - Original Minecraft translation files before processing
- **`Logs/`** - Runtime logs and error tracking
- **`Scripts/`** - Utility scripts for fetching Google voice data

### Files

#### Core Python Files
- **`main.py`** - Main orchestrator script that runs the complete audio generation pipeline
- **`audio_generator.py`** - Handles Google TTS audio generation and WAV to OGG conversion
- **`voice_selector.py`** - Matches Minecraft languages to available Google TTS voices
- **`bucket_manager.py`** - Manages Google Cloud Storage operations and file transfers
- **`archive_manager.py`** - Handles versioning and archiving of completed runs
- **`preprocess_translations.py`** - Filters and standardizes translation files against reference data

#### Reference Files
- **`Reference_Files/Google-tts-supported-languages.json`** - Complete list of available Google TTS voices and languages
- **`Reference_Files/Minecraft_languages_table.html`** - HTML table mapping Minecraft language codes to standard language codes
- **`Reference_Files/en_us_processed.json`** - Reference file containing 2747 standard entries for filtering other languages

#### Generated/Output Files
- **`BucketLogs/af-ZA-Standard-A_OGG_files.txt`** - Inventory log of OGG files for Afrikaans voice in bucket storage
- **`Translations/af_za_processed.json`** - Filtered Afrikaans translation file with 2747 entries matching reference
- **`Translations_Original/af_za.json`** - Original unprocessed Afrikaans translation file from Minecraft
- **`Scripts/Google-tts_supported_voices.py`** - Utility script to fetch and update Google TTS voice data
- **`Logs/log.txt`** - Runtime execution log with timestamps, errors, and processing statistics

## Example: af_za Processing

1. **Input**: `af_za.json` (original Minecraft Afrikaans translations)
2. **Processing**: Filters against `en_us_processed.json` → keeps 2747 matching entries
3. **Voice Match**: `af_za` → `af-ZA` → `af-ZA-Standard-A` (female voice)
4. **Audio Generation**: Creates `item.minecraft.stone.wav` and `item.minecraft.stone.ogg` for each entry
5. **Storage**: Files uploaded to bucket path `AudioProject-Female/af-ZA-Standard-A-female-WAV/`
6. **Logging**: Updates `af-ZA-Standard-A_WAV_files.txt` with inventory

## Key Features

- **Batch File Operations**: Uses `os.scandir()` and `list_blobs()` for efficient file existence checking
- **Smart Skipping**: Only generates audio for files that don't exist in bucket storage
- **Cloud Storage**: Automatically manages files in Google Cloud Storage with cleanup
- **Error Handling**: Comprehensive logging and error recovery mechanisms
- **Scalable**: Processes 40+ languages with thousands of files each efficiently