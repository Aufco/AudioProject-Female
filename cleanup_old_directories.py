#!/usr/bin/env python3
"""
Delete old Neural2 directories for languages that changed to Chirp3-HD
"""

import subprocess
import sys

def run_gcloud_command(command):
    """Run a gcloud command and return success/failure"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def delete_directory(bucket_path):
    """Delete a directory and all its contents from the bucket"""
    command = f"gcloud storage rm -r {bucket_path}"
    success, output = run_gcloud_command(command)
    return success, output

def main():
    """Delete old Neural2 directories for the 14 languages that changed"""
    
    # The 14 languages that changed from Neural2 to Chirp3-HD
    languages_to_cleanup = [
        "en-AU-Neural2-A",
        "vi-VN-Neural2-A", 
        "es-ES-Neural2-A",
        "th-TH-Neural2-C",
        "pt-BR-Neural2-A",
        "fr-FR-Neural2-F",
        "ko-KR-Neural2-A",
        "it-IT-Neural2-A",
        "fr-CA-Neural2-A",
        "hi-IN-Neural2-A",
        "ja-JP-Neural2-B",
        "en-US-Neural2-C",
        "en-GB-Neural2-A",
        "de-DE-Neural2-G"
    ]
    
    bucket_base = "gs://myproject-461901-bucket/AudioProject-Female/"
    
    print("Deleting old Neural2 directories for languages that changed to Chirp3-HD...")
    print("=" * 80)
    
    deleted_count = 0
    failed_count = 0
    
    for language_voice in languages_to_cleanup:
        # Delete both OGG and WAV directories
        ogg_dir = f"{bucket_base}{language_voice}-female-OGG/"
        wav_dir = f"{bucket_base}{language_voice}-female-WAV/"
        
        print(f"\nDeleting {language_voice}...")
        
        # Delete OGG directory
        success, output = delete_directory(ogg_dir)
        if success:
            print(f"✓ Deleted: {ogg_dir}")
            deleted_count += 1
        else:
            print(f"✗ Failed to delete: {ogg_dir}")
            print(f"  Error: {output}")
            failed_count += 1
        
        # Delete WAV directory
        success, output = delete_directory(wav_dir)
        if success:
            print(f"✓ Deleted: {wav_dir}")
            deleted_count += 1
        else:
            print(f"✗ Failed to delete: {wav_dir}")
            print(f"  Error: {output}")
            failed_count += 1
    
    print("\n" + "=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"Directories successfully deleted: {deleted_count}")
    print(f"Directories that failed to delete: {failed_count}")
    
    if failed_count == 0:
        print("✓ All old Neural2 directories successfully deleted!")
        print("✓ Ready to generate new Chirp3-HD audio files")
    else:
        print("⚠ Some directories failed to delete - check errors above")
    
    return failed_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)