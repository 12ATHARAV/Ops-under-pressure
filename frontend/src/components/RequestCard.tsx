import React from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow, isPast } from 'date-fns';
import { Request } from '../types';
import StatusBadge from './StatusBadge';
import PriorityBadge from './PriorityBadge';

interface RequestCardProps {
  request: Request;
}

export const RequestCard: React.FC<RequestCardProps> = ({ request }) => {
  const navigate = useNavigate();

  let timeAgo = '';
  try {
    timeAgo = formatDistanceToNow(new Date(request.last_activity_at), { addSuffix: true });
  } catch {
    timeAgo = request.last_activity_at;
  }

  const isOverdue =
    request.due_at &&
    request.status !== 'done' &&
    request.status !== 'cancelled' &&
    isPast(new Date(request.due_at));

  return (
    <div
      onClick={() => navigate(`/requests/${request.id}`)}
      className="bg-white border border-gray-200 hover:border-indigo-400 hover:shadow-md rounded-lg p-4 transition-all duration-150 cursor-pointer flex flex-col justify-between group"
    >
      <div>
        {/* Header row with badges and ID */}
        <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-medium text-gray-400">
              #{request.id}
            </span>
            <StatusBadge status={request.status} size="sm" />
            <PriorityBadge priority={request.priority} size="sm" />
          </div>

          <div className="text-xs text-gray-500 font-medium">
            {request.team_name || `Team ${request.team_id}`}
          </div>
        </div>

        {/* Title */}
        <h3 className="text-sm sm:text-base font-semibold text-gray-900 group-hover:text-indigo-600 line-clamp-1 mb-1 transition-colors">
          {request.title}
        </h3>

        {/* Description snippet */}
        {request.description && (
          <p className="text-xs text-gray-500 line-clamp-2 mb-3">
            {request.description}
          </p>
        )}
      </div>

      {/* Footer metadata */}
      <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          {request.owner_name ? (
            <div className="flex items-center gap-1.5 font-medium text-gray-700">
              <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">
                {request.owner_name.charAt(0).toUpperCase()}
              </span>
              <span>{request.owner_name}</span>
            </div>
          ) : (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
              Unowned
            </span>
          )}

          {request.type_name && (
            <span className="hidden sm:inline text-gray-400 font-normal">
              &bull; {request.type_name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {isOverdue && (
            <span className="text-red-600 font-semibold text-[11px] flex items-center gap-1">
              <span>⚠</span> Overdue
            </span>
          )}
          <span className="text-gray-400 text-[11px]">Active {timeAgo}</span>
        </div>
      </div>
    </div>
  );
};

export default RequestCard;
