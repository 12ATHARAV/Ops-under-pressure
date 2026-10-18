import { apiClient } from './client';
import { Notification, PaginatedResponse } from '../types';

export const fetchNotifications = async (
  cursor?: string | null
): Promise<PaginatedResponse<Notification>> => {
  const params: Record<string, any> = {};
  if (cursor) {
    params.cursor = cursor;
  }
  const response = await apiClient.get<PaginatedResponse<Notification>>('/notifications', {
    params,
  });
  return response.data;
};

export const markRead = async (id: string | number): Promise<Notification> => {
  const response = await apiClient.post<Notification>(`/notifications/${id}/read`);
  return response.data;
};
