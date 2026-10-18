import React from 'react';
import { RequestStatus } from '../types';

interface StatusBadgeProps {
  status: RequestStatus | string;
  size?: 'sm' | 'md';
}

const statusConfig: Record<
  string,
  { label: string; bg: string; text: string; dot: string }
> = {
  new: {
    label: 'New',
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    dot: 'bg-gray-400',
  },
  triage: {
    label: 'Triage',
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    dot: 'bg-blue-500',
  },
  awaiting_start_approval: {
    label: 'Awaiting Start Approval',
    bg: 'bg-amber-100',
    text: 'text-amber-800',
    dot: 'bg-amber-500',
  },
  in_progress: {
    label: 'In Progress',
    bg: 'bg-indigo-100',
    text: 'text-indigo-800',
    dot: 'bg-indigo-500',
  },
  awaiting_completion_approval: {
    label: 'Awaiting Completion Approval',
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    dot: 'bg-yellow-500',
  },
  done: {
    label: 'Done',
    bg: 'bg-emerald-100',
    text: 'text-emerald-800',
    dot: 'bg-emerald-500',
  },
  cancelled: {
    label: 'Cancelled',
    bg: 'bg-rose-100',
    text: 'text-rose-800',
    dot: 'bg-rose-500',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalizedStatus = status.toLowerCase();
  const config = statusConfig[normalizedStatus] || {
    label: status.replace(/_/g, ' '),
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    dot: 'bg-gray-400',
  };

  const sizeClasses =
    size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-semibold';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.bg} ${config.text} ${sizeClasses}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
};

export default StatusBadge;
