import os
import json
from io_helpers import load_json, save_json, log_message, get_files_in_directory

ACCEPTED_PREFIXES = [
    "item.minecraft.",
    "entity.minecraft.",
    "block.minecraft.",
    "biome.minecraft."
]

def preprocess_translation_file(input_file, output_dir, reference_keys, log_file):
    """
    Clean a translation file by filtering keys and validating against reference.
    
    Args:
        input_file: Path to input JSON file
        output_dir: Directory to save processed file
        reference_keys: Set of valid keys from en_us_processed.json
        log_file: Path to log file
        
    Returns:
        dict: Statistics about processing (kept, dropped, missing)
    """
    filename = os.path.basename(input_file)
    language_code = filename.replace('.json', '')
    
    # Load the translation file
    data = load_json(input_file)
    if data is None:
        return None
    
    # Filter by accepted prefixes
    filtered_data = {}
    for key, value in data.items():
        if any(key.startswith(prefix) for prefix in ACCEPTED_PREFIXES):
            filtered_data[key] = value
    
    # Keep only keys that exist in reference
    final_data = {}
    missing_keys = []
    
    for key in reference_keys:
        if key in filtered_data:
            final_data[key] = filtered_data[key]
        else:
            missing_keys.append(key)
    
    # Calculate statistics
    stats = {
        'original_count': len(data),
        'filtered_count': len(filtered_data),
        'final_count': len(final_data),
        'missing_count': len(missing_keys)
    }
    
    # Save processed file
    output_file = os.path.join(output_dir, f"{language_code}_processed.json")
    if save_json(final_data, output_file):
        print(f"Processed {filename}: {stats['final_count']} entries kept")
    else:
        print(f"Failed to save processed file for {filename}")
        return None
    
    # Log missing keys
    if missing_keys:
        log_message(log_file, f"\nMissing keys in {language_code}:")
        for key in missing_keys[:10]:  # Log first 10 missing keys
            log_message(log_file, f"  - {key}", timestamp=False)
        if len(missing_keys) > 10:
            log_message(log_file, f"  ... and {len(missing_keys) - 10} more missing keys", timestamp=False)
    
    return stats

def preprocess_all_translations(input_dir, output_dir, reference_file, log_file):
    """
    Process all translation files in the input directory.
    
    Args:
        input_dir: Directory containing raw translation files
        output_dir: Directory to save processed files
        reference_file: Path to en_us_processed.json reference file
        log_file: Path to log file
        
    Returns:
        dict: Overall statistics
    """
    # Load reference keys
    reference_data = load_json(reference_file)
    if reference_data is None:
        print(f"Error: Could not load reference file {reference_file}")
        return None
    
    reference_keys = set(reference_data.keys())
    print(f"Reference file loaded with {len(reference_keys)} keys")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all JSON files in input directory
    input_files = get_files_in_directory(input_dir, '.json')
    if not input_files:
        print(f"No JSON files found in {input_dir}")
        return None
    
    log_message(log_file, f"\n=== Translation Preprocessing Started ===")
    log_message(log_file, f"Processing {len(input_files)} translation files")
    log_message(log_file, f"Reference keys: {len(reference_keys)}")
    
    overall_stats = {
        'files_processed': 0,
        'files_failed': 0,
        'total_entries_kept': 0,
        'total_missing_keys': 0
    }
    
    for input_file in input_files:
        stats = preprocess_translation_file(input_file, output_dir, reference_keys, log_file)
        if stats:
            overall_stats['files_processed'] += 1
            overall_stats['total_entries_kept'] += stats['final_count']
            overall_stats['total_missing_keys'] += stats['missing_count']
        else:
            overall_stats['files_failed'] += 1
    
    log_message(log_file, f"\n=== Preprocessing Summary ===")
    log_message(log_file, f"Files processed: {overall_stats['files_processed']}")
    log_message(log_file, f"Files failed: {overall_stats['files_failed']}")
    log_message(log_file, f"Total entries kept: {overall_stats['total_entries_kept']}")
    log_message(log_file, f"Total missing keys: {overall_stats['total_missing_keys']}")
    
    return overall_stats