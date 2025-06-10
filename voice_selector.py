import re
import os
from bs4 import BeautifulSoup
from io_helpers import load_json

def parse_minecraft_language_table(html_file):
    """
    Parse the Minecraft languages HTML table to extract language mappings.
    
    Args:
        html_file: Path to the HTML file
        
    Returns:
        dict: Mapping of in-game codes to ISO-639-3 codes
    """
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        table = soup.find('table', class_='wikitable')
        
        if not table:
            raise ValueError("Could not find wikitable in HTML file")
        
        # Analyze table structure - the header is complex with multiple rows
        # Based on analysis: in-game code is at index 4, ISO code is at index 5
        in_game_idx = 4
        iso_idx = 5
        
        # Extract data rows
        language_mapping = {}
        tbody = table.find('tbody')
        
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > max(in_game_idx, iso_idx):
                in_game_code = cells[in_game_idx].get_text().strip()
                iso_code = cells[iso_idx].get_text().strip()
                
                if in_game_code and iso_code and in_game_code != '–' and iso_code != '–':
                    language_mapping[in_game_code] = iso_code
        
        
        print(f"Parsed {len(language_mapping)} language mappings from HTML table")
        return language_mapping
        
    except Exception as e:
        print(f"Error parsing Minecraft language table: {e}")
        return None

def convert_language_code(in_game_code):
    """
    Convert in-game language code from ll_cc to ll-CC format.
    
    Args:
        in_game_code: Language code like 'af_za'
        
    Returns:
        str: Converted code like 'af-ZA'
    """
    if '_' in in_game_code:
        parts = in_game_code.split('_')
        if len(parts) == 2:
            return f"{parts[0].lower()}-{parts[1].upper()}"
    return in_game_code

def find_matching_google_language(in_game_code, iso_code, google_voices):
    """
    Find matching Google language code for a Minecraft language.
    
    Args:
        in_game_code: Minecraft in-game language code
        iso_code: ISO-639-3 language code
        google_voices: List of Google voice data
        
    Returns:
        str or None: Matching Google language code
    """
    # Get all unique language codes from Google voices
    google_lang_codes = set()
    for voice in google_voices:
        for lang_code in voice.get('language_codes', []):
            google_lang_codes.add(lang_code.lower().replace('_', '-'))
    
    # Try exact match with converted in-game code
    converted_code = convert_language_code(in_game_code).lower().replace('_', '-')
    if converted_code in google_lang_codes:
        # Find the original format from Google voices
        for voice in google_voices:
            for lang_code in voice.get('language_codes', []):
                if lang_code.lower().replace('_', '-') == converted_code:
                    return lang_code
    
    # Try ISO code match
    iso_lower = iso_code.lower().replace('_', '-')
    if iso_lower in google_lang_codes:
        for voice in google_voices:
            for lang_code in voice.get('language_codes', []):
                if lang_code.lower().replace('_', '-') == iso_lower:
                    return lang_code
    
    return None

def check_existing_audio_directories(google_language_code):
    """
    Check what audio directories already exist for a Google language code.
    Only checks for female voices since this project generates female-only audio.
    
    Args:
        google_language_code: Google language code (e.g., 'af-ZA')
        
    Returns:
        bool: True if female voice already exists, False otherwise
    """
    try:
        # Look for directories matching the pattern: {google_language_code}-*-female-*
        current_dir = "."
        for item in os.listdir(current_dir):
            if os.path.isdir(item) and item.startswith(google_language_code + "-"):
                # Parse directory name to extract gender
                if "-female-" in item:
                    return True
    except Exception as e:
        print(f"Warning: Could not check existing directories: {e}")
    
    return False

def select_voices_for_language(language_code, google_voices, required_genders=None):
    """
    Select the best female voice for a given language following priority rules.
    This project only generates female voices.
    
    Args:
        language_code: Google language code
        google_voices: List of Google voice data
        required_genders: Ignored - always selects female voice only
        
    Returns:
        list: List of tuples (voice_name, gender) with single female voice
    """
    # Filter voices for this language
    matching_voices = []
    for voice in google_voices:
        if language_code in voice.get('language_codes', []):
            matching_voices.append(voice)
    
    if not matching_voices:
        return []
    
    # Categorize female voices by type
    premium_female = []
    standard_female = []
    
    for voice in matching_voices:
        name = voice.get('name', '')
        gender = voice.get('ssml_gender', '')
        
        # Only process female voices
        if gender == 'FEMALE':
            is_premium = 'WaveNet' in name or 'Neural2' in name or 'Journey' in name or 'Studio' in name
            
            if is_premium:
                premium_female.append(voice)
            else:
                standard_female.append(voice)
    
    # Select best female voice following priority: Premium Female > Standard Female
    if premium_female:
        return [(premium_female[0]['name'], 'female')]
    elif standard_female:
        return [(standard_female[0]['name'], 'female')]
    else:
        return []

def match_languages_to_voices(processed_translations_dir, html_table_file, google_voices_file, used_languages=None):
    """
    Match processed translation files to Google voices.
    
    Args:
        processed_translations_dir: Directory with processed translation files
        html_table_file: Path to Minecraft languages HTML table
        google_voices_file: Path to Google voices JSON file
        used_languages: Set of already used language codes
        
    Returns:
        dict: Mapping of translation files to voice information
    """
    if used_languages is None:
        used_languages = set()
    
    # Load Google voices
    google_voices = load_json(google_voices_file)
    if not google_voices:
        print("Error: Could not load Google voices file")
        return {}
    
    # Parse language mapping table
    language_mapping = parse_minecraft_language_table(html_table_file)
    if not language_mapping:
        print("Error: Could not parse language mapping table")
        return {}
    
    # Get processed translation files
    import os
    translation_files = []
    if os.path.exists(processed_translations_dir):
        for file in os.listdir(processed_translations_dir):
            if file.endswith('_processed.json'):
                in_game_code = file.replace('_processed.json', '')
                translation_files.append((file, in_game_code))
    
    language_voice_mapping = {}
    
    for filename, in_game_code in translation_files:
        print(f"Processing language: {in_game_code}")
        
        # Get ISO code from mapping
        iso_code = language_mapping.get(in_game_code, '')
        
        # Find matching Google language
        google_lang_code = find_matching_google_language(in_game_code, iso_code, google_voices)
        
        if not google_lang_code:
            print(f"  No matching Google language found for {in_game_code}")
            continue
        
        # Check if language already used
        if google_lang_code in used_languages:
            print(f"  Language {google_lang_code} already used, skipping")
            continue
        
        # Check existing audio directories
        female_exists = check_existing_audio_directories(google_lang_code)
        print(f"  Existing audio: female={female_exists}")
        
        # If female voice already exists, skip this language
        if female_exists:
            print(f"  Female voice already exists for {google_lang_code}, skipping")
            continue
        
        print(f"  Need to generate: female")
        
        # Select female voice for this language
        selected_voices = select_voices_for_language(google_lang_code, google_voices, ['female'])
        
        if not selected_voices:
            print(f"  No supported voices found for {google_lang_code} ({', '.join(required_genders)})")
            continue
        
        # Add to mapping
        language_voice_mapping[filename] = {
            'in_game_code': in_game_code,
            'google_language_code': google_lang_code,
            'iso_code': iso_code,
            'voices': selected_voices
        }
        
        used_languages.add(google_lang_code)
        voice_info = ", ".join([f"{voice[1]} ({voice[0]})" for voice in selected_voices])
        print(f"  Matched to {google_lang_code} with {len(selected_voices)} voice(s): {voice_info}")
    
    return language_voice_mapping