import { useState, useRef, useEffect } from 'react'
import { useChatHistory } from '../../hooks/useApi'
import { api, DEFAULT_USER } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { BrainIcon, ExternalLinkIcon, RefreshIcon } from '../../icons/icons'
import ExplainabilityPanel from '../../components/explain/ExplainabilityPanel'

const USER_ID = DEFAULT_USER

export default function ChatPage() {
  const { data: history, loading: histLoading, refetch } = useChatHistory(USER_ID)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [streamingMsg, setStreamingMsg] = useState('')
  const [explainTrace, setExplainTrace] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (history?.messages) {
      setMessages(history.messages.map(m => ({
        id: m.id || Math.random(),
        role: m.role || 'assistant',
        content: m.content || m.text || '',
        timestamp: m.timestamp || m.created_at,
      })))
    }
  }, [history])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMsg])

  const sendMessage = async () => {
    if (!input.trim() || sending) return
    const userMsg = { id: Date.now(), role: 'user', content: input.trim(), timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)
    setStreamingMsg('...')
    try {
      const res = await api.sendChatMessage(USER_ID, input)
      setStreamingMsg('')
      const reply = res?.response || res?.message || res?.text || JSON.stringify(res)
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant', content: typeof reply === 'string' ? reply : JSON.stringify(reply),
        timestamp: new Date().toISOString(), trace_id: res?.trace_id || res?.pipeline_id,
      }])
    } catch (err) {
      setStreamingMsg('')
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant', content: `Error: ${err.message}`,
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setSending(false)
    }
  }

  const clearChat = () => {
    setMessages([])
    refetch()
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Chat</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Conversational interface with your Cognitive Twin</p>
      </div>

      <div style={{
        background: 'var(--bg-surface)', backdropFilter: 'blur(20px)',
        border: '1px solid var(--border-strong)', borderRadius: 16,
        height: 'calc(100vh - 240px)', minHeight: 500,
        display: 'flex', flexDirection: 'column',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8' }}>
              <BrainIcon />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>Cognitive Chat</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>AI-powered behavioral insights</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={clearChat} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
              <RefreshIcon /> Clear
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          {messages.length === 0 && !sending && (
            <div style={{ textAlign: 'center', paddingTop: '15vh' }}>
              <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.2 }}>💬</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Start a conversation</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 400, margin: '0 auto' }}>
                Ask about your behavioral patterns, identity insights, or cognitive state
              </div>
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.map((msg) => (
              <div key={msg.id} style={{
                display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                animation: 'fadeIn 0.3s ease-out',
              }}>
                <div style={{
                  maxWidth: '75%', padding: '12px 16px', borderRadius: 12,
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))'
                    : 'rgba(51,65,85,0.4)',
                  border: `1px solid ${msg.role === 'user' ? 'rgba(99,102,241,0.2)' : 'var(--border-subtle)'}`,
                }}>
                  <div style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </div>
                  {msg.trace_id && (
                    <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                      <button onClick={() => setExplainTrace(msg.trace_id)} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        padding: '4px 10px', borderRadius: 4,
                        background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.25)',
                        color: '#818cf8', fontSize: 11, cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}>
                        🔍 Why did the AI say this?
                      </button>
                      <a href={`/trace/${msg.trace_id}`} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        padding: '4px 8px', borderRadius: 4,
                        background: 'rgba(148,163,184,0.1)', color: 'var(--text-muted)',
                        fontSize: 11, textDecoration: 'none',
                      }}>
                        <ExternalLinkIcon /> Trace
                      </a>
                    </div>
                  )}
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                    {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                  </div>
                </div>
              </div>
            ))}
            {sending && streamingMsg && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div style={{
                  padding: '12px 16px', borderRadius: 12,
                  background: 'rgba(51,65,85,0.4)', border: '1px solid var(--border-subtle)',
                }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <div className="skeleton" style={{ width: 6, height: 6, borderRadius: '50%', animation: 'pulse 1.4s infinite' }} />
                    <div className="skeleton" style={{ width: 6, height: 6, borderRadius: '50%', animation: 'pulse 1.4s infinite 0.2s' }} />
                    <div className="skeleton" style={{ width: 6, height: 6, borderRadius: '50%', animation: 'pulse 1.4s infinite 0.4s' }} />
                  </div>
                </div>
              </div>
            )}
          </div>
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }}}
              placeholder="Ask about your cognitive state..."
              rows={1}
              style={{
                flex: 1, padding: '10px 14px', borderRadius: 10,
                background: 'rgba(30,41,59,0.5)', border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)', fontSize: 14, outline: 'none',
                resize: 'none', fontFamily: 'var(--font-sans)', lineHeight: 1.5,
              }}
              onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || sending}
              style={{
                padding: '10px 16px', borderRadius: 10,
                background: input.trim() && !sending ? 'var(--accent-gradient)' : 'rgba(148,163,184,0.1)',
                border: 'none', color: 'white', cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 13, fontWeight: 600, opacity: input.trim() && !sending ? 1 : 0.5,
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {explainTrace && (
        <ExplainabilityPanel traceId={explainTrace} onClose={() => setExplainTrace(null)} />
      )}
    </div>
  )
}
