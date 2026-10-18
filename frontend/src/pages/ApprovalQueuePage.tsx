import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Request } from '../types';
import { useApprovals } from '../hooks/useApprovals';
import { useTransition } from '../hooks/useTransition';
import { useAuth } from '../hooks/useAuth';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import TransitionModal from '../components/TransitionModal';
import LoadingSpinner from '../components/LoadingSpinner';

export const ApprovalQueuePage: React.FC = () => {
  const { user } = useAuth();
  const { requests, isLoading, isError, error, refetch, isRefetching } = useApprovals();
  const { mutateAsync: transitionMutate, isPending: isTransitioning } = useTransition();

  const [activeModal, setActiveModal] = useState<{
    request: Request | null;
    targetStatus: string;
    actionLabel: string;
    requiresReason: boolean;
  }>({
    request: null,
    targetStatus: '',
    actionLabel: '',
    requiresReason: false,
  });

  const [actionError, setActionError] = useState<string | null>(null);

  const handleApprove = async (req: Request) => {
    // If awaiting start approval -> in_progress; if awaiting completion approval -> done
    const targetStatus =
      req.status === 'awaiting_start_approval' ? 'in_progress' : 'done';

    setActionError(null);
    try {
      await transitionMutate({
        requestId: req.id,
        to: targetStatus,
        version: req.version,
      });
      refetch();
    } catch (err: any) {
      setActionError(
        err?.response?.data?.message || 'Failed to approve request.'
      );
    }
  };

  const handleOpenRejectModal = (req: Request) => {
    const targetStatus =
      req.status === 'awaiting_start_approval' ? 'triage' : 'in_progress';

    setActiveModal({
      request: req,
      targetStatus,
      actionLabel: 'Reject Request',
      requiresReason: true,
    });
  };

  const handleConfirmReject = async (reason?: string) => {
    if (!activeModal.request) return;

    setActionError(null);
    try {
      await transitionMutate({
        requestId: activeModal.request.id,
        to: activeModal.targetStatus,
        version: activeModal.request.version,
        reason,
      });
      setActiveModal({ request: null, targetStatus: '', actionLabel: '', requiresReason: false });
      refetch();
    } catch (err: any) {
      setActionError(
        err?.response?.data?.message || 'Failed to reject request.'
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight">
            Approval Queue
          </h1>
          <p className="text-xs sm:text-sm text-gray-500">
            Operational items requiring formal reviewer sign-off before proceeding
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded-md text-xs font-medium text-gray-700 bg-white hover:bg-gray-50 self-start sm:self-auto transition-colors"
        >
          <span className={isRefetching ? 'animate-spin' : ''}>↻</span> Refresh
        </button>
      </div>

      {/* Separation of duties banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 flex items-center gap-2">
        <span className="font-bold text-blue-600">ℹ Rule:</span>
        <span>
          Separation of duties is enforced. You cannot approve start or completion of work you
          created or own.
        </span>
      </div>

      {actionError && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-md flex items-center justify-between">
          <span>{actionError}</span>
          <button
            onClick={() => setActionError(null)}
            className="text-red-500 hover:text-red-700 font-bold ml-2"
          >
            &times;
          </button>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" label="Loading approval queue..." />
        </div>
      ) : isError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center text-red-700">
          <p className="font-semibold text-sm mb-1">Failed to load approvals</p>
          <p className="text-xs mb-3">{error?.message || 'Server error occurred'}</p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center shadow-2xs">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-3">
            ✓
          </div>
          <h3 className="text-sm font-bold text-gray-900 mb-1">Queue is clear!</h3>
          <p className="text-xs text-gray-500 max-w-sm mx-auto">
            You have no pending operational approvals requiring your review at this time.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((req) => {
            const isMyWork = Boolean(
              (req.owner_id && String(req.owner_id) === String(user?.id)) ||
              (req.created_by && String(req.created_by) === String(user?.id))
            );

            let timeAgo = '';
            try {
              timeAgo = formatDistanceToNow(new Date(req.last_activity_at), { addSuffix: true });
            } catch {
              timeAgo = req.last_activity_at;
            }

            return (
              <div
                key={req.id}
                className="bg-white border border-gray-200 rounded-lg p-4 shadow-2xs flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-gray-300 transition-colors"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-medium text-gray-400">
                      #{req.id}
                    </span>
                    <StatusBadge status={req.status} size="sm" />
                    <PriorityBadge priority={req.priority} size="sm" />
                    <span className="text-xs text-gray-500 font-medium">
                      {req.team_name || `Team ${req.team_id}`}
                    </span>
                  </div>

                  <Link
                    to={`/requests/${req.id}`}
                    className="text-sm font-bold text-gray-900 hover:text-indigo-600 transition-colors block"
                  >
                    {req.title}
                  </Link>

                  <div className="text-xs text-gray-500 flex items-center gap-2 flex-wrap">
                    <span>
                      Owner: <strong>{req.owner_name || 'Unowned'}</strong>
                    </span>
                    <span>&bull;</span>
                    <span>Active {timeAgo}</span>
                    {isMyWork && (
                      <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-semibold border border-amber-200">
                        Your Work (Cannot Self-Approve)
                      </span>
                    )}
                  </div>
                </div>

                {/* Approve / Reject Action Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleOpenRejectModal(req)}
                    disabled={isTransitioning || isMyWork}
                    className="px-3 py-1.5 border border-red-300 text-red-700 hover:bg-red-50 text-xs font-semibold rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Reject...
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApprove(req)}
                    disabled={isTransitioning || isMyWork}
                    className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-md shadow-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Approve
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Reject Transition Modal */}
      {activeModal.request && (
        <TransitionModal
          isOpen={true}
          targetStatus={activeModal.targetStatus}
          actionLabel={activeModal.actionLabel}
          requiresReason={activeModal.requiresReason}
          isLoading={isTransitioning}
          onConfirm={handleConfirmReject}
          onCancel={() =>
            setActiveModal({
              request: null,
              targetStatus: '',
              actionLabel: '',
              requiresReason: false,
            })
          }
        />
      )}
    </div>
  );
};

export default ApprovalQueuePage;
