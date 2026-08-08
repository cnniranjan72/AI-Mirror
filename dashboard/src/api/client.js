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
  deleteAllData: async (confirmUserId, userId = activeUser()) => {
    const { data } = await client.post('/privacy/delete-all-data', { user_id: userId, confirm_user_id: confirmUserId });
    return data;
  },
};

export default client;
