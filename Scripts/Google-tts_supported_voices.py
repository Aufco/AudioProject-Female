from google.cloud import texttospeech
import sys
import json

def list_voices():
    """Lists the available voices from Google Cloud Text-to-Speech and saves to a JSON file."""
    try:
        client = texttospeech.TextToSpeechClient()
        voices = client.list_voices()

        output = []

        for voice in voices.voices:
            voice_info = {
                "name": voice.name,
                "language_codes": list(voice.language_codes),
                "ssml_gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
            }
            output.append(voice_info)

        # Save to file in Reference_Files
        import os
        reference_dir = os.path.join(os.path.dirname(__file__), "..", "Reference_Files")
        os.makedirs(reference_dir, exist_ok=True)
        output_path = os.path.join(reference_dir, "Google-tts-supported-languages.json")
        
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Voice list saved to {output_path}")

    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_voices()
