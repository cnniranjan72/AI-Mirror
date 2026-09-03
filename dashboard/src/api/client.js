import axios from 'axios';

// Single backend base URL. Override per-environment with VITE_API_URL
// (e.g. http://localhost:8001). Defaults to the documented port.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Demo user shown when NOT logged in. Override with VITE_USER_ID.
const DEMO_USER = import.meta.env.VITE_USER_ID || 'test_user_001';

// Auth is additive: when signed in we use the authenticated username as the
// user_id and attach a Bearer token; when signed out the app runs in demo mode
// against DEMO_USER, exactly as before. Nothing breaks without a login.
export function activeUser() {
  return localStorage.getItem('aim_user') || DEMO_USER;
}
export function authToken() {
  return localStorage.getItem('aim_token') || null;
}
export function isAuthed() {
  return !!authToken();
}
export function setAuth(token, user) {
  localStorage.setItem('aim_token', token);
  localStorage.setItem('aim_user', user.username);
  localStorage.setItem('aim_display', user.display_name || user.username);
}
export function clearAuth() {
  localStorage.removeItem('aim_token');
  localStorage.removeItem('aim_user');
  localStorage.removeItem('aim_display');
}
export function displayName() {
  return localStorage.getItem('aim_display') || null;
}

// Backwards-compatible alias (some pages import DEFAULT_USER).
export const DEFAULT_USER = activeUser();

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach the Bearer token when signed in (no-op when signed out).
client.interceptors.request.use((config) => {
  const t = authToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

export const api = {
  // === Auth ===
  register: async (username, password, displayName) => {
    const { data } = await client.post('/auth/register', { username, password, display_name: displayName });
    setAuth(data.token, data.user);
    return data.user;
  },
  login: async (username, password) => {
    const { data } = await client.post('/auth/login', { username, password });
    setAuth(data.token, data.user);
    return data.user;
  },
  me: async () => {
    const { data } = await client.get('/auth/me');
    return data.user;
  },
  logout: () => { clearAuth(); },

  // === Profile & Analytics ===
  getProfile: async (userId = activeUser()) => {
    const { data } = await client.get('/profile', { params: { user_id: userId } });
    return data;
  },

  // === Chat === (cognitive pipeline: POST /query, with persistent memory)
  sendChatMessage: async (userId = activeUser(), query, conversationId) => {
    const { data } = await client.post('/query', {
      user_id: userId, query, conversation_id: conversationId,
    });
    return {
      response: data.answer,
      trace_id: data.trace_id,
      sources: data.sources || [],
      llm_used: data.llm_used,
      follow_ups: data.follow_ups || [],
      pipeline_stages: data.pipeline_stages,
      pipeline_time_ms: data.pipeline_time_ms,
    };
  },

  getChatHistory: async (userId = activeUser(), conversationId) => {
    const { data } = await client.get('/chat/history', {
      params: { user_id: userId, conversation_id: conversationId },
    });
    return data;
  },

  clearChatHistory: async (userId = activeUser(), conversationId) => {
    const { data } = await client.delete('/chat/history', {
      params: { user_id: userId, conversation_id: conversationId },
    });
    return data;
  },

  // The cognitive backend has no legacy session store; behavior is modeled as
  // BehaviorObjects. Return empty so pages that still reference sessions render.
  getSessions: async () => [],

  // === Health ===
  v3Health: async () => {
    const { data } = await client.get('/health');
    return data;
  },

  // === Explainability / Reasoning ===
  getIdentitySnapshot: async (userId = activeUser(), limit = 10) => {
    const { data } = await client.get('/identity/snapshot', { params: { user_id: userId, limit } });
    return data;
  },
  getCurrentIdentity: async (userId = activeUser()) => {
    const { data } = await client.get('/identity/current', { params: { user_id: userId } });
    return data;
  },
  getSelfModel: async (userId = activeUser()) => {
    const { data } = await client.get('/identity/self-model', { params: { user_id: userId } });
    return data;
  },
  getEvidence: async (userId = activeUser(), evidenceType = '', limit = 50) => {
    const { data } = await client.get('/reasoning/evidence', { params: { user_id: userId, evidence_type: evidenceType, limit } });
    return data;
  },
  getInferences: async (userId = activeUser(), limit = 50) => {
    const { data } = await client.get('/reasoning/inferences', { params: { user_id: userId, limit } });
    return data;
  },
  getReflections: async (userId = activeUser(), limit = 20) => {
    const { data } = await client.get('/reasoning/reflections', { params: { user_id: userId, limit } });
    return data;
  },
  getBehaviorObjects: async (userId = activeUser(), limit = 50) => {
    const { data } = await client.get('/reasoning/behavior-objects', { params: { user_id: userId, limit } });
    return data;
  },
  getTraces: async (userId = activeUser(), limit = 20) => {
    const { data } = await client.get('/query/traces', { params: { user_id: userId, limit } });
    return data;
  },
  // One reasoning run opened up: per-stage timings, the decision funnel, and
  // the split between deciding and talking. Built from what the run recorded.
  getReasoningXray: async (traceId, userId = activeUser()) => {
    const { data } = await client.get(`/query/traces/${traceId}/xray`, { params: { user_id: userId } });
    return data;
  },
  getTraceDetail: async (traceId) => {
    const { data } = await client.get(`/query/traces/${traceId}`);
    return data;
  },
  getCognitiveMetrics: async (userId = activeUser(), metricName = '', limit = 100) => {
    const { data } = await client.get('/cognitive/metrics', { params: { user_id: userId, metric_name: metricName, limit } });
    return data;
  },
  getCognitiveSummary: async (userId = activeUser()) => {
    const { data } = await client.get('/cognitive/summary', { params: { user_id: userId } });
    return data;
  },

  // === Explainability details ===
  getExplain: async (traceId) => {
    const { data } = await client.get(`/explain/${traceId}`);
    return data;
  },
  getEvidenceDetail: async (evidenceId) => {
    const { data } = await client.get(`/explain/evidence/${evidenceId}`);
    return data;
  },
  getIdentityDetail: async (identityId) => {
    const { data } = await client.get(`/explain/identity/${identityId}`);
    return data;
  },

  // === Reinforcement Learning ===
  getRlPolicy: async () => {
    const { data } = await client.get('/rl/policy');
    return data;
  },
  getRlHistory: async (userId = activeUser(), limit = 30) => {
    const { data } = await client.get('/rl/history', { params: { user_id: userId, limit } });
    return data;
  },
  sendRlFeedback: async (contextKey, actionId, reward) => {
    const { data } = await client.post('/rl/feedback', { context_key: contextKey, action_id: actionId, reward });
    return data;
  },

  // === Timeline ===
  getTimeline: async (userId = activeUser(), opts = {}) => {
    const { data } = await client.get('/timeline', {
      params: {
        user_id: userId,
        platform: opts.platform || undefined,
        liked_only: opts.likedOnly || undefined,
        saved_only: opts.savedOnly || undefined,
        attention: opts.attention || undefined,
        search: opts.search || undefined,
        limit: opts.limit || 30,
        before_id: opts.beforeId || undefined,
      },
    });
    return data;
  },

  // === Knowledge Graph ===
  getKnowledgeGraph: async (userId = activeUser()) => {
    const { data } = await client.get('/graph/knowledge', { params: { user_id: userId } });
    return data;
  },

  // === Diary (AI-narrated weekly/monthly story) ===
  getDiaryStory: async (userId = activeUser(), period = 'week', offset = 0) => {
    const { data } = await client.get('/diary/story', { params: { user_id: userId, period, offset } });
    return data;
  },

  // === Goals ===
  getGoals: async (userId = activeUser(), status) => {
    const { data } = await client.get('/goals', { params: { user_id: userId, status } });
    return data;
  },
  createGoal: async (goalDescription, goalType, targetKeywords, targetDate, userId = activeUser()) => {
    const { data } = await client.post('/goals', {
      user_id: userId, goal_description: goalDescription, goal_type: goalType,
      target_keywords: targetKeywords, target_date: targetDate || undefined,
    });
    return data;
  },
  updateGoal: async (goalId, updates) => {
    const { data } = await client.patch(`/goals/${goalId}`, updates);
    return data;
  },
  deleteGoal: async (goalId) => {
    const { data } = await client.delete(`/goals/${goalId}`);
    return data;
  },

  // === Seed (demo data) ===
  seedDemo: async () => {
    const { data } = await client.post('/seed');
    return data;
  },

  // === Data export import (Instagram DYI / Google Takeout) ===
  importArchive: async (fileObj, userId = activeUser(), onProgress) => {
    const form = new FormData();
    form.append('file', fileObj);
    form.append('user_id', userId);
    // Content-Type is deliberately NOT set: the browser has to add the
    // multipart boundary itself, and supplying the header without one makes
    // the request unparseable server-side.
    const { data } = await client.post('/import/archive', form, {
      // A full export runs to tens of thousands of events and every one goes
      // through the real pipeline, so this legitimately outlives the default.
      timeout: 15 * 60 * 1000,
      onUploadProgress: onProgress
        ? (e) => onProgress(e.total ? e.loaded / e.total : 0)
        : undefined,
    });
    return data;
  },

  // === Algorithmic Mirror ===
  getMirrorReport: async (userId = activeUser()) => {
    const { data } = await client.get('/mirror/report', { params: { user_id: userId } });
    return data;
  },
  getMirrorClaims: async (userId = activeUser()) => {
    const { data } = await client.get('/mirror/claims', { params: { user_id: userId } });
    return data;
  },

  // How the seventeen identity measures moved over time. Same vector the
  // snapshot threshold is judged against, so chart and number agree.
  getIdentityDrift: async (userId = activeUser(), limit = 12) => {
    const { data } = await client.get('/identity/drift', { params: { user_id: userId, limit } });
    return data;
  },

  // Re-runs the reasoning stages over real history plus hypothetical events.
  // Writes nothing: the result is discarded, which is what makes the question
  // safe to ask of your own profile.
  runCounterfactual: async (events, userId = activeUser()) => {
    const { data } = await client.post('/identity/counterfactual', { user_id: userId, events });
    return data;
  },

  // The stored embeddings projected to 3D. PCA, so the same history always
  // draws the same shape; the response carries how much structure survives.
  getRestorePoints: async (userId = activeUser()) => {
    const { data } = await client.get('/identity/restore-points', { params: { user_id: userId } });
    return data;
  },

  // snapshotId null means unpin.
  setRestorePoint: async (snapshotId, reason, userId = activeUser()) => {
    const { data } = await client.post('/identity/restore', {
      user_id: userId, snapshot_id: snapshotId, reason: reason || null,
    });
    return data;
  },

  getLifecycle: async (userId = activeUser()) => {
    const { data } = await client.get('/reasoning/lifecycle', { params: { user_id: userId } });
    return data;
  },

  getBlindSpots: async (userId = activeUser()) => {
    const { data } = await client.get('/identity/blind-spots', { params: { user_id: userId } });
    return data;
  },

  getContestedClaims: async (userId = activeUser(), limit = 40) => {
    const { data } = await client.get('/reasoning/contested', { params: { user_id: userId, limit } });
    return data;
  },

  getBehaviourSpace: async (userId = activeUser(), limit = 600) => {
    const { data } = await client.get('/identity/space', { params: { user_id: userId, limit } });
    return data;
  },

  // === Collection control ===
  // Whether the system is allowed to collect. Enforced server-side at /ingest:
  // a switch honoured only by the client would be a request, not a guarantee.
  getCollectionStatus: async (userId = activeUser()) => {
    const { data } = await client.get('/collection/status', { params: { user_id: userId } });
    return data;
  },
  setCollectionPaused: async (paused, userId = activeUser()) => {
    const { data } = await client.post('/collection/pause', { user_id: userId, paused });
    return data;
  },

  // === Accuracy ledger ===
  // The system's own scorecard: what it claimed about you, and whether you
  // said it was right. See backend/app/services/calibration.py.
  getCalibrationReport: async (userId = activeUser()) => {
    const { data } = await client.get('/calibration/report', { params: { user_id: userId } });
    return data;
  },
  getOpenClaims: async (userId = activeUser(), limit = 20) => {
    const { data } = await client.get('/calibration/open', { params: { user_id: userId, limit } });
    return data;
  },
  // Already-answered claims, so a verdict can be changed. Each row carries
  // live_claim_id — the id to POST against now; the stored claim_id goes stale
  // because the pipeline regenerates inferences on every ingest.
  getAnsweredClaims: async (userId = activeUser(), limit = 50) => {
    const { data } = await client.get('/calibration/answered', { params: { user_id: userId, limit } });
    return data;
  },
  sendClaimVerdict: async (claimId, verdict, claimType = 'inference', userId = activeUser()) => {
    const { data } = await client.post('/calibration/verdict', {
      user_id: userId, claim_type: claimType, claim_id: claimId, verdict,
    });
    return data;
  },

  getProvenanceReport: async (userId = activeUser()) => {
    const { data } = await client.get('/provenance/report', { params: { user_id: userId } });
    return data;
  },

  getProvenanceTimeline: async (userId = activeUser()) => {
    const { data } = await client.get('/provenance/timeline', { params: { user_id: userId } });
    return data;
  },

  getLlmStatus: async () => {
    const { data } = await client.get('/settings/llm/status');
    return data;
  },

  // === Search ===
  search: async (q, limit = 20) => {
    const { data } = await client.get('/search', { params: { q, limit } });
    return data;
  },

  // === Guardian / Wellbeing ===
  getGuardianReport: async (userId = activeUser()) => {
    const { data } = await client.get('/guardian/report', { params: { user_id: userId } });
    return data;
  },

  // === Character ===
  getCharacterState: async (userId = activeUser()) => {
    const { data } = await client.get('/character/state', { params: { user_id: userId } });
    return data;
  },
  getCharacterActivity: async (userId = activeUser(), limit = 10) => {
    const { data } = await client.get('/character/activity', { params: { user_id: userId, limit } });
    return data;
  },
  getCharacterLearningSummary: async (userId = activeUser()) => {
    const { data } = await client.get('/character/learning-summary', { params: { user_id: userId } });
    return data;
  },

  // === Insights / Export ===
  getInsightsProfile: async (userId = activeUser()) => {
    const { data } = await client.get('/insights/profile', { params: { user_id: userId } });
    return data;
  },
  exportCsvUrl: (userId = activeUser(), table = 'behavior_objects') =>
    `${API_BASE_URL}/insights/export.csv?user_id=${encodeURIComponent(userId)}&table=${encodeURIComponent(table)}`,
  postCampaignResonance: async (campaignText, userId = activeUser()) => {
    const { data } = await client.post('/insights/campaign-resonance', { user_id: userId, campaign_text: campaignText });
    return data;
  },
  getGuardianAlertLog: async (userId = activeUser(), limit = 20) => {
    const { data } = await client.get('/guardian/alert-log', { params: { user_id: userId, limit } });
    return data;
  },
  getGuardianUnacknowledgedCount: async (userId = activeUser()) => {
    const { data } = await client.get('/guardian/alert-log/unacknowledged-count', { params: { user_id: userId } });
    return data;
  },
  acknowledgeGuardianAlert: async (alertId, userId = activeUser()) => {
    const { data } = await client.post(`/guardian/alert-log/${alertId}/acknowledge`, null, { params: { user_id: userId } });
    return data;
  },
  exportAllDataUrl: (userId = activeUser()) =>
    `${API_BASE_URL}/privacy/export-all?user_id=${encodeURIComponent(userId)}`,

  // === Organizations (seats/roster — never cross-user cognitive data) ===
  getMyOrg: async () => {
    const { data } = await client.get('/orgs/me');
    return data;
  },
  createOrg: async (name) => {
    const { data } = await client.post('/orgs', { name });
    return data;
  },
  getOrgMembers: async () => {
    const { data } = await client.get('/orgs/members');
    return data;
  },
  createOrgInvite: async (maxUses = 1, expiresHours = 168) => {
    const { data } = await client.post('/orgs/invites', { max_uses: maxUses, expires_hours: expiresHours });
    return data;
  },
  listOrgInvites: async () => {
    const { data } = await client.get('/orgs/invites');
    return data;
  },
  joinOrg: async (code) => {
    const { data } = await client.post('/orgs/join', { code });
    return data;
  },
  removeOrgMember: async (username) => {
    const { data } = await client.delete(`/orgs/members/${encodeURIComponent(username)}`);
    return data;
  },
  leaveOrg: async () => {
    const { data } = await client.post('/orgs/leave');
    return data;
  },

  // === Research (opt-in de-identified export) ===
  getResearchStatus: async () => {
    const { data } = await client.get('/research/status');
    return data;
  },
  setResearchOptIn: async (optIn) => {
    const { data } = await client.post('/research/opt-in', { opt_in: optIn });
    return data;
  },
  // GET /research/export requires a bearer token, so it can't be a plain
  // download link (no way to attach an Authorization header to <a href>) —
  // fetch it through the authenticated client and save the blob instead.
  downloadResearchExport: async () => {
    const { data } = await client.get('/research/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aimirror_research_export_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return data;
  },

  // === AI Provider settings (per-user LLM key, falls back to server default) ===
  getLlmSettings: async () => {
    const { data } = await client.get('/settings/llm');
    return data;
  },
  setLlmSettings: async (provider, apiKey, baseUrl, model) => {
    const { data } = await client.post('/settings/llm', {
      provider, api_key: apiKey || undefined, base_url: baseUrl || undefined, model: model || undefined,
    });
    return data;
  },
  clearLlmSettings: async () => {
    const { data } = await client.delete('/settings/llm');
    return data;
  },

  // === Admin (local debugging — no per-user auth, not a data endpoint) ===
  getAdminErrors: async (errorType, limit = 20) => {
    const { data } = await client.get('/admin/errors', { params: { error_type: errorType, limit } });
    return data;
  },
  // confirmUserId must be what the user actually typed to confirm — the
  // backend rejects the call if it doesn't match user_id, as a guard
  // against an accidental click triggering an irreversible deletion.
  // deleteAccount is opt-in and separate: erasing what the system learned and
  // deleting the login are different requests. The response always reports what
  // survived (the users row holds the password hash and the stored LLM key).
  deleteAllData: async (confirmUserId, userId = activeUser(), deleteAccount = false) => {
    const { data } = await client.post('/privacy/delete-all-data', {
      user_id: userId, confirm_user_id: confirmUserId, delete_account: deleteAccount,
    });
    return data;
  },
};

export default client;
