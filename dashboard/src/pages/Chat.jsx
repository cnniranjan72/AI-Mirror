import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { formatTimeWithTimezone, getCurrentTimezone } from '../utils/timezone';
import TimezoneSelector from '../components/TimezoneSelector';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [userId] = useState('user_123'); // In production, get from auth
  const [currentTimezone, setCurrentTimezone] = useState(getCurrentTimezone());
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Listen for timezone changes
    const handleTimezoneChange = () => {
      setCurrentTimezone(getCurrentTimezone());
    };
    
    window.addEventListener('timezone-changed', handleTimezoneChange);
    
    return () => {
      window.removeEventListener('timezone-changed', handleTimezoneChange);
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load chat history on component mount
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      const history = await api.getChatHistory(userId);
      if (history && history.history) {
        setMessages(history.history);
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    const messageContent = input;
    setInput('');

    try {
      const response = await api.sendChatMessage(userId, messageContent, true);
      
      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Add error message
      const errorMessage = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      // Clear local state
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear chat:', error);
    }
  };

  return (
    <div className="container">
      <div className="page-header">
        <div className="page-header-content">
          <div>
            <h1 className="page-title">AI Mirror Chat</h1>
            <p className="page-subtitle">Ask questions about your Instagram Reels behavior</p>
          </div>
          <div className="timezone-selector">
            <TimezoneSelector />
          </div>
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">9178;</div>
              <div className="empty-state-title">Start a Conversation</div>
              <div className="empty-state-description">
                Ask me about your Instagram Reels behavior, patterns, or get personalized insights
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
              >
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-time">
                    {formatTimeWithTimezone(message.timestamp, currentTimezone)}
                  </div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message assistant-message">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className="chat-input">
          <div className="input-group">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your Instagram behavior..."
              disabled={loading}
              className="chat-input-field"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="send-button"
            >
              {loading ? (
                <div className="loading-spinner"></div>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 2L11 13M22 2L15 22L11 13L2 22L22 2Z" />
                </svg>
              )}
            </button>
          </div>
        </form>

        <div className="chat-actions">
          <button onClick={clearChat} className="clear-button">
            Clear Chat
          </button>
        </div>
      </div>
    </div>
  );
}

export default Chat;
