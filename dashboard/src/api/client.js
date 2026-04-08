import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  getSessions: async (limit = 50, offset = 0) => {
    const response = await apiClient.get('/api/sessions', {
      params: { limit, offset }
    });
    return response.data;
  },

  getSession: async (sessionId) => {
    const response = await apiClient.get(`/api/sessions/${sessionId}`);
    return response.data;
  },

  getSessionEvents: async (sessionId) => {
    const response = await apiClient.get(`/api/sessions/${sessionId}/events`);
    return response.data;
  },

  getEvents: async (limit = 100, offset = 0) => {
    const response = await apiClient.get('/api/events', {
      params: { limit, offset }
    });
    return response.data;
  },

  getAnalytics: async () => {
    const response = await apiClient.get('/api/analytics');
    return response.data;
  },

  deleteSession: async (sessionId) => {
    const response = await apiClient.delete(`/api/sessions/${sessionId}`);
    return response.data;
  },

  healthCheck: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  }
};

export default apiClient;
