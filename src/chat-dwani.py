import gradio as gr
import requests
import dwani
import os

# Set API key and base URL
api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

def chat_api(prompt, language, tgt_language):
    # Configure headers with Bearer token
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Assuming dwani.Chat.create accepts headers; adjust if the library uses a different method
    try:
        resp = dwani.Chat.create(
            prompt=prompt,
            language=language,
            tgt_language=tgt_language,
            headers=headers  # Pass headers if supported
        )
        return resp
    except Exception as e:
        return {"error": str(e)}

# Language options
language_options = [
    ("English", "eng_Latn"),
    ("Kannada", "kan_Knda"),
    ("Hindi", "hin_Deva")
]

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
                value="eng_Latn",
                type="value"
            )
            tgt_language_input = gr.Dropdown(
                label="Target Language",
                choices=language_options,
                value="eng_Latn",
                type="value"
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