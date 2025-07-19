import gradio as gr
import logging
import dwani
import os
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure dwani API settings from environment variables
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")


def translate_to_kannada(text):
    """Translate English text to Kannada using dwani.Translate.run_translate."""
    if not text or text.strip() == "":
        return ""
    start_time = time.time()
    try:
        resp = dwani.Translate.run_translate(
            sentences=text,
            src_lang="english",
            tgt_lang="kannada"
        )

        elapsed = time.time() - start_time
        logger.info(f"Translation took {elapsed:.2f} seconds")
        if isinstance(resp, dict):
            translated = resp.get("translated_text")
            if translated:
                return translated.strip()
            if "translations" in resp and isinstance(resp["translations"], list):
                return " ".join(t.strip() for t in resp["translations"] if isinstance(t, str))
            return str(resp).strip()
        elif isinstance(resp, str):
            return resp.strip()
        else:
            return str(resp).strip()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return f"Translation error: {e}"

def process_pdf(pdf_file):
    logger.debug("Received inputs - PDF: %s", pdf_file)
    overall_start = time.time()
    if not pdf_file:
        logger.error("No PDF file provided")
        return None
    extraction_start = time.time()
    file_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
  
    result = dwani.Documents.run_ocr_all(file_path=file_path, model="gemma3")

    extracted_details = extract_resume_sections(result)

    translation = translate_to_kannada(extracted_details)

 #   formatted_resume = format_resume(contact_kan, objective_kan, education_kan, work_experience_kan, skills_kan, certifications_kan)
    extraction_elapsed = time.time() - extraction_start
    logger.info(f"Extraction from PDF took {extraction_elapsed:.2f} seconds")
    text_filename = "resume.txt"
    with open(text_filename, "w", encoding="utf-8") as f:
        f.write(translation)
    return text_filename

def extract_text_from_response(chat_response):
    if isinstance(chat_response, dict):
        for key in ("text", "response", "content"):
            if key in chat_response and isinstance(chat_response[key], str):
                return chat_response[key]
        return str(chat_response)
    elif isinstance(chat_response, str):
        return chat_response
    else:
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


def safe_strip(value):
    if isinstance(value, dict):
        value = extract_text_from_response(value)
    return str(value).strip()

def format_resume(contact, objective, education, work_experience, skills, certifications):
    return f"""# Resume (Kannada)

## ಸಂಪರ್ಕ ವಿವರಗಳು (Contact Details)
{safe_strip(contact)}

## ಉದ್ದೇಶ (Objective)
{safe_strip(objective)}

## ಶಿಕ್ಷಣ (Education)
{safe_strip(education)}

## ಕೆಲಸದ ಅನುಭವ (Work Experience)
{safe_strip(work_experience)}

## ಕೌಶಲ್ಯಗಳು (Skills)
{safe_strip(skills)}

## ಪ್ರಮಾಣಪತ್ರಗಳು (Certifications)
{safe_strip(certifications)}
"""

with gr.Blocks(title="Resume Translator with Kannada Translation") as resume_translator:
    gr.Markdown("# Resume Upload")
    gr.Markdown("Upload a Resume PDF to extract, translate to Kannada, and download.")

    with gr.Row():
        with gr.Column():
            pdf_input = gr.File(label="Upload Resume", file_types=[".pdf"])
            submit_btn = gr.Button("Process")

        with gr.Column():
            text_output = gr.File(label="Download Formatted Resume (.txt)")

    submit_btn.click(
        fn=process_pdf,
        inputs=[pdf_input],
        outputs=text_output
    )

if __name__ == "__main__":
    resume_translator.launch()
