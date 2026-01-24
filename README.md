# Keeto Sales Agent 🤖

An AI-powered Sales Agent with browser automation, voice capabilities, and a premium glassmorphism UI. Built with LangChain, Playwright, and React.

## 🚀 Features

| Feature | Status | Description |
|---------|--------|-------------|
| **LLM Integration** | ✅ | Groq (fast, cloud) or Ollama (local) |
| **Browser Automation** | ✅ | Navigate, type, click with Playwright |
| **Live Browser Stream** | ✅ | MJPEG streaming at ~10 FPS |
| **Text-to-Speech** | ✅ | gTTS for voice responses |
| **Premium UI** | ✅ | Glassmorphism dark theme |
| **Docker Orchestration** | ✅ | Full containerized stack |

## 📁 Project Structure

```
.
├── docker-compose.yml          # Orchestrates all services
├── .env                        # Environment variables (GROQ_API_KEY)
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
            ├── agent.py        # ReAct agent with tools
            ├── tools.py        # Browser tool definitions
            └── voice.py        # TTS module
```

## 🛠️ Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Node.js 18+ (for frontend dev)

### 1. Setup Environment
```bash
# Create .env file
echo "GROQ_API_KEY=your-api-key-here" > .env
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
| "go to youtube.com" | Navigate browser |
| "type artificial intelligence" | Type in search field |
| "click search" | Click search button |
| "what page am I on?" | Get current page info |

## 🏗️ Architecture

```
┌─────────────┐     WebSocket      ┌─────────────────────┐
│   Frontend  │◄──────────────────►│ conversation_service│
│  (React)    │                    │   (LangChain/Groq)  │
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
| `LLM_PROVIDER` | `groq` | `groq` (fast) or `ollama` (local) |
| `GROQ_API_KEY` | - | Your Groq API key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model to use |
| `OLLAMA_HOST` | `host.docker.internal:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model to use |

### Switching LLM Providers

```yaml
# In docker-compose.yml, change:
LLM_PROVIDER: groq   # Fast cloud-based (~1-2s)
# OR
LLM_PROVIDER: ollama # Local, slower on CPU
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
- [ ] **Phase 4**: Enrichment, CRM, Observability

## 📝 License

MIT

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `ruff check .`
5. Submit a pull request