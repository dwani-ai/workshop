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
import uuid
from openai import OpenAI
import re

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
CHAT_IMAGE_LANGUAGES = ["kannada", "english", "hindi", "german", "assamese", "punjabi", "bengali", "malayalam", 
                        "marathi", "tamil", "gujarati", "telugu", "odia"]
ASR_LANGUAGES = ["kannada", "english", "hindi", "german", "assamese", "punjabi", "bengali", "malayalam", 
                 "marathi", "tamil", "gujarati", "telugu", "odia"]
TRANSLATION_LANGUAGES = ["assamese", "punjabi", "bengali", "malayalam", "english",
                        "marathi", "tamil", "gujarati", "telugu", "hindi", "kannada", "odia"]
TTS_LANGUAGES = ["kannada", "english", "hindi", "german", "assamese", "punjabi", "bengali", "malayalam", 
                 "marathi", "tamil", "gujarati", "telugu", "odia"]

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

# --- OCR Module ---
def ocr_image(image):
    if not image:
        return {"error": "Please upload an image"}
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        image.save(temp_file.name, format="PNG")
        temp_file_path = temp_file.name
    try:
        result = dwani.Vision.ocr_image(
            file_path=temp_file_path,
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
        result = dwani.Documents.query_page(
            file_path, model="gemma3", tgt_lang=tgt_lang, prompt=prompt, page_number=1
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

# --- Chatbot from File 2 ---
# Initialize OpenAI client for Chatbot
gemma_base_url = os.getenv('GEMMA_VLLM_IP', 'http://localhost:9000/v1')
api_key = os.getenv('OPENAI_API_KEY', 'your-api-key')
client = OpenAI(api_key=api_key, base_url=gemma_base_url)

# Configuration for Chatbot
DEFAULT_SYS_PROMPT = "You are a helpful and harmless assistant. Respond concisely but meaningfully to short inputs, and provide detailed answers when appropriate."
DEFAULT_MODEL = "gemma3"
MODEL_OPTIONS = [{"label": "Gemma3", "value": "gemma3"}]
MODEL_OPTIONS_MAP = {model["value"]: model for model in MODEL_OPTIONS}
DEFAULT_SETTINGS = {"model": DEFAULT_MODEL, "sys_prompt": DEFAULT_SYS_PROMPT}

def format_history(history, sys_prompt):
    messages = [{"role": "system", "content": sys_prompt}] + history
    return messages

class Gradio_Events:
    @staticmethod
    def submit(state_value, user_input, model_value, sys_prompt_value):
        conversation_id = state_value["conversation_id"]
        history = state_value["conversation_contexts"][conversation_id]["history"]
        settings = {"model": model_value, "sys_prompt": sys_prompt_value}
        state_value["conversation_contexts"][conversation_id]["settings"] = settings

        history.append({"role": "user", "content": user_input})
        messages = format_history(history, sys_prompt_value)

        try:
            response = client.chat.completions.create(
                model=model_value,
                messages=messages,
                stream=False
            )
            start_time = time.time()
            answer_content = response.choices[0].message.content
            history.append({"role": "assistant", "content": f"{answer_content}\n\n*Generated in {time.time() - start_time:.2f}s*"})
        except Exception as e:
            history.append({"role": "assistant", "content": f"Error: {str(e)}"})

        return (
            gr.update(value=history),
            gr.update(value=state_value),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], 
                     visible=bool(state_value["conversations"]), 
                     value=state_value["conversation_id"])
        )

    @staticmethod
    def add_message(user_input, model_value, sys_prompt_value, state_value):
        if not user_input.strip():
            return (
                gr.skip(),
                state_value,
                user_input,
                gr.skip(),
                gr.skip(),
                gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], 
                         visible=bool(state_value["conversations"]), 
                         value=state_value["conversation_id"])
            )

        if not state_value["conversation_id"]:
            random_id = str(uuid.uuid4())
            state_value["conversation_id"] = random_id
            state_value["conversation_contexts"][random_id] = {
                "history": [],
                "settings": {"model": model_value, "sys_prompt": sys_prompt_value}
            }
            state_value["conversations"].append({
                "label": user_input[:30] + "..." if len(user_input) > 30 else user_input,
                "key": random_id
            })

        return Gradio_Events.submit(state_value, user_input, model_value, sys_prompt_value)

    @staticmethod
    def new_chat(state_value):
        state_value["conversation_id"] = ""
        return (
            gr.update(value=[]),
            gr.update(value=state_value),
            gr.update(value=DEFAULT_SETTINGS["model"]),
            gr.update(value=DEFAULT_SETTINGS["sys_prompt"]),
            gr.update(choices=[], visible=False)
        )

    @staticmethod
    def select_conversation(state_value, evt: gr.EventData):
        conversation_id = evt._data
        if conversation_id not in state_value["conversation_contexts"]:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip()
        state_value["conversation_id"] = conversation_id
        history = state_value["conversation_contexts"][conversation_id]["history"]
        settings = state_value["conversation_contexts"][conversation_id]["settings"]
        return (
            gr.update(value=history),
            gr.update(value=state_value),
            gr.update(value=settings["model"]),
            gr.update(value=settings["sys_prompt"])
        )

    @staticmethod
    def delete_conversation(state_value, evt: gr.EventData):
        conversation_id = evt._data
        if conversation_id in state_value["conversation_contexts"]:
            del state_value["conversation_contexts"][conversation_id]
            state_value["conversations"] = [c for c in state_value["conversations"] if c["key"] != conversation_id]
            if state_value["conversation_id"] == conversation_id:
                state_value["conversation_id"] = ""
                return (
                    gr.update(value=[]),
                    gr.update(value=state_value),
                    gr.update(choices=[], visible=False)
                )
        return gr.skip(), gr.update(value=state_value), gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], 
                                                                visible=bool(state_value["conversations"]), 
                                                                value=state_value["conversation_id"])

    @staticmethod
    def clear_conversation(state_value):
        if state_value["conversation_id"]:
            state_value["conversation_contexts"][state_value["conversation_id"]]["history"] = []
            return gr.update(value=[]), gr.update(value=state_value)
        return gr.skip(), gr.skip()

