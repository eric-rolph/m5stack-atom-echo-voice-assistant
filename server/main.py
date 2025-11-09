"""
Voice AI Gateway Server
Handles audio transcription, AI conversation, and text-to-speech
Supports both OpenAI and Google Gemini APIs
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
import os
import io
import logging
from openai import OpenAI
import google.generativeai as genai
from pydub import AudioSegment
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice AI Gateway")

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # "openai" or "gemini"
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "openai")  # "openai" for now

# Initialize clients
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✓ OpenAI client initialized")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✓ Gemini client initialized")

# Conversation context (simple in-memory storage)
conversation_history = []
MAX_HISTORY = 10


def convert_pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    """Convert raw PCM to WAV format for Whisper API"""
    audio = AudioSegment(
        data=pcm_data,
        sample_width=2,  # 16-bit
        frame_rate=sample_rate,
        channels=1
    )
    
    wav_buffer = io.BytesIO()
    audio.export(wav_buffer, format="wav")
    wav_buffer.seek(0)
    return wav_buffer.read()


def transcribe_audio(audio_data: bytes) -> Optional[str]:
    """Transcribe audio using OpenAI Whisper API"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI not configured")
    
    try:
        # Convert PCM to WAV
        wav_data = convert_pcm_to_wav(audio_data)
        
        # Create a file-like object
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "audio.wav"
        
        # Transcribe with Whisper
        logger.info("Transcribing audio with Whisper...")
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        
        logger.info(f"Transcription: {transcript}")
        return transcript
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


def get_ai_response_openai(user_text: str) -> str:
    """Get AI response using OpenAI ChatGPT"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI not configured")
    
    try:
        # Add user message to history
        conversation_history.append({"role": "user", "content": user_text})
        
        # Trim history if too long
        if len(conversation_history) > MAX_HISTORY * 2:
            conversation_history[:] = conversation_history[-MAX_HISTORY * 2:]
        
        # Get response
        logger.info("Getting ChatGPT response...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4" for better quality
            messages=[
                {"role": "system", "content": "You are a helpful voice assistant. Keep responses concise and conversational."},
                *conversation_history
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        ai_text = response.choices[0].message.content
        logger.info(f"AI Response: {ai_text}")
        
        # Add assistant response to history
        conversation_history.append({"role": "assistant", "content": ai_text})
        
        return ai_text
        
    except Exception as e:
        logger.error(f"ChatGPT error: {e}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


def get_ai_response_gemini(user_text: str) -> str:
    """Get AI response using Google Gemini"""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini not configured")
    
    try:
        # Use Gemini Flash for speed
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Build context from history
        context = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in conversation_history[-6:]  # Last 3 exchanges
        ])
        
        prompt = f"""You are a helpful voice assistant. Keep responses concise and conversational.

Previous conversation:
{context}

User: {user_text}
Assistant:"""
        
        logger.info("Getting Gemini response...")
        response = model.generate_content(prompt)
        ai_text = response.text
        
        logger.info(f"AI Response: {ai_text}")
        
        # Update history
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": ai_text})
        
        if len(conversation_history) > MAX_HISTORY * 2:
            conversation_history[:] = conversation_history[-MAX_HISTORY * 2:]
        
        return ai_text
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


def text_to_speech(text: str) -> bytes:
    """Convert text to speech using OpenAI TTS"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI TTS not configured")
    
    try:
        logger.info("Converting text to speech...")
        response = openai_client.audio.speech.create(
            model="tts-1",  # or "tts-1-hd" for better quality
            voice="alloy",  # alloy, echo, fable, onyx, nova, shimmer
            input=text,
            response_format="pcm",  # Raw PCM 16-bit
            speed=1.0
        )
        
        # The response is already PCM data
        pcm_data = response.content
        logger.info(f"Generated {len(pcm_data)} bytes of audio")
        
        return pcm_data
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "ai_provider": AI_PROVIDER,
        "tts_provider": TTS_PROVIDER,
        "openai_configured": bool(OPENAI_API_KEY),
        "gemini_configured": bool(GEMINI_API_KEY)
    }


@app.post("/api/voice")
async def process_voice(request: Request):
    """
    Main voice processing endpoint
    Receives PCM audio, transcribes, gets AI response, returns TTS audio
    """
    try:
        # Read raw PCM audio data
        audio_data = await request.body()
        logger.info(f"Received {len(audio_data)} bytes of audio data")
        
        if len(audio_data) < 1000:
            raise HTTPException(status_code=400, detail="Audio data too short")
        
        # Step 1: Transcribe audio to text
        user_text = transcribe_audio(audio_data)
        if not user_text or len(user_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Could not transcribe audio")
        
        # Step 2: Get AI response
        if AI_PROVIDER == "gemini":
            ai_response = get_ai_response_gemini(user_text)
        else:
            ai_response = get_ai_response_openai(user_text)
        
        # Step 3: Convert response to speech
        audio_response = text_to_speech(ai_response)
        
        # Return audio as PCM
        return Response(
            content=audio_response,
            media_type="application/octet-stream",
            headers={
                "X-Transcription": user_text[:200],  # Send back what was heard
                "X-AI-Response": ai_response[:200]   # Send back what AI said
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-history")
async def clear_history():
    """Clear conversation history"""
    conversation_history.clear()
    return {"status": "cleared"}


@app.get("/api/history")
async def get_history():
    """Get conversation history (for debugging)"""
    return {"history": conversation_history}


if __name__ == "__main__":
    import uvicorn
    
    # Check configuration
    if not OPENAI_API_KEY and not GEMINI_API_KEY:
        logger.error("⚠️  No API keys configured! Set OPENAI_API_KEY or GEMINI_API_KEY")
        exit(1)
    
    logger.info("=" * 50)
    logger.info("Voice AI Gateway Server Starting")
    logger.info(f"AI Provider: {AI_PROVIDER.upper()}")
    logger.info(f"TTS Provider: {TTS_PROVIDER.upper()}")
    logger.info("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
