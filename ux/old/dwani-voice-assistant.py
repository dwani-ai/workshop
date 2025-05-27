import gradio as gr
import requests
import os
from pathlib import Path
from pydub import AudioSegment
import logging
import time
import atexit

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# In-memory metrics storage
METRICS = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_processing_time": 0.0,
    "total_api_time": 0.0,
    "total_conversion_time": 0.0,
    "request_count_for_avg": 0
}

# Cleanup temporary files
def cleanup():
    for file in ["converted_audio.wav", "output_audio.wav"]:
        if os.path.exists(file):
            os.remove(file)
atexit.register(cleanup)

def log_metrics(language):
    """Log metrics summary to app.log."""
    avg_processing = (
        METRICS["total_processing_time"] / METRICS["request_count_for_avg"]
        if METRICS["request_count_for_avg"] > 0 else 0.0
    )
    avg_api = (
        METRICS["total_api_time"] / METRICS["request_count_for_avg"]
        if METRICS["request_count_for_avg"] > 0 else 0.0
    )
    avg_conversion = (
        METRICS["total_conversion_time"] / METRICS["request_count_for_avg"]
        if METRICS["request_count_for_avg"] > 0 else 0.0
    )
    success_rate = (
        (METRICS["successful_requests"] / METRICS["total_requests"] * 100)
        if METRICS["total_requests"] > 0 else 0.0
    )

    logger.info(
        f"Metrics Summary: Total Requests={METRICS['total_requests']}, "
        f"Successful={METRICS['successful_requests']}, Failed={METRICS['failed_requests']}, "
        f"Success Rate={success_rate:.2f}%, "
        f"Avg Processing Time={avg_processing:.2f}s, "
        f"Avg API Time={avg_api:.2f}s, "
        f"Avg Conversion Time={avg_conversion:.2f}s, Language={language}"
    )

def process_audio(audio, language):
    start_time = time.time()
    METRICS["total_requests"] += 1
    status_message = f"Processing audio in {language}..."

    if audio is None or not os.path.isfile(audio):
        METRICS["failed_requests"] += 1
        total_time = time.time() - start_time
        METRICS["total_processing_time"] += total_time
        METRICS["request_count_for_avg"] += 1
        logger.info(f"Failed request (no audio): Total time={total_time:.2f}s, Language={language}")
        log_metrics(language)
        return None, f"Error: No valid audio recorded. Total time: {total_time:.2f}s"

    try:
        # Convert audio to WAV, 16kHz, mono using pydub
        conversion_start = time.time()
        audio_segment = AudioSegment.from_file(audio)
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
        converted_audio = "converted_audio.wav"
        audio_segment.export(converted_audio, format="wav")
        conversion_time = time.time() - conversion_start
        METRICS["total_conversion_time"] += conversion_time
        logger.info(f"Audio conversion took {conversion_time:.2f}s, Language={language}")

        # Get the base URL (IP or domain) from environment variable
        base_url = os.getenv("DWANI_AI_API_BASE_URL")

        if not base_url:
            raise ValueError("DWANI_AI_API_BASE_URL environment variable is not set")

        # Define the endpoint path
        endpoint = "/v1/speech_to_speech?language"

        # Construct the full API URL
        url = f"{base_url.rstrip('/')}{endpoint}={language.lower()}"

        headers = {"accept": "application/json"}
        api_start = time.time()
        with open(converted_audio, "rb") as audio_file:
            files = {"file": (f"{language.lower()}_sample.wav", audio_file, "audio/x-wav")}
            response = requests.post(url, headers=headers, files=files, timeout=60)
        api_time = time.time() - api_start
        METRICS["total_api_time"] += api_time
        logger.info(f"API response took {api_time:.2f}s, Language={language}")

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "audio" not in content_type:
                METRICS["failed_requests"] += 1
                total_time = time.time() - start_time
                METRICS["total_processing_time"] += total_time
                METRICS["request_count_for_avg"] += 1
                logger.info(f"Failed request (non-audio response): Total time={total_time:.2f}s, Language={language}")
                log_metrics(language)
                return None, f"Error: API returned non-audio content: {response.text}"
            
            output_audio_path = "output_audio.wav"
            with open(output_audio_path, "wb") as f:
                f.write(response.content)
            METRICS["successful_requests"] += 1
            total_time = time.time() - start_time
            METRICS["total_processing_time"] += total_time
            METRICS["request_count_for_avg"] += 1
            logger.info(
                f"Successful request: Total time={total_time:.2f}s, "
                f"API time={api_time:.2f}s, Conversion time={conversion_time:.2f}s, Language={language}"
            )
            log_metrics(language)
            return output_audio_path, "Processing complete."
        else:
            METRICS["failed_requests"] += 1
            total_time = time.time() - start_time
            METRICS["total_processing_time"] += total_time
            METRICS["request_count_for_avg"] += 1
            try:
                error_details = response.json()
                logger.info(f"Failed request (API error): Total time={total_time:.2f}s, Language={language}")
                log_metrics(language)
                return None, f"API Error {response.status_code}: {error_details.get('message', response.text)}"
            except ValueError:
                logger.info(f"Failed request (API error, non-JSON): Total time={total_time:.2f}s, Language={language}")
                log_metrics(language)
                return None, f"API Error {response.status_code}: {response.text}"

    except requests.exceptions.Timeout:
        METRICS["failed_requests"] += 1
        total_time = time.time() - start_time
        METRICS["total_processing_time"] += total_time
        METRICS["request_count_for_avg"] += 1
        logger.info(f"Failed request (timeout): Total time={total_time:.2f}s, Language={language}")
        log_metrics(language)
        return None, "Error: API request timed out."
    except requests.exceptions.ConnectionError:
        METRICS["failed_requests"] += 1
        total_time = time.time() - start_time
        METRICS["total_processing_time"] += total_time
        METRICS["request_count_for_avg"] += 1
        logger.info(f"Failed request (connection error): Total time={total_time:.2f}s, Language={language}")
        log_metrics(language)
        return None, "Error: Failed to connect to the API."
    except Exception as e:
        METRICS["failed_requests"] += 1
        total_time = time.time() - start_time
        METRICS["total_processing_time"] += total_time
        METRICS["request_count_for_avg"] += 1
        logger.error(f"Error processing audio: {str(e)}, Total time={total_time:.2f}s, Language={language}")
        log_metrics(language)
        return None, f"Error: {str(e)}"

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("""
    # dwani.ai - Voice Assistant for India
    1. Select a language (Kannada, Tamil, or Hindi).
    2. Record audio using the microphone.
    3. Click 'Process Audio' to send it to the API.
    4. Listen to the processed audio in the output section.
    **Note**: Ensure your audio is clear and in the selected language.
    """)

    language_dropdown = gr.Dropdown(
        choices=["Kannada", "Tamil", "Hindi"],
        label="Select Language",
        value="Kannada"  # Default value
    )
    audio_input = gr.Audio(sources=["microphone"], type="filepath", label="Record Audio")
    process_button = gr.Button("Process Audio")
    audio_output = gr.Audio(label="Processed Audio", type="filepath")
    status_message = gr.Textbox(label="Status", interactive=False)
    reset_button = gr.Button("Reset")

    process_button.click(
        fn=process_audio,
        inputs=[audio_input, language_dropdown],
        outputs=[audio_output, status_message]
    )
    reset_button.click(
        fn=lambda: (None, None, "", "Kannada"),
        outputs=[audio_input, audio_output, status_message, language_dropdown]
    )

# Launch the app
demo.launch()