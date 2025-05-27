import gradio as gr
import requests
import dwani
import os

dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

def chat_api(prompt, language, tgt_language):  
    resp = dwani.Chat.create(prompt, language, tgt_language)
    return resp

# Language options as simple array
language_options = ["English", "Kannada", "Hindi"]

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
            language_input = gr.Dropdown(
                label="Source Language",
                choices=language_options,
                value="English"
            )
            tgt_language_input = gr.Dropdown(
                label="Target Language",
                choices=language_options,
                value="Kannada"
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