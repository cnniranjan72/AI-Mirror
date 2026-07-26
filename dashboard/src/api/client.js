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
  healthCheck: async () => {
    const { data } = await client.get('/health');
    return data;
  },
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
};

export default client;
