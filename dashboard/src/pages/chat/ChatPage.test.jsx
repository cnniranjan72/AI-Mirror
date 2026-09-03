import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

/**
 * How a question was read decides which stores the answer came from, and the
 * classifier gets it wrong on roughly half of unrehearsed phrasing. So the
 * chat surface has two obligations that are easy to lose in a refactor:
 *
 *   - say how the question was read, and admit when it is unsure
 *   - let the user say otherwise, and re-ask *their* question that way
 *
 * The specific failure pinned below is a correction that appends: leaving the
 * answer built from the wrong stores sitting above the right one, with
 * nothing saying which was which.
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

  it('admits when the classifier was not confident', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer({ intent_confidence: 0.33 }))
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).toContain('unsure')
  })

  it('does not cry unsure on a confident reading', async () => {
    mockApi.sendChatMessage.mockResolvedValue(answer({ intent_confidence: 0.9 }))
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).not.toContain('unsure')
  })

  it('shows no confidence hedge on a reading the user supplied', async () => {
    // An override is not a guess, so "unsure" would be theatre.
    mockApi.sendChatMessage.mockResolvedValue(
      answer({ intent_confidence: 0.1, intent_overridden: true })
    )
    await ask()
    const chip = await screen.findByRole('button', { name: /read as/i })
    expect(chip.textContent).not.toContain('unsure')
    expect(chip.textContent).toContain('yours')
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
