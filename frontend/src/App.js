import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

const BROWSER_STREAM_URL = 'http://localhost:8001/stream';
const TTS_URL = 'http://localhost:8000/speak';
const WS_URL = 'ws://localhost:8000/ws/chat';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isBrowserActive, setIsBrowserActive] = useState(false);
  const chatWindowRef = useRef(null);
  const audioRef = useRef(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('✅ Connected to AI Agent');
      setSocket(ws);
      setIsConnected(true);
      setMessages([{
        sender: 'agent',
        text: 'Hello! I\'m your AI Sales Agent. I can browse the web and help you with research. Try asking me to "go to google.com" or "what page am I on?"'
      }]);
    };

    ws.onmessage = async (event) => {
      setIsLoading(false);
      const agentResponse = event.data;
      setMessages(prev => [...prev, { sender: 'agent', text: agentResponse }]);

      // Activate browser stream if agent navigated
      if (agentResponse.toLowerCase().includes('navigated') || agentResponse.toLowerCase().includes('go to')) {
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
  }, []);

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
        body: JSON.stringify({ text: text.substring(0, 200) }) // Limit for faster TTS
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
    } finally {
      setIsSpeaking(false);
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
            <span className="logo-icon">🤖</span>
            <h1>Keeto Demo Agent</h1>
          </div>
          <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </header>

        {/* Content Area */}
        <div className="content">
          {/* Browser View Panel */}
          <div className="panel browser-panel">
            <div className="panel-header">
              <span>🌐 Browser View</span>
            </div>
            <div className="browser-frame">
              {isBrowserActive ? (
                <img
                  src={BROWSER_STREAM_URL}
                  alt="Live Browser"
                  className="browser-stream"
                  onError={(e) => e.target.style.display = 'none'}
                />
              ) : (
                <div className="browser-placeholder">
                  <div className="placeholder-content">
                    <span className="placeholder-icon">🖥️</span>
                    <h3>Ready to Browse</h3>
                    <p>Ask me to navigate to a website to see the live view.</p>
                  </div>
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
                    {msg.sender === 'user' ? '👤' : <img src="/avatar.png" alt="Agent" />}
                  </div>
                  <div className="message-content">
                    {msg.text}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message agent">
                  <div className="message-avatar"><img src="/avatar.png" alt="Agent" /></div>
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

export default App;