import gradio as gr
import requests
import base64
from PIL import Image
import io
import os


# Get the base URL (IP or domain) from environment variable
base_url = os.getenv("DWANI_AI_API_BASE_URL")



def image_to_base64(image):
    """Convert a PIL Image to base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format=image.format if image.format in ["JPEG", "PNG"] else "JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def query_vllm(image, prompt, max_tokens=512, temperature=0.7, top_p=0.9):
    """Send image and prompt to vLLM server and return response."""
    if image is None:
        return "Please upload an image."
    if not prompt:
        return "Please enter a prompt."

    try:
        # Convert image to base64
        img_base64 = image_to_base64(image)
        mime_type = "image/jpeg" if image.format == "JPEG" else "image/png"

        # Prepare payload
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

        # Construct the full API URL
        url = f"{base_url.rstrip('/')}{endpoint}"
        # Send request to vLLM
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

        # Check response
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error querying vLLM server: {str(e)}"
    except KeyError as e:
        return f"Error parsing response: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

# Define Gradio interface
with gr.Blocks(title="dwani.ai Visual Query") as demo:
    gr.Markdown("#dwani.ai  Visual Query Interface")
    gr.Markdown("Upload an image and enter a prompt to query the Gemma 3 4B IT model.")

    with gr.Row():
        with gr.Column():
            image_input = gr.Image(type="pil", label="Upload Image (JPEG/PNG)")
            prompt_input = gr.Textbox(label="Prompt", placeholder="e.g., Describe this image in detail")
            submit_button = gr.Button("Submit")
        with gr.Column():
            output = gr.Textbox(label="Response", lines=10)

    # Bind the query function to the button
    submit_button.click(
        fn=query_vllm,
        inputs=[image_input, prompt_input],
        outputs=output
    )

# Launch the interface
demo.launch(server_name="0.0.0.0", server_port=7860)