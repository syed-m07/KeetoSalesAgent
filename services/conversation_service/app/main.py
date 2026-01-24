from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from .agent import get_agent_response
from .voice import text_to_speech, get_available_voices


app = FastAPI(
    title="Conversation Service",
    description="The 'Brain' of the AI Agent - LLM + Voice",
    version="2.0.0",
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/voices")
def list_voices():
    """List available TTS languages."""
    voices = get_available_voices()
    return {"voices": voices}


@app.post("/speak")
async def speak(request: SpeakRequest):
    """
    Convert text to speech and return audio.
    Returns MP3 audio bytes.
    """
    audio_bytes = await text_to_speech(
        request.text,
        lang=request.voice or "en"
    )
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"}
    )


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat conversations."""
    await websocket.accept()
    print("Client connected to chat endpoint")
    try:
        while True:
            user_input = await websocket.receive_text()
            agent_response = get_agent_response(user_input)
            await websocket.send_text(agent_response)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011, reason="An internal error occurred.")
