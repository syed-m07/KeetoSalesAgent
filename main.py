from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/health")
async def health_check():
    """
    A simple health check endpoint that returns a success message.
    Used by monitoring tools to verify that the service is running.
    """
    return {"status": "ok"}


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    The main WebSocket endpoint for handling chat connections.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # For now, just echo the received message back
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")

