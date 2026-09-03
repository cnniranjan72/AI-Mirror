import { describe, it, expect, vi, beforeEach } from 'vitest'

/**
 * The client is the seam between the API's field names and the shapes the
 * pages expect, and every page test mocks it away — so nothing exercised its
 * normalisation. A mutation run found that directly: replacing
 * `data.intent_understood !== false` with `!!data.intent_understood` changed
 * how an older backend's response reads and no test noticed.
 *
 * The defaults matter because they decide what an *absent* field means. Absent
 * has to mean "the backend predates this", not "the backend said no".
 */
const post = vi.fn()
const get = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: () => ({
      post,
      get,
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    }),
  },
}))

const { api } = await import('./client')

beforeEach(() => {
  vi.clearAllMocks()
})

describe('sendChatMessage', () => {
  it('sends the intent override, and omits it when there is none', async () => {
    post.mockResolvedValue({ data: { answer: 'x' } })

    await api.sendChatMessage('u1', 'why', 'conv1')
    expect(post).toHaveBeenCalledWith('/query', {
      user_id: 'u1', query: 'why', conversation_id: 'conv1', intent: null,
    })

    await api.sendChatMessage('u1', 'why', 'conv1', 'identity_question')
    expect(post).toHaveBeenLastCalledWith('/query', {
      user_id: 'u1', query: 'why', conversation_id: 'conv1',
      intent: 'identity_question',
    })
  })

  it('reads a missing intent_understood as understood', async () => {
    // An older backend sends no such field. Treating that as "could not read
    // the question" would put a warning on every answer it returns.
    post.mockResolvedValue({ data: { answer: 'x' } })
    const res = await api.sendChatMessage('u1', 'why', 'c')
    expect(res.intent_understood).toBe(true)
  })

  it('passes through an explicit false', async () => {
    post.mockResolvedValue({ data: { answer: 'x', intent_understood: false } })
    const res = await api.sendChatMessage('u1', 'why', 'c')
    expect(res.intent_understood).toBe(false)
  })

  it('distinguishes a confidence of zero from an absent one', async () => {
    // 0.0 is what the classifier reports when nothing matched, so collapsing
    // it to null with || would erase the most informative value there is.
    post.mockResolvedValue({ data: { answer: 'x', intent_confidence: 0 } })
    expect((await api.sendChatMessage('u1', 'q', 'c')).intent_confidence).toBe(0)

    post.mockResolvedValue({ data: { answer: 'x' } })
    expect((await api.sendChatMessage('u1', 'q', 'c')).intent_confidence).toBeNull()
  })

  it('defaults the list fields so callers can map over them', async () => {
    post.mockResolvedValue({ data: { answer: 'x' } })
    const res = await api.sendChatMessage('u1', 'q', 'c')
    expect(res.sources).toEqual([])
    expect(res.follow_ups).toEqual([])
    expect(res.intent_options).toEqual([])
    expect(res.intent).toBeNull()
    expect(res.intent_overridden).toBe(false)
  })

  it('carries the answer and the trace id under the names the page uses', async () => {
    post.mockResolvedValue({
      data: { answer: 'because it rained', trace_id: 't7', llm_used: true },
    })
    const res = await api.sendChatMessage('u1', 'q', 'c')
    expect(res.response).toBe('because it rained')
    expect(res.trace_id).toBe('t7')
    expect(res.llm_used).toBe(true)
  })
})
