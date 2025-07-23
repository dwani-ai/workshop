import dwani
import logging

logger = logging.getLogger(__name__)

def transcribe_api(audio_file, language):
    if not audio_file:
        return {"error": "Please upload an audio file"}
    try:
        result = dwani.ASR.transcribe(file_path=audio_file, language=language)
        return result
    except Exception as e:
        logger.error(f"ASR API error: {str(e)}")
        return {"error": f"ASR API error: {str(e)}"}