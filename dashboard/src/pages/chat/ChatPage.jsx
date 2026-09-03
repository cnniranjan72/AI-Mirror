import { useState, useRef, useEffect } from 'react'
import { useChatHistory, useCharacterState, useApi } from '../../hooks/useApi'
import { api, DEFAULT_USER } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { BrainIcon, ExternalLinkIcon, RefreshIcon } from '../../icons/icons'
import ExplainabilityPanel from '../../components/explain/ExplainabilityPanel'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

const USER_ID = DEFAULT_USER
const CONVERSATION_ID = `conv_${USER_ID}`

// The reading decides which stores an answer was drawn from, so a wrong reading
// produces a confident answer assembled from the wrong material. The classifier
// is right about 56% of the time on phrasing it was not built from, which makes
// this the difference between a system that is sometimes wrong and one that is
// wrong without saying so.
function ReadingControl({ msg, open, busy, onToggle, onPick }) {
  const label = msg.intentOptions?.find(o => o.value === msg.intent)?.label || msg.intent
  // A low classifier confidence is the signal that the reading is worth
  // checking. An override has no confidence to show: the user said what they
  // meant, so the number would be theatre.
  const unsure = !msg.intentOverridden && msg.intentConfidence != null && msg.intentConfidence < 0.5

  return (
    <div style={{ marginTop: 8 }}>
      <button
        onClick={onToggle}
        disabled={busy}
        title="How this question was read. Click to read it a different way."
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '3px 9px', borderRadius: 100, cursor: busy ? 'wait' : 'pointer',
          background: unsure ? 'rgba(251,191,36,0.10)' : 'rgba(148,163,184,0.10)',
          border: '1px solid ' + (unsure ? 'rgba(251,191,36,0.28)' : 'var(--border-subtle)'),
          color: unsure ? '#fbbf24' : 'var(--text-muted)',
          fontSize: 10.5, fontWeight: 600,
        }}
      >
        {busy ? 'Re-reading...' : 'Read as: ' + label}
        {msg.intentOverridden && !busy && <span style={{ opacity: 0.75 }}>· yours</span>}
        {unsure && !busy && <span style={{ opacity: 0.75 }}>· unsure</span>}
        <span style={{ opacity: 0.6 }}>{open ? '\u25be' : '\u25b8'}</span>
      </button>

      {msg.rereadError && (
        <div style={{ fontSize: 10.5, color: '#f87171', marginTop: 5 }}>
          Couldn't re-read that: {msg.rereadError}
        </div>
      )}

      {open && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(148,163,184,0.12)' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Read it as something else
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {msg.intentOptions.filter(o => o.value !== msg.intent).map(o => (
              <button
                key={o.value}
                onClick={() => onPick(o.value)}
                style={{
                  padding: '4px 10px', borderRadius: 100, cursor: 'pointer',
                  background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
                  color: '#a5b4fc', fontSize: 11.5,
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.18)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.08)' }}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ChatPage() {
  const { data: history, loading: histLoading, error: histError, refetch } = useChatHistory(USER_ID, CONVERSATION_ID)
  const [messages, setMessages] = useState([])
  // Whether a language model is phrasing these answers. Surfaced because the
  // difference is visible in the output and was previously unexplained.
  const { data: llmStatus } = useApi(() => api.getLlmStatus(), [])

  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [streamingMsg, setStreamingMsg] = useState('')
  const [explainTrace, setExplainTrace] = useState(null)
  // Which answer currently has its reading-picker open, by message id.
  const [correcting, setCorrecting] = useState(null)
  const [rereadingId, setRereadingId] = useState(null)
  const messagesEndRef = useRef(null)
  const { data: charState, refetch: refetchCharState } = useCharacterState(USER_ID)

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

  const sendMessage = async (overrideText) => {
    const text = (overrideText ?? input).trim()
    if (!text || sending) return
    const userMsg = { id: Date.now(), role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)
    setStreamingMsg('...')
    try {
      const res = await api.sendChatMessage(USER_ID, text, CONVERSATION_ID)
      setStreamingMsg('')
      const reply = res?.response || res?.message || res?.text || JSON.stringify(res)
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant', content: typeof reply === 'string' ? reply : JSON.stringify(reply),
        timestamp: new Date().toISOString(), trace_id: res?.trace_id || res?.pipeline_id,
        followUps: res?.follow_ups || [],
        // Kept so the answer can say how the question was read, and be re-asked
        // a different way without the user retyping it.
        askedQuery: text,
        intent: res?.intent || null,
        intentConfidence: res?.intent_confidence ?? null,
        intentOptions: res?.intent_options || [],
        intentOverridden: !!res?.intent_overridden,
      }])
    } catch (err) {
      setStreamingMsg('')
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant', content: `Error: ${err.message}`,
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setSending(false)
      refetchCharState()
    }
  }

  // Re-asks the same question with the reading the user picked, and replaces
  // the answer in place. It is a correction, not a new question - appending
  // would leave the wrong answer sitting above the right one with nothing to
  // say which was which.
  const reread = async (msg, intent) => {
    if (!msg.askedQuery || rereadingId) return
    setCorrecting(null)
    setRereadingId(msg.id)
    try {
      const res = await api.sendChatMessage(USER_ID, msg.askedQuery, CONVERSATION_ID, intent)
      const reply = res?.response || res?.message || res?.text || ''
      setMessages(prev => prev.map(m => m.id !== msg.id ? m : {
        ...m,
        content: typeof reply === 'string' ? reply : JSON.stringify(reply),
        timestamp: new Date().toISOString(),
        trace_id: res?.trace_id || m.trace_id,
        followUps: res?.follow_ups || [],
        intent: res?.intent || m.intent,
        intentConfidence: res?.intent_confidence ?? null,
        intentOptions: res?.intent_options || m.intentOptions,
        intentOverridden: !!res?.intent_overridden,
        rereadError: null,
      }))
    } catch (err) {
      setMessages(prev => prev.map(m => m.id !== msg.id ? m : {
        ...m, rereadError: err.message,
      }))
    } finally {
      setRereadingId(null)
      refetchCharState()
    }
  }

  const clearChat = async () => {
    setMessages([])
    try { await api.clearChatHistory(USER_ID, CONVERSATION_ID) } catch (_) { /* ignore */ }
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 56, height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '-8px 0' }}>
              <CharacterCreature3D
                size={56}
                confidence={charState?.identity_snapshot?.overall_confidence ?? 0.3}
                topics={charState?.identity_snapshot?.dominant_topics ?? []}
                thinking={sending}
                showLabels={false}
              />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>Cognitive Chat</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {charState?.identity_snapshot
                  ? `${Math.round((charState.identity_snapshot.overall_confidence ?? 0) * 100)}% confidence · ${charState.inference_count ?? 0} active inferences`
                  : 'AI-powered behavioral insights'}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {/* Framed as a mode, not a fault. Deterministic answers are the
                product's actual claim; the model is a phrasing layer over
                findings that are already decided. */}
            {llmStatus?.llm_phrasing_available === false && (
              <span
                title="Answers are composed directly from your cognitive data. Add a provider key in Settings for natural-language phrasing."
                style={{
                  fontSize: 10.5, fontWeight: 600, padding: '4px 9px', borderRadius: 100,
                  background: 'rgba(148,163,184,0.12)', border: '1px solid var(--border-subtle)',
                  color: 'var(--text-muted)', whiteSpace: 'nowrap',
                }}
              >
                deterministic mode
              </span>
            )}
            <button onClick={clearChat} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
              <RefreshIcon /> Clear
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          {messages.length === 0 && !sending && histError && (
            <div style={{ textAlign: 'center', paddingTop: '15vh' }}>
              <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }}>⚠️</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#f87171', marginBottom: 8 }}>Couldn't load conversation history</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 400, margin: '0 auto 16px' }}>
                {typeof histError === 'string' ? histError : 'You can still start a new message below.'}
              </div>
              <button className="btn btn-secondary" onClick={refetch}>Try again</button>
            </div>
          )}
          {messages.length === 0 && !sending && !histError && (
            <div style={{ textAlign: 'center', paddingTop: '15vh' }}>
              <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.2 }}>💬</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Start a conversation</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 400, margin: '0 auto' }}>
                Ask about your behavioral patterns, identity insights, or cognitive state
              </div>
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.map((msg, idx) => {
              const isLastAssistant = msg.role === 'assistant' && idx === messages.length - 1
              return (
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
                  {msg.intent && (
                    <ReadingControl
                      msg={msg}
                      open={correcting === msg.id}
                      busy={rereadingId === msg.id}
                      onToggle={() => setCorrecting(correcting === msg.id ? null : msg.id)}
                      onPick={intent => reread(msg, intent)}
                    />
                  )}

                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                    {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                  </div>

                  {isLastAssistant && msg.followUps?.length > 0 && !sending && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(148,163,184,0.12)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        Continue the thread
                      </div>
                      {msg.followUps.map((q, i) => (
                        <button
                          key={i}
                          onClick={() => sendMessage(q)}
                          style={{
                            textAlign: 'left', padding: '7px 12px', borderRadius: 8,
                            background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
                            color: '#a5b4fc', fontSize: 12.5, cursor: 'pointer', transition: 'all 0.15s',
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.16)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.08)' }}
                        >
                          {q} →
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              )
            })}
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
                flex: 1, padding: '13px 16px', borderRadius: 13,
                // Solid dark bg + explicit light text + dark color-scheme so the
                // typed text is always high-contrast, regardless of the OS/browser
                // light-mode form-control defaults.
                background: '#1e293b', border: '1px solid var(--border-strong, rgba(148,163,184,0.25))',
                color: '#f8fafc', caretColor: '#818cf8', colorScheme: 'dark',
                fontSize: 14, outline: 'none',
                resize: 'none', fontFamily: 'var(--font-sans)', lineHeight: 1.5,
                transition: 'border-color var(--dur-fast) var(--ease-swift), box-shadow var(--dur-fast) var(--ease-swift)',
              }}
              // Focus ring is applied imperatively because this is an inline-styled
              // element — a :focus rule in CSS would lose to the inline style.
              onFocus={e => {
                e.target.style.borderColor = 'rgba(99,102,241,0.6)'
                e.target.style.boxShadow = '0 0 0 3px rgba(99,102,241,0.15), 0 0 26px -8px rgba(99,102,241,0.8)'
              }}
              onBlur={e => {
                e.target.style.borderColor = 'var(--border-strong, rgba(148,163,184,0.25))'
                e.target.style.boxShadow = 'none'
              }}
              onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className={input.trim() && !sending ? 'btn-3d btn-aurora' : ''}
              style={{
                padding: '13px 22px', borderRadius: 13,
                background: input.trim() && !sending ? undefined : 'rgba(148,163,184,0.1)',
                border: 'none', color: 'white', cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
                display: 'flex', alignItems: 'center', gap: 8,
                fontSize: 13.5, fontWeight: 700, opacity: input.trim() && !sending ? 1 : 0.5,
              }}
            >
              {/* Spinner while the pipeline runs — a 7-stage query can take a
                  few seconds, and the button previously gave no sign it was
                  working. */}
              {sending && (
                <span style={{
                  width: 13, height: 13, borderRadius: '50%', flexShrink: 0,
                  border: '2px solid rgba(255,255,255,0.35)', borderTopColor: '#fff',
                  animation: 'spin 0.7s linear infinite',
                }} />
              )}
              {sending ? 'Thinking' : 'Send'}
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
