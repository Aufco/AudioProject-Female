import os
import subprocess
from google.cloud import texttospeech
from io_helpers import ensure_directory, log_message

class AudioGenerator:
    def __init__(self, log_file):
        self.client = texttospeech.TextToSpeechClient()
        self.log_file = log_file
        
    def make_wav(self, voice_name, text, output_path):
        """
        Generate WAV audio using Google Text-to-Speech.
        
        Args:
            voice_name: Google TTS voice name (e.g., 'af-ZA-Standard-A')
            text: Text to synthesize
            output_path: Path to save WAV file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            ensure_directory(os.path.dirname(output_path))
            
            # Extract language code from voice name
            language_code = '-'.join(voice_name.split('-')[:2])
            
            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # Configure audio output (LINEAR16 format, mono, default sample rate)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000  # Standard sample rate
            )
            
            # Perform synthesis
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice, 
                audio_config=audio_config
            )
            
            # Write audio to file
            with open(output_path, 'wb') as f:
                f.write(response.audio_content)
            
            return True
            
        except Exception as e:
            error_msg = f"Error generating WAV for '{text}': {e}"
            print(error_msg)
            log_message(self.log_file, error_msg)
            return False
    
    def wav_to_ogg(self, wav_path, ogg_path):
        """
        Convert WAV file to OGG Vorbis format using ffmpeg.
        
        Args:
            wav_path: Input WAV file path
            ogg_path: Output OGG file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            ensure_directory(os.path.dirname(ogg_path))
            
            # Run ffmpeg conversion
            cmd = [
                'ffmpeg', 
                '-hide_banner', 
                '-loglevel', 'error',
                '-i', wav_path,
                '-c:a', 'libvorbis',
                '-y',  # Overwrite output file
                ogg_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                error_msg = f"FFmpeg error converting {wav_path}: {result.stderr}"
                print(error_msg)
                log_message(self.log_file, error_msg)
                return False
                
        except FileNotFoundError:
            error_msg = "Error: ffmpeg not found in PATH. Please install ffmpeg."
            print(error_msg)
            log_message(self.log_file, error_msg)
            return False
        except Exception as e:
            error_msg = f"Error converting {wav_path} to OGG: {e}"
            print(error_msg)
            log_message(self.log_file, error_msg)
            return False

def generate_audio_for_language(translation_file, voice_info, wav_dir, ogg_dir, log_file, bucket_manager=None, skip_existing=True):
    """
    Generate audio files for all entries in a translation file.
    
    Args:
        translation_file: Path to processed translation JSON file
        voice_info: Voice information dictionary
        wav_dir: Directory for WAV files
        ogg_dir: Directory for OGG files  
        log_file: Path to log file
        bucket_manager: BucketManager instance for checking existing files
        skip_existing: Whether to skip existing files
        
    Returns:
        dict: Statistics about audio generation
    """
    from io_helpers import load_json
    
    # Load translation data
    translation_data = load_json(translation_file)
    if not translation_data:
        return None
    
    # Initialize audio generator
    generator = AudioGenerator(log_file)
    
    # Ensure directories exist
    ensure_directory(wav_dir)
    ensure_directory(ogg_dir)
    
    # Initialize counters
    stats = {
        'wav_made': 0,
        'wav_skipped': 0,
        'ogg_made': 0, 
        'ogg_skipped': 0,
        'wav_failed': 0,
        'ogg_failed': 0,
        'total_entries': len(translation_data)
    }
    
    # Get voice information
    voices = voice_info['voices']
    if not voices:
        print(f"No voices available for {voice_info['in_game_code']}")
        return stats
    
    # Use first available voice
    voice_name, _ = voices[0]
    
    print(f"Generating audio for {voice_info['in_game_code']} using {voice_name}")
    
    # Process each translation entry
    for key, text in translation_data.items():
        if not text or not text.strip():
            continue
            
        # Generate file paths
        wav_filename = f"{key}.wav"
        ogg_filename = f"{key}.ogg"
        wav_path = os.path.join(wav_dir, wav_filename)
        ogg_path = os.path.join(ogg_dir, ogg_filename)
        
        # Check if files exist in bucket (if bucket_manager is provided)
        wav_exists_in_bucket = False
        ogg_exists_in_bucket = False
        
        if bucket_manager and skip_existing:
            from bucket_manager import check_file_exists_in_bucket
            wav_exists_in_bucket = check_file_exists_in_bucket(bucket_manager, voice_name, "WAV", wav_filename)
            ogg_exists_in_bucket = check_file_exists_in_bucket(bucket_manager, voice_name, "OGG", ogg_filename)
        
        # Generate WAV file
        local_wav_exists = os.path.exists(wav_path)
        should_skip_wav = skip_existing and (local_wav_exists or wav_exists_in_bucket)
        
        if should_skip_wav:
            stats['wav_skipped'] += 1
            skip_reason = "local" if local_wav_exists else "bucket"
            print(f"Skipped {wav_filename} (exists in {skip_reason}) | {os.path.basename(wav_dir)}")
        else:
            if generator.make_wav(voice_name, text, wav_path):
                stats['wav_made'] += 1
                print(f"Made {wav_filename} | \"{text}\" | {os.path.basename(wav_dir)}")
            else:
                stats['wav_failed'] += 1
                continue
        
        # Convert to OGG
        local_ogg_exists = os.path.exists(ogg_path)
        should_skip_ogg = skip_existing and (local_ogg_exists or ogg_exists_in_bucket)
        
        if should_skip_ogg:
            stats['ogg_skipped'] += 1
            skip_reason = "local" if local_ogg_exists else "bucket"
            print(f"Skipped {ogg_filename} (exists in {skip_reason}) | {os.path.basename(ogg_dir)}")
        else:
            if os.path.exists(wav_path):  # Only convert if WAV exists
                if generator.wav_to_ogg(wav_path, ogg_path):
                    stats['ogg_made'] += 1
                    print(f"Made {ogg_filename} | \"{text}\" | {os.path.basename(ogg_dir)}")
                else:
                    stats['ogg_failed'] += 1
            else:
                stats['ogg_failed'] += 1
    
    return stats

def create_audio_directories(voice_info):
    """
    Create WAV and OGG directories for a voice.
    
    Args:
        voice_info: Voice information dictionary
        
    Returns:
        tuple: (wav_dir, ogg_dir) paths
    """
    if not voice_info['voices']:
        return None, None
    
    voice_name, _ = voice_info['voices'][0]
    
    # Create directory names
    wav_dir = f"{voice_name}-female-WAV"
    ogg_dir = f"{voice_name}-female-OGG"
    
    # Ensure directories exist
    ensure_directory(wav_dir)
    ensure_directory(ogg_dir)
    
    return wav_dir, ogg_dir