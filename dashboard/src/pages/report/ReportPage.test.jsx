import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

/**
 * The Report is the one artefact that leaves the product, so what's locked in
 * here is not layout but the claims it makes: the coverage arithmetic, the
 * framing that arithmetic selects, the provenance lines, and the promise that
 * no language model touched any figure.
 *
 * Reduced motion is forced on so CountUp resolves to its final value
 * synchronously — otherwise every numeric assertion races an animation.
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
  getCognitiveSummary: vi.fn(),
  getCurrentIdentity: vi.fn(),
  getBehaviorObjects: vi.fn(),
  getInferences: vi.fn(),
  getReflections: vi.fn(),
  getGuardianReport: vi.fn(),
  getMirrorReport: vi.fn(),
  getProvenanceReport: vi.fn(),
}

vi.mock('../../api/client', () => ({
  api: new Proxy({}, { get: (_t, prop) => mockApi[prop] }),
}))

const ReportPage = (await import('./ReportPage')).default

/** Counts matching what production actually held when this page was built. */
function setup({ summary = {}, guardian = {}, identity = {}, behaviors = [], inferences = [], reflections = [], mirror = null, provenance = null } = {}) {
  mockApi.getCognitiveSummary.mockResolvedValue({
    behavior_object_count: 7,
    evidence_count: 16,
    inference_count: 4,
    reflection_count: 6,
    snapshot_count: 1,
    platform_breakdown: { instagram: 63, youtube: 32 },
    ...summary,
  })
  mockApi.getCurrentIdentity.mockResolvedValue({
    identity: {
      overall_confidence: 0.48,
      identity_completeness: 0.6,
      identity_version: 4,
      dominant_topics: '["#ai", "travel"]',
      interest_graph: '{"dominant_interests": [{"topic": "#ai", "strength": 0.7}]}',
      ...identity,
    },
  })
  mockApi.getBehaviorObjects.mockResolvedValue(behaviors)
  mockApi.getInferences.mockResolvedValue(inferences)
  mockApi.getReflections.mockResolvedValue(reflections)
  // Default: no audit data at all, which is the state of a fresh account and
  // must leave the rest of the report intact.
  mockApi.getMirrorReport.mockResolvedValue(mirror ?? { claims_total: 0, summary: {}, caveats: [] })
  mockApi.getProvenanceReport.mockResolvedValue(provenance ?? { topics: [], measurable: false, summary: {}, caveats: [] })
  mockApi.getGuardianReport.mockResolvedValue({
    risk_level: 'low',
    risk_factors: [],
    recommendations: [],
    session_patterns: { total_events: 95, total_watch_time_sec: 3512, avg_watch_time_sec: 37, late_night_share: 0.074, hourly_distribution: { 7: 18, 17: 20 } },
    ...guardian,
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ReportPage — coverage arithmetic', () => {
  it('averages the five signals against their targets', async () => {
    // 95/200, 7/12, 16/40, 4/8, 1/5 -> mean 0.4317 -> 43%
    setup()
    render(<ReportPage />)
    expect(await screen.findByText('43%')).toBeInTheDocument()
  })

  it('shows each signal as actual over target, so a thin profile reads as thin', async () => {
    setup()
    render(<ReportPage />)
    expect(await screen.findByText('95 / 200')).toBeInTheDocument()
    expect(screen.getByText('7 / 12')).toBeInTheDocument()
    expect(screen.getByText('1 / 5')).toBeInTheDocument()
  })

  it('caps a signal at its target so one huge number cannot mask the rest', async () => {
    // 10x the event target, everything else at zero: coverage must stay at
    // 1/5 of the total, not be dragged upward by the outlier.
    setup({
      summary: { behavior_object_count: 0, evidence_count: 0, inference_count: 0, snapshot_count: 0 },
      guardian: { session_patterns: { total_events: 2000 } },
    })
    render(<ReportPage />)
    expect(await screen.findByText('20%')).toBeInTheDocument()
  })
})

describe('ReportPage — framing follows the evidence', () => {
  it('calls a thin profile provisional', async () => {
    setup({
      summary: { behavior_object_count: 0, evidence_count: 0, inference_count: 0, snapshot_count: 0 },
      guardian: { session_patterns: { total_events: 0 } },
    })
    render(<ReportPage />)
    expect(await screen.findByText('Early / thin data')).toBeInTheDocument()
    expect(screen.getByText(/provisional/i)).toBeInTheDocument()
  })

  it('hedges a partially covered profile', async () => {
    setup()
    render(<ReportPage />)
    expect(await screen.findByText('Partial coverage')).toBeInTheDocument()
  })

  it('only calls a profile well covered once the signals are actually met', async () => {
    setup({
      summary: { behavior_object_count: 12, evidence_count: 40, inference_count: 8, snapshot_count: 5 },
      guardian: { session_patterns: { total_events: 200 } },
    })
    render(<ReportPage />)
    expect(await screen.findByText('Well covered')).toBeInTheDocument()
    expect(await screen.findByText('100%')).toBeInTheDocument()
  })
})

describe('ReportPage — provenance and honesty', () => {
  it('names the endpoint behind each section', async () => {
    setup()
    render(<ReportPage />)
    expect(await screen.findByText(/cognitive\/summary/)).toBeInTheDocument()
    expect(screen.getByText('/reasoning/behavior-objects')).toBeInTheDocument()
  })

  it('states that no language model produced any figure', async () => {
    setup()
    render(<ReportPage />)
    expect(
      await screen.findByText(/No language model\s+contributed to any number/i)
    ).toBeInTheDocument()
  })

  it('tags every inference with the rule that produced it', async () => {
    setup({
      inferences: [{
        inference_id: 'i1',
        label: 'Primary interests',
        description: 'Primary interests account for 68% of activity',
        confidence: 0.87,
        rule_name: 'PrimaryInterestRule',
      }],
    })
    render(<ReportPage />)
    expect(await screen.findByText('Primary interests')).toBeInTheDocument()
    expect(screen.getByText('PrimaryInterestRule')).toBeInTheDocument()
    expect(screen.getByText('87% confidence')).toBeInTheDocument()
  })
})

describe('ReportPage — empty states', () => {
  it('says there are no inferences rather than rendering an empty section', async () => {
    setup({ inferences: [] })
    render(<ReportPage />)
    expect(await screen.findByText(/No inferences yet/i)).toBeInTheDocument()
  })

  it('survives a backend that returns nothing at all', async () => {
    // Every endpoint failing must still produce a readable page — this is the
    // state a brand-new account is in.
    Object.values(mockApi).forEach(fn => fn.mockRejectedValue(new Error('offline')))
    render(<ReportPage />)
    expect(await screen.findByText('Cognitive Report')).toBeInTheDocument()
    expect(await screen.findByText('0%')).toBeInTheDocument()
  })
})

describe('ReportPage - the audits are part of the document', () => {
  const RELIABLE_MIRROR = {
    claims_total: 10,
    verdict_reliable: true,
    summary: { testable_claims: 8, corroborated: 4, unsupported: 4, not_comparable: 2, missed: 3, supported_share: 0.5 },
    corroborated: [], not_comparable: [], caveats: [],
    unsupported: [{ label: 'Cryptocurrency', platform: 'meta' }],
    missed: [{ topic: 'pottery', observations: 12 }],
  }

  const MEASURABLE_PROVENANCE = {
    measurable: true,
    summary: { fed: 2, mixed: 0, chosen: 1, unknown: 0, search_signals: 21, fed_share_of_attention: 0.77 },
    topics: [
      { topic: 'outrage', exposure: 46, searches: 0, agency: 0, verdict: 'fed' },
      { topic: 'robotics', exposure: 14, searches: 7, agency: 0.5, verdict: 'chosen' },
    ],
    caveats: [],
  }

  it('reports the platform audit finding', async () => {
    setup({ mirror: RELIABLE_MIRROR })
    render(<ReportPage />)
    expect(await screen.findByText(/50% of 8 testable/)).toBeInTheDocument()
    expect(screen.getByText('Cryptocurrency')).toBeInTheDocument()
  })

  it('reports the provenance finding', async () => {
    setup({ provenance: MEASURABLE_PROVENANCE })
    render(<ReportPage />)
    expect(await screen.findByText(/77% of judged watching/)).toBeInTheDocument()
    expect(screen.getByText('outrage')).toBeInTheDocument()
  })

  // The point of composing three independent gates: a document can be
  // confident enough to describe someone and still refuse to judge a platform.
  it('withholds the audit verdict when the audit says it is unreliable', async () => {
    setup({ mirror: { ...RELIABLE_MIRROR, verdict_reliable: false } })
    render(<ReportPage />)
    expect(await screen.findByText(/not yet enough\s+behavioural data to test them/i)).toBeInTheDocument()
    expect(screen.queryByText(/50% of 8 testable/)).not.toBeInTheDocument()
  })

  it('says agency is unmeasurable rather than reporting everything as fed', async () => {
    setup({
      provenance: {
        measurable: false,
        summary: { fed: 0, mixed: 0, chosen: 0, unknown: 2 },
        topics: [{ topic: 'robotics', exposure: 14, searches: 0, agency: null, verdict: 'unknown' }],
        caveats: [],
      },
    })
    render(<ReportPage />)
    expect(await screen.findByText(/Agency cannot be measured/i)).toBeInTheDocument()
  })

  it('omits both sections entirely when there is nothing imported', async () => {
    setup()
    render(<ReportPage />)
    await screen.findByText('Cognitive Report')
    expect(screen.queryByText('What the platform claims about you')).not.toBeInTheDocument()
    expect(screen.queryByText('Chosen or fed')).not.toBeInTheDocument()
  })

  it('explains that the audits are gated separately from page coverage', async () => {
    setup({ mirror: RELIABLE_MIRROR })
    render(<ReportPage />)
    // Matched on a fragment inside a single text node: the sentence is split
    // by a <strong>, and a regex spanning both elements finds nothing.
    expect(await screen.findByText(/reliability gates/i)).toBeInTheDocument()
  })
})
