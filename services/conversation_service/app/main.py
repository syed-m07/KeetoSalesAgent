"""
Conversation Service - The 'Brain' of the AI Agent.
LangGraph Multi-Agent System with JWT Authentication.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
from typing import Optional
import uuid

# Database and auth
from .database import engine, get_db, Base
from .models import User
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    get_current_user,
)
from .schemas import UserCreate, UserLogin, UserResponse, TokenResponse, SpeakRequest

# Use the new LangGraph-based agent
from .graph.builder import invoke_graph
from .voice import text_to_speech, get_available_voices


# Create database tables on startup
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Conversation Service",
    description="The 'Brain' of the AI Agent - LangGraph Multi-Agent System with Auth",
    version="3.1.0",
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
Instrumentator().instrument(app).expose(app)


# =============================================================================
# Health & Info Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.1.0", "engine": "langgraph", "auth": "jwt"}


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    Returns JWT token on success.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name,
        company=user_data.company,
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access token
    access_token = create_access_token(new_user.id)

    print(f"✅ New user registered: {new_user.email}")

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(new_user)
    )


@app.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create access token
    access_token = create_access_token(user.id)

    print(f"✅ User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@app.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    Requires Bearer token.
    """
    return UserResponse.model_validate(current_user)


# =============================================================================
# TTS Endpoints
# =============================================================================

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
        lang=request.lang or "en"
    )
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"}
    )


# =============================================================================
# WebSocket Chat Endpoint
# =============================================================================

# Store session IDs and user contexts per WebSocket connection
_sessions = {}


@app.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """
    WebSocket endpoint for chat conversations using LangGraph.
    
    Optionally accepts 'token' query parameter for authenticated sessions.
    Example: ws://localhost:8000/ws/chat?token=eyJhbGc...
    """
    await websocket.accept()

    # Determine thread_id based on authentication
    # For authenticated users, use a constant user-based ID for persistent memory
    # For guests, use a random UUID (memory will not persist across sessions)
    thread_id = None
    user_context = None
    
    if token:
        user_id = verify_token(token)
        if user_id:
            from .database import SessionLocal
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user_context = user.to_context_dict()
                    thread_id = f"user_{user.id}"  # Persistent thread ID
                    print(f"🔐 Authenticated user: {user.name} ({user.email}) | Thread: {thread_id}")
            finally:
                db.close()
    
    # Fallback to random session for guests
    if not thread_id:
        thread_id = str(uuid.uuid4())
        print(f"👤 Guest session - Thread: {thread_id}")

    greeting = f"Thread: {thread_id}"
    if user_context:
        greeting += f" | User: {user_context['name']}"
    print(f"🧠 Client connected - {greeting}")

    try:
        while True:
            user_input = await websocket.receive_text()

            # Invoke the LangGraph agent with user context and thread_id
            agent_response = invoke_graph(
                user_input,
                thread_id=thread_id,
                user_context=user_context,
            )

            await websocket.send_text(agent_response)

    except WebSocketDisconnect:
        print(f"Client disconnected - Thread: {thread_id}")
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011, reason="An internal error occurred.")