# --- gpt-oss Chat Interface ---
GPT_OSS_API_URL = os.getenv('GPT_OSS_API_URL', "http://localhost:9500/v1/chat/completions")

def extract_values(text):
    pattern = r'<\|channel\|>(.*?)<\|message\|>(.*?)(?=<\|start\|>|<\|channel\|>|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    result = [{'channel': m[0], 'message': m[1].strip()} for m in matches]
    return result

def get_final_message(text):
    extracted = extract_values(text)
    for item in extracted:
        if item['channel'] == 'final':
            return item['message']
    return None

def ask_gpt(user_message, history):
    messages = [{"role": "system", "content": "You are a helpful assistant."}]

    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        if assistant:
            messages.append({"role": "assistant", "content": assistant})

    messages.append({"role": "user", "content": user_message})

    data = {
        "messages": messages,
        "temperature": 1.0,
        "max_tokens": 1000,
        "stream": False,
        "model": "openai/gpt-oss-120b"
    }

    try:
        resp = requests.post(GPT_OSS_API_URL, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        raw_answer = result["choices"][0]["message"]["content"]
        final_message = get_final_message(raw_answer)
        answer = final_message if final_message is not None else raw_answer
    except Exception as e:
        answer = f"Error: {e}"
    return answer

# --- Custom CSS ---
css = """
.gradio-container {
    max-width: 1200px;
    margin: auto;
}
#chatbot {
    height: calc(100vh - 200px);
    max-height: 800px;
}
#conversations {
    max-height: 600px;
    overflow-y: auto;
}
"""

# --- Gradio Interface ---
with gr.Blocks() as demo:  # Removed css and fill_width from constructor
    gr.Markdown("# dwani.ai API Suite")
    gr.Markdown("A comprehensive interface for dwani.ai APIs: Chat, Image Query, Transcription, Translation, PDF Processing, Resume Translation, Text-to-Speech, and Chatbot.")

    with gr.Tabs():

        # PDF Query Tab
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

        with gr.Tab("gpt-oss", visible=False):
            gr.Markdown("gpt-oss")
            gr.ChatInterface(ask_gpt, title="gpt-oss")

        """
        # Chatbot Tab
        with gr.Tab("Chatbot", visible=False):
            state = gr.State({
                "conversation_contexts": {},
                "conversations": [],
                "conversation_id": ""
            })
            with gr.Row():
                with gr.Column(scale=1, min_width=200):
                    gr.Markdown("## Conversations")
                    conversations = gr.Dropdown(
                        label="Conversations",
                        elem_id="conversations",
                        choices=[],
                        interactive=True,
                        visible=False
                    )
                    new_chat_btn = gr.Button("New Conversation")
                    delete_conversation_btn = gr.Button("Delete Selected Conversation")
                with gr.Column(scale=3):
                    gr.Markdown("## Chatbot")
                    chatbot = gr.Chatbot(elem_id="chatbot", buttons=["copy"], type="messages")  # Fixed: use buttons=["copy"]
                    user_input = gr.Textbox(placeholder="Type your message...", label="Message")
                    with gr.Row():
                        model_select = gr.Dropdown(choices=list(MODEL_OPTIONS_MAP.keys()), value=DEFAULT_SETTINGS["model"], label="Model")
                        sys_prompt = gr.Textbox(value=DEFAULT_SETTINGS["sys_prompt"], label="System Prompt")
                    with gr.Row():
                        submit_btn = gr.Button("Send", elem_id="submit_btn")
                        clear_btn = gr.Button("Clear Conversation")
            # Event Handlers
            submit_btn.click(
                fn=Gradio_Events.add_message,
                inputs=[user_input, model_select, sys_prompt, state],
                outputs=[chatbot, state, user_input, submit_btn, clear_btn, conversations]
            )
            user_input.submit(
                fn=Gradio_Events.add_message,
                inputs=[user_input, model_select, sys_prompt, state],
                outputs=[chatbot, state, user_input, submit_btn, clear_btn, conversations]
            )
            new_chat_btn.click(
                fn=Gradio_Events.new_chat,
                inputs=[state],
                outputs=[chatbot, state, model_select, sys_prompt, conversations]
            )
            conversations.select(
                fn=Gradio_Events.select_conversation,
                inputs=[state],
                outputs=[chatbot, state, model_select, sys_prompt]
            )
            delete_conversation_btn.click(
                fn=Gradio_Events.delete_conversation,
                inputs=[state],
                outputs=[chatbot, state, conversations]
            )
            clear_btn.click(
                fn=Gradio_Events.clear_conversation,
                inputs=[state],
                outputs=[chatbot, state]
            )
        """
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

        # OCR Image Tab
        with gr.Tab("OCR Image"):
            gr.Markdown("OCR for Images")
            with gr.Row():
                with gr.Column():
                    image_input = gr.Image(type="pil", label="Upload Image")
                    image_submit = gr.Button("Query")
                with gr.Column():
                    image_output = gr.JSON(label="OCR Response")
            image_submit.click(
                fn=ocr_image,
                inputs=[image_input],
                outputs=image_output
            )

        # Transcription Tab
        with gr.Tab("Transcription"):
            gr.Markdown("Transcribe audio from a file or microphone recording")
            with gr.Row():
                with gr.Column():
                    audio_input = gr.Audio(
                        label="Record or Upload Audio",
                        type="filepath",
                        sources=["upload", "microphone"],
                        waveform_options=gr.WaveformOptions(
                            show_recording_waveform=True
                        )
                    )
                    asr_language = gr.Dropdown(
                        label="Language",
                        choices=ASR_LANGUAGES,
                        value="kannada"
                    )
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

        # Chat Tab
        with gr.Tab("Chat", visible=False):
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

        # Resume Translation Tab
        with gr.Tab("Resume Translation", visible=False):
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
        demo.launch(server_name="0.0.0.0", server_port=80, css=css)  # css moved to launch()
    except Exception as e:
        logger.error(f"Failed to launch Gradio interface: {str(e)}")
        print(f"Failed to launch Gradio interface: {str(e)}")