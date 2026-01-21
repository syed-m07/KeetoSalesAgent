from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .agent import get_agent_response # Import the agent function

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
    print("Client connected to chat endpoint")
    try:
        while True:
            # Receive message from the client
            user_input = await websocket.receive_text()
            
            # Get response from the agent
            agent_response = get_agent_response(user_input)
            
            # Send response back to the client
            await websocket.send_text(agent_response)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
        # Optionally, send an error message to the client
        await websocket.close(code=1011, reason=f"An internal error occurred.")

