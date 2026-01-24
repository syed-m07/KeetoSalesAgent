# Project Overview

This project implements a Conversational AI Agent with a web-based frontend and two backend services orchestrated using Docker Compose. The `conversation_service` acts as the "Brain," handling natural language interactions and maintaining conversation memory. The `browser_service` is intended to be the "Hands," providing capabilities for browser automation and interaction, though it currently only includes a health check. The `frontend` provides a simple chat interface for users to interact with the AI agent.

## Project Structure

```
.
├── .gitignore
├── docker-compose.yml
├── __pycache__/
├── .git/
├── .github/
│   └── workflows/
│       └── ci.yml
├── frontend/
│   ├── .gitignore
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── node_modules/
│   ├── public/
│   │   ├── favicon.ico
│   │   ├── index.html
│   │   ├── logo192.png
│   │   ├── logo512.png
│   │   ├── manifest.json
│   │   └── robots.txt
│   └── src/
│       ├── App.css
│       ├── App.js
│       ├── App.test.js
│       ├── index.css
│       ├── index.js
│       ├── logo.svg
│       ├── reportWebVitals.js
│       ├── setupTests.js
│       └── components/
├── salesenv/
│   ├── pyvenv.cfg
│   ├── bin/
│   ├── include/
│   └── lib/
└── services/
    ├── browser_service/
    │   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       └── main.py
└── conversation_service/
        ├── Dockerfile
        ├── requirements.txt
        ├── app/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── main.py
        └── tests/
            └── test_app.py
```

## Services

### `conversation_service` (The "Brain")

This service is responsible for the core conversational logic, interacting with a Large Language Model (LLM) and managing conversation history.

*   **`Dockerfile`**:
    *   Uses `python:3.10-slim` as the base image.
    *   Sets the working directory to `/app`.
    *   Copies `requirements.txt` and installs Python dependencies using `pip`.
    *   Copies the application code from `./app` into the container.
    *   Exposes port `8000`.
    *   Defines the command to run the FastAPI application using `uvicorn`.
*   **`requirements.txt`**:
    *   `fastapi==0.111.0`: Web framework for building APIs.
    *   `uvicorn[standard]==0.29.0`: ASGI server to run FastAPI.
    *   `langchain==0.2.0`: Framework for developing applications powered by language models.
    *   `websockets==12.0`: Library for building WebSocket servers and clients.
    *   `langchain-community==0.2.0`: Community integrations for LangChain.
*   **`app/__init__.py`**: An empty file indicating that `app` is a Python package.
*   **`app/main.py`**:
    *   Initializes a FastAPI application.
    *   **`GET /health`**: A simple health check endpoint that returns `{"status": "ok"}` to verify the service is running.
    *   **`websocket /ws/chat`**: The main WebSocket endpoint. It accepts client connections, receives user text input, passes it to the `get_agent_response` function from `agent.py`, and sends the agent's response back to the client. It also handles `WebSocketDisconnect` and other exceptions.
*   **`app/agent.py`**:
    *   Imports `ChatOllama`, `ConversationChain`, and `ConversationSummaryBufferMemory` from `langchain`.
    *   **`llm = ChatOllama(model="llama3.2:3b", temperature=0.3)`**: Initializes the Large Language Model using `ChatOllama` with the `llama3.2:3b` model and a temperature of 0.3.
    *   **`memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=1000)`**: Sets up a conversational memory that summarizes older parts of the conversation to stay within a token limit, using the LLM for summarization.
    *   **`conversation_chain = ConversationChain(llm=llm, memory=memory, verbose=True)`**: Creates a LangChain `ConversationChain` that orchestrates the interaction between the LLM and the memory.
    *   **`get_agent_response(user_input: str) -> str`**: A function that takes user input, predicts a response using the `conversation_chain`, and returns the agent's reply.
*   **`tests/test_app.py`**:
    *   Uses `TestClient` from `fastapi.testclient` to test the FastAPI application.
    *   **`test_health_check()`**: Verifies that the `/health` endpoint returns a 200 status code and the expected JSON response.

### `browser_service` (The "Hands")

This service is intended to provide browser automation capabilities, likely using Playwright. Currently, it only includes a basic health check.

*   **`Dockerfile`**:
    *   Uses `mcr.microsoft.com/playwright/python:v1.44.0` as the base image, which comes with Playwright and necessary browser dependencies pre-installed.
    *   Installs build-time dependencies like `build-essential` and `libav*` for libraries like PyAV.
    *   Copies `requirements.txt` and installs Python dependencies.
    *   Copies the application code from `./app` into the container.
    *   Exposes port `8001`.
    *   Defines the command to run the FastAPI application using `uvicorn`.
