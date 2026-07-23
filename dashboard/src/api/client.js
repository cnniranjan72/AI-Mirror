import axios from 'axios';

// Single backend base URL. Override per-environment with VITE_API_URL
// (e.g. http://localhost:8001). Defaults to the documented port.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// The user whose cognitive twin the dashboard displays. Override with
// VITE_USER_ID. Defaults to a user that has data in the dev database.
export const DEFAULT_USER = import.meta.env.VITE_USER_ID || 'test_user_001';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const api = {
  // === Profile & Analytics ===
  getProfile: async (userId = DEFAULT_USER) => {
    const { data } = await client.get('/profile', { params: { user_id: userId } });
    return data;
  },

  // === Chat === (cognitive pipeline: POST /query)
  sendChatMessage: async (userId = DEFAULT_USER, query) => {
    const { data } = await client.post('/query', { user_id: userId, query });
    return {
      response: data.answer,
      trace_id: data.trace_id,
      sources: data.sources || [],
      llm_used: data.llm_used,
      pipeline_stages: data.pipeline_stages,
      pipeline_time_ms: data.pipeline_time_ms,
    };
  },

  // No server-side chat persistence yet — history lives in component state.
  getChatHistory: async () => ({ messages: [] }),

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
  getIdentitySnapshot: async (userId = DEFAULT_USER, limit = 10) => {
    const { data } = await client.get('/identity/snapshot', { params: { user_id: userId, limit } });
    return data;
  },
  getCurrentIdentity: async (userId = DEFAULT_USER) => {
    const { data } = await client.get('/identity/current', { params: { user_id: userId } });
    return data;
  },
  getSelfModel: async (userId = DEFAULT_USER) => {
    const { data } = await client.get('/identity/self-model', { params: { user_id: userId } });
    return data;
  },
  getEvidence: async (userId = DEFAULT_USER, evidenceType = '', limit = 50) => {
    const { data } = await client.get('/reasoning/evidence', { params: { user_id: userId, evidence_type: evidenceType, limit } });
    return data;
  },
  getInferences: async (userId = DEFAULT_USER, limit = 50) => {
    const { data } = await client.get('/reasoning/inferences', { params: { user_id: userId, limit } });
    return data;
  },
  getReflections: async (userId = DEFAULT_USER, limit = 20) => {
    const { data } = await client.get('/reasoning/reflections', { params: { user_id: userId, limit } });
    return data;
  },
  getBehaviorObjects: async (userId = DEFAULT_USER, limit = 50) => {
    const { data } = await client.get('/reasoning/behavior-objects', { params: { user_id: userId, limit } });
    return data;
  },
  getTraces: async (userId = DEFAULT_USER, limit = 20) => {
    const { data } = await client.get('/query/traces', { params: { user_id: userId, limit } });
    return data;
  },
  getTraceDetail: async (traceId) => {
    const { data } = await client.get(`/query/traces/${traceId}`);
    return data;
  },
  getCognitiveMetrics: async (userId = DEFAULT_USER, metricName = '', limit = 100) => {
    const { data } = await client.get('/cognitive/metrics', { params: { user_id: userId, metric_name: metricName, limit } });
    return data;
  },
  getCognitiveSummary: async (userId = DEFAULT_USER) => {
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
  getRlHistory: async (userId = DEFAULT_USER, limit = 30) => {
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
