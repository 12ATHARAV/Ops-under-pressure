import React from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { RequestEvent } from '../types';

interface TimelineProps {
  events: RequestEvent[];
  isLoading?: boolean;
}

export const Timeline: React.FC<TimelineProps> = ({ events, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="py-8 text-center text-sm text-gray-500">
        Loading timeline events...
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-gray-400">
        No recorded events yet for this request.
      </div>
    );
  }

  // Sort chronologically (oldest to newest for linear timeline or newest first)
  // Most operational timelines show oldest first (downward flow)
  const sortedEvents = [...events].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  const getEventIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'created':
        return (
          <span className="w-7 h-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            +
          </span>
        );
      case 'status_changed':
        return (
          <span className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            ⇄
          </span>
        );
      case 'owner_changed':
      case 'claimed':
      case 'assigned':
        return (
          <span className="w-7 h-7 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            👤
          </span>
        );
      case 'approved':
        return (
          <span className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            ✓
          </span>
        );
      case 'rejected':
        return (
          <span className="w-7 h-7 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            ✕
          </span>
        );
      case 'priority_changed':
        return (
          <span className="w-7 h-7 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            ▲
          </span>
        );
      case 'commented':
        return (
          <span className="w-7 h-7 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            💬
          </span>
        );
      default:
        return (
          <span className="w-7 h-7 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs font-bold ring-4 ring-white">
            •
          </span>
        );
    }
  };

  const formatEventText = (event: RequestEvent) => {
    const actor = event.actor_name || `User #${event.actor_id}`;

    switch (event.type.toLowerCase()) {
      case 'created':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> created this request
          </span>
        );
      case 'status_changed':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> changed status from{' '}
            <span className="font-medium text-gray-800">
              {String(event.from_value || 'None').replace(/_/g, ' ')}
            </span>{' '}
            to{' '}
            <span className="font-semibold text-indigo-700">
              {String(event.to_value || 'None').replace(/_/g, ' ')}
            </span>
          </span>
        );
      case 'owner_changed':
      case 'claimed':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong>{' '}
            {event.to_value ? (
              <>claimed ownership</>
            ) : (
              <>unassigned ownership</>
            )}
          </span>
        );
      case 'assigned':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> assigned this request to{' '}
            <strong className="text-gray-800">{String(event.to_value)}</strong>
          </span>
        );
      case 'approved':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> approved this transition
          </span>
        );
      case 'rejected':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> rejected this transition
          </span>
        );
      case 'priority_changed':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> changed priority from{' '}
            <span className="font-medium text-gray-700">{String(event.from_value)}</span> to{' '}
            <span className="font-semibold text-gray-900">{String(event.to_value)}</span>
          </span>
        );
      case 'commented':
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> added a comment
          </span>
        );
      default:
        return (
          <span>
            <strong className="text-gray-900 font-semibold">{actor}</strong> updated {event.type}
          </span>
        );
    }
  };

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {sortedEvents.map((event, index) => {
          const isLast = index === sortedEvents.length - 1;
          let timeAgo = '';
          let fullDate = '';
          try {
            timeAgo = formatDistanceToNow(new Date(event.created_at), { addSuffix: true });
            fullDate = format(new Date(event.created_at), 'MMM d, yyyy h:mm a');
          } catch {
            timeAgo = event.created_at;
          }

          return (
            <li key={event.id || index}>
              <div className="relative pb-8">
                {!isLast && (
                  <span
                    className="absolute top-4 left-3.5 -ml-px h-full w-0.5 bg-gray-200"
                    aria-hidden="true"
                  />
                )}
                <div className="relative flex items-start space-x-3">
                  <div className="shrink-0">{getEventIcon(event.type)}</div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="text-xs sm:text-sm text-gray-700">
                      {formatEventText(event)}
                    </div>

                    {event.reason && (
                      <div className="mt-1.5 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-900">
                        <span className="font-semibold">Reason:</span> {event.reason}
                      </div>
                    )}

                    <div className="mt-1 text-[11px] text-gray-400" title={fullDate}>
                      {timeAgo} &bull; {fullDate}
                    </div>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default Timeline;
