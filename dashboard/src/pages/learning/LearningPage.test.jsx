import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'

/**
 * The Learning page rates a policy that is SHARED by every user, so the server
 * only applies a rating from a signed-in caller and answers everyone else with
 * applied=false. What's locked in here is that the page tells the truth about
 * that — a rating that changed nothing must not look like it worked.
 *
 * See backend/app/api/rl.py for why the endpoint answers 200 rather than 401.
 */
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
  getRlPolicy: vi.fn(),
  getRlHistory: vi.fn(),
  sendRlFeedback: vi.fn(),
}
let signedIn = false

vi.mock('../../api/client', () => ({
  api: new Proxy({}, { get: (_t, prop) => mockApi[prop] }),
  isAuthed: () => signedIn,
}))

const LearningPage = (await import('./LearningPage')).default

const POLICY = [
  { context_key: 'weak_depth', action_id: 'reduce_session', q_value: 0.62, n: 12 },
]

beforeEach(() => {
  vi.clearAllMocks()
  signedIn = false
  mockApi.getRlPolicy.mockResolvedValue(POLICY)
  mockApi.getRlHistory.mockResolvedValue([])
})

async function thumbsUp() {
  const button = await screen.findByTitle('This nudge helps')
  await act(async () => { fireEvent.click(button) })
}

describe('rating a policy shared by every user', () => {
  it('says up front that ratings need a sign-in', async () => {
    render(<LearningPage />)
    const notice = await screen.findByRole('status')
    expect(notice.textContent).toMatch(/shared by every user/i)
    expect(notice.textContent).toMatch(/signed in/i)
  })

  it('surfaces the reason when the server did not apply the rating', async () => {
    mockApi.sendRlFeedback.mockResolvedValue({
      success: true,
      applied: false,
      reason: 'Sign in to train the shared model.',
    })
    render(<LearningPage />)
    await thumbsUp()

    await waitFor(() => {
      expect(screen.getByRole('status').textContent).toMatch(/Sign in to train the shared model/i)
    })
  })

  it('does not refetch when nothing was applied', async () => {
    /* A refetch would redraw the same numbers and read as "it worked". */
    mockApi.sendRlFeedback.mockResolvedValue({ success: true, applied: false, reason: 'nope' })
    render(<LearningPage />)
    await screen.findByTitle('This nudge helps')
    mockApi.getRlPolicy.mockClear()

    await thumbsUp()
    await waitFor(() => expect(screen.getByRole('status').textContent).toMatch(/nope/))
    expect(mockApi.getRlPolicy).not.toHaveBeenCalled()
  })

  it('reloads the policy when a signed-in rating IS applied', async () => {
    signedIn = true
    mockApi.sendRlFeedback.mockResolvedValue({ success: true, applied: true, new_q: 0.71 })
    render(<LearningPage />)
    await screen.findByTitle('This nudge helps')
    mockApi.getRlPolicy.mockClear()

    await thumbsUp()
    await waitFor(() => expect(mockApi.getRlPolicy).toHaveBeenCalled())
  })

  it('explains a rate-limit rejection instead of failing silently', async () => {
    signedIn = true
    mockApi.sendRlFeedback.mockRejectedValue({ response: { status: 429 } })
    render(<LearningPage />)
    await thumbsUp()

    await waitFor(() => {
      expect(screen.getByRole('status').textContent).toMatch(/rate limited/i)
    })
  })

  it('does not nag a signed-in user with the sign-in notice', async () => {
    signedIn = true
    render(<LearningPage />)
    await screen.findByTitle('This nudge helps')
    expect(screen.queryByRole('status')).toBeNull()
  })
})
