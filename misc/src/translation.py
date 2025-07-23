import dwani
import logging

logger = logging.getLogger(__name__)

def translate_api(sentences, src_lang, tgt_lang):
    if isinstance(sentences, str):
        sentences = [s.strip() for s in sentences.split(",") if s.strip()]
    elif isinstance(sentences, list):
        sentences = [s.strip() for s in sentences if isinstance(s, str) and s.strip()]
    else:
        return {"error": "Invalid input: sentences must be a string or list of strings"}
    if not sentences:
        return {"error": "Please provide at least one non-empty sentence"}
    try:
        result = dwani.Translate.run_translate(sentences=sentences, src_lang=src_lang, tgt_lang=tgt_lang)
        return result
    except dwani.exceptions.DhwaniAPIError as e:
        logger.error(f"Dhwani API error: {str(e)}")
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}