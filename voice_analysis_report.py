#!/usr/bin/env python3
"""
Voice model analysis report - shows what would change with new priority order
"""

import json
import csv
from google.cloud import texttospeech

def load_current_selections():
    """Load current voice selections from language_table.csv"""
    current_selections = {}
    try:
        with open('language_table.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Voice name'] and row['Language code']:
                    current_selections[row['Language code']] = {
                        'voice_name': row['Voice name'],
                        'voice_type': row['Voice type']
                    }
    except FileNotFoundError:
        print("language_table.csv not found")
    return current_selections

def load_available_voices():
    """Load available voices from Google TTS API"""
    try:
        with open('Reference_Files/Google-tts-supported-languages.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Fetching voices from Google TTS API...")
        client = texttospeech.TextToSpeechClient()
        response = client.list_voices()
        voices_data = []
        for voice in response.voices:
            voices_data.append({
                'name': voice.name,
                'language_codes': list(voice.language_codes),
                'ssml_gender': voice.ssml_gender.name,
                'natural_sample_rate_hertz': voice.natural_sample_rate_hertz
            })
        return voices_data

def get_voice_priority(voice_name):
    """Get priority score for voice (lower = higher priority)"""
    if 'Chirp3-HD' in voice_name:
        return 1
    elif 'Chirp-HD' in voice_name:
        return 2
    elif 'Neural2' in voice_name:
        return 3
    elif 'WaveNet' in voice_name:
        return 4
    else:
        return 5  # Standard voices

def select_new_voice_for_language(language_code, available_voices):
    """Select voice using new priority order"""
    # Find all female voices for this language
    female_voices = []
    for voice in available_voices:
        if (language_code in voice['language_codes'] and 
            voice['ssml_gender'] == 'FEMALE'):
            female_voices.append(voice)
    
    if not female_voices:
        return None
    
    # Sort by priority (Chirp3-HD > Chirp-HD > Neural2 > others)
    female_voices.sort(key=lambda v: get_voice_priority(v['name']))
    
    return female_voices[0]['name']

def get_voice_type(voice_name):
    """Get voice type from voice name"""
    if 'Chirp3-HD' in voice_name:
        return 'Chirp3-HD'
    elif 'Chirp-HD' in voice_name:
        return 'Chirp-HD'
    elif 'Neural2' in voice_name:
        return 'Neural2'
    elif 'WaveNet' in voice_name:
        return 'WaveNet'
    else:
        return 'Standard'

def generate_report():
    """Generate voice change analysis report"""
    print("Loading current voice selections...")
    current_selections = load_current_selections()
    
    print("Loading available voices...")
    available_voices = load_available_voices()
    
    changes = []
    no_changes = []
    
    print("\nAnalyzing voice selection changes...\n")
    
    for language_code, current in current_selections.items():
        new_voice = select_new_voice_for_language(language_code, available_voices)
        
        if new_voice and new_voice != current['voice_name']:
            changes.append({
                'language': language_code,
                'old_voice': current['voice_name'],
                'old_type': current['voice_type'],
                'new_voice': new_voice,
                'new_type': get_voice_type(new_voice)
            })
        else:
            no_changes.append({
                'language': language_code,
                'voice': current['voice_name'],
                'type': current['voice_type']
            })
    
    # Print results
    print("=" * 80)
    print("VOICE MODEL ANALYSIS REPORT")
    print("=" * 80)
    print(f"New Priority Order: Chirp3-HD > Chirp-HD > Neural2 > WaveNet > Standard")
    print()
    
    print("LANGUAGES THAT WOULD CHANGE:")
    print("=" * 80)
    
    for change in changes:
        print(f"\n{change['language']}:")
        print(f"  OLD: {change['old_voice']} ({change['old_type']})")
        print(f"  NEW: {change['new_voice']} ({change['new_type']})")
    
    print(f"\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Languages that would change: {len(changes)}")
    print(f"Languages with no changes: {len(no_changes)}")
    
    if changes:
        print(f"\nFiles to be deleted from bucket (if proceeding):")
        for change in changes:
            print(f"  - {change['language']}-{change['old_voice']}.ogg")
            print(f"  - {change['language']}-{change['old_voice']}.wav")
    
    print(f"\nTo proceed with changes, run the full script with interactive mode")
    return changes, no_changes

if __name__ == "__main__":
    generate_report()