import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Profile and Analytics
  getProfile: async () => {
    const response = await apiClient.get('/profile');
    return response.data;
  },

  getAnalytics: async () => {
    const response = await apiClient.get('/profile');
    return response.data; // Use profile data for analytics
  },

  // Chat System
  getChatHistory: async (userId = 'user_123') => {
    const response = await apiClient.get(`/chat/history/${userId}`);
    return response.data;
  },

  sendChatMessage: async (userId, query, includeContext = true) => {
    const response = await apiClient.post('/chat', {
      user_id: userId,
      query: query,
      include_context: includeContext
    });
    return response.data;
  },

  // RL Actions
  getAction: async (userId = 'user_123') => {
    const response = await apiClient.post('/action', {
      user_id: userId
    });
    return response.data;
  },

  sendFeedback: async (userId, actionId, followed, rating) => {
    const response = await apiClient.post('/feedback', {
      user_id: userId,
      action_id: actionId,
      followed: followed,
      user_rating: rating
    });
    return response.data;
  },

  // Alignment Goals
  getGoal: async (userId = 'user_123') => {
    const response = await apiClient.get(`/alignment/${userId}`);
    return response.data;
  },

  setGoal: async (userId, goal, targetWatchTime, priority = 'high') => {
    const response = await apiClient.post('/alignment', {
      user_id: userId,
      goal: goal,
      target_watch_time: targetWatchTime,
      priority: priority
    });
    return response.data;
  },

  // Query System
  queryInsights: async (query, topK = 5) => {
    const response = await apiClient.post('/query', {
      query: query,
      top_k: topK
    });
    return response.data;
  },

  // Health Check
  healthCheck: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  }
};

export default apiClient;
