import gradio as gr
import requests
import dwani
import os
import tempfile
import logging
from PIL import Image
import urllib.parse
import json
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure dwani API settings
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

# Log API configuration
logger.debug("DWANI_API_KEY: %s", "Set" if dwani.api_key else "Not set")
logger.debug("DWANI_API_BASE_URL: %s", dwani.api_base)

# Validate API configuration
if not dwani.api_key or not dwani.api_base:
    logger.error("API key or base URL not set. Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")
    raise ValueError("Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")

# Shared language options
CHAT_IMAGE_LANGUAGES = ["kannada",  "english", "hindi", "german", "assamese", "punjabi", "bengali", "malayalam", 
    "marathi", "tamil", "gujarati", "telugu",   "odia"]

ASR_LANGUAGES = ["kannada",  "english", "hindi", "german", "assamese", "punjabi", "bengali", "malayalam", 
    "marathi", "tamil", "gujarati", "telugu",   "odia"]


TRANSLATION_LANGUAGES = [
    "assamese", "punjabi", "bengali", "malayalam", "english",
    "marathi", "tamil", "gujarati", "telugu", "hindi", "kannada", "odia"
]
TTS_LANGUAGES = ["kannada",  "english", "hindi", "german", "assamese", "punjabi", "bengali", "malayalam", 
    "marathi", "tamil", "gujarati", "telugu",   "odia"]


# --- Chat Module ---
def chat_api(prompt, language, tgt_language):
    try:
        resp = dwani.Chat.create(prompt, language, tgt_language)
        return resp
    except Exception as e:
        return {"error": f"Chat API error: {str(e)}"}

# --- Image Query Module ---
def visual_query(image, src_lang, tgt_lang, prompt):
    if not image:
        return {"error": "Please upload an image"}
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        image.save(temp_file.name, format="PNG")
        temp_file_path = temp_file.name
    try:
        result = dwani.Vision.caption(
            file_path=temp_file_path,
            query=prompt,
            src_lang=src_lang,
            tgt_lang=tgt_lang
        )
        return result
    except Exception as e:
        return {"error": f"Vision API error: {str(e)}"}
    finally:
        os.unlink(temp_file_path)

# --- Transcription Module ---
def transcribe_api(audio_file, language):
    if not audio_file:
        return {"error": "Please upload an audio file"}
    try:
        result = dwani.ASR.transcribe(file_path=audio_file, language=language)
        return result
    except Exception as e:
        return {"error": f"ASR API error: {str(e)}"}

# --- Translation Module ---
def translate_api(sentences, src_lang, tgt_lang):
    if isinstance(sentences, str):
        sentences = [s.strip() for s in sentences.split(",") if s.strip()]
    elif isinstance(sentences, list):
        sentences = [s.strip() for s in sentences if isinstance(s, str) and s.strip()]
    else:
        return {"error": "Invalid input: sentences must be a string or list of strings"}
    if not sentences:
        return {"error": "Please provide at least one non-empty sentence"}
    try:
        result = dwani.Translate.run_translate(sentences=sentences, src_lang=src_lang, tgt_lang=tgt_lang)
        return result
    except dwani.exceptions.DhwaniAPIError as e:
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# --- PDF Processing Module ---
def process_pdf(pdf_file, page_number, prompt, src_lang, tgt_lang):
    if not pdf_file:
        return {"error": "Please upload a PDF file"}
    if not prompt.strip():
        return {"error": "Please provide a non-empty prompt"}
    try:
        page_number = int(page_number)
        if page_number < 1:
            raise ValueError("Page number must be at least 1")
    except (ValueError, TypeError):
        return {"error": "Page number must be a positive integer"}
    if src_lang not in CHAT_IMAGE_LANGUAGES or tgt_lang not in CHAT_IMAGE_LANGUAGES:
        return {"error": "Invalid source or target language selection"}
    file_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    try:
        result = dwani.Documents.query_all(
            file_path, model="gemma3", tgt_lang="kan_Knda", prompt=prompt
        )
        return {
            "Original Text": result.get("original_text", "N/A"),
            "Response": result.get("query_answer", "N/A"),
            "Translated Response": result.get("translated_query_answer", "N/A")
        }
    except Exception as e:
        return {"error": f"PDF API error: {str(e)}"}

