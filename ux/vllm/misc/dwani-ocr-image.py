import gradio as gr
import requests
import os 
base_url = os.getenv("DWANI_AI_API_BASE_URL")


def process_ocr(image_file):
    endpoint = "/ocr"

    # Construct the full API URL
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {
        "accept": "application/json"
    }
    
    try:
        # Prepare the multipart form data
        files = {
            "file": (image_file.name, open(image_file.name, "rb"), "image/png")
        }
        
        # Send POST request
        response = requests.post(url, headers=headers, files=files)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            return {
                "Extracted Text": result.get("extracted_text", "N/A")
            }
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error: {str(e)}"

# Define Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# dwani.ai Image OCR Processor")
    
    image_input = gr.File(label="Upload PNG Image", file_types=[".png"])
    
    submit_btn = gr.Button("Extract Text")
    
    output = gr.JSON(label="Response")
    
    submit_btn.click(
        fn=process_ocr,
        inputs=image_input,
        outputs=output
    )

# Launch the interface
demo.launch()