import { apiClient } from './client';
import {
  Request,
  RequestEvent,
  Comment,
  PaginatedResponse,
  AttentionResponse,
  RequestFilters,
  CreateRequestInput,
  EditRequestInput,
  Team,
  RequestType,
  User,
} from '../types';

export const fetchRequests = async (
  filters?: RequestFilters,
  cursor?: string | null
): Promise<PaginatedResponse<Request>> => {
  const params: Record<string, any> = { ...filters };
  if (cursor) {
    params.cursor = cursor;
  }
  // Remove empty string/undefined values
  Object.keys(params).forEach((key) => {
    if (params[key] === undefined || params[key] === '' || params[key] === 'all') {
      delete params[key];
    }
  });

  const response = await apiClient.get<PaginatedResponse<Request>>('/requests', { params });
  return response.data;
};

export const fetchRequest = async (id: string | number): Promise<Request> => {
  const response = await apiClient.get<Request>(`/requests/${id}`);
  return response.data;
};

export const createRequest = async (
  data: CreateRequestInput,
  idempotencyKey?: string
): Promise<Request> => {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const response = await apiClient.post<Request>('/requests', data, { headers });
  return response.data;
};

export const editRequest = async (
  id: string | number,
  data: EditRequestInput,
  version: number
): Promise<Request> => {
  const response = await apiClient.patch<Request>(
    `/requests/${id}`,
    { ...data, version },
    {
      headers: {
        'If-Match': String(version),
      },
    }
  );
  return response.data;
};

export const claimRequest = async (
  id: string | number,
  idempotencyKey?: string
): Promise<Request> => {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const response = await apiClient.post<Request>(`/requests/${id}/claim`, {}, { headers });
  return response.data;
};

export const transitionRequest = async (
  id: string | number,
  to: string,
  version: number,
  reason?: string,
  idempotencyKey?: string
): Promise<Request> => {
  const headers: Record<string, string> = {
    'If-Match': String(version),
  };
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const payload: { to: string; version: number; reason?: string } = {
    to,
    version,
  };
  if (reason) {
    payload.reason = reason;
  }
  const response = await apiClient.post<Request>(`/requests/${id}/transition`, payload, {
    headers,
  });
  return response.data;
};

export const assignRequest = async (
  id: string | number,
  userId: string | number,
  version: number,
  reason?: string
): Promise<Request> => {
  const response = await apiClient.post<Request>(
    `/requests/${id}/assign`,
    {
      user_id: userId,
      version,
      reason,
    },
    {
      headers: {
        'If-Match': String(version),
      },
    }
  );
  return response.data;
};

export const fetchEvents = async (
  requestId: string | number,
  cursor?: string | null
): Promise<PaginatedResponse<RequestEvent> | RequestEvent[]> => {
  const params: Record<string, any> = {};
  if (cursor) {
    params.cursor = cursor;
  }
  const response = await apiClient.get<PaginatedResponse<RequestEvent> | RequestEvent[]>(
    `/requests/${requestId}/events`,
    { params }
  );
  return response.data;
};

export const addComment = async (
  requestId: string | number,
  body: string,
  idempotencyKey?: string
): Promise<Comment> => {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const response = await apiClient.post<Comment>(
    `/requests/${requestId}/comments`,
    { body },
    { headers }
  );
  return response.data;
};

export const fetchApprovalQueue = async (
  cursor?: string | null
): Promise<PaginatedResponse<Request>> => {
  const params: Record<string, any> = {};
  if (cursor) {
    params.cursor = cursor;
  }
  const response = await apiClient.get<PaginatedResponse<Request>>('/approvals/queue', {
    params,
  });
  return response.data;
};

export const fetchAttention = async (): Promise<AttentionResponse> => {
  const response = await apiClient.get<AttentionResponse>('/attention');
  return response.data;
};

export const fetchTeams = async (): Promise<Team[]> => {
  const response = await apiClient.get<Team[]>('/teams');
  return response.data;
};

export const fetchRequestTypes = async (teamId?: string | number): Promise<RequestType[]> => {
  const params: Record<string, any> = {};
  if (teamId) {
    params.team_id = teamId;
  }
  const response = await apiClient.get<RequestType[]>('/request-types', { params });
  return response.data;
};

export const fetchTeamMembers = async (teamId: string | number): Promise<User[]> => {
  const response = await apiClient.get<User[]>(`/teams/${teamId}/members`);
  return response.data;
};
