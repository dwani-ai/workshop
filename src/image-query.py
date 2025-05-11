import gradio as gr
import requests
from PIL import Image

import dwani
import os

dwani.api_key = os.getenv("DWANI_API_KEY")

dwani.api_base = os.getenv("DWANI_API_BASE_URL")

def visual_query(image, src_lang, tgt_lang, prompt):
    # API endpoint


    result = dwani.Vision.caption(
        file_path=image,
        query=prompt ,
        src_lang=src_lang,
        tgt_lang=tgt_lang
    )
    print(result)
    return result

# Create Gradio interface
iface = gr.Interface(
    fn=visual_query,
    inputs=[
        gr.Image(type="pil", label="Upload Image"),
        gr.Textbox(label="Source Language (e.g., kan_Knda)", placeholder="kan_Knda"),
        gr.Textbox(label="Target Language (e.g., kan_Knda)", placeholder="kan_Knda"),
        gr.Textbox(label="Prompt", placeholder="e.g., describe the image")
    ],
    outputs=gr.JSON(label="API Response"),
    title="Visual Query API Interface",
    description="Upload an image, specify source and target languages, and provide a prompt to query the visual API."
)

# Launch the interface
iface.launch()