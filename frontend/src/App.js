import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import Login from './Login';
import Register from './Register';
import './App.css';

const BROWSER_STREAM_URL = 'http://localhost:8001/stream';
const TTS_URL = 'http://localhost:8000/speak';
const WS_URL = 'ws://localhost:8000/ws/chat';

// Main Chat Component
function ChatApp({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isBrowserActive, setIsBrowserActive] = useState(false);
  const chatWindowRef = useRef(null);
  const audioRef = useRef(null);

  // Initialize WebSocket connection with token
  useEffect(() => {
    const token = localStorage.getItem('token');
    const wsUrl = token ? `${WS_URL}?token=${token}` : WS_URL;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ Connected to AI Agent');
      setSocket(ws);
      setIsConnected(true);

      // Personalized greeting
      const greeting = user
        ? `Hello ${user.name}! I'm Ravi, your YouTube Product Consultant. How can I help you today?`
        : 'Hello! I\'m your YouTube Product Consultant. I can demonstrate YouTube features for you.';

      setMessages([{ sender: 'agent', text: greeting }]);
    };

    ws.onmessage = async (event) => {
      setIsLoading(false);
      const agentResponse = event.data;
      setMessages(prev => [...prev, { sender: 'agent', text: agentResponse }]);

      // Activate browser stream if agent navigated
      if (agentResponse.toLowerCase().includes('navigated') || agentResponse.toLowerCase().includes('go to') || agentResponse.toLowerCase().includes('youtube')) {
        setIsBrowserActive(true);
      }

      // Auto-play TTS for agent responses
      await speakText(agentResponse);
    };

    ws.onclose = () => {
      console.log('❌ Disconnected from AI Agent');
      setSocket(null);
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    return () => {
      if (ws.readyState === 1) ws.close();
    };
  }, [user]);

  // Auto-scroll chat
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  // Text-to-Speech function
  const speakText = useCallback(async (text) => {
    if (!text || text.length > 500) return; // Skip long texts

    try {
      setIsSpeaking(true);
      const response = await fetch(TTS_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.substring(0, 500) })
      });

      if (response.ok) {
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        if (audioRef.current) {
          audioRef.current.src = audioUrl;
          audioRef.current.play().catch(e => console.log('Audio play blocked:', e));
        }
      }
    } catch (error) {
      console.error('TTS error:', error);
    }
  }, []);

  // Send message
  const sendMessage = () => {
    if (input.trim() && socket && isConnected) {
      setMessages(prev => [...prev, { sender: 'user', text: input }]);
      socket.send(input);
      setInput('');
      setIsLoading(true);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      {/* Background gradient */}
      <div className="bg-gradient"></div>

      {/* Main Layout */}
      <div className="main-container">
        {/* Header */}
        <header className="header">
          <div className="logo">
            <img src="/avatar.jpg" alt="Ravi" className="logo-icon" style={{ width: '32px', height: '32px', borderRadius: '50%', objectFit: 'cover' }} />
            <h1>YouTube Product Consultant</h1>
          </div>
          <div className="user-info">
            {user && <span className="user-name">👤 {user.name}</span>}
            <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
              <span className="status-dot"></span>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            {user && (
              <button className="logout-btn" onClick={onLogout}>
                Logout
              </button>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="content">
          {/* Browser View Panel */}
          <div className="panel browser-panel">
            <div className="panel-header">
              <span>🌐 Browser View</span>
            </div>
            <div className="browser-frame" style={{ position: 'relative' }}>
              {isBrowserActive ? (
                <img
                  src={BROWSER_STREAM_URL}
                  alt="Live Browser"
                  className="browser-stream"
                  onError={(e) => e.target.style.display = 'none'}
                />
              ) : (
                <div className="profile-placeholder">
                  <img
                    src="/avatar.jpg"
                    alt="Ravi"
                    className={`profile-avatar ${isSpeaking ? 'speaking' : ''}`}
                  />
                  <span className="profile-name">Ravi</span>
                  <span className="powered-by">Powered by Button AI</span>
                </div>
              )}
            </div>
          </div>

          {/* Chat Panel */}
          <div className="panel chat-panel">
            <div className="panel-header">
              <span>💬 Chat</span>
              {isSpeaking && <span className="speaking-indicator">🔊</span>}
            </div>

            <div className="chat-messages" ref={chatWindowRef}>
              {messages.map((msg, index) => (
                <div key={index} className={`message ${msg.sender}`}>
                  <div className="message-avatar">
                    {msg.sender === 'user' ? '👤' : <img src="/avatar.jpg" alt="Ravi" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />}
                  </div>
                  <div className="message-content">
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message agent">
                  <div className="message-avatar"><img src="/avatar.jpg" alt="Ravi" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} /></div>
                  <div className="message-content loading">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                </div>
              )}
            </div>

            <div className="chat-input-area">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={isConnected ? "Ask me anything..." : "Connecting..."}
                disabled={!isConnected || isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={!isConnected || isLoading || !input.trim()}
                className="send-btn"
              >
                {isLoading ? '...' : '→'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden audio element for TTS */}
      <audio ref={audioRef} onEnded={() => setIsSpeaking(false)} />
    </div>
  );
}

// Protected Route Wrapper
function ProtectedRoute({ user, children }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// Main App with Routing
function App() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');

    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        // Invalid stored data, clear it
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    }
    setIsLoading(false);
  }, []);

  const handleLogin = (data) => {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setUser(data.user);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <h2>Loading...</h2>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        <Route
          path="/login"
          element={
            user ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />
          }
        />
        <Route
          path="/register"
          element={
            user ? <Navigate to="/" replace /> : <Register onLogin={handleLogin} />
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute user={user}>
              <ChatApp user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;