import gradio as gr
import requests
import os
import dwani

# List of supported languages
LANGUAGES = ["malayalam", "tamil", "telugu", "hindi", "kannada"]
dwani.api_key = os.getenv("DWANI_API_KEY")

dwani.api_base = os.getenv("DWANI_API_BASE_URL")

# Function to extract language name
def get_lang_name(lang_string):
    return lang_string.split("(")[0].strip().lower()

def transcribe_api(audio_file, language):
    # Get the base URL from environment variable
    result = dwani.ASR.transcribe(file_path=audio_file, language=language)
    return result

# Create Gradio interface
with gr.Blocks(title="Speech to Text API Interface") as demo:
    gr.Markdown("# Speech to Text API Interface")
    
    with gr.Row():
        with gr.Column():
            # Input components
            audio_input = gr.Audio(
                label="Audio File",
                type="filepath",
                sources=["upload"]
            )
            language_input = gr.Dropdown(
                label="Language",
                choices=LANGUAGES,
                value="kannada"
            )
            
            submit_btn = gr.Button("Transcribe")
        
        with gr.Column():
            # Output component
            output = gr.JSON(label="Transcription Response")
    
    # Connect the button click to the API function
    submit_btn.click(
        fn=transcribe_api,
        inputs=[audio_input, language_input],
        outputs=output
    )

# Launch the interface
demo.launch()