import gradio as gr
import logging
import os
from src.chat import chat_api
from src.image_query import visual_query
from src.transcription import transcribe_api
from src.translation import translate_api
from src.pdf_processing import process_pdf
from src.resume import process_pdf_resume
from src.text_to_speech import text_to_speech
import dwani

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure dwani API settings
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

# Validate API configuration
if not dwani.api_key or not dwani.api_base:
    logger.error("API key or base URL not set. Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")
    raise ValueError("Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")

# Language options
CHAT_IMAGE_LANGUAGES = ["english", "kannada", "hindi"]
TRANSLATION_LANGUAGES = [
    "Assamese", "Punjabi", "Bengali", "Malayalam", "English",
    "Marathi", "Tamil", "Gujarati", "Telugu", "Hindi", "Kannada", "Odia"
]
ASR_LANGUAGES = ["malayalam", "tamil", "telugu", "hindi", "kannada"]
TTS_LANGUAGES = ["kannada", "english", "telugu", "hindi", "german"]

# Gradio Interface
with gr.Blocks(title="Dhwani API Suite") as demo:
    gr.Markdown("# Dhwani API Suite")
    gr.Markdown("A comprehensive interface for Dhwani APIs: Chat, Image Query, Transcription, Translation, PDF Processing, Resume Translation, and Text-to-Speech.")

    with gr.Tabs():
        # Chat Tab
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
                    trans_src_lang = gr.Dropdown(label="Source Language", choices=TRANSLATION_LANGUAGES, value="English")
                    trans_tgt_lang = gr.Dropdown(label="Target Language", choices=TRANSLATION_LANGUAGES, value="Kannada")
                    trans_submit = gr.Button("Translate")
                with gr.Column():
                    trans_output = gr.JSON(label="Translation Response")
            trans_submit.click(
                fn=translate_api,
                inputs=[trans_sentences, trans_src_lang, trans_tgt_lang],
                outputs=trans_output
            )

        # PDF Processing Tab
        with gr.Tab("PDF Processing"):
            gr.Markdown("Process PDF files with a custom prompt")
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
                fn=lambda *args: process_pdf(*args, valid_languages=CHAT_IMAGE_LANGUAGES),
                inputs=[pdf_input, pdf_page, pdf_prompt, pdf_src_lang, pdf_tgt_lang],
                outputs=pdf_output
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
        demo.launch(server_name="0.0.0.0", server_port=80)
    except Exception as e:
        logger.error(f"Failed to launch Gradio interface: {str(e)}")
        print(f"Failed to launch Gradio interface: {str(e)}")