*   **`requirements.txt`**:
    *   `fastapi==0.111.0`: Web framework.
    *   `uvicorn[standard]==0.29.0`: ASGI server.
    *   `playwright==1.44.0`: Library for browser automation.
    *   `aiortc==1.6.0`: WebRTC for Python (potentially for real-time media processing).
    *   `opencv-python-headless==4.9.0.80`: OpenCV library for computer vision tasks (headless version).
    *   `numpy==1.26.4`: Numerical computing library.
    *   `websockets==12.0`: Library for WebSockets.
*   **`app/__init__.py`**: An empty file indicating that `app` is a Python package.
*   **`app/main.py`**:
    *   Initializes a FastAPI application.
    *   **`GET /health`**: A simple health check endpoint that returns `{"status": "ok", "service": "browser"}`.

## Frontend

A React application that serves as the user interface for the conversational AI agent.

*   **`.gitignore`**: Specifies files and directories to be ignored by Git, common for Create React App projects.
*   **`package.json`**:
    *   Defines project metadata, scripts (`start`, `build`, `test`, `eject`), and dependencies required for the React application (e.g., `react`, `react-dom`, `react-scripts`, `@testing-library/*`, `web-vitals`).
*   **`package-lock.json`**: Records the exact versions of all dependencies and their sub-dependencies.
*   **`README.md`**: The default README generated by Create React App.
*   **`node_modules/`**: Directory containing all installed Node.js modules and dependencies.
*   **`public/`**: Contains static assets served directly by the web server.
    *   `index.html`: The main HTML file where the React application is mounted.
    *   `favicon.ico`, `logo192.png`, `logo512.png`: Application icons and logos.
    *   `manifest.json`: Web app manifest file for progressive web app features.
    *   `robots.txt`: Directives for web crawlers.
*   **`src/`**: Contains the source code for the React application.
    *   **`App.css`**: CSS file for styling the `App` component.
    *   **`App.js`**: The main React component.
        *   Manages the state for chat messages, user input, and the WebSocket connection.
        *   Establishes a WebSocket connection to `ws://localhost:8000/ws/chat` (the `conversation_service`).
        *   Handles sending user messages and displaying agent responses in a chat window.
        *   Includes basic UI elements for the chat interface.
    *   `App.test.js`: A placeholder file for unit tests related to the `App` component.
    *   `index.css`: Global CSS styles for the application.
    *   **`index.js`**: The entry point of the React application. It renders the `App` component into the `root` DOM element defined in `public/index.html`.
    *   `logo.svg`: The React logo used in the application.
    *   `reportWebVitals.js`: A utility for measuring and reporting web performance metrics.
    *   `setupTests.js`: Configuration file for the testing framework (e.g., Jest, React Testing Library).
    *   `components/`: An empty directory, likely intended for reusable React components.

## Docker-Related Information

*   **`docker-compose.yml`**:
    *   This file defines and orchestrates the multi-container Docker application.
    *   It sets up two services: `conversation_service` and `browser_service`.
    *   For each service, it specifies the `build` context (the directory containing the `Dockerfile`).
    *   It maps container ports to host ports (`8000:8000` for `conversation_service` and `8001:8001` for `browser_service`).
    *   Crucially, it mounts the local application code directories (`./services/conversation_service/app` and `./services/browser_service/app`) into their respective containers. This enables live-reloading, meaning changes made to the local code are automatically reflected in the running containers without needing to rebuild or restart them.
    *   The `command` directive overrides the `CMD` in the Dockerfiles to explicitly enable `uvicorn --reload`, ensuring the live-reloading functionality.
*   **`Dockerfile`s**: (Detailed above for each service) These files contain instructions for building the Docker images for each service, including base images, dependencies, and application code.
*   **Docker Status**: The `docker-compose.yml` is configured for a development environment, allowing developers to easily spin up both backend services, with live-reloading, and access them via `localhost:8000` and `localhost:8001`.

## Other Files

*   **`.gitignore` (root)**: Specifies files and directories that Git should ignore across the entire project.
*   **`__pycache__/` (root)**: Directory for Python bytecode cache files.
*   **`.git/`**: Contains all the necessary metadata for the Git repository.
*   **`.github/workflows/ci.yml`**: A GitHub Actions workflow file, likely used for Continuous Integration (CI) to automate building, testing, and potentially deploying the project.
*   **`salesenv/`**: A Python virtual environment, containing isolated Python dependencies for local development outside of Docker.