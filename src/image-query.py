import gradio as gr
import requests
from PIL import Image
import dwani
import os
import tempfile

dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

def visual_query(image, src_lang, tgt_lang, prompt):
    # Save PIL Image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        image.save(temp_file.name, format="PNG")  # Explicitly save as PNG
        temp_file_path = temp_file.name

    try:
        # Call the API with the file path
        result = dwani.Vision.caption(
            file_path=temp_file_path,
            query=prompt,
            src_lang=src_lang,
            tgt_lang=tgt_lang
        )
        print(result)
        return result
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

# Create Gradio interface
iface = gr.Interface(
    fn=visual_query,
    inputs=[
        gr.Image(type="pil", label="Upload Image"),
        gr.Textbox(label="Source Language (e.g., eng_Latn)", placeholder="eng_Latn"),
        gr.Textbox(label="Target Language (e.g., kan_Knda)", placeholder="kan_Knda"),
        gr.Textbox(label="Prompt", placeholder="e.g., describe the image")
    ],
    outputs=gr.JSON(label="API Response"),
    title="Visual Query API Interface",
    description="Upload an image, specify source and target languages, and provide a prompt to query the visual API."
)

# Launch the interface
iface.launch()