from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    """
    A simple health check endpoint to confirm the service is running.
    """
    return {"status": "ok", "service": "browser"}
