import gradio as gr
import openai
import re

# Configure the OpenAI client
client = openai.OpenAI(
    base_url="http://localhost:9500/v1",  # Custom API URL
    api_key="YOUR_API_KEY"  # Replace with your API key if required; use empty string if no key is needed
)

def extract_values(text):
    pattern = r'<\|channel\|>(.*?)<\|message\|>(.*?)(?=<\|start\|>|<\|channel\|>|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    result = [{'channel': m[0], 'message': m[1].strip()} for m in matches]
    return result

def get_final_message(text):
    extracted = extract_values(text)
    for item in extracted:
        if item['channel'] == 'final':
            return item['message']
    return None  # Return None if no "final" message found

def ask_gpt(user_message, history):
    # Compose conversation history to OpenAI format
    messages = [{"role": "system", "content": "hello"}]  # Optional system prompt

    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        if assistant:
            messages.append({"role": "assistant", "content": assistant})

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    try:
        # Use OpenAI client to make the API call
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=1.0,
            max_tokens=10000,
            stream=False
        )

        # Extract the raw content
        raw_answer = response.choices[0].message.content
        final_message = get_final_message(raw_answer)
        answer = final_message if final_message is not None else raw_answer
    except Exception as e:
        answer = f"Error: {e}"
    return answer

with gr.Blocks() as demo:
    gr.ChatInterface(ask_gpt, title="gpt-oss")

demo.launch()