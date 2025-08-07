import gradio as gr
import requests

# You may need to adjust the endpoint depending on how llama.cpp is started
API_URL = "http://localhost:9500/v1/chat/completions"

# For normal completions endpoint use instead:
# API_URL = "http://localhost:9500/v1/completions"

def ask_gpt(message, history):
    # Compose messages in OpenAI format (for chat endpoint)
    chat_history = [{"role": "system", "content": "You are a helpful assistant."}]
    for item in history:
        chat_history.append({"role": "user", "content": item[0]})
        if item[1]:
            chat_history.append({"role": "assistant", "content": item[1]})
    
    chat_history.append({"role": "user", "content": message})
    data = {
        "model": "gpt-oss-20b",
        "messages": chat_history,
        "max_tokens": 512,
        "temperature": 0.7,
        "stream": False,  # If you want streaming output, extra logic is needed
    }
    try:
        response = requests.post(API_URL, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"Error: {e}"
    return answer

with gr.Blocks() as demo:
    gr.ChatInterface(ask_gpt, title="GPT-OSS-20B Chat (via llama.cpp API)")

demo.launch()
