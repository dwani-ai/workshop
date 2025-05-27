import gradio as gr
import requests
import urllib.parse
import tempfile
import os

import dwani
dwani.api_key = os.getenv("DWANI_API_KEY")

dwani.api_base = os.getenv("DWANI_API_BASE_URL")

def text_to_speech(text):
    # Validate input
    
    try:
        response = dwani.Audio.speech(input=text, response_format="mp3")
        
        # Save the audio content to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response)
            temp_file_path = temp_file.name
        
        return temp_file_path
    except requests.exceptions.RequestException as e:
        raise ValueError(f"API request failed: {str(e)}")
    except IOError as e:
        raise ValueError(f"Failed to save audio file: {str(e)}")

# Create Gradio interface
with gr.Blocks(title="Text to Speech API Interface") as demo:
    gr.Markdown("# Text to Speech API Interface")
    
    with gr.Row():
        with gr.Column():
            # Input components
            text_input = gr.Textbox(
                label="Text",
                placeholder="Enter text to convert to speech",
                value="ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ ಬೆಂಗಳೂರು."
            )
            submit_btn = gr.Button("Generate Speech")
        
        with gr.Column():
            # Output component
            audio_output = gr.Audio(
                label="Generated Speech",
                type="filepath",
                interactive=False
            )
    
    # Connect the button click to the API function
    submit_btn.click(
        fn=text_to_speech,
        inputs=[text_input],
        outputs=audio_output
    )

# Launch the interface
try:
    demo.launch(server_name="0.0.0.0", server_port=7860)
except Exception as e:
    print(f"Failed to launch Gradio interface: {str(e)}")