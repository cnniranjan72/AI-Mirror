import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const v3Client = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const DEFAULT_USER = 'user_123';

export const api = {
  // === Profile & Analytics ===
  getProfile: async () => {
    const { data } = await v3Client.get('/profile');
    return data;
  },

  // === Sessions (legacy backend) ===
  getSessions: async () => {
    const { data } = await apiClient.get('/api/sessions');
    return data;
  },

  // === Chat System ===
  getChatHistory: async (userId = DEFAULT_USER) => {
    const { data } = await v3Client.get(`/chat/history/${userId}`);
    return data;
  },

  sendChatMessage: async (userId = DEFAULT_USER, query, includeContext = true) => {
    const { data } = await v3Client.post('/chat', { user_id: userId, query, include_context: includeContext });
    return data;
  },

  // === Health ===
  healthCheck: async () => {
    const { data } = await apiClient.get('/health');
    return data;
  },

  v3Health: async () => {
    const { data } = await v3Client.get('/health');
    return data;
  },

  // === EXPLAINABILITY API (V3/8000) ===
  getIdentitySnapshot: async (userId = DEFAULT_USER, limit = 10) => {
    const { data } = await v3Client.get('/identity/snapshot', { params: { user_id: userId, limit } });
    return data;
  },

  getCurrentIdentity: async (userId = DEFAULT_USER) => {
    const { data } = await v3Client.get('/identity/current', { params: { user_id: userId } });
    return data;
  },

  getEvidence: async (userId = DEFAULT_USER, evidenceType = '', limit = 50) => {
    const { data } = await v3Client.get('/reasoning/evidence', { params: { user_id: userId, evidence_type: evidenceType, limit } });
    return data;
  },

  getInferences: async (userId = DEFAULT_USER, limit = 50) => {
    const { data } = await v3Client.get('/reasoning/inferences', { params: { user_id: userId, limit } });
    return data;
  },

  getReflections: async (userId = DEFAULT_USER, limit = 20) => {
    const { data } = await v3Client.get('/reasoning/reflections', { params: { user_id: userId, limit } });
    return data;
  },

  getBehaviorObjects: async (userId = DEFAULT_USER, limit = 50) => {
    const { data } = await v3Client.get('/reasoning/behavior-objects', { params: { user_id: userId, limit } });
    return data;
  },

  getTraces: async (userId = DEFAULT_USER, limit = 20) => {
    const { data } = await v3Client.get('/query/traces', { params: { user_id: userId, limit } });
    return data;
  },

  getTraceDetail: async (traceId) => {
    const { data } = await v3Client.get(`/query/traces/${traceId}`);
    return data;
  },

  getCognitiveMetrics: async (userId = DEFAULT_USER, metricName = '', limit = 100) => {
    const { data } = await v3Client.get('/cognitive/metrics', { params: { user_id: userId, metric_name: metricName, limit } });
    return data;
  },

  getCognitiveSummary: async (userId = DEFAULT_USER) => {
    const { data } = await v3Client.get('/cognitive/summary', { params: { user_id: userId } });
    return data;
  },

  // === Explainability Details ===
  getExplain: async (traceId) => {
    const { data } = await v3Client.get(`/explain/${traceId}`);
    return data;
  },

  getEvidenceDetail: async (evidenceId) => {
    const { data } = await v3Client.get(`/explain/evidence/${evidenceId}`);
    return data;
  },

  getIdentityDetail: async (identityId) => {
    const { data } = await v3Client.get(`/explain/identity/${identityId}`);
    return data;
  },

  // === Seed (Demo) ===
  seedDemo: async () => {
    const { data } = await v3Client.post('/seed');
    return data;
  },

  // === Search ===
  search: async (q, limit = 20) => {
    const { data } = await v3Client.get('/search', { params: { q, limit } });
    return data;
  },
};

export default apiClient;
