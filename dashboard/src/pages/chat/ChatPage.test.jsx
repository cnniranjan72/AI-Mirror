import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

/**
 * How a question was read decides which stores the answer came from, and the
 * classifier gets it wrong on roughly half of unrehearsed phrasing. So the
 * chat surface has two obligations that are easy to lose in a refactor:
 *
 *   - say how the question was read, and say when it was not read at all
 *   - let the user say otherwise, and re-ask *their* question that way
 *
 * Two specific failures are pinned below. A correction that appends leaves the
 * answer built from the wrong stores sitting above the right one with nothing
 * saying which was which. And a warning that fires on everything is not a
 * warning: the surface used to flag any reading under 0.5 confidence, which
 * was 56 of 65 real queries. What it flags now is the reading where no pattern
 * matched at all, 9% correct on the held-out set against 76% for the rest.
 */
// jsdom has no layout, so it has no scrollIntoView.
window.HTMLElement.prototype.scrollIntoView = () => {}

vi.stubGlobal('matchMedia', (query) => ({
  matches: query.includes('prefers-reduced-motion'),
  media: query,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
}))

const mockApi = {
  getChatHistory: vi.fn(),
  getCharacterState: vi.fn(),
  getLlmStatus: vi.fn(),
  sendChatMessage: vi.fn(),
  clearChatHistory: vi.fn(),
}

vi.mock('../../api/client', () => ({
  api: new Proxy({}, { get: (_t, prop) => mockApi[prop] }),
  DEFAULT_USER: 'test_user',
}))

// The creature is a WebGL canvas and has nothing to do with the reading.
vi.mock('../../components/character/CharacterCreature3D', () => ({
  default: () => null,
}))
vi.mock('../../components/explain/ExplainabilityPanel', () => ({
  default: () => null,
}))

const ChatPage = (await import('./ChatPage')).default

const OPTIONS = [
  { value: 'information', label: 'A plain fact' },
  { value: 'identity_question', label: 'Who I am' },
  { value: 'memory_question', label: 'Something I saw' },
]

function answer(overrides = {}) {
  return {
    response: 'Because it rained.',
    trace_id: 't1',
    sources: [],
    llm_used: false,
    follow_ups: [],
    intent: 'information',
    intent_confidence: 0.33,
    intent_options: OPTIONS,
    intent_overridden: false,
    intent_understood: true,
    ...overrides,
  }
}

async function ask(text = 'what do i keep coming back to') {
  render(<ChatPage />)
  const box = await screen.findByPlaceholderText(/ask about your cognitive state/i)
  fireEvent.change(box, { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }))
}

beforeEach(() => {
  vi.clearAllMocks()
  mockApi.getChatHistory.mockResolvedValue({ messages: [] })
  mockApi.getCharacterState.mockResolvedValue({})
  mockApi.getLlmStatus.mockResolvedValue({ llm_phrasing_available: true })
  mockApi.clearChatHistory.mockResolvedValue({})
})

