import gradio as gr
import os
import tempfile
import dwani
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure dwani API settings from environment variables
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE_URL")

if not dwani.api_key or not dwani.api_base:
    logger.error("API key or base URL not set. Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")
    raise RuntimeError("Please set DWANI_API_KEY and DWANI_API_BASE_URL environment variables.")

# Language options for dropdowns (display name and code)
language_options = [
    ("English", "eng_Latn"),
    ("Kannada", "kan_Knda"),
    ("Hindi", "hin_Deva")
]

language_names = [lang[0] for lang in language_options]
lang_code_map = {lang[0]: lang[1] for lang in language_options}


def parse_page_numbers(pages_str):
    """
    Parse a string of comma-separated page numbers/ranges into a sorted list of unique integers.
    Example inputs:
        "1,3,5"
        "1-3,5"
    """
    pages = set()
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                if start > end or start < 1:
                    continue
                pages.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                page = int(part)
                if page >= 1:
                    pages.add(page)
            except ValueError:
                continue
    return sorted(pages)


def simple_format_resume(text):
    """
    Basic formatting for resume text:
    - Convert '** text **' to bold <b>text</b>
    - Replace multiple dots or underscores with horizontal lines
    - Preserve line breaks with <br>
    """
    # Convert ** bold ** to <b>bold</b>
    text = re.sub(r"\*\*\s*(.*?)\s*\*\*", r"<b>\1</b>", text)

    # Replace long sequences of dots or underscores with <hr>
    text = re.sub(r"([.\-_])\1{5,}", "<hr>", text)

    # Preserve line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '<br>')

    return text


def results_to_html(results):
    """
    Convert the results dictionary into an HTML formatted string,
    applying basic formatting to preserve resume style.
    """
    html_lines = []
    for page, content in results.items():
        html_lines.append(f"<h2>{page}</h2>")
        if "error" in content:
            html_lines.append(f"<p style='color:red;'><b>Error:</b> {content['error']}</p>")
        else:
            html_lines.append("<h3>Original Text:</h3>")
            original_html = simple_format_resume(content.get('Original Text', ''))
            html_lines.append(f"<div style='background:#f0f0f0; padding:10px; border-radius:5px;'>{original_html}</div>")

            response_text = content.get('Response', '')
            if response_text:
                html_lines.append(f"<p><b>Response:</b><br>{response_text}</p>")

            html_lines.append(f"<p><b>Processed Page:</b> {content.get('Processed Page', '')}</p>")

            translated_html = simple_format_resume(content.get('Translated Response', ''))
            html_lines.append("<h3>Translated Resume:</h3>")
            html_lines.append(f"<div style='background:#e8f5e9; padding:10px; border-radius:5px;'>{translated_html}</div>")

        html_lines.append("<hr>")
    return "\n".join(html_lines)


def results_to_markdown(results):
    """
    Convert the results dictionary into a Markdown formatted string,
    preserving the translated resume content in code blocks.
    """
    md_lines = []
    for page, content in results.items():
        md_lines.append(f"## {page}\n")
        if "error" in content:
            md_lines.append(f"**Error:** {content['error']}\n")
        else:
            md_lines.append("**Original Text:**\n\n```")
            md_lines.append(content.get('Original Text', '') + "\n")
            md_lines.append("```\n")

            response_text = content.get('Response', '')
            if response_text:
                md_lines.append("Response:\n\n" + response_text + "\n")

            md_lines.append("**Processed Page:** " + str(content.get('Processed Page', '')) + "\n")

            translated = content.get('Translated Response', '')
            md_lines.append("**Translated Resume:**\n\n```")
            md_lines.append(translated + "\n")
            md_lines.append("```\n")

        md_lines.append("\n---\n")
    return "\n".join(md_lines)


def process_pdf(pdf_file, pages_str, prompt, src_lang, tgt_lang):
    logger.info(f"Processing PDF: {pdf_file}, Pages: {pages_str}, Prompt: {prompt}, Source: {src_lang}, Target: {tgt_lang}")

    if not pdf_file:
        return "Error: Please upload a PDF file", None

    if not prompt.strip():
        return "Error: Please provide a non-empty prompt", None

    pages = parse_page_numbers(pages_str)
    if not pages:
        return "Error: Please provide valid page numbers (e.g., 1,3,5 or 1-3)", None

    src_lang_code = lang_code_map.get(src_lang)
    tgt_lang_code = lang_code_map.get(tgt_lang)

    if not src_lang_code or not tgt_lang_code:
        return "Error: Invalid source or target language selection", None

    file_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file

    results = {}
    for page_number in pages:
        try:
            # Call Dwani API (without 'prompt' arg as it's unsupported)
            result = dwani.Documents.run_extract(
                file_path=file_path,
                page_number=page_number,
                src_lang=src_lang_code,
                tgt_lang=tgt_lang_code
            )
            logger.debug(f"API response for page {page_number}: {result}")

            page_data = None
            for p in result.get('pages', []):
                if p.get('processed_page') == page_number:
                    page_data = p
                    break

            if page_data is None:
                results[f"Page {page_number}"] = {"error": "No data returned for this page"}
                continue

            results[f"Page {page_number}"] = {
                "Processed Page": page_data.get("processed_page", "N/A"),
                "Original Text": page_data.get("page_content", "N/A"),
                "Translated Response": page_data.get("translated_content", "N/A"),
                "Response": ""
            }
        except dwani.exceptions.DwaniAPIError as e:
            logger.error(f"Dwani API error on page {page_number}: {e}")
            results[f"Page {page_number}"] = {"error": f"API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error on page {page_number}: {e}")
            results[f"Page {page_number}"] = {"error": f"Unexpected error: {str(e)}"}

    # Convert results to HTML for display
    html_text = results_to_html(results)

    # Save markdown for download
    markdown_text = results_to_markdown(results)
    temp_md_file = tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode='w', encoding='utf-8')
    temp_md_file.write(markdown_text)
    temp_md_file.close()

    return html_text, temp_md_file.name


# Gradio UI
with gr.Blocks(title="Resume Translator") as demo:
    gr.Markdown("# Resume Translator")
    gr.Markdown(
        "Upload your resume PDF, specify pages to translate, enter a prompt (e.g., 'Translate the resume'), "
        "and select source and target languages."
    )

    with gr.Row():
        with gr.Column():
            pdf_input = gr.File(label="Upload Resume PDF", file_types=[".pdf"])
            pages_input = gr.Textbox(
                label="Page Numbers",
                placeholder="e.g., 1,3,5 or 1-3",
                value="1",
                lines=1
            )
            prompt_input = gr.Textbox(
                label="Custom Prompt",
                placeholder="e.g., Translate the resume",
                value="Translate the resume",
                lines=2
            )
            src_lang_input = gr.Dropdown(
                label="Source Language",
                choices=language_names,
                value="English"
            )
            tgt_lang_input = gr.Dropdown(
                label="Target Language",
                choices=language_names,
                value="Kannada"
            )
            submit_btn = gr.Button("Translate")

        with gr.Column():
            output_html = gr.HTML(label="Translated Resume Output")
            download_md = gr.File(label="Download Translated Resume (Markdown)")

    submit_btn.click(
        fn=process_pdf,
        inputs=[pdf_input, pages_input, prompt_input, src_lang_input, tgt_lang_input],
        outputs=[output_html, download_md]
    )


if __name__ == "__main__":
    demo.launch()
