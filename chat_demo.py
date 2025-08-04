import os
import uuid
import time
import gradio as gr
from openai import OpenAI

# Environment variables
is_cn = os.getenv('MODELSCOPE_ENVIRONMENT') == 'studio'
api_key = os.getenv('OPENAI_API_KEY', 'dummy-key')  # Use dummy key for local server if not required

# Bilingual text function
def get_text(text: str, cn_text: str):
    return cn_text if is_cn else text

# Configuration
DEFAULT_SUGGESTIONS = [
    {"label": get_text('Make a plan', '制定计划'), "value": get_text('Help me with a plan to start a business', '帮助我制定一个创业计划')},
    {"label": get_text('Achieve my goals', '实现我的目标'), "value": get_text('Help me with a plan to achieve my goals', '帮助我制定一个实现目标的计划')},
    {"label": get_text('Successful interview', '成功的面试'), "value": get_text('Help me with a plan for a successful interview', '帮助我制定一个成功的面试计划')},
    {"label": get_text('Help me write', '帮我写'), "value": get_text('Help me write a story with a twist ending', '帮助我写一个带有意外结局的故事')},
    {"label": get_text('Blog post on mental health', '关于心理健康的博客文章'), "value": get_text('Help me write a blog post on mental health', '帮助我写一篇关于心理健康的博客文章')},
    {"label": get_text('Letter to my future self', '给未来自己的信'), "value": get_text('Letter to my future self', '帮助我写一封给未来自己的信')}
]

DEFAULT_SYS_PROMPT = "You are a helpful and harmless assistant."
DEFAULT_MODEL = "gemma3"  # Adjust to the exact model name used by your local server

MODEL_OPTIONS = [
    {"label": get_text("Gemma3", "Gemma3"), "modelId": "gemma3", "value": "gemma3", "link": "https://huggingface.co/google/gemma-3"}
]
MODEL_OPTIONS_MAP = {model["value"]: model for model in MODEL_OPTIONS}

DEFAULT_SETTINGS = {
    "model": DEFAULT_MODEL,
    "sys_prompt": DEFAULT_SYS_PROMPT
}

base_url = os.getenv("VLLM_IP", "http://localhost:8000/v1")
api_key= "jellp"
client = OpenAI(
    api_key=api_key,  # Use dummy key or server-specific key
    base_url=base_url
)

def format_history(history, sys_prompt):
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in history:
        messages.append(msg)
    return messages

class Gradio_Events:
    @staticmethod
    def submit(state_value, user_input, model_value, sys_prompt_value):
        conversation_id = state_value["conversation_id"]
        history = state_value["conversation_contexts"][conversation_id]["history"]
        settings = {"model": model_value, "sys_prompt": sys_prompt_value}
        state_value["conversation_contexts"][conversation_id]["settings"] = settings
        model = model_value
        sys_prompt = sys_prompt_value
        messages = format_history(history, sys_prompt=sys_prompt)

        history.append({"role": "user", "content": user_input})
        chatbot_update = gr.update(value=history)
        state_update = gr.update(value=state_value)
        user_input_update = gr.update(value="", interactive=False)
        submit_btn_update = gr.update(interactive=False)
        clear_btn_update = gr.update(interactive=False)
        conversations_update = gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], visible=bool(state_value["conversations"]), value=state_value["conversation_id"])

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            start_time = time.time()
            answer_content = ""
            history.append({"role": "assistant", "content": ""})

            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    answer_content += delta
                    history[-1]["content"] = answer_content
                    chatbot_update = gr.update(value=history)
                    state_update = gr.update(value=state_value)

            cost_time = "{:.2f}".format(time.time() - start_time)
            history[-1]["content"] += f"\n\n*Generated in {cost_time}s*"
            return (
                chatbot_update,
                state_update,
                gr.update(interactive=True),
                gr.update(interactive=True),
                gr.update(interactive=True),
                gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], visible=bool(state_value["conversations"]), value=state_value["conversation_id"])
            )
        except Exception as e:
            print(f"Model: {model} - Error: {e}")
            history[-1]["content"] = f"Error: {str(e)}"
            return (
                gr.update(value=history),
                gr.update(value=state_value),
                gr.update(interactive=True),
                gr.update(interactive=True),
                gr.update(interactive=True),
                gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], visible=bool(state_value["conversations"]), value=state_value["conversation_id"])
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
                gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], visible=bool(state_value["conversations"]), value=state_value["conversation_id"])
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
        return gr.skip(), gr.update(value=state_value), gr.update(choices=[(c["label"], c["key"]) for c in state_value["conversations"]], visible=bool(state_value["conversations"]), value=state_value["conversation_id"])

    @staticmethod
    def clear_conversation(state_value):
        if state_value["conversation_id"]:
            state_value["conversation_contexts"][state_value["conversation_id"]]["history"] = []
            return gr.update(value=[]), gr.update(value=state_value)
        return gr.skip(), gr.skip()

    @staticmethod
    def select_suggestion(evt: gr.EventData):
        return evt._data

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
            user_input = gr.Textbox(placeholder="Type your message or enter '/' for suggestions", label="Message")
            suggestions = gr.Dropdown(choices=[s["value"] for s in DEFAULT_SUGGESTIONS], label="Suggestions", visible=False)
            with gr.Row():
                model_select = gr.Dropdown(choices=list(MODEL_OPTIONS_MAP.keys()), value=DEFAULT_SETTINGS["model"], label="Model")
                sys_prompt = gr.Textbox(value=DEFAULT_SETTINGS["sys_prompt"], label="System Prompt")
            with gr.Row():
                submit_btn = gr.Button("Send", elem_id="submit_btn")
                clear_btn = gr.Button("Clear Conversation")

    # Event Handlers
    submit_event = user_input.submit(
        fn=Gradio_Events.add_message,
        inputs=[user_input, model_select, sys_prompt, state],
        outputs=[chatbot, state, user_input, submit_btn, clear_btn, conversations]
    )
    submit_btn.click(
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
    user_input.change(
        fn=lambda x: gr.update(visible=x.startswith("/")),
        inputs=[user_input],
        outputs=[suggestions]
    )
    suggestions.select(
        fn=Gradio_Events.select_suggestion,
        outputs=[user_input]
    )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=100, max_size=100).launch()