describe('the reading an answer was given', () => {
  it('is shown, by its label rather than its enum name', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer())
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).toContain('A plain fact')
    expect(chip.textContent).not.toContain('information')
  })

  it('says plainly when nothing in the question matched', async () => {
    // Not "read as unknown", which reports a default as though it were a
    // conclusion. These readings are 9% correct on the held-out set.
    mockApi.sendChatMessage.mockResolvedValue(
      answer({ intent: 'unknown', intent_understood: false })
    )
    await ask()
    const chip = await screen.findByRole('button', { name: /couldn't tell/i })
    expect(chip.textContent).not.toContain('Read as')
    expect(chip.textContent).not.toContain('unknown')
  })

  it('leads with the correction when it could not read the question', async () => {
    // The picker is the useful thing at that point, so it starts open.
    mockApi.sendChatMessage.mockResolvedValue(
      answer({ intent: 'unknown', intent_understood: false })
    )
    await ask()
    await screen.findByText(/what were you asking/i)
    expect(screen.getByRole('button', { name: 'Who I am' })).toBeTruthy()
  })

  it('can still be dismissed when it opened itself', async () => {
    mockApi.sendChatMessage.mockResolvedValue(
      answer({ intent: 'unknown', intent_understood: false })
    )
    await ask()
    fireEvent.click(await screen.findByRole('button', { name: /couldn't tell/i }))
    expect(screen.queryByText(/what were you asking/i)).toBeNull()
  })

  it('does not warn on a low confidence number alone', async () => {
    // The old rule warned below 0.5, which fired on 56 of 65 real queries.
    // A reading that matched something is reported as a reading.
    mockApi.sendChatMessage.mockResolvedValue(
      answer({ intent_confidence: 0.3, intent_understood: true })
    )
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).toContain('A plain fact')
    expect(chip.textContent).not.toMatch(/unsure|couldn't tell/i)
  })

  it('treats a reading the user supplied as understood', async () => {
    mockApi.sendChatMessage.mockResolvedValue(
      answer({ intent_confidence: 0.1, intent_overridden: true, intent_understood: false })
    )
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).toContain('yours')
    expect(chip.textContent).not.toMatch(/couldn't tell/i)
  })

  it('assumes understood when the server says nothing about it', async () => {
    // An older backend sends no such field; that must not read as failure.
    const res = answer()
    delete res.intent_understood
    mockApi.sendChatMessage.mockResolvedValue(res)
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).not.toMatch(/couldn't tell/i)
  })

  it('is absent when the server did not report one', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer({ intent: null }))
    await ask()
    await screen.findByText('Because it rained.')
    expect(screen.queryByRole('button', { name: /read as/i })).toBeNull()
  })
})

describe('correcting the reading', () => {
  it('re-asks the original question under the chosen reading', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer())
    await ask('what do i keep coming back to')

    fireEvent.click(await screen.findByRole('button', { name: /read as/i }))
    mockApi.sendChatMessage.mockResolvedValue(
      answer({
        response: 'You keep coming back to systems programming.',
        intent: 'identity_question',
        intent_confidence: 1.0,
        intent_overridden: true,
      })
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Who I am' }))

    await waitFor(() => expect(mockApi.sendChatMessage).toHaveBeenCalledTimes(2))
    const [, query, , intent] = mockApi.sendChatMessage.mock.calls[1]
    expect(query).toBe('what do i keep coming back to')
    expect(intent).toBe('identity_question')
  })

  it('replaces the answer rather than appending a second one', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer())
    await ask()

    fireEvent.click(await screen.findByRole('button', { name: /read as/i }))
    mockApi.sendChatMessage.mockResolvedValue(
      answer({
        response: 'You keep coming back to systems programming.',
        intent: 'identity_question',
        intent_overridden: true,
      })
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Who I am' }))

    await screen.findByText('You keep coming back to systems programming.')
    // The answer assembled from the wrong stores must be gone, not stacked.
    expect(screen.queryByText('Because it rained.')).toBeNull()
    expect(screen.getAllByRole('button', { name: /read as/i })).toHaveLength(1)
  })

  it('does not offer the reading the answer already has', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer())
    await ask()
    fireEvent.click(await screen.findByRole('button', { name: /read as/i }))

    expect(screen.getByRole('button', { name: 'Who I am' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'A plain fact' })).toBeNull()
  })

  it('keeps the answer and says so when the re-ask fails', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer())
    await ask()

    fireEvent.click(await screen.findByRole('button', { name: /read as/i }))
    mockApi.sendChatMessage.mockRejectedValue(new Error('backend asleep'))
    fireEvent.click(await screen.findByRole('button', { name: 'Who I am' }))

    await screen.findByText(/backend asleep/)
    expect(screen.getByText('Because it rained.')).toBeTruthy()
  })
})
