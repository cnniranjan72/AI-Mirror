import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'

/**
 * The Accuracy Ledger is the page that scores the system itself, so the thing
 * worth locking in is that it does not flatter it.
 *
 * Two specific ways this page could lie, both pinned below:
 *   - drawing a thin bucket as an empty bar, which reads as 0% accuracy when
 *     the server said "no rate, not enough answers"
 *   - leading with an accuracy number the server declared unmeasurable
 *
 * Reduced motion is forced so CountUp resolves synchronously.
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
  getCalibrationReport: vi.fn(),
  getOpenClaims: vi.fn(),
  sendClaimVerdict: vi.fn(),
}

vi.mock('../../api/client', () => ({
  api: new Proxy({}, { get: (_t, prop) => mockApi[prop] }),
}))

const CalibrationPage = (await import('./CalibrationPage')).default

const THIN_BUCKET = {
  range: '0.8-1.0', claimed_confidence: 0.9, samples: 3, correct: 3,
  observed_rate: null, assessment: 'insufficient_data', needed: 7,
}
const OVERCONFIDENT_BUCKET = {
  range: '0.8-1.0', claimed_confidence: 0.9, samples: 20, correct: 10,
  observed_rate: 0.5, interval: [0.3, 0.7], gap: -0.4, assessment: 'overconfident',
}

function setup({ report = {}, open = [] } = {}) {
  mockApi.getCalibrationReport.mockResolvedValue({
    user_id: 'u',
    measurable: false,
    summary: { verdicts_total: 0, scored: 0, unsure: 0, correct: 0, min_samples_for_verdict: 20 },
    buckets: [],
    brier_score: null,
    accuracy: null,
    verdict: 'Not enough answers yet. 0 of 20 needed before this can say anything.',
    ...report,
  })
  mockApi.getOpenClaims.mockResolvedValue(open)
  mockApi.sendClaimVerdict.mockResolvedValue({ recorded: true })
}

beforeEach(() => vi.clearAllMocks())

describe('refusing to overclaim', () => {
  it('does not show an accuracy figure the server called unmeasurable', async () => {
    setup()
    render(<CalibrationPage />)

    // The badge and the verdict paragraph both say it; either is fine.
    expect((await screen.findAllByText(/Not enough answers yet/i)).length).toBeGreaterThan(0)
    // No percentage headline anywhere.
    expect(screen.queryByText(/marked correct/i)).toBeNull()
    expect(screen.queryByText(/Brier score/i)).toBeNull()
  })

  it('renders a thin bucket as "needs more", never as an empty bar', async () => {
    /* The failure that would make this page actively misleading: a bucket the
       server refused to score, drawn as 0%. */
    setup({ report: { buckets: [THIN_BUCKET] } })
    render(<CalibrationPage />)

    expect(await screen.findByText(/7 more answers needed/i)).toBeTruthy()
    // The bucket must not be drawn with any observed rate at all.
    expect(screen.queryByText(/observed/)).toBeNull()
    expect(screen.queryByText(/95% CI/)).toBeNull()
  })

  it('shows the interval next to every rate it does report', async () => {
    setup({
      report: {
        measurable: true, accuracy: 0.5, accuracy_interval: [0.3, 0.7],
        brier_score: 0.31,
        summary: { verdicts_total: 20, scored: 20, unsure: 0, correct: 10, min_samples_for_verdict: 20 },
        buckets: [OVERCONFIDENT_BUCKET],
        verdict: 'You marked 50% of the system’s claims correct. It is overconfident in the 0.8-1.0 band.',
      },
    })
    render(<CalibrationPage />)

    expect(await screen.findByText(/95% CI 30–70%/)).toBeTruthy()
  })
})

describe('naming the failure', () => {
  it('calls an overconfident band overconfident', async () => {
    setup({
      report: {
        measurable: true, accuracy: 0.5, accuracy_interval: [0.3, 0.7], brier_score: 0.31,
        summary: { verdicts_total: 20, scored: 20, unsure: 0, correct: 10, min_samples_for_verdict: 20 },
        buckets: [OVERCONFIDENT_BUCKET],
        verdict: 'It is overconfident in the 0.8-1.0 band.',
      },
    })
    render(<CalibrationPage />)

    expect(await screen.findByText('Overconfident')).toBeTruthy()
    expect(screen.getByText(/claimed 90% · observed 50%/)).toBeTruthy()
  })

  it('reports unsure answers separately from wrong ones', async () => {
    setup({
      report: {
        measurable: true, accuracy: 1, accuracy_interval: [0.8, 1], brier_score: 0.01,
        summary: { verdicts_total: 27, scored: 20, unsure: 7, correct: 20, min_samples_for_verdict: 20 },
        buckets: [], verdict: 'ok',
      },
    })
    render(<CalibrationPage />)
    expect(await screen.findByText(/7 unsure, not scored/)).toBeTruthy()
  })
})

describe('answering a claim', () => {
  const CLAIM = {
    claim_id: 'inf_1', claim_type: 'inference', label: 'Likes wildlife content',
    description: 'seen across 12 events', confidence: 0.92,
  }

  it('lists open claims with the confidence being asserted', async () => {
    setup({ open: [CLAIM] })
    render(<CalibrationPage />)

    expect(await screen.findByText('Likes wildlife content')).toBeTruthy()
    expect(screen.getByText(/it claims 92% confidence/)).toBeTruthy()
  })

  it('records a verdict and refreshes the score', async () => {
    setup({ open: [CLAIM] })
    render(<CalibrationPage />)

    const wrong = await screen.findByTitle('Wrong')
    await act(async () => { fireEvent.click(wrong) })

    await waitFor(() => {
      expect(mockApi.sendClaimVerdict).toHaveBeenCalledWith('inf_1', 'wrong', 'inference')
    })
    // The score must be recomputed, not left stale.
    expect(mockApi.getCalibrationReport).toHaveBeenCalledTimes(2)
  })

  it('offers "not sure" as a real answer', async () => {
    setup({ open: [CLAIM] })
    render(<CalibrationPage />)

    const unsure = await screen.findByTitle('Not sure')
    await act(async () => { fireEvent.click(unsure) })

    await waitFor(() => {
      expect(mockApi.sendClaimVerdict).toHaveBeenCalledWith('inf_1', 'unsure', 'inference')
    })
  })

  it('surfaces a rate-limit rejection instead of failing silently', async () => {
    setup({ open: [CLAIM] })
    mockApi.sendClaimVerdict.mockRejectedValue({ response: { status: 429 } })
    render(<CalibrationPage />)

    // Query OUTSIDE act: awaiting a findBy inside act holds the update queue,
    // so the resolved data never flushes and the button never appears.
    const right = await screen.findByTitle('Right')
    await act(async () => { fireEvent.click(right) })
    await waitFor(() => {
      expect(screen.getByRole('status').textContent).toMatch(/Too many answers/i)
    })
  })

  it('says so plainly when there is nothing left to answer', async () => {
    setup({ open: [] })
    render(<CalibrationPage />)
    expect(await screen.findByText(/Nothing waiting/i)).toBeTruthy()
  })
})
