import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ApiError, RequestEvent } from '../types';

interface ConflictDialogProps {
  isOpen: boolean;
  error: ApiError | null;
  onReload: () => void;
  onClose: () => void;
}

export const ConflictDialog: React.FC<ConflictDialogProps> = ({
  isOpen,
  error,
  onReload,
  onClose,
}) => {
  if (!isOpen) return null;

  const eventsSince: RequestEvent[] = error?.events_since || [];
  const currentState = error?.current_state;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full overflow-hidden border border-amber-300 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-amber-50 px-6 py-4 border-b border-amber-200 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-bold text-amber-900">
              State Conflict Detected (409)
            </h3>
            <p className="text-xs text-amber-700">
              This request was modified by another user since you loaded it.
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="text-sm text-gray-700">
            <p className="mb-2">
              {error?.message ||
                'Another team member updated this record. To prevent overwriting their work, your change was paused.'}
            </p>

            {currentState && (
              <div className="p-3 bg-gray-50 rounded-md border border-gray-200 text-xs space-y-1">
                <div className="font-semibold text-gray-800">Current Server State:</div>
                <div>
                  <span className="text-gray-500">Status:</span>{' '}
                  <span className="font-medium text-gray-900">{currentState.status}</span>
                </div>
                <div>
                  <span className="text-gray-500">Owner:</span>{' '}
                  <span className="font-medium text-gray-900">
                    {currentState.owner_name || 'Unowned'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Version:</span>{' '}
                  <span className="font-mono font-medium text-gray-900">
                    v{currentState.version}
                  </span>
                </div>
              </div>
            )}
          </div>

          {eventsSince.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Changes made in the interim ({eventsSince.length}):
              </h4>
              <div className="max-h-44 overflow-y-auto space-y-2 border border-gray-200 rounded p-2 bg-gray-50">
                {eventsSince.map((evt, idx) => {
                  let timeAgo = '';
                  try {
                    timeAgo = formatDistanceToNow(new Date(evt.created_at), { addSuffix: true });
                  } catch {
                    timeAgo = evt.created_at;
                  }

                  return (
                    <div
                      key={evt.id || idx}
                      className="text-xs bg-white p-2 rounded border border-gray-100 shadow-2xs"
                    >
                      <div className="flex items-center justify-between text-gray-500 text-[10px] mb-1">
                        <span className="font-semibold text-gray-700">
                          {evt.actor_name || `User #${evt.actor_id}`}
                        </span>
                        <span>{timeAgo}</span>
                      </div>
                      <div className="text-gray-800">
                        Type: <span className="font-mono text-indigo-600">{evt.type}</span>
                        {evt.reason && (
                          <div className="text-gray-600 italic mt-0.5">
                            Reason: "{evt.reason}"
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            Dismiss
          </button>
          <button
            type="button"
            onClick={() => {
              onReload();
              onClose();
            }}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            Reload Latest State
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConflictDialog;
