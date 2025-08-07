import gradio as gr
import requests

API_URL = "http://localhost:9500/v1/chat/completions"

def ask_gpt(user_message, history):
    # Compose conversation history to OpenAI format
    messages = [{"role": "system", "content": "hello"}]  # Start with optional system prompt

    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        if assistant:
            messages.append({"role": "assistant", "content": assistant})

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    data = {
        "messages": messages,
        "temperature": 1.0,
        "max_tokens": 1000,
        "stream": False,   # Set to True if you want to implement streaming logic
        "model": "openai/gpt-oss-120b"
    }

    try:
        resp = requests.post(API_URL, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        # OpenAI API usually returns the response here:
        answer = result["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"Error: {e}"

    return answer

with gr.Blocks() as demo:
    gr.ChatInterface(ask_gpt, title="Chat with gpt-oss-120b /v1/chat/completions")

demo.launch()
