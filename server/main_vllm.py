import argparse
import os
from typing import List
from abc import ABC, abstractmethod
import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
import requests
from time import time
from typing import Optional
# Assuming these are in your project structure
from config.tts_config import SPEED, ResponseFormat, config as tts_config
from config.logging_config import logger

# FastAPI app setup with enhanced docs
app = FastAPI(
    title="Dhwani API",
    description="A multilingual AI-powered API supporting Indian languages for chat, text-to-speech, audio processing, and transcription.",
    version="1.0.0",
    redirect_slashes=False,
    openapi_tags=[
        {"name": "Chat", "description": "Chat-related endpoints"},
        {"name": "Audio", "description": "Audio processing and TTS endpoints"},
        {"name": "Translation", "description": "Text translation endpoints"},
        {"name": "Utility", "description": "General utility endpoints"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Transcribed text from the audio")

    class Config:
        schema_extra = {"example": {"text": "Hello, how are you?"}} 

class TextGenerationResponse(BaseModel):
    text: str = Field(..., description="Generated text response")

    class Config:
        schema_extra = {"example": {"text": "Hi there, I'm doing great!"}} 

class AudioProcessingResponse(BaseModel):
    result: str = Field(..., description="Processed audio result")

    class Config:
        schema_extra = {"example": {"result": "Processed audio output"}} 

class ChatRequest(BaseModel):
    prompt: str = Field(..., description="Prompt for chat (max 1000 characters)")
    src_lang: str = Field(..., description="Source language code")
    tgt_lang: str = Field(..., description="Target language code")

    class Config:
        schema_extra = {
            "example": {
                "prompt": "Hello, how are you?",
                "src_lang": "kan_Knda",
                "tgt_lang": "kan_Knda"
            }
        }

class ChatResponse(BaseModel):
    response: str = Field(..., description="Generated chat response")

    class Config:
        schema_extra = {"example": {"response": "Hi there, I'm doing great!"}} 

class TranslationRequest(BaseModel):
    sentences: List[str] = Field(..., description="List of sentences to translate")
    src_lang: str = Field(..., description="Source language code")
    tgt_lang: str = Field(..., description="Target language code")

    class Config:
        schema_extra = {
            "example": {
                "sentences": ["Hello", "How are you?"],
                "src_lang": "en",
                "tgt_lang": "kan_Knda"
            }
        }

class TranslationResponse(BaseModel):
    translations: List[str] = Field(..., description="Translated sentences")

    class Config:
        schema_extra = {"example": {"translations": ["ನಮಸ್ಕಾರ", "ನೀವು ಹೇಗಿದ್ದೀರಿ?"]}} 

class VisualQueryRequest(BaseModel):
    query: str = Field(..., description="Text query")
    src_lang: str = Field(..., description="Source language code")
    tgt_lang: str = Field(..., description="Target language code")

    class Config:
        schema_extra = {
            "example": {
                "query": "Describe the image",
                "src_lang": "kan_Knda",
                "tgt_lang": "kan_Knda"
            }
        }

class VisualQueryResponse(BaseModel):
    answer: str

# TTS Service Interface
class TTSService(ABC):
    @abstractmethod
    async def generate_speech(self, payload: dict) -> requests.Response:
        pass

class ExternalTTSService(TTSService):
    async def generate_speech(self, payload: dict) -> requests.Response:
        try:
            base_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/audio/speech"
            return requests.post(
                base_url,
                json=payload,
                headers={"accept": "*/*", "Content-Type": "application/json"},
                stream=True,
                timeout=60
            )
        except requests.Timeout:
            logger.error("External TTS API timeout")
            raise HTTPException(status_code=504, detail="External TTS API timeout")
        except requests.RequestException as e:
            logger.error(f"External TTS API error: {str(e)}")
            raise HTTPException(status_code=502, detail=f"External TTS service error: {str(e)}")

def get_tts_service() -> TTSService:
    return ExternalTTSService()

# Endpoints with enhanced Swagger docs
@app.get("/v1/health", 
         summary="Check API Health",
         description="Returns the health status of the API and the current model in use.",
         tags=["Utility"],
         response_model=dict)
async def health_check():
    return {"status": "healthy", "model": "llm_model_name"}  # Placeholder model name

@app.get("/",
         summary="Redirect to Docs",
         description="Redirects to the Swagger UI documentation.",
         tags=["Utility"])
async def home():
    return RedirectResponse(url="/docs")

from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
import tempfile
import os

@app.post("/v1/audio/speech",
          summary="Generate Speech from Text",
          description="Convert text to speech using an external TTS service and return as a downloadable audio file.",
          tags=["Audio"],
          responses={
              200: {"description": "Audio file", "content": {"audio/mp3": {"example": "Binary audio data"}}},
              400: {"description": "Invalid or empty input"},
              502: {"description": "External TTS service unavailable"},
              504: {"description": "TTS service timeout"}
          })
async def generate_audio(
    request: Request,
    input: str = Query(..., description="Text to convert to speech (max 1000 characters)"),
    response_format: str = Query("mp3", description="Audio format (ignored, defaults to mp3 for external API)"),
    tts_service: TTSService = Depends(get_tts_service),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    if not input.strip():
        raise HTTPException(status_code=400, detail="Input cannot be empty")
    if len(input) > 1000:
        raise HTTPException(status_code=400, detail="Input cannot exceed 1000 characters")
    
    logger.info("Processing speech request", extra={
        "endpoint": "/v1/audio/speech",
        "input_length": len(input),
        "client_ip": request.client.host
    })
    
    payload = {"text": input}
    
    # Create a temporary file to store the audio
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file_path = temp_file.name
    
    try:
        response = await tts_service.generate_speech(payload)
        response.raise_for_status()
        
        # Write audio content to the temporary file
        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Prepare headers for the response
        headers = {
            "Content-Disposition": "attachment; filename=\"speech.mp3\"",
            "Cache-Control": "no-cache",
        }
        
        # Schedule file cleanup as a background task
        def cleanup_file(file_path: str):
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Deleted temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temporary file {file_path}: {str(e)}")
        
        background_tasks.add_task(cleanup_file, temp_file_path)
        
        # Return the file as a FileResponse
        return FileResponse(
            path=temp_file_path,
            filename="speech.mp3",
            media_type="audio/mp3",
            headers=headers
        )
    
    except requests.HTTPError as e:
        logger.error(f"External TTS request failed: {str(e)}")
        raise HTTPException(status_code=502, detail=f"External TTS service error: {str(e)}")
    finally:
        # Close the temporary file to ensure it's fully written
        temp_file.close()

@app.post("/v1/indic_chat", 
          response_model=ChatResponse,
          summary="Chat with AI",
          description="Generate a chat response from a prompt and language code.",
          tags=["Chat"],
          responses={
              200: {"description": "Chat response", "model": ChatResponse},
              400: {"description": "Invalid prompt or language code"},
              504: {"description": "Chat service timeout"}
          })
async def chat(
    request: Request,
    chat_request: ChatRequest
):
    if not chat_request.prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(chat_request.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt cannot exceed 1000 characters")
    
    logger.info(f"Received prompt: {chat_request.prompt}, src_lang: {chat_request.src_lang}")
    
    try:
        external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/indic_chat"
        payload = {
            "prompt": chat_request.prompt,
            "src_lang": chat_request.src_lang,
            "tgt_lang": chat_request.tgt_lang
        }
        
        response = requests.post(
            external_url,
            json=payload,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        response.raise_for_status()
        
        response_data = response.json()
        response_text = response_data.get("response", "")
        logger.info(f"Generated Chat response from external API: {response_text}")
        return ChatResponse(response=response_text)
    
    except requests.Timeout:
        logger.error("External chat API request timed out")
        raise HTTPException(status_code=504, detail="Chat service timeout")
    except requests.RequestException as e:
        logger.error(f"Error calling external chat API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/v1/transcribe/", 
          response_model=TranscriptionResponse,
          summary="Transcribe Audio File",
          description="Transcribe an audio file into text in the specified language.",
          tags=["Audio"],
          responses={
              200: {"description": "Transcription result", "model": TranscriptionResponse},
              400: {"description": "Invalid audio or language"},
              504: {"description": "Transcription service timeout"}
          })
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Query(..., description="Language of the audio (kannada, hindi, tamil)")
):
    # Validate language
    allowed_languages = ["kannada", "hindi", "tamil"]
    if language not in allowed_languages:
        raise HTTPException(status_code=400, detail=f"Language must be one of {allowed_languages}")
    
    start_time = time()
    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/transcribe/?language={language}"
        response = requests.post(
            external_url,
            files=files,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        transcription = response.json().get("text", "")
        logger.info(f"Transcription completed in {time() - start_time:.2f} seconds")
        return TranscriptionResponse(text=transcription)
    
    except requests.Timeout:
        logger.error("Transcription service timed out")
        raise HTTPException(status_code=504, detail="Transcription service timeout")
    except requests.RequestException as e:
        logger.error(f"Transcription request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/v1/translate", 
          response_model=TranslationResponse,
          summary="Translate Text",
          description="Translate a list of sentences from a source to a target language.",
          tags=["Translation"],
          responses={
              200: {"description": "Translation result", "model": TranslationResponse},
              400: {"description": "Invalid sentences or languages"},
              500: {"description": "Translation service error"},
              504: {"description": "Translation service timeout"}
          })
async def translate(
    request: TranslationRequest
):
    # Validate inputs
    if not request.sentences:
        raise HTTPException(status_code=400, detail="Sentences cannot be empty")
    
    # Validate language codes
    supported_languages = [
        "eng_Latn", "hin_Deva", "kan_Knda", "tam_Taml", "mal_Mlym", "tel_Telu",
        "deu_Latn", "fra_Latn", "nld_Latn", "spa_Latn", "ita_Latn", "por_Latn",
        "rus_Cyrl", "pol_Latn"
    ]
    if request.src_lang not in supported_languages or request.tgt_lang not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported language codes: src={request.src_lang}, tgt={request.tgt_lang}")

    logger.info(f"Received translation request: {len(request.sentences)} sentences, src_lang: {request.src_lang}, tgt_lang: {request.tgt_lang}")

    external_url = f"{os.getenv('DWANI_API_BASE_URL_TRANSLATE')}"

    payload = {
        "sentences": request.sentences,
        "src_lang": request.src_lang,
        "tgt_lang": request.tgt_lang
    }

    try:
        response = requests.post(
            f"{external_url}/translate?src_lang={request.src_lang}&tgt_lang={request.tgt_lang}",
            json=payload,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        translations = response_data.get("translations", [])

        if not translations or len(translations) != len(request.sentences):
            logger.warning(f"Unexpected response format: {response_data}")
            raise HTTPException(status_code=500, detail="Invalid response from translation service")

        logger.info(f"Translation successful: {translations}")
        return TranslationResponse(translations=translations)

    except requests.Timeout:
        logger.error("Translation request timed out")
        raise HTTPException(status_code=504, detail="Translation service timeout")
    except requests.RequestException as e:
        logger.error(f"Error during translation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from translation service")
    
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Form, Query
from pydantic import BaseModel, Field

class VisualQueryResponse(BaseModel):
    answer: str

    class Config:
        schema_extra = {"example": {"answer": "The image shows a screenshot of a webpage."}}

@app.post("/v1/indic_visual_query", 
          response_model=VisualQueryResponse,
          summary="Visual Query with Image",
          description="Process a visual query with a text query, image, and language codes. Provide the query and image as form data, and source/target languages as query parameters.",
          tags=["Chat"],
          responses={
              200: {"description": "Query response", "model": VisualQueryResponse},
              400: {"description": "Invalid query or language codes"},
              422: {"description": "Validation error in request body"},
              504: {"description": "Visual query service timeout"}
          })
async def visual_query(
    request: Request,
    query: str = Form(..., description="Text query to describe or analyze the image (e.g., 'describe the image')"),
    file: UploadFile = File(..., description="Image file to analyze (e.g., PNG, JPEG)"),
    src_lang: str = Query(..., description="Source language code (e.g., kan_Knda, en)"),
    tgt_lang: str = Query(..., description="Target language code (e.g., kan_Knda, en)")
):
    # Validate query
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(query) > 1000:
        raise HTTPException(status_code=400, detail="Query cannot exceed 1000 characters")
    
    # Validate language codes
    supported_languages = ["kan_Knda", "hin_Deva", "tam_Taml", "eng_Latn"]  # Add more as needed
    if src_lang not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {src_lang}. Must be one of {supported_languages}")
    if tgt_lang not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {tgt_lang}. Must be one of {supported_languages}")
    
    logger.info("Processing visual query request", extra={
        "endpoint": "/v1/visual_query",
        "query_length": len(query),
        "file_name": file.filename,
        "client_ip": request.client.host,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang
    })
    
    external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/indic_visual_query/?src_lang={src_lang}&tgt_lang={tgt_lang}"
    
    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        data = {"query": query}
        
        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        response_data = response.json()
        answer = response_data.get("answer", "")
        
        if not answer:
            logger.warning(f"Empty answer received from external API: {response_data}")
            raise HTTPException(status_code=500, detail="No answer provided by visual query service")
        
        logger.info(f"Visual query successful: {answer}")
        return VisualQueryResponse(answer=answer)
    
    except requests.Timeout:
        logger.error("Visual query request timed out")
        raise HTTPException(status_code=504, detail="Visual query service timeout")
    except requests.RequestException as e:
        logger.error(f"Error during visual query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Visual query failed: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from visual query service")

from enum import Enum

class SupportedLanguage(str, Enum):
    kannada = "kannada"
    hindi = "hindi"
    tamil = "tamil"

@app.post("/v1/speech_to_speech",
          summary="Speech-to-Speech Conversion",
          description="Convert input speech to processed speech in the specified language by calling an external speech-to-speech API.",
          tags=["Audio"],
          responses={
              200: {"description": "Audio stream", "content": {"audio/mp3": {"example": "Binary audio data"}}},
              400: {"description": "Invalid input or language"},
              504: {"description": "External API timeout"},
              500: {"description": "External API error"}
          })
async def speech_to_speech(
    request: Request,
    file: UploadFile = File(..., description="Audio file to process"),
    language: str = Query(..., description="Language of the audio (kannada, hindi, tamil)")
) -> StreamingResponse:
    # Validate language
    allowed_languages = [lang.value for lang in SupportedLanguage]
    if language not in allowed_languages:
        raise HTTPException(status_code=400, detail=f"Language must be one of {allowed_languages}")
    
    logger.info("Processing speech-to-speech request", extra={
        "endpoint": "/v1/speech_to_speech",
        "audio_filename": file.filename,
        "language": language,
        "client_ip": request.client.host
    })

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/speech_to_speech?language={language}"

        response = requests.post(
            external_url,
            files=files,
            headers={"accept": "application/json"},
            stream=True,
            timeout=60
        )
        response.raise_for_status()

        headers = {
            "Content-Disposition": f"inline; filename=\"speech.mp3\"",
            "Cache-Control": "no-cache",
            "Content-Type": "audio/mp3"
        }

        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type="audio/mp3",
            headers=headers
        )

    except requests.Timeout:
        logger.error("External speech-to-speech API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External speech-to-speech API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    

'''
Upgrading system to use Vllm server
'''

class PDFTextExtractionResponse(BaseModel):
    page_content: str = Field(..., description="Extracted text from the specified PDF page")

    class Config:
        schema_extra = {
            "example": {
                "page_content": "Google Interview Preparation Guide\nCustomer Engineer Specialist\n\nOur hiring process\n..."
            }
        }

@app.post("/v1/extract-text", 
          response_model=PDFTextExtractionResponse,
          summary="Extract Text from PDF",
          description="Extract text from a specified page of a PDF file by calling an external API.",
          tags=["PDF"],
          responses={
              200: {"description": "Extracted text", "model": PDFTextExtractionResponse},
              400: {"description": "Invalid PDF or page number"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def extract_text(
    request: Request,
    file: UploadFile = File(..., description="PDF file to extract text from"),
    page_number: int = Query(1, description="Page number to extract text from (1-based indexing)")
):
    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")
    
    logger.info("Processing PDF text extraction request", extra={
        "endpoint": "/v1/extract-text",
        "file_name": file.filename,
        "page_number": page_number,
        "client_ip": request.client.host
    })
    
    start_time = time()
    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/extract-text/?page_number={page_number}"
        response = requests.post(
            external_url,
            files=files,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        response_data = response.json()
        extracted_text = response_data.get("page_content", "")
        if not extracted_text:
            logger.warning("No page_content found in external API response")
            extracted_text = ""
        
        logger.info(f"PDF text extraction completed in {time() - start_time:.2f} seconds")
        return PDFTextExtractionResponse(page_content=extracted_text.strip())
    
    except requests.Timeout:
        logger.error("External PDF extraction API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External PDF extraction API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")


class DocumentProcessPage(BaseModel):
    processed_page: int = Field(..., description="Page number of the extracted text")
    page_content: str = Field(..., description="Extracted text from the page")
    translated_content: Optional[str] = Field(None, description="Translated text of the page, if applicable")

    class Config:
        schema_extra = {
            "example": {
                "processed_page": 1,
                "page_content": "Okay, here's a plain text representation of the document...",
                "translated_content": "ಸರಿ, ಇಲ್ಲಿ ಡಾಕ್ಯುಮೆಂಟ್ನ ಸರಳ ಪಠ್ಯ ಪ್ರಾತಿನಿಧ್ಯವಿದೆ..."
            }
        }

class DocumentProcessResponse(BaseModel):
    pages: List[DocumentProcessPage] = Field(..., description="List of pages with extracted and translated text")

    class Config:
        schema_extra = {
            "example": {
                "pages": [
                    {
                        "processed_page": 1,
                        "page_content": "Okay, here's a plain text representation of the document...\n\n**Electronic Reservation Slip (ERS) - Normal User**\n...",
                        "translated_content": "ಸರಿ, ಇಲ್ಲಿ ಡಾಕ್ಯುಮೆಂಟ್ನ ಸರಳ ಪಠ್ಯ ಪ್ರಾತಿನಿಧ್ಯವಿದೆ...\n\n**ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಮೀಸಲಾತಿ ಸ್ಲಿಪ್ (ಇಆರ್ಎಸ್) - ಸಾಮಾನ್ಯ ಬಳಕೆದಾರ**\n..."
                    }
                ]
            }
        }

@app.post("/v1/indic-extract-text/", response_model=DocumentProcessResponse, tags=["PDF"])
async def extract_and_translate(
    file: UploadFile = File(...),
    page_number: int = 1,
    src_lang: str = "eng_Latn",
    tgt_lang: str = "kan_Knda"
):
    """
    FastAPI endpoint to call the indic-extract-text API, extract text from a PDF,
    and return the page content and translated content in the specified format.
    """
    try:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Prepare the API URL and headers

        url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/indic-extract-text/"
        
        headers = {
            "accept": "application/json"
        }

        # Prepare form data
        files = {
            "file": (file.filename, await file.read(), "application/pdf")
        }
        data = {
            "page_number": str(page_number),
            "src_lang": src_lang,
            "tgt_lang": tgt_lang
        }

        # Make the POST request to the external API
        response = requests.post(url, headers=headers, files=files, data=data)

        # Check for successful response
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"External API error: {response.text}"
            )

        # Parse the API response
        api_response = response.json()

        # Assuming the external API returns 'page_content' and 'translated_content'
        # Adjust these keys based on the actual API response structure
        page_content = api_response.get("page_content", "")
        translated_content = api_response.get("translated_content", "")

        # Create a DocumentProcessPage instance
        page = DocumentProcessPage(
            processed_page=page_number,
            page_content=page_content,
            translated_content=translated_content
        )

        # Wrap the page in DocumentProcessResponse
        result = DocumentProcessResponse(pages=[page])

        return result

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error calling external API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Close the uploaded file
        await file.close()


class SummarizePDFResponse(BaseModel):
    original_text: str = Field(..., description="Extracted text from the specified page")
    summary: str = Field(..., description="Summary of the specified page")
    processed_page: int = Field(..., description="Page number processed")

    class Config:
        schema_extra = {
            "example": {
                "original_text": "Okay, here's a plain text representation of the document...\n\nElectronic Reservation Slip (ERS)...",
                "summary": "This ERS details a sleeper class train booking (17307/Basava Express) from KSR Bengaluru to Kalaburagi...",
                "processed_page": 1
            }
        }

@app.post("/v1/summarize-pdf",
          response_model=SummarizePDFResponse,
          summary="Summarize a Specific Page of a PDF",
          description="Summarize the content of a specific page of a PDF file using an external API.",
          tags=["PDF"],
          responses={
              200: {"description": "Extracted text and summary of the specified page", "model": SummarizePDFResponse},
              400: {"description": "Invalid PDF or page number"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def summarize_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to summarize"),
    page_number: int = Form(..., description="Page number to summarize (1-based indexing)")
):
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")

    logger.info("Processing PDF summary request", extra={
        "endpoint": "/summarize-pdf",
        "file_name": file.filename,
        "page_number": page_number,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/summarize-pdf"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {"page_number": page_number}

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        original_text = response_data.get("original_text", "")
        summary = response_data.get("summary", "")
        processed_page = response_data.get("processed_page", page_number)

        if not original_text or not summary:
            logger.warning(f"Incomplete response from external API: original_text={'present' if original_text else 'missing'}, summary={'present' if summary else 'missing'}")
            return SummarizePDFResponse(
                original_text=original_text or "No text extracted",
                summary=summary or "No summary provided",
                processed_page=processed_page
            )

        logger.info(f"PDF summary completed in {time() - start_time:.2f} seconds, page processed: {processed_page}, summary length: {len(summary)}")
        return SummarizePDFResponse(
            original_text=original_text,
            summary=summary,
            processed_page=processed_page
        )

    except requests.Timeout:
        logger.error("External PDF summary API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External PDF summary API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")


class IndicSummarizePDFResponse(BaseModel):
    original_text: str = Field(..., description="Extracted text from the specified page")
    summary: str = Field(..., description="Summary of the specified page in the source language")
    translated_summary: str = Field(..., description="Summary translated into the target language")
    processed_page: int = Field(..., description="Page number processed")

    class Config:
        schema_extra = {
            "example": {
                "original_text": "Okay, here's a plain text representation of the document...\n\nElectronic Reservation Slip (ERS)...",
                "summary": "This ERS details a Sleeper Class train booking for passenger Anand on Train 17307 (Basava Express)...",
                "translated_summary": "ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಮೀಸಲಾತಿ ಸ್ಲಿಪ್ (ಇಆರ್ಎಸ್) ನ 4-ವಾಕ್ಯಗಳ ಸಾರಾಂಶ ಹೀಗಿದೆ...",
                "processed_page": 1
            }
        }

@app.post("/v1/indic-summarize-pdf",
          response_model=IndicSummarizePDFResponse,
          summary="Summarize and Translate a Specific Page of a PDF",
          description="Summarize the content of a specific page of a PDF file and translate the summary into the target language using an external API.",
          tags=["PDF"],
          responses={
              200: {"description": "Extracted text, summary, and translated summary of the specified page", "model": IndicSummarizePDFResponse},
              400: {"description": "Invalid PDF, page number, or language codes"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def indic_summarize_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to summarize"),
    page_number: int = Form(..., description="Page number to summarize (1-based indexing)"),
    src_lang: str = Form(..., description="Source language code (e.g., eng_Latn)"),
    tgt_lang: str = Form(..., description="Target language code (e.g., kan_Knda)")
):
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")

    # Validate language codes
    supported_languages = [
        "eng_Latn", "hin_Deva", "kan_Knda", "tam_Taml", "mal_Mlym", "tel_Telu",
        "deu_Latn", "fra_Latn", "nld_Latn", "spa_Latn", "ita_Latn", "por_Latn",
        "rus_Cyrl", "pol_Latn"
    ]
    if src_lang not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {src_lang}. Must be one of {supported_languages}")
    if tgt_lang not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {tgt_lang}. Must be one of {supported_languages}")

    logger.info("Processing Indic PDF summary request", extra={
        "endpoint": "/indic-summarize-pdf",
        "file_name": file.filename,
        "page_number": page_number,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/indic-summarize-pdf"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {
            "page_number": page_number,
            "src_lang": src_lang,
            "tgt_lang": tgt_lang
        }

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        original_text = response_data.get("original_text", "")
        summary = response_data.get("summary", "")
        translated_summary = response_data.get("translated_summary", "")
        processed_page = response_data.get("processed_page", page_number)

        if not original_text or not summary or not translated_summary:
            logger.warning(f"Incomplete response from external API: original_text={'present' if original_text else 'missing'}, summary={'present' if summary else 'missing'}, translated_summary={'present' if translated_summary else 'missing'}")
            return IndicSummarizePDFResponse(
                original_text=original_text or "No text extracted",
                summary=summary or "No summary provided",
                translated_summary=translated_summary or "No translated summary provided",
                processed_page=processed_page
            )

        logger.info(f"Indic PDF summary completed in {time() - start_time:.2f} seconds, page processed: {processed_page}, summary length: {len(summary)}, translated summary length: {len(translated_summary)}")
        return IndicSummarizePDFResponse(
            original_text=original_text,
            summary=summary,
            translated_summary=translated_summary,
            processed_page=processed_page
        )

    except requests.Timeout:
        logger.error("External Indic PDF summary API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External Indic PDF summary API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")


class CustomPromptPDFResponse(BaseModel):
    original_text: str = Field(..., description="Extracted text from the specified page")
    response: str = Field(..., description="Response based on the custom prompt")
    processed_page: int = Field(..., description="Page number processed")

    class Config:
        schema_extra = {
            "example": {
                "original_text": "Okay, here's a plain text representation of the document...\n\n**Clevertronic**\nBestellnummer: 801772347...",
                "response": "Okay, here’s a list of the key points from the document:\n* Company Information: Clevertronic GmbH...",
                "processed_page": 1
            }
        }


@app.post("/v1/custom-prompt-pdf",
             response_model=CustomPromptPDFResponse,
             summary="Process a PDF with a Custom Prompt",
             description="Extract text from a specific page of a PDF and process it with a custom prompt using an external API.",
             tags=["PDF"],
             responses={
                 200: {"description": "Extracted text and custom prompt response for the specified page", "model": CustomPromptPDFResponse},
                 400: {"description": "Invalid PDF, page number, or prompt"},
                 500: {"description": "External API error"},
                 504: {"description": "External API timeout"}
             })
async def custom_prompt_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to process"),
    page_number: int = Form(..., description="Page number to process (1-based indexing)"),
    prompt: str = Form(..., description="Custom prompt to process the page content")
):
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")

    # Validate prompt
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    logger.info("Processing custom prompt PDF request", extra={
        "endpoint": "/custom-prompt-pdf",
        "file_name": file.filename,
        "page_number": page_number,
        "prompt": prompt,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/custom-prompt-pdf"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {"page_number": page_number, "prompt": prompt}

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        original_text = response_data.get("original_text", "")
        custom_response = response_data.get("response", "")
        processed_page = response_data.get("processed_page", page_number)

        if not original_text or not custom_response:
            logger.warning(f"Incomplete response from external API: original_text={'present' if original_text else 'missing'}, response={'present' if custom_response else 'missing'}")
            return CustomPromptPDFResponse(
                original_text=original_text or "No text extracted",
                response=custom_response or "No response provided",
                processed_page=processed_page
            )

        logger.info(f"Custom prompt PDF processing completed in {time() - start_time:.2f} seconds, page processed: {processed_page}, response length: {len(custom_response)}")
        return CustomPromptPDFResponse(
            original_text=original_text,
            response=custom_response,
            processed_page=processed_page
        )

    except requests.Timeout:
        logger.error("External custom prompt PDF API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External custom prompt PDF API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")


class IndicCustomPromptPDFResponse(BaseModel):
    original_text: str = Field(..., description="Extracted text from the specified page")
    response: str = Field(..., description="Response based on the custom prompt")
    translated_response: str = Field(..., description="Translated response in the target language")
    processed_page: int = Field(..., description="Page number processed")

    class Config:
        schema_extra = {
            "example": {
                "original_text": "Okay, here's a plain text representation of the document...\n\n**Clevertronic. Voll. Venture GmbH**...",
                "response": "Okay, here’s a list of key points from the document:\n* Company Information: Clevertronic. Voll. Venture GmbH...",
                "translated_response": "ಸರಿ, ಡಾಕ್ಯುಮೆಂಟ್ನ ಪ್ರಮುಖ ಅಂಶಗಳ ಪಟ್ಟಿ ಹೀಗಿದೆ...\n* ಕಂಪನಿ ಮಾಹಿತಿ: ಕ್ಲೆವರ್ಟ್ರಾನಿಕ್. ಮತಪತ್ರ. ವೆಂಚರ್ ಜಿಎಂಬಿಎಚ್...",
                "processed_page": 1
            }
        }


@app.post("/v1/indic-custom-prompt-pdf",
             response_model=IndicCustomPromptPDFResponse,
             summary="Process a PDF with a Custom Prompt and Translation",
             description="Extract text from a specific page of a PDF, process it with a custom prompt, and translate the response into a target language using an external API.",
             tags=["PDF"],
             responses={
                 200: {"description": "Extracted text, custom prompt response, and translated response for the specified page", "model": IndicCustomPromptPDFResponse},
                 400: {"description": "Invalid PDF, page number, prompt, or language codes"},
                 500: {"description": "External API error"},
                 504: {"description": "External API timeout"}
             })
async def indic_custom_prompt_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to process"),
    page_number: int = Form(..., description="Page number to process (1-based indexing)"),
    prompt: str = Form(..., description="Custom prompt to process the page content"),
    source_language: str = Form(..., description="Source language code (e.g., eng_Latn)"),
    target_language: str = Form(..., description="Target language code (e.g., kan_Knda)")
):
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")

    # Validate prompt
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Validate language codes (basic check for non-empty)
    if not source_language.strip() or not target_language.strip():
        raise HTTPException(status_code=400, detail="Source and target language codes cannot be empty")

    logger.info("Processing indic custom prompt PDF request", extra={
        "endpoint": "/indic-custom-prompt-pdf",
        "file_name": file.filename,
        "page_number": page_number,
        "prompt": prompt,
        "source_language": source_language,
        "target_language": target_language,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/indic-custom-prompt-pdf"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {
            "page_number": page_number,
            "prompt": prompt,
            "source_language": source_language,
            "target_language": target_language
        }

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        original_text = response_data.get("original_text", "")
        custom_response = response_data.get("response", "")
        translated_response = response_data.get("translated_response", "")
        processed_page = response_data.get("processed_page", page_number)

        if not original_text or not custom_response or not translated_response:
            logger.warning(f"Incomplete response from external API: "
                          f"original_text={'present' if original_text else 'missing'}, "
                          f"response={'present' if custom_response else 'missing'}, "
                          f"translated_response={'present' if translated_response else 'missing'}")
            return IndicCustomPromptPDFResponse(
                original_text=original_text or "No text extracted",
                response=custom_response or "No response provided",
                translated_response=translated_response or "No translated response provided",
                processed_page=processed_page
            )

        logger.info(f"Indic custom prompt PDF processing completed in {time() - start_time:.2f} seconds, "
                    f"page processed: {processed_page}, response length: {len(custom_response)}, "
                    f"translated response length: {len(translated_response)}")
        return IndicCustomPromptPDFResponse(
            original_text=original_text,
            response=custom_response,
            translated_response=translated_response,
            processed_page=processed_page
        )

    except requests.Timeout:
        logger.error("External indic custom prompt PDF API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External indic custom prompt PDF API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")

@app.post("/v1/indic-custom-prompt-kannada-pdf",
          summary="Generate Kannada PDF with Custom Prompt",
          description="Process a PDF with a custom prompt and generate a new PDF in Kannada using an external API.",
          tags=["PDF"],
          responses={
              200: {"description": "Generated Kannada PDF file", "content": {"application/pdf": {"example": "Binary PDF data"}}},
              400: {"description": "Invalid PDF, page number, prompt, or language"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def indic_custom_prompt_kannada_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to process"),
    page_number: int = Form(..., description="Page number to process (1-based indexing)"),
    prompt: str = Form(..., description="Custom prompt to process the page content (e.g., 'list key points')"),
    src_lang: str = Form(..., description="Source language code (e.g., eng_Latn)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")

    # Validate prompt
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Validate source language
    supported_languages = ["eng_Latn", "hin_Deva", "kan_Knda", "tam_Taml", "mal_Mlym", "tel_Telu"]
    if src_lang not in supported_languages:
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {src_lang}. Must be one of {supported_languages}")

    logger.info("Processing Kannada PDF generation request", extra={
        "endpoint": "/v1/indic-custom-prompt-kannada-pdf",
        "file_name": file.filename,
        "page_number": page_number,
        "prompt": prompt,
        "src_lang": src_lang,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/indic-custom-prompt-kannada-pdf/"
    start_time = time()

    # Create a temporary file to store the generated PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file_path = temp_file.name

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {
            "page_number": page_number,
            "prompt": prompt,
            "src_lang": src_lang
        }

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            stream=True,
            timeout=60
        )
        response.raise_for_status()

        # Write the PDF content to the temporary file
        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Prepare headers for the response
        headers = {
            "Content-Disposition": "attachment; filename=\"generated_kannada.pdf\"",
            "Cache-Control": "no-cache",
        }

        # Schedule file cleanup as a background task
        def cleanup_file(file_path: str):
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Deleted temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temporary file {file_path}: {str(e)}")

        background_tasks.add_task(cleanup_file, temp_file_path)

        logger.info(f"Kannada PDF generation completed in {time() - start_time:.2f} seconds")
        return FileResponse(
            path=temp_file_path,
            filename="generated_kannada.pdf",
            media_type="application/pdf",
            headers=headers
        )

    except requests.Timeout:
        logger.error("External Kannada PDF API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External Kannada PDF API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    finally:
        # Close the temporary file to ensure it's fully written
        temp_file.close()


if __name__ == "__main__":
    # Ensure EXTERNAL_API_BASE_URL is set
    external_api_base_url = os.getenv("EXTERNAL_API_BASE_URL")
    if not external_api_base_url:
        raise ValueError("Environment variable EXTERNAL_API_BASE_URL must be set")
    
    external_pdf_api_base_url = os.getenv("EXTERNAL_PDF_API_BASE_URL")
    if not external_pdf_api_base_url:
        raise ValueError("Environment variable EXTERNAL_PDF_API_BASE_URL must be set")
    
    parser = argparse.ArgumentParser(description="Run the FastAPI server.")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on.")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)