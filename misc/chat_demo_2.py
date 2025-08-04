import os
import uuid
import time
import gradio as gr
from openai import OpenAI

base_url = os.getenv('VLLM_IP', 'http://localhost:8000/v1') 
# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY', 'your-api-key')  # Replace with your API key or set as environment variable
client = OpenAI(
    api_key=api_key,
    base_url=base_url
#    base_url="http://192.222.51.102:9000/v1"  # Adjust to your local server's endpoint
)

# Configuration
DEFAULT_SYS_PROMPT = "You are a helpful and harmless assistant. Respond concisely but meaningfully to short inputs, and provide detailed answers when appropriate."
DEFAULT_MODEL = "gemma3"  # Adjust to your model's name

MODEL_OPTIONS = [
    {"label": "Gemma3", "value": "gemma3"}
]
MODEL_OPTIONS_MAP = {model["value"]: model for model in MODEL_OPTIONS}

DEFAULT_SETTINGS = {
    "model": DEFAULT_MODEL,
    "sys_prompt": DEFAULT_SYS_PROMPT
}

def format_history(history, sys_prompt):
    messages = [{"role": "system", "content": sys_prompt}] + history
    return messages

class Gradio_Events:
    @staticmethod
    def submit(state_value, user_input, model_value, sys_prompt_value):
        conversation_id = state_value["conversation_id"]
        history = state_value["conversation_contexts"][conversation_id]["history"]
        settings = {"model": model_value, "sys_prompt": sys_prompt_value}
        state_value["conversation_contexts"][conversation_id]["settings"] = settings

        history.append({"role": "user", "content": user_input})
        messages = format_history(history, sys_prompt_value)

        try:
            response = client.chat.completions.create(
                model=model_value,
                messages=messages,
                stream=False
            )
            start_time = time.time()
            answer_content = response.choices[0].message.content
            history.append({"role": "assistant", "content": f"{answer_content}\n\n*Generated in {time.time() - start_time:.2f}s*"})
        except Exception as e:
            history.append({"role": "assistant", "content": f"Error: {str(e)}"})

        return (
            gr.update(value=history),
            gr.update(value=state_value),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], 
                     visible=bool(state_value["conversations"]), 
                     value=state_value["conversation_id"])
        )

    @staticmethod
    def add_message(user_input, model_value, sys_prompt_value, state_value):
        if not user_input.strip():
            return (
                gr.skip(),
                state_value,
                user_input,
                gr.skip(),
                gr.skip(),
                gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], 
                         visible=bool(state_value["conversations"]), 
                         value=state_value["conversation_id"])
            )

        if not state_value["conversation_id"]:
            random_id = str(uuid.uuid4())
            state_value["conversation_id"] = random_id
            state_value["conversation_contexts"][random_id] = {
                "history": [],
                "settings": {"model": model_value, "sys_prompt": sys_prompt_value}
            }
            state_value["conversations"].append({
                "label": user_input[:30] + "..." if len(user_input) > 30 else user_input,
                "key": random_id
            })

        return Gradio_Events.submit(state_value, user_input, model_value, sys_prompt_value)

    @staticmethod
    def new_chat(state_value):
        state_value["conversation_id"] = ""
        return (
            gr.update(value=[]),
            gr.update(value=state_value),
            gr.update(value=DEFAULT_SETTINGS["model"]),
            gr.update(value=DEFAULT_SETTINGS["sys_prompt"]),
            gr.update(choices=[], visible=False)
        )

    @staticmethod
    def select_conversation(state_value, evt: gr.EventData):
        conversation_id = evt._data
        if conversation_id not in state_value["conversation_contexts"]:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip()
        state_value["conversation_id"] = conversation_id
        history = state_value["conversation_contexts"][conversation_id]["history"]
        settings = state_value["conversation_contexts"][conversation_id]["settings"]
        return (
            gr.update(value=history),
            gr.update(value=state_value),
            gr.update(value=settings["model"]),
            gr.update(value=settings["sys_prompt"])
        )

    @staticmethod
    def delete_conversation(state_value, evt: gr.EventData):
        conversation_id = evt._data
        if conversation_id in state_value["conversation_contexts"]:
            del state_value["conversation_contexts"][conversation_id]
            state_value["conversations"] = [c for c in state_value["conversations"] if c["key"] != conversation_id]
            if state_value["conversation_id"] == conversation_id:
                state_value["conversation_id"] = ""
                return (
                    gr.update(value=[]),
                    gr.update(value=state_value),
                    gr.update(choices=[], visible=False)
                )
        return gr.skip(), gr.update(value=state_value), gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], 
                                                                visible=bool(state_value["conversations"]), 
                                                                value=state_value["conversation_id"])

    @staticmethod
    def clear_conversation(state_value):
        if state_value["conversation_id"]:
            state_value["conversation_contexts"][state_value["conversation_id"]]["history"] = []
            return gr.update(value=[]), gr.update(value=state_value)
        return gr.skip(), gr.skip()

css = """
.gradio-container {
    max-width: 1200px;
    margin: auto;
}
#chatbot {
    height: calc(100vh - 200px);
    max-height: 800px;
}
#conversations {
    max-height: 600px;
    overflow-y: auto;
}
"""

with gr.Blocks(css=css, fill_width=True) as demo:
    state = gr.State({
        "conversation_contexts": {},
        "conversations": [],
        "conversation_id": ""
    })

    with gr.Row():
        with gr.Column(scale=1, min_width=200):
            gr.Markdown("## Conversations")
            conversations = gr.Dropdown(
                label="Conversations",
                elem_id="conversations",
                choices=[],
                interactive=True,
                visible=False
            )
            new_chat_btn = gr.Button("New Conversation")
            delete_conversation_btn = gr.Button("Delete Selected Conversation")

        with gr.Column(scale=3):
            gr.Markdown("## Chatbot")
            chatbot = gr.Chatbot(elem_id="chatbot", show_copy_button=True, type="messages")
            user_input = gr.Textbox(placeholder="Type your message...", label="Message")
            with gr.Row():
                model_select = gr.Dropdown(choices=list(MODEL_OPTIONS_MAP.keys()), value=DEFAULT_SETTINGS["model"], label="Model")
                sys_prompt = gr.Textbox(value=DEFAULT_SETTINGS["sys_prompt"], label="System Prompt")
            with gr.Row():
                submit_btn = gr.Button("Send", elem_id="submit_btn")
                clear_btn = gr.Button("Clear Conversation")

    # Event Handlers
    submit_btn.click(
        fn=Gradio_Events.add_message,
        inputs=[user_input, model_select, sys_prompt, state],
        outputs=[chatbot, state, user_input, submit_btn, clear_btn, conversations]
    )
    user_input.submit(
        fn=Gradio_Events.add_message,
        inputs=[user_input, model_select, sys_prompt, state],
        outputs=[chatbot, state, user_input, submit_btn, clear_btn, conversations]
    )
    new_chat_btn.click(
        fn=Gradio_Events.new_chat,
        inputs=[state],
        outputs=[chatbot, state, model_select, sys_prompt, conversations]
    )
    conversations.select(
        fn=Gradio_Events.select_conversation,
        inputs=[state],
        outputs=[chatbot, state, model_select, sys_prompt]
    )
    delete_conversation_btn.click(
        fn=Gradio_Events.delete_conversation,
        inputs=[state],
        outputs=[chatbot, state, conversations]
    )
    clear_btn.click(
        fn=Gradio_Events.clear_conversation,
        inputs=[state],
        outputs=[chatbot, state]
    )

if __name__ == "__main__":
    demo.launch()