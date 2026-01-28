"""
Browser Service - The "Hands" of the AI Agent.
Provides browser automation capabilities via Playwright.
"""
import asyncio
import base64
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, Page, Playwright


# --- Pydantic Models for API ---

class NavigateRequest(BaseModel):
    url: str
    wait_until: str = "domcontentloaded"  # "load", "domcontentloaded", "networkidle"


class ClickRequest(BaseModel):
    selector: str
    timeout: int = 5000


class TypeRequest(BaseModel):
    selector: str
    text: str
    timeout: int = 5000


class GetTextRequest(BaseModel):
    selector: Optional[str] = None  # If None, gets full page text


class ScreenshotRequest(BaseModel):
    full_page: bool = True
    selector: Optional[str] = None  # If provided, screenshots only that element


class BrowserActionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# --- Browser Manager (Singleton) ---

class BrowserManager:
    """Manages a single browser instance with a persistent page."""
    
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize Playwright and browser."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            self._page = await self._browser.new_page()
            print("Browser initialized successfully")
    
    async def close(self):
        """Cleanup browser resources."""
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("Browser closed")
    
    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self._page
    
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """Navigate to a URL."""
        async with self._lock:
            await self.page.goto(url, wait_until=wait_until)
            return {
                "url": self.page.url,
                "title": await self.page.title(),
            }
    
    async def click(self, selector: str, timeout: int = 5000) -> dict:
        """Click an element."""
        async with self._lock:
            await self.page.click(selector, timeout=timeout)
            return {"clicked": selector}
    
    async def type_text(self, selector: str, text: str, timeout: int = 5000) -> dict:
        """Type text into an input field."""
        async with self._lock:
            await self.page.fill(selector, text, timeout=timeout)
            return {"typed": text, "selector": selector}
    
    async def get_text(self, selector: Optional[str] = None) -> dict:
        """Get text content from page or element."""
        async with self._lock:
            if selector:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.text_content()
                else:
                    text = None
            else:
                text = await self.page.text_content("body")
            return {"text": text, "selector": selector or "body"}
    
    async def screenshot(self, full_page: bool = True, selector: Optional[str] = None) -> dict:
        """Take a screenshot and return as base64."""
        async with self._lock:
            if selector:
                element = await self.page.query_selector(selector)
                if element:
                    screenshot_bytes = await element.screenshot()
                else:
                    raise ValueError(f"Element not found: {selector}")
            else:
                screenshot_bytes = await self.page.screenshot(full_page=full_page)
            
            b64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
            return {
                "screenshot_base64": b64_image,
                "format": "png",
                "full_page": full_page,
            }
    
    async def get_page_info(self) -> dict:
        """Get current page information."""
        async with self._lock:
            return {
                "url": self.page.url,
                "title": await self.page.title(),
            }
    
    async def get_frame(self) -> bytes:
        """Capture current page as JPEG bytes for streaming."""
        # Don't lock here - we want non-blocking frame capture for streaming
        try:
            return await self.page.screenshot(type="jpeg", quality=70)
        except Exception:
            # Return empty bytes on error (page may be navigating)
            return b""


# Global browser manager instance
browser_manager = BrowserManager()


# --- FastAPI Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage browser lifecycle with FastAPI."""
    await browser_manager.initialize()
    yield
    await browser_manager.close()


# --- FastAPI App ---

app = FastAPI(
    title="Browser Service",
    description="The 'Hands' of the AI Agent - Browser automation via Playwright",
    version="1.0.0",
    lifespan=lifespan,
)

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "browser"}


async def generate_mjpeg_frames() -> AsyncGenerator[bytes, None]:
    """Generate MJPEG frames for streaming."""
    while True:
        frame = await browser_manager.get_frame()
        if frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        await asyncio.sleep(0.1)  # ~10 FPS


@app.get("/stream")
async def stream_browser():
    """
    Stream the browser view as MJPEG.
    Open in browser or use in <img> tag: <img src="http://localhost:8001/stream" />
    """
    return StreamingResponse(
        generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/page-info", response_model=BrowserActionResponse)
async def get_page_info():
    """Get current page URL and title."""
    try:
        data = await browser_manager.get_page_info()
        return BrowserActionResponse(success=True, message="Page info retrieved", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/navigate", response_model=BrowserActionResponse)
async def navigate(request: NavigateRequest):
    """Navigate to a URL."""
    try:
        data = await browser_manager.navigate(request.url, request.wait_until)
        return BrowserActionResponse(success=True, message=f"Navigated to {request.url}", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/click", response_model=BrowserActionResponse)
async def click(request: ClickRequest):
    """Click an element by selector."""
    try:
        data = await browser_manager.click(request.selector, request.timeout)
        return BrowserActionResponse(success=True, message=f"Clicked {request.selector}", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/type", response_model=BrowserActionResponse)
async def type_text(request: TypeRequest):
    """Type text into an input field."""
    try:
        data = await browser_manager.type_text(request.selector, request.text, request.timeout)
        return BrowserActionResponse(success=True, message=f"Typed into {request.selector}", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-text", response_model=BrowserActionResponse)
async def get_text(request: GetTextRequest):
    """Get text content from page or element."""
    try:
        data = await browser_manager.get_text(request.selector)
        return BrowserActionResponse(success=True, message="Text retrieved", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screenshot", response_model=BrowserActionResponse)
async def screenshot(request: ScreenshotRequest):
    """Take a screenshot of the page or element."""
    try:
        data = await browser_manager.screenshot(request.full_page, request.selector)
        return BrowserActionResponse(success=True, message="Screenshot taken", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- WebSocket for Real-time Browser Control ---

@app.websocket("/ws/browser")
async def websocket_browser(websocket: WebSocket):
    """
    WebSocket endpoint for real-time browser control.
    Accepts JSON commands: {"action": "navigate|click|type|get_text|screenshot", "params": {...}}
    """
    await websocket.accept()
    print("Browser WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            params = data.get("params", {})
            
            try:
                if action == "navigate":
                    result = await browser_manager.navigate(**params)
                elif action == "click":
                    result = await browser_manager.click(**params)
                elif action == "type":
                    result = await browser_manager.type_text(**params)
                elif action == "get_text":
                    result = await browser_manager.get_text(**params)
                elif action == "screenshot":
                    result = await browser_manager.screenshot(**params)
                elif action == "page_info":
                    result = await browser_manager.get_page_info()
                else:
                    result = {"error": f"Unknown action: {action}"}
                
                await websocket.send_json({"success": True, "action": action, "data": result})
            
            except Exception as e:
                await websocket.send_json({"success": False, "action": action, "error": str(e)})
    
    except WebSocketDisconnect:
        print("Browser WebSocket client disconnected")
