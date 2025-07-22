import dwani
import logging
import os

logger = logging.getLogger(__name__)

def translate_to_kannada(text):
    if not text or text.strip() == "":
        return ""
    try:
        resp = dwani.Translate.run_translate(
            sentences=text,
            src_lang="english",
            tgt_lang="kannada"
        )
        if isinstance(resp, dict):
            translated = resp.get("translated_text")
            if translated:
                return translated.strip()
            if "translations" in resp and isinstance(resp["translations"], list):
                return " ".join(t.strip() for t in resp["translations"] if isinstance(t, str))
            return str(resp).strip()
        return resp.strip() if isinstance(resp, str) else str(resp).strip()
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return f"Translation error: {str(e)}"

def extract_text_from_response(chat_response):
    if isinstance(chat_response, dict):
        for key in ("text", "response", "content"):
            if key in chat_response and isinstance(chat_response[key], str):
                return chat_response[key]
        return str(chat_response)
    return str(chat_response)

def extract_resume_sections(extracted_resume):
    resume_str = str(extracted_resume)
    prompt = (
        resume_str +
        "\n\nExtract the following details from the resume:\n"
        "1. Contact details\n"
        "2. Objective or professional summary\n"
        "3. Education details\n"
        "4. Work experience\n"
        "5. Skills\n"
        "6. Certifications\n\n"
        "Return the information in a JSON format with keys: "
        "'contact_details', 'objective', 'education', 'work_experience', 'skills', 'certifications'."
    )
    response = dwani.Chat.direct(prompt=prompt, model="gemma3")
    return extract_text_from_response(response)

def process_pdf_resume(pdf_file):
    if not pdf_file:
        return None
    file_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    try:
        result = dwani.Documents.run_ocr_all(file_path=file_path, model="gemma3")
        extracted_details = extract_resume_sections(result)
        translation = translate_to_kannada(extracted_details)
        text_filename = "/data/resume.txt"
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(translation)
        return text_filename
    except Exception as e:
        logger.error(f"Resume processing error: {str(e)}")
        return None