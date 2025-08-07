import gradio as gr
import requests
from openai_harmony import (
    load_harmony_encoding,
    HarmonyEncodingName,
    Role,
    Message,
    Conversation,
    SystemContent,
    DeveloperContent,
)

# Load the harmony encoding for GPT-OSS style models
enc = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)

# Initialize conversation with system and developer instructions
convo = Conversation.from_messages([
    Message.from_role_and_content(Role.SYSTEM, SystemContent.new()),
    Message.from_role_and_content(Role.DEVELOPER, DeveloperContent.new().with_instructions("You are a helpful assistant.")),
])

MODEL_SERVER_URL = "http://localhost:9500"  # URL for your model server


def chat_with_harmony(user_input, conversation=convo):
    # Append user message to conversation
    conversation.messages.append(Message.from_role_and_content(Role.USER, user_input))
    
    # Encode conversation into harmony format tokens and decode to string prompt
    prompt_tokens = enc.render_conversation_for_completion(conversation, Role.ASSISTANT)
    prompt_text = enc.decode(prompt_tokens)
    
    # Send the harmony prompt text to the model server
    # Assuming your server API expects JSON with {'prompt': prompt_text}
    # and responds with JSON {'response': assistant_reply}
    response = requests.post(
        MODEL_SERVER_URL,
        json={"prompt": prompt_text}
    )
    response.raise_for_status()
    assistant_response = response.json().get("response", "Sorry, no response from model.")
    
    # Append assistant response to conversation
    conversation.messages.append(Message.from_role_and_content(Role.ASSISTANT, assistant_response))
    
    # Prepare chat history for Gradio chatbot interface: pairs of (user, assistant)
    chat_history = []
    # Collect messages with roles user or assistant only
    pairs = []
    user_msgs = [m.content for m in conversation.messages if m.role == Role.USER]
    assistant_msgs = [m.content for m in conversation.messages if m.role == Role.ASSISTANT]
    # pair them by order (assuming alternating turns)
    for u, a in zip(user_msgs, assistant_msgs):
        pairs.append((u, a))
    
    return pairs, conversation


with gr.Blocks() as demo:
    chatbot = gr.Chatbot()
    user_input = gr.Textbox(placeholder="Say something...")
    state = gr.State(value=convo)  # Keeps conversation state
    
    user_input.submit(chat_with_harmony, inputs=[user_input, state], outputs=[chatbot, state])
    
demo.launch()
