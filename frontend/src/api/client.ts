import axios, { AxiosError } from 'axios';
import { ApiError } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 (clear token, redirect to login)
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const generateIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'ik-' + Date.now() + '-' + Math.random().toString(36).substring(2, 11);
};

export const parseApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as any;
    return {
      code: data.code || String(error.response.status),
      message: data.message || data.detail || 'An unexpected error occurred',
      details: data.details,
      current_state: data.current_state,
      events_since: data.events_since || data.events_since_version,
    };
  }
  if (error instanceof Error) {
    return {
      code: 'CLIENT_ERROR',
      message: error.message,
    };
  }
  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unknown error occurred',
  };
};
