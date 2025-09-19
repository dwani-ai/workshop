import dwani
import os

# Set API key and base URL from environment variables
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

# Validate environment variables
if not dwani.api_key or not dwani.api_base:
    raise ValueError("Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")

language = "kannada"
text = "ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ ಯಾವುದು"
output_file = "question_1.mp3"  # Specify the desired file name

try:
    # Generate speech from text
    response = dwani.Audio.speech(
        input=text,
        response_format="mp3",
        language=language
    )
    # Write the response to a file with the specified name
    with open(output_file, "wb") as audio_file:
        audio_file.write(response)
    print(f"Audio file saved as {output_file}")
except Exception as e:
    print(f"Error: {e}")


audio_file = output_file
if not audio_file:
    print("error", "Please upload an audio file")
try:
    result = dwani.ASR.transcribe(file_path=audio_file, language=language)
    print(result)
except Exception as e:
    print(f"Error: {e}")


prompt = result['text']
source_language = "kannada"
target_language = "kannada"

try:
    respone = dwani.Chat.create(prompt, source_language, target_language)
    result = response["response"]
    print(result)
except Exception as e:
    print(f"Error: {e}")


language = "kannada"
text = result
output_file = "answer.mp3"  # Specify the desired file name

try:
    # Generate speech from text
    response = dwani.Audio.speech(
        input=text,
        response_format="mp3",
        language=language
    )
    # Write the response to a file with the specified name
    with open(output_file, "wb") as audio_file:
        audio_file.write(response)
    print(f"Audio file saved as {output_file}")
except Exception as e:
    print(f"Error: {e}")
