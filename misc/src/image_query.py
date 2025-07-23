import dwani
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

def visual_query(image, src_lang, tgt_lang, prompt):
    if not image:
        return {"error": "Please upload an image"}
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        image.save(temp_file.name, format="PNG")
        temp_file_path = temp_file.name
    try:
        result = dwani.Vision.caption(
            file_path=temp_file_path,
            query=prompt,
            src_lang=src_lang,
            tgt_lang=tgt_lang
        )
        return result
    except Exception as e:
        logger.error(f"Vision API error: {str(e)}")
        return {"error": f"Vision API error: {str(e)}"}
    finally:
        os.unlink(temp_file_path)