import React, { useState } from 'react';
import LoadingSpinner from './LoadingSpinner';

interface TransitionModalProps {
  isOpen: boolean;
  targetStatus: string;
  actionLabel: string;
  requiresReason?: boolean;
  isLoading?: boolean;
  onConfirm: (reason?: string) => void;
  onCancel: () => void;
}

export const TransitionModal: React.FC<TransitionModalProps> = ({
  isOpen,
  targetStatus,
  actionLabel,
  requiresReason = false,
  isLoading = false,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (requiresReason && !reason.trim()) {
      setError('A reason is mandatory for this transition.');
      return;
    }
    setError(null);
    onConfirm(reason.trim() || undefined);
  };

  const isDestructive =
    targetStatus === 'cancelled' ||
    actionLabel.toLowerCase().includes('reject') ||
    actionLabel.toLowerCase().includes('cancel');

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full overflow-hidden border border-gray-200">
        <form onSubmit={handleSubmit}>
          <div className="p-6">
            <h3 className="text-base font-bold text-gray-900 mb-2">
              Confirm Action: {actionLabel}
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Transitioning request state to{' '}
              <span className="font-semibold text-gray-800">
                {targetStatus.replace(/_/g, ' ')}
              </span>
              .
            </p>

            {error && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 text-xs rounded">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Reason {requiresReason ? <span className="text-red-500">*</span> : <span className="text-gray-400 font-normal">(optional)</span>}
              </label>
              <textarea
                rows={3}
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  if (error) setError(null);
                }}
                placeholder={
                  requiresReason
                    ? 'Explain the decision or justification...'
                    : 'Add any context for this state transition...'
                }
                className="w-full p-2.5 text-xs sm:text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className={`px-4 py-2 text-xs font-semibold rounded-md shadow-sm text-white flex items-center gap-1.5 transition-colors ${
                isDestructive
                  ? 'bg-rose-600 hover:bg-rose-700'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {isLoading ? (
                <LoadingSpinner size="sm" className="text-white" />
              ) : (
                actionLabel
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TransitionModal;
