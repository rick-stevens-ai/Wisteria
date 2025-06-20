import axios from 'axios';
import { Session, Hypothesis, Model, ApiResponse } from '../types/hypothesis';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Health check
  healthCheck: async (): Promise<ApiResponse<{ status: string; message: string }>> => {
    try {
      const response = await api.get('/health');
      return { data: response.data };
    } catch (error) {
      return { error: 'API is not available' };
    }
  },

  // Get available models
  getModels: async (): Promise<ApiResponse<Model[]>> => {
    try {
      const response = await api.get('/models');
      return { data: response.data.models };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to fetch models' };
    }
  },

  // Get all sessions
  getSessions: async (): Promise<ApiResponse<Session[]>> => {
    try {
      const response = await api.get('/sessions');
      return { data: response.data.sessions };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to fetch sessions' };
    }
  },

  // Create new session
  createSession: async (researchGoal: string, modelShortname: string): Promise<ApiResponse<Session>> => {
    try {
      const response = await api.post('/sessions', {
        research_goal: researchGoal,
        model_shortname: modelShortname,
      });
      return { data: response.data.session, message: response.data.message };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to create session' };
    }
  },

  // Get specific session
  getSession: async (sessionId: string): Promise<ApiResponse<Session>> => {
    try {
      const response = await api.get(`/sessions/${sessionId}`);
      return { data: response.data.session };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to fetch session' };
    }
  },

  // Generate initial hypothesis
  generateHypothesis: async (sessionId: string): Promise<ApiResponse<Hypothesis>> => {
    try {
      const response = await api.post(`/sessions/${sessionId}/hypotheses`);
      return { data: response.data.hypothesis, message: response.data.message };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to generate hypothesis' };
    }
  },

  // Improve hypothesis
  improveHypothesis: async (sessionId: string, hypothesisId: string, feedback: string): Promise<ApiResponse<Hypothesis>> => {
    try {
      const response = await api.post(`/sessions/${sessionId}/hypotheses/${hypothesisId}/improve`, {
        feedback,
      });
      return { data: response.data.hypothesis, message: response.data.message };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to improve hypothesis' };
    }
  },

  // Generate new hypothesis
  generateNewHypothesis: async (sessionId: string): Promise<ApiResponse<Hypothesis>> => {
    try {
      const response = await api.post(`/sessions/${sessionId}/hypotheses/new`);
      return { data: response.data.hypothesis, message: response.data.message };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to generate new hypothesis' };
    }
  },

  // Get session hypotheses
  getSessionHypotheses: async (sessionId: string): Promise<ApiResponse<Hypothesis[]>> => {
    try {
      const response = await api.get(`/sessions/${sessionId}/hypotheses`);
      return { data: response.data.hypotheses };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to fetch hypotheses' };
    }
  },

  // Delete session
  deleteSession: async (sessionId: string): Promise<ApiResponse<void>> => {
    try {
      const response = await api.delete(`/sessions/${sessionId}`);
      return { message: response.data.message };
    } catch (error: any) {
      return { error: error.response?.data?.error || 'Failed to delete session' };
    }
  },
}; 