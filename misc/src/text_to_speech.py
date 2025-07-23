import dwani
import tempfile
import logging

logger = logging.getLogger(__name__)

def text_to_speech(text, language):
    if not text:
        return None
    try:
        response = dwani.Audio.speech(
            input=text,
            response_format="mp3",
            language=language
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response)
            return temp_file.name
    except Exception as e:
        logger.error(f"TTS API error: {str(e)}")
        return None