# --- Resume Translation Module ---
def translate_to_kannada(text):
    if not text or text.strip() == "":
        return ""
    try:
        resp = dwani.Translate.run_translate(
            sentences=text,
            src_lang="english",
            tgt_lang="kannada"
        )
        if isinstance(resp, dict):
            translated = resp.get("translated_text")
            if translated:
                return translated.strip()
            if "translations" in resp and isinstance(resp["translations"], list):
                return " ".join(t.strip() for t in resp["translations"] if isinstance(t, str))
            return str(resp).strip()
        return resp.strip() if isinstance(resp, str) else str(resp).strip()
    except Exception as e:
        return f"Translation error: {str(e)}"

def extract_text_from_response(chat_response):
    if isinstance(chat_response, dict):
        for key in ("text", "response", "content"):
            if key in chat_response and isinstance(chat_response[key], str):
                return chat_response[key]
        return str(chat_response)
    return str(chat_response)

def extract_resume_sections(extracted_resume):
    resume_str = str(extracted_resume)
    prompt = (
        resume_str +
        "\n\nExtract the following details from the resume:\n"
        "1. Contact details\n"
        "2. Objective or professional summary\n"
        "3. Education details\n"
        "4. Work experience\n"
        "5. Skills\n"
        "6. Certifications\n\n"
        "Return the information in a JSON format with keys: "
        "'contact_details', 'objective', 'education', 'work_experience', 'skills', 'certifications'."
    )
    response = dwani.Chat.direct(prompt=prompt, model="gemma3")
    return extract_text_from_response(response)

def process_pdf_resume(pdf_file):
    if not pdf_file:
        return None
    file_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    try:
        result = dwani.Documents.run_ocr_all(file_path=file_path, model="gemma3")
        extracted_details = extract_resume_sections(result)
        translation = translate_to_kannada(extracted_details)
        text_filename = "resume.txt"
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(translation)
        return text_filename
    except Exception as e:
        logger.error(f"Resume processing error: {str(e)}")
        return None

# --- Text-to-Speech Module ---
def text_to_speech(text, language):
    if not text:
        return None
    try:
        response = dwani.Audio.speech(
            input=text,
            response_format="mp3",
            language=language
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response)
            return temp_file.name
    except Exception as e:
        return None

