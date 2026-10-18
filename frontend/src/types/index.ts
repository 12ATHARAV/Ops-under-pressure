export type Role = 'member' | 'approver' | 'lead';

export type ApprovalMode = 'none' | 'before' | 'after' | 'both';

export type RequestStatus =
  | 'new'
  | 'triage'
  | 'awaiting_start_approval'
  | 'in_progress'
  | 'awaiting_completion_approval'
  | 'done'
  | 'cancelled';

export const RequestStatusEnum = {
  NEW: 'new' as RequestStatus,
  TRIAGE: 'triage' as RequestStatus,
  AWAITING_START_APPROVAL: 'awaiting_start_approval' as RequestStatus,
  IN_PROGRESS: 'in_progress' as RequestStatus,
  AWAITING_COMPLETION_APPROVAL: 'awaiting_completion_approval' as RequestStatus,
  DONE: 'done' as RequestStatus,
  CANCELLED: 'cancelled' as RequestStatus,
};

export type RequestPriority = 'low' | 'medium' | 'high' | 'urgent';

export const RequestPriorityEnum = {
  LOW: 'low' as RequestPriority,
  MEDIUM: 'medium' as RequestPriority,
  HIGH: 'high' as RequestPriority,
  URGENT: 'urgent' as RequestPriority,
};

export interface User {
  id: string | number;
  email: string;
  name: string;
}

export interface Team {
  id: string | number;
  name: string;
}

export interface TeamMembership {
  team_id: string | number;
  team: Team;
  role: Role;
}

export interface MeResponse {
  user: User;
  memberships: TeamMembership[];
}

export interface RequestType {
  id: string | number;
  team_id: string | number;
  name: string;
  approval_mode: ApprovalMode;
  sla_hours?: number;
}

export interface Request {
  id: string | number;
  team_id: string | number;
  team_name?: string;
  type_id: string | number;
  type_name?: string;
  title: string;
  description: string;
  status: RequestStatus;
  priority: RequestPriority;
  owner_id: string | number | null;
  owner_name?: string | null;
  created_by: string | number;
  created_by_name?: string;
  version: number;
  due_at: string | null;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
  allowed_actions: string[];
}

export interface RequestEvent {
  id: string | number;
  request_id: string | number;
  actor_id: string | number;
  actor_name?: string;
  type: string;
  from_value?: any;
  to_value?: any;
  reason?: string | null;
  created_at: string;
}

export interface Comment {
  id: string | number;
  request_id: string | number;
  author_id: string | number;
  author_name?: string;
  body: string;
  created_at: string;
}

export interface Notification {
  id: string | number;
  request_id: string | number;
  kind: string;
  body: string;
  read_at: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  cursor: string | null;
  has_more: boolean;
}

export interface AttentionBucket {
  name: string;
  count: number;
  items: Request[];
}

export interface AttentionResponse {
  buckets: AttentionBucket[];
}

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  current_state?: Request;
  events_since?: RequestEvent[];
}

export interface RequestFilters {
  team?: string | number;
  status?: RequestStatus | string;
  owner?: 'me' | 'none' | string | number;
  priority?: RequestPriority | string;
  type?: string | number;
  q?: string;
  cursor?: string | null;
  limit?: number;
}

export interface CreateRequestInput {
  team_id: string | number;
  type_id: string | number;
  title: string;
  description: string;
  priority: RequestPriority;
  due_at?: string | null;
}

export interface EditRequestInput {
  title?: string;
  description?: string;
  priority?: RequestPriority;
  due_at?: string | null;
}
