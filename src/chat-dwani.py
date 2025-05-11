import gradio as gr
import requests

import dwani
import os

dwani.api_key = os.getenv("DWANI_API_KEY")

dwani.api_base = os.getenv("DWANI_API_BASE_URL")

def chat_api(prompt, language, tgt_language):  
    resp = dwani.Chat.create(prompt, language, tgt_language)
    return resp

# Create Gradio interface
with gr.Blocks(title="Chat API Interface") as demo:
    gr.Markdown("# Chat API Interface")
    
    with gr.Row():
        with gr.Column():
            # Input components
            prompt_input = gr.Textbox(
                label="Prompt",
                placeholder="Enter your prompt here (e.g., 'hi')"
            )
            language_input = gr.Textbox(
                label="Source Language",
                placeholder="Enter source language code (e.g., 'eng_Latn')",
                value="eng_Latn"
            )
            tgt_language_input = gr.Textbox(
                label="Target Language",
                placeholder="Enter target language code (e.g., 'eng_Latn')",
                value="eng_Latn"
            )
            
            submit_btn = gr.Button("Submit")
        
        with gr.Column():
            # Output component
            output = gr.JSON(label="Response")
    
    # Connect the button click to the API function
    submit_btn.click(
        fn=chat_api,
        inputs=[prompt_input, language_input, tgt_language_input],
        outputs=output
    )

# Launch the interface
demo.launch()