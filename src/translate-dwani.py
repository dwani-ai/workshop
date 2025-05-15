import gradio as gr
import requests
import json
import os
import dwani
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure dwani API settings
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

# Log API configuration for debugging
logger.debug("DWANI_API_KEY: %s", "Set" if dwani.api_key else "Not set")
logger.debug("DWANI_API_BASE_URL: %s", dwani.api_base)

# List of supported languages
LANGUAGES = [
    "Assamese (asm_Beng)", "Kashmiri (Arabic) (kas_Arab)", "Punjabi (pan_Guru)",
    "Bengali (ben_Beng)", "Kashmiri (Devanagari) (kas_Deva)", "Sanskrit (san_Deva)",
    "Bodo (brx_Deva)", "Maithili (mai_Deva)", "Santali (sat_Olck)",
    "Dogri (doi_Deva)", "Malayalam (mal_Mlym)", "Sindhi (Arabic) (snd_Arab)",
    "English (eng_Latn)", "Marathi (mar_Deva)", "Sindhi (Devanagari) (snd_Deva)",
    "Konkani (gom_Deva)", "Manipuri (Bengali) (mni_Beng)", "Tamil (tam_Taml)",
    "Gujarati (guj_Gujr)", "Manipuri (Meitei) (mni_Mtei)", "Telugu (tel_Telu)",
    "Hindi (hin_Deva)", "Nepali (npi_Deva)", "Urdu (urd_Arab)",
    "Kannada (kan_Knda)", "Odia (ory_Orya)"
]

# Function to extract language code from selection
def get_lang_code(lang_string):
    try:
        return lang_string.split("(")[-1].rstrip(")")
    except IndexError:
        logger.error("Invalid language string format: %s", lang_string)
        return None

def translate_api(sentences, src_lang, tgt_lang):
    logger.debug("Received inputs - Sentences: %s, Source Lang: %s, Target Lang: %s", sentences, src_lang, tgt_lang)
    
    # Convert simple string input to list
    try:
        if isinstance(sentences, str):
            # Split on commas and strip whitespace
            sentences = [s.strip() for s in sentences.split(",") if s.strip()]
        elif isinstance(sentences, list):
            # Ensure all elements are strings and non-empty
            sentences = [s.strip() for s in sentences if isinstance(s, str) and s.strip()]
        else:
            logger.error("Invalid input type for sentences: %s", type(sentences))
            return {"error": "Invalid input: sentences must be a string or list of strings"}
    except Exception as e:
        logger.error("Error processing sentences input: %s", str(e))
        return {"error": f"Error processing input: {str(e)}"}
    
    # Validate sentences content
    if not sentences:
        logger.error("No valid sentences provided: %s", sentences)
        return {"error": "Please provide at least one non-empty sentence"}
    
    # Extract language codes
    src_lang_code = get_lang_code(src_lang)
    tgt_lang_code = get_lang_code(tgt_lang)
    
    if not src_lang_code or not tgt_lang_code:
        logger.error("Invalid language codes - Source: %s, Target: %s", src_lang_code, tgt_lang_code)
        return {"error": "Invalid source or target language selection"}
    
    logger.debug("Calling API with sentences: %s, src_lang: %s, tgt_lang: %s", sentences, src_lang_code, tgt_lang_code)
    
    # Call the API
    try:
        result = dwani.Translate.run_translate(sentences=sentences, src_lang=src_lang_code, tgt_lang=tgt_lang_code)
        logger.debug("API response: %s", result)
        return result
    except dwani.exceptions.DhwaniAPIError as e:
        logger.error("Dhwani API error: %s", str(e))
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": f"Unexpected error: {str(e)}"}

# Create Gradio interface
with gr.Blocks(title="Translation API Interface") as demo:
    gr.Markdown("# Translation API Interface")
    gr.Markdown("Enter one or more sentences (separated by commas) and select languages to translate.")
    
    with gr.Row():
        with gr.Column():
            # Input components
            sentences_input = gr.Textbox(
                label="Sentences",
                placeholder="Enter your sentence (e.g., Hello, Good morning)",
                lines=3,
                value="Hi"
            )
            src_lang_input = gr.Dropdown(
                label="Source Language",
                choices=LANGUAGES,
                value="English (eng_Latn)"
            )
            tgt_lang_input = gr.Dropdown(
                label="Target Language",
                choices=LANGUAGES,
                value="Kannada (kan_Knda)"
            )
            
            submit_btn = gr.Button("Translate")
        
        with gr.Column():
            # Output component
            output = gr.JSON(label="Translation Response")
    
    # Connect the button click to the API function
    submit_btn.click(
        fn=translate_api,
        inputs=[sentences_input, src_lang_input, tgt_lang_input],
        outputs=output
    )

# Launch the interface
if __name__ == "__main__":
    # Test API configuration
    if not dwani.api_key or not dwani.api_base:
        logger.error("API key or base URL not set. Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")
        print("Error: Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")
    else:
        logger.debug("Starting Gradio interface...")
        demo.launch()