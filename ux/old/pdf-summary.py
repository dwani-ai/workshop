import gradio as gr
import requests
from PyPDF2 import PdfReader
import os

# Function to validate PDF file
def is_valid_pdf(file_path):
    try:
        if isinstance(file_path, str) and os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
            if file_size > 50:  # Limit to 50 MB
                return False, "PDF file is too large (max 50 MB)"
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
def extract_text_from_pdf(pdf_file, src_lang, tgt_lang, prompt):
    if not pdf_file:
        return "Error: No file uploaded. Please upload a PDF file.", ""

    # Validate the PDF
    valid, message = is_valid_pdf(pdf_file)
    if not valid:
        return f"Error: {message}. Please upload a valid PDF file or repair the current one.", ""

    # Get the base URL from environment variable
    base_url = os.getenv("DWANI_AI_API_BASE_URL")
    if not base_url:
        return "Error: DWANI_AI_API_BASE_URL environment variable is not set", ""

    # Define the endpoint path
    endpoint = "/v1/document_summary_v0"

    # Construct the full API URL
    url = f"{base_url.rstrip('/')}{endpoint}"

    # Prepare the payload
    with open(pdf_file, "rb") as f:
        files = {
            "file": ("uploaded.pdf", f, "application/pdf")
        }
        data = {
            "src_lang": src_lang,
            "tgt_lang": tgt_lang,
            "prompt": prompt
        }

        # Headers
        headers = {
            "accept": "application/json"
        }

        try:
            # Send the POST request with increased timeout (120 seconds)
            response = requests.post(url, files=files, data=data, headers=headers, timeout=120)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                summary = result.get("summary", "No summary returned from API")
                pages = result.get("pages", [])
                if not pages:
                    page_text = "No text returned from API"
                else:
                    # Concatenate text from all pages
                    page_text = "\n\n".join(
                        f"Page {page.get('page_number')}: {page.get('page_text', 'No text available')}"
                        for page in pages
                    )
                return summary, page_text
            else:
                return f"Error: {response.status_code} - {response.text}", ""
        except requests.Timeout:
            return "Error: API request timed out. Please try again or check the API server.", ""
        except Exception as e:
            return f"Error: Failed to connect to the API - {str(e)}", ""

# Gradio interface
with gr.Blocks(title="PDF Content Description") as demo:
    gr.Markdown("# PDF Content Description Extractor")
    gr.Markdown(
        """
        Upload a PDF file (e.g., gaganyatri.pdf) and specify parameters to extract a summary and text content.
        The API will analyze the entire document and return a summary and the extracted text for all pages based on the provided prompt and languages.
        """
    )
    
    # Input components
    pdf_input = gr.File(label="Upload PDF File", file_types=[".pdf"], type="filepath")
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
        value="Summarize the document in 3 sentences",
        placeholder="Enter prompt (e.g., Summarize the document in 3 sentences)"
    )
    
    # Submit button
    submit_button = gr.Button("Extract Summary and Text")
    
    # Output components
    summary_output = gr.Textbox(
        label="Document Summary",
        lines=5,
        placeholder="The API summary will appear here."
    )
    text_output = gr.Textbox(
        label="Extracted Text (All Pages)",
        lines=10,
        placeholder="The extracted text for all pages will appear here."
    )
    
    # Connect the button to the function
    submit_button.click(
        fn=extract_text_from_pdf,
        inputs=[pdf_input, src_lang_input, tgt_lang_input, prompt_input],
        outputs=[summary_output, text_output]
    )

# Launch the Gradio app
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)