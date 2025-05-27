import gradio as gr
import PyPDF2
from pdf2image import convert_from_path
import requests
import os
import tempfile

base_url = os.getenv("DWANI_AI_API_BASE_URL")


def process_pdf(pdf_file, page_number, prompt, src_lang):
    try:
        # Validate inputs
        if not pdf_file:
            return "Error: No file uploaded", None, "Error: No file uploaded", None

        # Use the file path from Gradio
        input_pdf_path = pdf_file

        # Preview the input PDF's first page
        with open(input_pdf_path, "rb") as file:
            pdf = PyPDF2.PdfReader(file)
            num_pages = len(pdf.pages)
            input_info = f"Input PDF Info:\n- Number of pages: {num_pages}"

        # Convert the first page of input PDF to an image
        input_images = convert_from_path(input_pdf_path, first_page=1, last_page=1)
        input_image_path = os.path.join(tempfile.gettempdir(), "input_preview.png")
        input_images[0].save(input_image_path, "PNG")

        endpoint = "/v1/indic-custom-prompt-kannada-pdf"

        # Construct the full API URL
        url = f"{base_url.rstrip('/')}{endpoint}"
        # Prepare the API request
        headers = {
            "accept": "application/json",
            "Content-Type": "multipart/form-data"
        }
        files = {
            "file": (os.path.basename(input_pdf_path), open(input_pdf_path, "rb"), "application/pdf")
        }
        data = {
            "page_number": str(page_number),
            "prompt": prompt,
            "src_lang": src_lang
        }

        # Send the POST request
        response = requests.post(url, headers={"accept": "application/json"}, files=files, data=data)

        # Check if the response is successful
        if response.status_code != 200:
            return input_info, input_image_path, f"API Error: {response.status_code} - {response.text}", None

        # Save the response PDF to a temporary file
        output_pdf_path = os.path.join(tempfile.gettempdir(), "output_pdf.pdf")
        with open(output_pdf_path, "wb") as f:
            f.write(response.content)

        # Extract info from the output PDF
        with open(output_pdf_path, "rb") as file:
            output_pdf = PyPDF2.PdfReader(file)
            output_num_pages = len(output_pdf.pages)
            output_info = f"Output PDF Info:\n- Number of pages: {output_num_pages}"

        # Convert the first page of the output PDF to an image
        output_images = convert_from_path(output_pdf_path, first_page=1, last_page=1)
        output_image_path = os.path.join(tempfile.gettempdir(), "output_preview.png")
        output_images[0].save(output_image_path, "PNG")

        return input_info, input_image_path, output_info, output_image_path
    except Exception as e:
        return f"Error: {str(e)}", None, f"Error: {str(e)}", None
    finally:
        # Clean up file handles
        if "files" in locals() and files["file"][1]:
            files["file"][1].close()

# Define the Gradio interface
interface = gr.Interface(
    fn=process_pdf,
    inputs=[
        gr.File(label="Upload PDF", file_types=[".pdf"]),
        gr.Number(label="Page Number", value=1, precision=0, minimum=1),
        gr.Textbox(label="Prompt", value="list the points"),
        gr.Textbox(label="Source Language", value="eng_Latn")
    ],
    outputs=[
        gr.Textbox(label="Input PDF Information"),
        gr.Image(label="Input PDF Preview (First Page)"),
        gr.Textbox(label="Output PDF Information"),
        gr.Image(label="Output PDF Preview (First Page)")
    ],
    title="Kannada - PDF Query and translation ",
    description="Upload a PDF, specify a page number, prompt, and source language. The PDF is sent to an API, and both the input and output PDFs are previewed."
)

# Launch the interface
interface.launch()