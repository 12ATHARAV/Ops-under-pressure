import { apiClient } from './client';
import { MeResponse } from '../types';

export interface LoginResponse {
  access_token?: string;
  token?: string;
  token_type?: string;
  user?: any;
}

export const login = async (email: string, password: string): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', {
    email,
    password,
  });

  const token = response.data.access_token || response.data.token;
  if (token) {
    localStorage.setItem('token', token);
  }

  return response.data;
};

export const getMe = async (): Promise<MeResponse> => {
  const response = await apiClient.get<MeResponse>('/me');
  return response.data;
};

export const logout = (): void => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};
