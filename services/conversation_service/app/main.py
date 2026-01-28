from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import uuid

# Use the new LangGraph-based agent
from .graph.builder import invoke_graph
from .voice import text_to_speech, get_available_voices


app = FastAPI(
    title="Conversation Service",
    description="The 'Brain' of the AI Agent - LangGraph Multi-Agent System",
    version="3.0.0",
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.0.0", "engine": "langgraph"}


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


# Store session IDs per WebSocket connection
_sessions = {}


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat conversations using LangGraph."""
    await websocket.accept()
    
    # Generate a unique session ID for this connection
    session_id = str(uuid.uuid4())
    _sessions[id(websocket)] = session_id
    
    print(f"🧠 Client connected - Session: {session_id}")
    
    try:
        while True:
            user_input = await websocket.receive_text()
            
            # Invoke the LangGraph agent
            agent_response = invoke_graph(user_input, session_id=session_id)
            
            await websocket.send_text(agent_response)

    except WebSocketDisconnect:
        print(f"Client disconnected - Session: {session_id}")
        _sessions.pop(id(websocket), None)
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011, reason="An internal error occurred.")
        _sessions.pop(id(websocket), None)

