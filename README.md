# Minecraft Audio Project

Converts Minecraft translation files to high-quality audio using Google Text-to-Speech, with intelligent voice selection and efficient processing.

## Overview

This project processes Minecraft language files and generates audio pronunciations for all game items, blocks, entities, and biomes. It intelligently manages voice selection, skips existing audio files, and archives results efficiently.

## Flow Chart

```
Minecraft Version Input → Translation Preprocessing → Language Matching → Voice Selection → Audio Generation → Archiving
```

### Detailed Workflow

```
User Input (Version) 
    ↓
Fetch Google Voices → Parse HTML Language Table → Load Translation Files
    ↓                        ↓                           ↓
Reference_Files/         Minecraft Wiki              Translations_Original/
Google-tts-supported-    Language Mappings            *.json files
languages.json          (in-game ↔ ISO codes)
    ↓                        ↓                           ↓
                    Match Languages to Google Voices
                              ↓
                    Check Existing Audio Directories
                              ↓
                    Select Missing Voice Genders
                              ↓
                    Generate WAV Files (Google TTS)
                              ↓
                    Convert WAV to OGG (ffmpeg)
                              ↓
                    Archive Results & Cleanup
```

## Key Logic Components

### 1. Translation JSON Parsing Logic
- **Filter by prefixes**: Only keeps keys starting with `item.minecraft.`, `entity.minecraft.`, `block.minecraft.`, `biome.minecraft.`
- **Validate against reference**: Drops keys not present in `en_us_processed.json` to ensure consistency
- **Track missing keys**: Logs which translation keys are missing for each language

### 2. HTML Language Table Parsing Logic
- **Extract language mappings**: Parses complex HTML table from Minecraft Wiki
- **Map in-game codes to ISO codes**: Creates mapping like `af_za → afr_ZA`
- **Handle table structure**: Accounts for multi-row headers and specific column indices (in-game code at index 4, ISO code at index 5)

### 3. Voice Model Selection Logic
- **Check existing directories**: Scans for `{language}-*-{gender}-*` folders to avoid regeneration
- **Priority system**: Premium Female → Premium Male → Standard Female → Standard Male
- **Gender-aware selection**: Only generates missing genders when some audio already exists
- **Skip optimization**: Completely skips languages where both male and female voices exist

#### Voice Selection Examples:
- **No existing audio**: Generates female voice (highest priority)
- **Female exists, male missing**: Generates only male voice
- **Male exists, female missing**: Generates only female voice  
- **Both exist**: Skips language entirely

## File Structure

```
AudioProject/
├── main.py                           # Main orchestration script
├── Scripts/
│   └── Google-tts_supported_voices.py # Fetches available Google TTS voices
├── Reference_Files/
│   ├── Minecraft_languages_table.html # Language mapping table from wiki
│   ├── Google-tts-supported-languages.json # Available Google voices
│   └── en_us_processed.json          # Reference translation keys
├── Translations_Original/            # Raw Minecraft translation files
├── Translations/                     # Processed translation files
├── Logs/                            # Execution logs
├── Archive/                         # Versioned results
└── {language}-{voice}-{gender}-{format}/ # Generated audio directories
```

## Python Files

| File | Purpose |
|------|---------|
| `main.py` | Orchestrates the entire workflow from user input to final archiving with comprehensive error handling and logging. |
| `io_helpers.py` | Provides utility functions for file operations, JSON handling, directory management, and progress tracking. |
| `preprocess_translations.py` | Cleans raw Minecraft translation files by filtering prefixes and validating against English reference keys. |
| `voice_selector.py` | Matches Minecraft languages to Google TTS voices and selects optimal voice models based on priority and existing audio. |
| `audio_generator.py` | Handles Google TTS synthesis to WAV files and ffmpeg conversion to OGG format with skip logic for existing files. |
| `archive_manager.py` | Creates versioned archives containing translations, reference files, and only relevant OGG files matching processed translations. |
| `Scripts/Google-tts_supported_voices.py` | Fetches the latest available Google TTS voices and saves them to the reference directory for voice matching. |

## Prerequisites

### Required Software
- Python 3.11+
- ffmpeg (for audio conversion)
- Google Cloud Text-to-Speech API access

### Python Dependencies
```bash
pip install beautifulsoup4 tqdm google-cloud-texttospeech
```

### Google Cloud Setup
1. Create a Google Cloud project
2. Enable the Text-to-Speech API
3. Create a service account with TTS permissions
4. Download credentials JSON and set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

## Usage

### Basic Execution
```bash
python3 main.py
```

The script will:
1. Use version `1.21.4` (or prompt for input if modified)
2. Process all translation files in `Translations_Original/`
3. Generate audio for missing voice genders only
4. Archive results to `Archive/{version}/`

### Manual Language Table Update
When new Minecraft versions are released:
1. Visit https://minecraft.fandom.com/wiki/Language
2. Copy the "Available Languages" table HTML
3. Replace content in `Reference_Files/Minecraft_languages_table.html`

## Features

### Smart Audio Generation
- **Existing file detection**: Automatically skips regenerating existing audio
- **Gender-aware processing**: Only generates missing male/female voices
- **Efficient API usage**: Minimizes Google TTS API calls and costs

### Robust Processing
- **Version management**: Handles version conflicts with automatic run numbering
- **Error handling**: Graceful handling of quota limits, missing files, and network issues
- **Comprehensive logging**: Detailed logs with timestamps and statistics

### Quality Output
- **High-quality audio**: LINEAR16 format at 24kHz sample rate
- **Universal compatibility**: OGG Vorbis format for broad platform support
- **Organized structure**: Clear directory naming and systematic file organization

## Output

### Generated Directories
- `{language}-{voice}-female-WAV/` - High-quality WAV files
- `{language}-{voice}-female-OGG/` - Compressed OGG files
- Similar male directories if both genders are available

### Archive Structure
```
Archive/{version}/
├── Translations/          # Processed translation files
├── Reference_Files/       # Language mappings and voice data
└── {language}-{voice}-{gender}-OGG/  # Only relevant OGG files
```

## Example Output

```
Processing af_za (1/1)
Generating audio for af_za using af-ZA-Standard-A
  Existing audio: female=True, male=False
  Need to generate: male
  Matched to af-ZA with 1 voice(s): male (af-ZA-Standard-B)

Made block.minecraft.stone.wav | "Klip" | af-ZA-Standard-B-male-WAV
Made block.minecraft.stone.ogg | "Klip" | af-ZA-Standard-B-male-OGG
Skipped item.minecraft.apple.wav (exists) | af-ZA-Standard-A-female-WAV
Skipped item.minecraft.apple.ogg (exists) | af-ZA-Standard-A-female-OGG
```

## Troubleshooting

### Common Issues
- **Google quota exceeded**: Wait for quota reset or increase limits
- **ffmpeg not found**: Install ffmpeg and ensure it's in PATH
- **Missing translation files**: Place Minecraft .json files in `Translations_Original/`
- **Language table parsing errors**: Update `Minecraft_languages_table.html` with latest wiki content

### Debug Information
- Check `Logs/log.txt` for detailed execution logs
- Verify Google Cloud credentials and API access
- Ensure translation files follow Minecraft naming conventions

## Contributing

When adding new features:
1. Maintain the existing code style and patterns
2. Add comprehensive error handling and logging
3. Update this README with new functionality
4. Test with multiple language files and edge cases

## License

This project is for educational and personal use. Respect Minecraft's terms of service and Google Cloud's usage policies.