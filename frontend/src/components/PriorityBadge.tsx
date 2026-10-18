import React from 'react';
import { RequestPriority } from '../types';

interface PriorityBadgeProps {
  priority: RequestPriority | string;
  size?: 'sm' | 'md';
}

const priorityConfig: Record<
  string,
  { label: string; bg: string; text: string; icon: string }
> = {
  low: {
    label: 'Low',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    icon: '↓',
  },
  medium: {
    label: 'Medium',
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    icon: '→',
  },
  high: {
    label: 'High',
    bg: 'bg-orange-100',
    text: 'text-orange-800',
    icon: '↑',
  },
  urgent: {
    label: 'Urgent',
    bg: 'bg-red-100',
    text: 'text-red-800',
    icon: '⚡',
  },
};

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority, size = 'md' }) => {
  const normalizedPriority = priority.toLowerCase();
  const config = priorityConfig[normalizedPriority] || {
    label: priority,
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    icon: '•',
  };

  const sizeClasses =
    size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-semibold';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded font-medium ${config.bg} ${config.text} ${sizeClasses}`}
    >
      <span className="font-bold">{config.icon}</span>
      {config.label}
    </span>
  );
};

export default PriorityBadge;
