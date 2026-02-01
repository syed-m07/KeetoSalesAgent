# Keeto Sales Agent 🤖

An AI-powered Sales Agent with browser automation, voice capabilities, and a premium glassmorphism UI. Built with LangChain, Playwright, and React.

## 🚀 Features

| Feature | Status | Description |
|---------|--------|-------------|
| **LLM Integration** | ✅ | **Gemini 2.0 Flash** (smart/fast) or **Llama 3.3 70B** (Groq) |
| **Guided Demo Mode** | ✅ | Interactive YouTube pilot workflow (Search -> Select -> Pause) |
| **Browser Automation** | ✅ | Navigate, type, click with Playwright |
| **Live Browser Stream** | ✅ | MJPEG streaming at ~10 FPS |
| **Text-to-Speech** | ✅ | gTTS with markdown stripping for natural voice |
| **Premium UI** | ✅ | Glassmorphism dark theme |
| **Docker Orchestration** | ✅ | Full containerized stack |

## 📁 Project Structure

```
.
├── docker-compose.yml          # Orchestrates all services
├── .env                        # Environment variables (GEMINI_API_KEY, GROQ_API_KEY)
├── frontend/                   # React frontend
│   └── src/
│       ├── App.js              # Main UI with chat + browser stream
│       └── App.css             # Glassmorphism styling
└── services/
    ├── browser_service/        # The "Hands" - Playwright automation
    │   └── app/
    │       └── main.py         # REST API + MJPEG stream
    └── conversation_service/   # The "Brain" - LLM + Voice
        └── app/
            ├── main.py         # FastAPI + WebSocket
            ├── graph/          # LangGraph Agent Logic
            │   ├── builder.py  # Graph construction
            │   ├── nodes.py    # Agent nodes (router, chat, demo)
            │   └── demo_node.py # YouTube Demo workflow logic
            ├── voice.py        # TTS module (supports markdown stripping)
            └── tools.py        # Browser tool definitions
```

## 🛠️ Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com)) OR Gemini API Key (recommended)
- Node.js 18+ (for frontend dev)

### 1. Setup Environment
```bash
# Create .env file
echo "GROQ_API_KEY=your-groq-key" > .env
echo "GEMINI_API_KEY=your-gemini-key" >> .env
```

### 2. Start Services
```bash
# Build and run all containers
docker compose up -d --build

# Check status
docker compose ps
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm start
```

### 4. Open the App
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Browser Stream**: http://localhost:8001/stream

## 🎯 Usage Examples

| Command | Action |
|---------|--------|
| "hello" | Simple greeting (no tools) |
| "show me a demo" | Starts the **Guided YouTube Demo** |
| "go to youtube.com" | Navigate browser (manual mode) |
| "type artificial intelligence" | Type in search field |
| "click search" | Click search button |

## 🏗️ Architecture

```
┌─────────────┐     WebSocket      ┌─────────────────────┐
│   Frontend  │◄──────────────────►│ conversation_service│
│  (React)    │                    │ (LangGraph/Gemini)  │
└──────┬──────┘                    └──────────┬──────────┘
       │                                      │
       │ MJPEG Stream                         │ HTTP API
       │                                      ▼
       │                           ┌─────────────────────┐
       └──────────────────────────►│   browser_service   │
                                   │    (Playwright)     │
                                   └─────────────────────┘
```

## 🔧 Configuration

### Environment Variables (docker-compose.yml)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | `groq` (free), `gemini` (smart), or `ollama` (local) |
| `GEMINI_API_KEY` | - | Google Gemini API Key |
| `GROQ_API_KEY` | - | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `OLLAMA_HOST` | `host.docker.internal:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model to use |

### Switching LLM Providers

```yaml
# In docker-compose.yml:
LLM_PROVIDER: gemini # Recommended for reasoning
# OR
LLM_PROVIDER: groq   # Fast, free 70B model
```

## 📡 API Endpoints

### Conversation Service (Port 8000)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ws/chat` | WS | Chat WebSocket |
| `/speak` | POST | Text-to-speech (returns MP3) |
| `/voices` | GET | List available TTS voices |

### Browser Service (Port 8001)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stream` | GET | MJPEG video stream |
| `/navigate` | POST | Navigate to URL |
| `/type` | POST | Type text into field |
| `/click` | POST | Click element |
| `/get-text` | POST | Get page text |
| `/page-info` | GET | Get current URL/title |

## 🧪 Testing

### Health Checks
```bash
curl http://localhost:8000/health  # {"status":"ok"}
curl http://localhost:8001/health  # {"status":"ok","service":"browser"}
```

### WebSocket Chat (CLI)
```bash
npx wscat -c ws://localhost:8000/ws/chat
> hello
< Hello! How can I help you today?
```

### Text-to-Speech
```bash
curl -X POST http://localhost:8000/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}' \
  --output test.mp3
```

## 🗺️ Roadmap

- [x] **Phase 1**: Core Infrastructure (Docker, Postgres, Ollama)
- [x] **Phase 2**: Browser Automation (Playwright, ReAct Agent)
- [x] **Phase 3**: Premium Frontend + Voice (TTS, MJPEG, Glassmorphism)
- [x] **Phase 4**: Agent Identity & Persistence (Postgres Checkpoints)
- [x] **Phase 5**: YouTube Demo Pilot (Gemini/Groq, Demo Workflow)
- [ ] **Phase 6**: Enrichment, CRM, Observability

## 📝 License

MIT

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `ruff check .`
5. Submit a pull request