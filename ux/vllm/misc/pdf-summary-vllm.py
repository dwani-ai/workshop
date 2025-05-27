import gradio as gr
import requests
import os 
base_url = os.getenv("DWANI_AI_API_BASE_URL")


def summarize_pdf(pdf_file, page_number):
    endpoint = "/summarize-pdf"

    # Construct the full API URL
    url = f"{base_url.rstrip('/')}{endpoint}"

    headers = {
        "accept": "application/json"
    }
    
    try:
        # Prepare the multipart form data
        files = {
            "file": (pdf_file.name, open(pdf_file.name, "rb"), "application/pdf")
        }
        data = {
            "page_number": str(page_number)
        }
        
        # Send POST request
        response = requests.post(url, headers=headers, files=files, data=data)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            return {
                "Original Text": result.get("original_text", "N/A"),
                "Summary": result.get("summary", "N/A"),
                "Processed Page": result.get("processed_page", "N/A")
            }
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error: {str(e)}"

# Define Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# PDF Summarizer")
    
    with gr.Row():
        pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
        page_number = gr.Number(label="Page Number", value=1, minimum=1, precision=0)
    
    submit_btn = gr.Button("Summarize")
    
    output = gr.JSON(label="Response")
    
    submit_btn.click(
        fn=summarize_pdf,
        inputs=[pdf_input, page_number],
        outputs=output
    )

# Launch the interface
demo.launch()