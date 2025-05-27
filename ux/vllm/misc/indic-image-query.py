import gradio as gr
import requests
import base64
from PIL import Image
import io
import os

# Get the base URL (IP or domain) from environment variable
base_url = os.getenv("DWANI_AI_API_BASE_URL")

# Translation API endpoint
translation_api_url = "https://dwani-dwani-server-workshop.hf.space/v1/translate"

def image_to_base64(image):
    """Convert a PIL Image to base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format=image.format if image.format in ["JPEG", "PNG"] else "JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def query_vllm(image, prompt, src_lang, tgt_lang, max_tokens=512, temperature=0.7, top_p=0.9):
    """Send image and prompt to vLLM server, then translate the response."""
    if image is None:
        return "Please upload an image."
    if not prompt:
        return "Please enter a prompt."

    try:
        # Convert image to base64
        img_base64 = image_to_base64(image)
        mime_type = "image/jpeg" if image.format == "JPEG" else "image/png"

        # Prepare payload for vLLM
        payload = {
            "model": "google/gemma-3-4b-it",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }

        endpoint = "/v1/chat/completions"
        url = f"{base_url.rstrip('/')}{endpoint}"
        headers = {"Content-Type": "application/json"}

        # Send request to vLLM
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        vllm_result = response.json()
        vllm_response = vllm_result["choices"][0]["message"]["content"]

        # Translate the vLLM response
        translation_payload = {
            "sentences": [vllm_response],
            "src_lang": src_lang,
            "tgt_lang": tgt_lang
        }
        translation_response = requests.post(
            translation_api_url,
            json=translation_payload,
            headers={"accept": "application/json", "Content-Type": "application/json"}
        )
        translation_response.raise_for_status()
        translation_result = translation_response.json()
        translated_text = translation_result["translations"][0]

        # Return both original and translated responses
        return f"Original Response:\n{vllm_response}\n\nTranslated Response ({src_lang} to {tgt_lang}):\n{translated_text}"

    except requests.exceptions.RequestException as e:
        return f"Error querying vLLM server or translation API: {str(e)}"
    except KeyError as e:
        return f"Error parsing response: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

# Define language options (based on the provided example and common use cases)
language_options = [
    "kan_Knda",  # Kannada
    "eng_Latn",  # English
    "hin_Deva",  # Hindi
    "tam_Taml",  # Tamil
    "tel_Telu",  # Telugu
]

# Define Gradio interface
with gr.Blocks(title="dwani.ai Visual Query with Translation") as demo:
    gr.Markdown("# dwani.ai Visual Query Interface with Translation")
    gr.Markdown("Upload an image, enter a prompt, and select source and target languages to query the Gemma 3 4B IT model and translate the response.")

    with gr.Row():
        with gr.Column():
            image_input = gr.Image(type="pil", label="Upload Image (JPEG/PNG)")
            prompt_input = gr.Textbox(label="Prompt", placeholder="e.g., Describe this image in detail")
            src_lang_input = gr.Dropdown(
                choices=language_options,
                label="Source Language",
                value="eng_Latn"  # Default to English
            )
            tgt_lang_input = gr.Dropdown(
                choices=language_options,
                label="Target Language",
                value="kan_Knda"  # Default to Kannada
            )
            submit_button = gr.Button("Submit")
        with gr.Column():
            output = gr.Textbox(label="Response", lines=10)

    # Bind the query function to the button
    submit_button.click(
        fn=query_vllm,
        inputs=[image_input, prompt_input, src_lang_input, tgt_lang_input],
        outputs=output
    )

# Launch the interface
demo.launch(server_name="0.0.0.0", server_port=7860)