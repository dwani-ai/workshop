import dwani
import logging

logger = logging.getLogger(__name__)

def chat_api(prompt, language, tgt_language):
    try:
        resp = dwani.Chat.create(prompt, language, tgt_language)
        return resp
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return {"error": f"Chat API error: {str(e)}"}