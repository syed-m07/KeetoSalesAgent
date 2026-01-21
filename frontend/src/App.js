import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [socket, setSocket] = useState(null);
  const chatWindowRef = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    // The backend server runs on port 8000 by default
    const ws = new WebSocket('ws://localhost:8000/ws/chat');

    ws.onopen = () => {
      console.log('WebSocket connection established');
      setSocket(ws);
      setMessages([{ sender: 'agent', text: 'Hello! How can I help you today?' }]);
    };

    ws.onmessage = (event) => {
      setMessages(prevMessages => [...prevMessages, { sender: 'agent', text: event.data }]);
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
      setSocket(null);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    // Clean up the connection when the component unmounts
    return () => {
      if (ws.readyState === 1) { // <-- This is important
        ws.close();
      }
    };
  }, []);

  useEffect(() => {
    // Scroll to the bottom of the chat window when new messages arrive
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = () => {
    if (input.trim() && socket) {
      const message = { sender: 'user', text: input };
      setMessages(prevMessages => [...prevMessages, message]);
      socket.send(input);
      setInput('');
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      sendMessage();
    }
  };

  return (
    <div className="App">
      <h1>Conversational AI Agent</h1>
      <div className="chat-window" ref={chatWindowRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={!socket}
        />
        <button onClick={sendMessage} disabled={!socket}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;