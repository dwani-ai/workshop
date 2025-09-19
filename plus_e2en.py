import dwani
import os
import pyaudio
import wave
import time

# Set API key and base URL from environment variables
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

# Validate environment variables
if not dwani.api_key or not dwani.api_base:
    raise ValueError("Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")

# Audio recording settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
RECORD_SECONDS = 5

def record_audio(output_file):
    """Record audio for 5 seconds and save to a WAV file."""
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    
    print("Recording for 5 seconds... (say 'exit' to stop)")
    frames = []
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    print("Recording finished.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save to WAV file
    with wave.open(output_file, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    return output_file

def play_audio(file_path):
    """Play an audio file."""
    try:
        wf = wave.open(file_path, 'rb')
        audio = pyaudio.PyAudio()
        stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
        
        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
    except Exception as e:
        print(f"Playback Error: {e}")

def text_to_speech(text, language, output_file):
    """Convert text to speech and save to file."""
    try:
        response = dwani.Audio.speech(
            input=text,
            response_format="mp3",
            language=language
        )
        with open(output_file, "wb") as audio_file:
            audio_file.write(response)
        print(f"Audio file saved as {output_file}")
        return output_file
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def speech_to_text(audio_file, language):
    """Transcribe audio to text."""
    try:
        result = dwani.ASR.transcribe(file_path=audio_file, language=language)
        return result['text']
    except Exception as e:
        print(f"ASR Error: {e}")
        return None

def get_chat_response(prompt, source_language, target_language):
    """Get response from chat API."""
    try:
        response = dwani.Chat.create(prompt, source_language, target_language)
        return response["response"]
    except Exception as e:
        print(f"Chat Error: {e}")
        return None

def main_conversation_loop():
    language = "kannada"
    conversation_active = True

    print("Voice conversation started. Speak for 5 seconds at a time. Say 'exit' to stop.")
    while conversation_active:
        # Record audio
        input_audio = f"input_{int(time.time())}.wav"
        record_audio(input_audio)

        # Transcribe audio to text
        text = speech_to_text(input_audio, language)
        if text:
            print(f"Transcribed: {text}")
            # Check for exit command
            if "exit" in text.lower():
                print("Exiting conversation.")
                conversation_active = False
                # Clean up input audio file
                if os.path.exists(input_audio):
                    os.remove(input_audio)
                break

            # Get chat response
            response_text = get_chat_response(text, language, language)
            if response_text:
                print(f"Response: {response_text}")
                # Convert response to audio
                output_audio = f"response_{int(time.time())}.mp3"
                audio_file = text_to_speech(response_text, language, output_audio)
                if audio_file:
                    # Play the response audio
                    play_audio(audio_file)
                    # Clean up response audio file
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
            else:
                print("No response generated. Please try again.")

        # Clean up input audio file
        if os.path.exists(input_audio):
            os.remove(input_audio)

if __name__ == "__main__":
    try:
        main_conversation_loop()
    except KeyboardInterrupt:
        print("\nConversation terminated by user.")
    except Exception as e:
        print(f"Fatal Error: {e}")