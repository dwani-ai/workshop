import gradio as gr
import requests
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

# Language options for dropdowns
language_options = [
    ("English", "eng_Latn"),
    ("Kannada", "kan_Knda"),
    ("Hindi", "hin_Deva")
]

# Create lists for Gradio dropdowns (display names only)
language_names = [lang[0] for lang in language_options]

# Map display names to language codes
lang_code_map = {lang[0]: lang[1] for lang in language_options}

def process_pdf(pdf_file, page_number, prompt, src_lang, tgt_lang):
    logger.debug("Received inputs - PDF: %s, Page: %s, Prompt: %s, Source Lang: %s, Target Lang: %s",
                pdf_file, page_number, prompt, src_lang, tgt_lang)
    
    # Validate inputs
    if not pdf_file:
        logger.error("No PDF file provided")
        return {"error": "Please upload a PDF file"}
    
    if not prompt.strip():
        logger.error("Prompt is empty")
        return {"error": "Please provide a non-empty prompt"}
    
    try:
        page_number = int(page_number)
        if page_number < 1:
            raise ValueError("Page number must be at least 1")
    except (ValueError, TypeError):
        logger.error("Invalid page number: %s", page_number)
        return {"error": "Page number must be a positive integer"}
    
    # Get language codes
    src_lang_code = lang_code_map.get(src_lang)
    tgt_lang_code = lang_code_map.get(tgt_lang)
    
    if not src_lang_code or not tgt_lang_code:
        logger.error("Invalid language selection - Source: %s, Target: %s", src_lang, tgt_lang)
        return {"error": "Invalid source or target language selection"}
    
    # Get file path from Gradio File object
    file_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    
    logger.debug("Calling API with file: %s, page: %d, prompt: %s, src_lang: %s, tgt_lang: %s",
                file_path, page_number, prompt, src_lang_code, tgt_lang_code)
    
    # Call the API
    try:
        result = dwani.Documents.run_doc_query(
            file_path=file_path,
            prompt=prompt,
            page_number=page_number,
            src_lang=src_lang_code,
            tgt_lang=tgt_lang_code
        )
        logger.debug("API response: %s", result)
        return {
            "Original Text": result.get("original_text", "N/A"),
            "Response": result.get("response", "N/A"),
            "Processed Page": result.get("processed_page", "N/A"),
            "Translated Response": result.get("translated_response", "N/A")
        }
    except dwani.exceptions.DhwaniAPIError as e:
        logger.error("Dhwani API error: %s", str(e))
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": f"Unexpected error: {str(e)}"}

# Define Gradio interface
with gr.Blocks(title="PDF Custom Prompt Processor") as demo:
    gr.Markdown("# PDF Custom Prompt Processor")
    gr.Markdown("Upload a PDF, specify a page number, enter a prompt, and select source and target languages.")
    
    with gr.Row():
        with gr.Column():
            pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
            page_number = gr.Number(label="Page Number", value=1, minimum=1, precision=0)
            prompt = gr.Textbox(
                label="Custom Prompt",
                placeholder="e.g., List the key points",
                value="List the key points",
                lines=3
            )
            src_lang_input = gr.Dropdown(
                label="Source Language",
                choices=language_names,
                value="English"
            )
            tgt_lang_input = gr.Dropdown(
                label="Target Language",
                choices=language_names,
                value="Kannada"
            )
            submit_btn = gr.Button("Process")
        
        with gr.Column():
            output = gr.JSON(label="Response")
    
    submit_btn.click(
        fn=process_pdf,
        inputs=[pdf_input, page_number, prompt, src_lang_input, tgt_lang_input],
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