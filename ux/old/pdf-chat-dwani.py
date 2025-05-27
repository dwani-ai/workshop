import gradio as gr
import requests
from PyPDF2 import PdfReader
import os

# Function to validate PDF file
def is_valid_pdf(file_path):
    try:
        # If file_path is a string (Gradio provides a temporary file path)
        if isinstance(file_path, str) and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                pdf = PdfReader(f)
                if len(pdf.pages) > 0:
                    return True, f"Valid PDF with {len(pdf.pages)} pages"
                return False, "Invalid PDF: No pages found"
        else:
            return False, "Invalid PDF: File path is not valid"
    except Exception as e:
        return False, f"Invalid PDF: {str(e)}"

# Function to send the POST request to the API
def extract_text_from_pdf(pdf_file, page_number, src_lang, tgt_lang, prompt):
    if not pdf_file:
        return "Error: No file uploaded. Please upload a PDF file."

    # Validate the PDF
    valid, message = is_valid_pdf(pdf_file)
    if not valid:
        return f"Error: {message}. Please upload a valid PDF file or repair the current one."

    import os

    # Get the base URL (IP or domain) from environment variable
    base_url = os.getenv("DWANI_AI_API_BASE_URL")

    if not base_url:
        raise ValueError("DWANI_AI_API_BASE_URL environment variable is not set")

    # Define the endpoint path
    endpoint = "/extract-text-eng/"

    # Construct the full API URL
    url = f"{base_url.rstrip('/')}{endpoint}"

    # Prepare the payload
    with open(pdf_file, "rb") as f:
        files = {
            "file": ("uploaded.pdf", f, "application/pdf")
        }
        data = {
            "page_number": str(page_number),
            "src_lang": src_lang,
            "tgt_lang": tgt_lang,
            "prompt": prompt
        }

        # Headers
        headers = {
            "accept": "application/json"
        }

        try:
            # Send the POST request
            response = requests.post(url, files=files, data=data, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                page_content = result.get("page_content", "No description returned from API")
                return page_content
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error: Failed to connect to the API - {str(e)}"

# Gradio interface
with gr.Blocks(title="PDF Content Description") as demo:
    gr.Markdown("# PDF Content Description Extractor")
    gr.Markdown(
        """
        Upload a PDF file (e.g., dwani-AI-Pitch-Europe.pdf) and specify parameters to extract a description of its content.
        The API will analyze the page and return a textual description based on the provided prompt and languages.
        """
    )
    
    # Input components
    pdf_input = gr.File(label="Upload PDF File", file_types=[".pdf"], type="filepath")
    page_number_input = gr.Number(label="Page Number", value=1, precision=0, minimum=1)
    src_lang_input = gr.Textbox(
        label="Source Language",
        value="eng_Latn",
        placeholder="Enter source language (e.g., eng_Latn)"
    )
    tgt_lang_input = gr.Textbox(
        label="Target Language",
        value="eng_Latn",
        placeholder="Enter target language (e.g., eng_Latn)"
    )
    prompt_input = gr.Textbox(
        label="Prompt",
        value="describe the image",
        placeholder="Enter prompt (e.g., describe the image)"
    )
    
    # Submit button
    submit_button = gr.Button("Extract Description")
    
    # Output component
    output_text = gr.Textbox(
        label="Content Description",
        lines=10,
        placeholder="The API response will appear here, describing the content of the specified PDF page."
    )
    
    # Connect the button to the function
    submit_button.click(
        fn=extract_text_from_pdf,
        inputs=[pdf_input, page_number_input, src_lang_input, tgt_lang_input, prompt_input],
        outputs=output_text
    )

# Launch the Gradio app
demo.launch()