# --- Gradio Interface ---
with gr.Blocks(title="dwani.ai API Suite") as demo:
    gr.Markdown("# dwani.ai API Suite")
    gr.Markdown("A comprehensive interface for dwani.ai APIs: Chat, Image Query, Transcription, Translation, PDF Processing, Resume Translation, and Text-to-Speech.")

    with gr.Tabs():
        # Chat Tab
                # PDF Processing Tab
        with gr.Tab("PDF Query"):
            gr.Markdown("Query PDF files with a custom prompt")
            with gr.Row():
                with gr.Column():
                    pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
                    pdf_page = gr.Number(label="Page Number", value=1, minimum=1, precision=0)
                    pdf_prompt = gr.Textbox(
                        label="Custom Prompt",
                        placeholder="e.g., List the key points",
                        value="List the key points",
                        lines=3
                    )
                    pdf_src_lang = gr.Dropdown(label="Source Language", choices=CHAT_IMAGE_LANGUAGES, value="english")
                    pdf_tgt_lang = gr.Dropdown(label="Target Language", choices=CHAT_IMAGE_LANGUAGES, value="kannada")
                    pdf_submit = gr.Button("Process")
                with gr.Column():
                    pdf_output = gr.JSON(label="PDF Response")
            pdf_submit.click(
                fn=process_pdf,
                inputs=[pdf_input, pdf_page, pdf_prompt, pdf_src_lang, pdf_tgt_lang],
                outputs=pdf_output
            )

        with gr.Tab("Chat"):
            gr.Markdown("Interact with the Chat API")
            with gr.Row():
                with gr.Column():
                    chat_prompt = gr.Textbox(label="Prompt", placeholder="Enter your prompt (e.g., 'hi')")
                    chat_src_lang = gr.Dropdown(label="Source Language", choices=CHAT_IMAGE_LANGUAGES, value="english")
                    chat_tgt_lang = gr.Dropdown(label="Target Language", choices=CHAT_IMAGE_LANGUAGES, value="kannada")
                    chat_submit = gr.Button("Submit")
                with gr.Column():
                    chat_output = gr.JSON(label="Chat Response")
            chat_submit.click(
                fn=chat_api,
                inputs=[chat_prompt, chat_src_lang, chat_tgt_lang],
                outputs=chat_output
            )

        # Image Query Tab
        with gr.Tab("Image Query"):
            gr.Markdown("Query images with a prompt")
            with gr.Row():
                with gr.Column():
                    image_input = gr.Image(type="pil", label="Upload Image")
                    image_prompt = gr.Textbox(label="Prompt", placeholder="e.g., describe the image")
                    image_src_lang = gr.Dropdown(label="Source Language", choices=CHAT_IMAGE_LANGUAGES, value="english")
                    image_tgt_lang = gr.Dropdown(label="Target Language", choices=CHAT_IMAGE_LANGUAGES, value="kannada")
                    image_submit = gr.Button("Query")
                with gr.Column():
                    image_output = gr.JSON(label="Image Query Response")
            image_submit.click(
                fn=visual_query,
                inputs=[image_input, image_src_lang, image_tgt_lang, image_prompt],
                outputs=image_output
            )

        # Transcription Tab
        with gr.Tab("Transcription"):
            gr.Markdown("Transcribe audio files")
            with gr.Row():
                with gr.Column():
                    audio_input = gr.Audio(label="Audio File", type="filepath", sources=["upload"])
                    asr_language = gr.Dropdown(label="Language", choices=ASR_LANGUAGES, value="kannada")
                    asr_submit = gr.Button("Transcribe")
                with gr.Column():
                    asr_output = gr.JSON(label="Transcription Response")
            asr_submit.click(
                fn=transcribe_api,
                inputs=[audio_input, asr_language],
                outputs=asr_output
            )

        # Translation Tab
        with gr.Tab("Translation"):
            gr.Markdown("Translate sentences between languages")
            with gr.Row():
                with gr.Column():
                    trans_sentences = gr.Textbox(
                        label="Sentences",
                        placeholder="Enter sentences (e.g., Hello, Good morning)",
                        lines=3,
                        value="Hi"
                    )
                    trans_src_lang = gr.Dropdown(label="Source Language", choices=TRANSLATION_LANGUAGES, value="english")
                    trans_tgt_lang = gr.Dropdown(label="Target Language", choices=TRANSLATION_LANGUAGES, value="kannada")
                    trans_submit = gr.Button("Translate")
                with gr.Column():
                    trans_output = gr.JSON(label="Translation Response")
            trans_submit.click(
                fn=translate_api,
                inputs=[trans_sentences, trans_src_lang, trans_tgt_lang],
                outputs=trans_output
            )

        # Resume Translation Tab
        with gr.Tab("Resume Translation"):
            gr.Markdown("Upload a resume PDF to extract and translate to Kannada")
            with gr.Row():
                with gr.Column():
                    resume_input = gr.File(label="Upload Resume", file_types=[".pdf"])
                    resume_submit = gr.Button("Process")
                with gr.Column():
                    resume_output = gr.File(label="Download Translated Resume (.txt)")
            resume_submit.click(
                fn=process_pdf_resume,
                inputs=[resume_input],
                outputs=resume_output
            )

        # Text-to-Speech Tab
        with gr.Tab("Text to Speech"):
            gr.Markdown("Convert text to speech")
            with gr.Row():
                with gr.Column():
                    tts_text = gr.Textbox(
                        label="Text",
                        placeholder="Enter text to convert to speech",
                        value="ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ ಬೆಂಗಳೂರು."
                    )
                    tts_language = gr.Dropdown(label="Language", choices=TTS_LANGUAGES, value="kannada")
                    tts_submit = gr.Button("Generate Speech")
                with gr.Column():
                    tts_output = gr.Audio(label="Generated Speech", type="filepath", interactive=False)
            tts_submit.click(
                fn=text_to_speech,
                inputs=[tts_text, tts_language],
                outputs=tts_output
            )

# Launch the interface
if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7860)
    except Exception as e:
        logger.error(f"Failed to launch Gradio interface: {str(e)}")
        print(f"Failed to launch Gradio interface: {str(e)}")