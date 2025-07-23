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

# Assuming these are in your project structure
from config.tts_config import SPEED, ResponseFormat, config as tts_config
from config.logging_config import logger

# FastAPI app setup with enhanced docs
app = FastAPI(
    title="dwani API",
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

@app.post("/v1/chat", 
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
        external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/chat"
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

    external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/translate"

    payload = {
        "sentences": request.sentences,
        "src_lang": request.src_lang,
        "tgt_lang": request.tgt_lang
    }

    try:
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
    page_number: int = Query(1, description="Page number to extract text from (1-based indexing)"),
    language: str = Query(..., description="Language of the PDF content (kannada, hindi, tamil)")
):
    # Validate page number
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be at least 1")
    
    logger.info("Processing PDF text extraction request", extra={
        "endpoint": "/v1/extract-text",
        "file_name": file.filename,
        "page_number": page_number,
        "language": language,
        "client_ip": request.client.host
    })
    
    start_time = time()
    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/extract-text/?page_number={page_number}&language={language}"
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

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Form, Query
from pydantic import BaseModel, Field

class VisualQueryResponse(BaseModel):
    answer: str

    class Config:
        schema_extra = {"example": {"answer": "The image shows a screenshot of a webpage."}}

@app.post("/v1/visual_query", 
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
    
    external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/visual_query/?src_lang={src_lang}&tgt_lang={tgt_lang}"
    
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


from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Form, Query
from pydantic import BaseModel, Field

class DocumentQueryResponse(BaseModel):
    answer: str

    class Config:
        schema_extra = {"example": {"answer": "The image shows a screenshot of a webpage."}}

@app.post("/v1/document_query", 
          response_model=DocumentQueryResponse,
          summary="Docuemnt Query with Image",
          description="Process a Document query with a text query, image, and language codes. Provide the query and image as form data, and source/target languages as query parameters.",
          tags=["Chat"],
          responses={
              200: {"description": "Query response", "model": DocumentQueryResponse},
              400: {"description": "Invalid query or language codes"},
              422: {"description": "Validation error in request body"},
              504: {"description": "Visual query service timeout"}
          })
async def document_query(
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
    
    logger.info("Processing document query request", extra={
        "endpoint": "/v1/document_query",
        "query_length": len(query),
        "file_name": file.filename,
        "client_ip": request.client.host,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang
    })
    
    external_url = f"{os.getenv('EXTERNAL_API_BASE_URL')}/v1/document_query/?src_lang={src_lang}&tgt_lang={tgt_lang}"
    
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
        
        logger.info(f"document_query query successful: {answer}")
        return VisualQueryResponse(answer=answer)
    
    except requests.Timeout:
        logger.error("document_query query request timed out")
        raise HTTPException(status_code=504, detail="document_query query service timeout")
    except requests.RequestException as e:
        logger.error(f"Error during document_query query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"document_query query failed: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from document_query query service")


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
    
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Form, Query
from pydantic import BaseModel, Field
from typing import List

# Request/Response Models for Document Process Endpoint
class DocumentProcessPage(BaseModel):
    page_number: int = Field(..., description="Page number of the extracted text")
    page_text: str = Field(..., description="Extracted text from the page")

    class Config:
        schema_extra = {
            "example": {
                "page_number": 1,
                "page_text": "Okay, here's the plain text representation of the document..."
            }
        }

class DocumentProcessResponse(BaseModel):
    pages: List[DocumentProcessPage] = Field(..., description="List of pages with extracted text")

    class Config:
        schema_extra = {
            "example": {
                "pages": [
                    {
                        "page_number": 1,
                        "page_text": "Okay, here's the plain text representation of the document...\n\n**DB Online-Ticket**\n..."
                    }
                ]
            }
        }

@app.post("/v1/document_process",
          response_model=DocumentProcessResponse,
          summary="Extract Text from All Pages of a PDF",
          description="Extract plain text from all pages of a PDF file using an external API, based on the provided prompt and language codes.",
          tags=["PDF"],
          responses={
              200: {"description": "Extracted text from all pages", "model": DocumentProcessResponse},
              400: {"description": "Invalid PDF, prompt, or language codes"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def document_process(
    request: Request,
    file: UploadFile = File(..., description="PDF file to extract text from"),
    src_lang: str = Form(..., description="Source language code (e.g., eng_Latn)"),
    tgt_lang: str = Form(..., description="Target language code (e.g., eng_Latn)"),
    prompt: str = Form(..., description="Prompt for text extraction (e.g., 'Return the plain text representation of this document as if you were reading it naturally')")
):
    # Validate inputs
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt cannot exceed 1000 characters")

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

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    logger.info("Processing document process request", extra={
        "endpoint": "/v1/document_process",
        "file_name": file.filename,
        "prompt_length": len(prompt),
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
        "client_ip": request.client.host
    })


    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/extract-text-all-pages-batch/"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {"src_lang": src_lang, "tgt_lang": tgt_lang, "prompt": prompt}

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        pages = response_data.get("pages", [])

        if not pages:
            logger.warning("No pages found in external API response")
            return DocumentProcessResponse(pages=[])

        # Validate and format response
        formatted_pages = [
            DocumentProcessPage(
                page_number=page.get("page_number"),
                page_text=page.get("page_text", "")
            ) for page in pages
        ]

        logger.info(f"Document process completed in {time() - start_time:.2f} seconds, pages extracted: {len(formatted_pages)}")
        return DocumentProcessResponse(pages=formatted_pages)

    except requests.Timeout:
        logger.error("External document process API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External document process API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")
    
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Form, Query
from pydantic import BaseModel, Field
from typing import List

# Request/Response Models for Document Summary Endpoint
class DocumentSummaryPage(BaseModel):
    page_number: int = Field(..., description="Page number of the extracted text")
    page_text: str = Field(..., description="Extracted text from the page")

    class Config:
        schema_extra = {
            "example": {
                "page_number": 1,
                "page_text": "Okay, here's the plain text representation of the document...\n\nDB Online-Ticket\n..."
            }
        }

class DocumentSummaryResponse(BaseModel):
    pages: List[DocumentSummaryPage] = Field(..., description="List of pages with extracted text")
    summary: str = Field(..., description="Summary of the document based on the provided prompt")

    class Config:
        schema_extra = {
            "example": {
                "pages": [
                    {
                        "page_number": 1,
                        "page_text": "Okay, here's the plain text representation of the document...\n\nDB Online-Ticket\n..."
                    }
                ],
                "summary": "This document is a digital train ticket for ICE 1126, traveling from Köln Hbf to Berlin Hbf on May second, two thousand twenty-four..."
            }
        }

@app.post("/v1/document_summary",
          response_model=DocumentSummaryResponse,
          summary="Summarize All Pages of a PDF",
          description="Summarize the content of all pages of a PDF file using an external API, based on the provided prompt and language codes.",
          tags=["PDF"],
          responses={
              200: {"description": "Extracted text and summary of all pages", "model": DocumentSummaryResponse},
              400: {"description": "Invalid PDF, prompt, or language codes"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def document_summary(
    request: Request,
    file: UploadFile = File(..., description="PDF file to summarize"),
    src_lang: str = Form(..., description="Source language code (e.g., eng_Latn)"),
    tgt_lang: str = Form(..., description="Target language code (e.g., eng_Latn)"),
    prompt: str = Form(..., description="Prompt for summarization (e.g., 'Summarize the document in 3 sentences.')")
):
    # Validate inputs
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt cannot exceed 1000 characters")

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

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    logger.info("Processing document summary request", extra={
        "endpoint": "/v1/document_summary",
        "file_name": file.filename,
        "prompt_length": len(prompt),
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/summarize-all-pages/"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {"src_lang": src_lang, "tgt_lang": tgt_lang, "prompt": prompt}

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        pages = response_data.get("pages", [])
        summary = response_data.get("summary", "")

        if not pages or not summary:
            logger.warning(f"Incomplete response from external API: pages={len(pages)}, summary={'present' if summary else 'missing'}")
            return DocumentSummaryResponse(pages=[], summary=summary or "No summary provided by the external API")

        # Validate and format response
        formatted_pages = [
            DocumentSummaryPage(
                page_number=page.get("page_number"),
                page_text=page.get("page_text", "")
            ) for page in pages
        ]

        logger.info(f"Document summary completed in {time() - start_time:.2f} seconds, pages extracted: {len(formatted_pages)}, summary length: {len(summary)}")
        return DocumentSummaryResponse(pages=formatted_pages, summary=summary)

    except requests.Timeout:
        logger.error("External document summary API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External document summary API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")
    

@app.post("/v1/document_summary_v0",
          response_model=DocumentSummaryResponse,
          summary="Summarize All Pages of a PDF",
          description="Summarize the content of all pages of a PDF file using an external API, based on the provided prompt and language codes.",
          tags=["PDF"],
          responses={
              200: {"description": "Extracted text and summary of all pages", "model": DocumentSummaryResponse},
              400: {"description": "Invalid PDF, prompt, or language codes"},
              500: {"description": "External API error"},
              504: {"description": "External API timeout"}
          })
async def document_summary_v0(
    request: Request,
    file: UploadFile = File(..., description="PDF file to summarize"),
    src_lang: str = Form(..., description="Source language code (e.g., eng_Latn)"),
    tgt_lang: str = Form(..., description="Target language code (e.g., eng_Latn)"),
    prompt: str = Form(..., description="Prompt for summarization (e.g., 'Summarize the document in 3 sentences.')")
):
    # Validate inputs
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt cannot exceed 1000 characters")

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

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    logger.info("Processing document summary request", extra={
        "endpoint": "/v1/document_summary_v0",
        "file_name": file.filename,
        "prompt_length": len(prompt),
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
        "client_ip": request.client.host
    })

    external_url = f"{os.getenv('EXTERNAL_PDF_API_BASE_URL')}/summarize-all-pages_v0/"
    start_time = time()

    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, "application/pdf")}
        data = {"src_lang": src_lang, "tgt_lang": tgt_lang, "prompt": prompt}

        response = requests.post(
            external_url,
            files=files,
            data=data,
            headers={"accept": "application/json"},
            timeout=60
        )
        response.raise_for_status()

        response_data = response.json()
        pages = response_data.get("pages", [])
        summary = response_data.get("summary", "")

        if not pages or not summary:
            logger.warning(f"Incomplete response from external API: pages={len(pages)}, summary={'present' if summary else 'missing'}")
            return DocumentSummaryResponse(pages=[], summary=summary or "No summary provided by the external API")

        # Validate and format response
        formatted_pages = [
            DocumentSummaryPage(
                page_number=page.get("page_number"),
                page_text=page.get("page_text", "")
            ) for page in pages
        ]

        logger.info(f"Document summary completed in {time() - start_time:.2f} seconds, pages extracted: {len(formatted_pages)}, summary length: {len(summary)}")
        return DocumentSummaryResponse(pages=formatted_pages, summary=summary)

    except requests.Timeout:
        logger.error("External document summary API timed out")
        raise HTTPException(status_code=504, detail="External API timeout")
    except requests.RequestException as e:
        logger.error(f"External document summary API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid JSON response from external API: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from external API")
    


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