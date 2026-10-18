import React, { useState } from 'react';
import { Request } from '../types';
import { useAuth } from '../hooks/useAuth';
import { useClaim } from '../hooks/useClaim';
import { useTransition } from '../hooks/useTransition';
import { assignRequest } from '../api/requests';
import TransitionModal from './TransitionModal';
import AssignModal from './AssignModal';
import LoadingSpinner from './LoadingSpinner';

interface ActionButtonsProps {
  request: Request;
  onRefresh?: () => void;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({ request, onRefresh }) => {
  const { user, isLead, hasRoleInTeam } = useAuth();
  const { mutateAsync: claimMutate, isPending: isClaiming, claimError, clearError: clearClaimError } = useClaim();
  const { mutateAsync: transitionMutate, isPending: isTransitioning } = useTransition();

  const [activeModal, setActiveModal] = useState<{
    type: 'transition' | 'assign' | null;
    targetStatus?: string;
    actionLabel?: string;
    requiresReason?: boolean;
  }>({ type: null });

  const [assignLoading, setAssignLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const allowedActions = request.allowed_actions || [];

  // Can user claim: if allowed_actions includes 'claim' or if owner is null and user is in team
  const canClaim =
    allowedActions.includes('claim') ||
    (!request.owner_id && hasRoleInTeam(request.team_id, ['member', 'approver', 'lead']));

  const isUserLead = isLead || hasRoleInTeam(request.team_id, ['lead']);

  const handleClaim = async () => {
    if (!user) return;
    setGeneralError(null);
    clearClaimError();
    try {
      await claimMutate({ requestId: request.id, user });
      onRefresh?.();
    } catch (err: any) {
      setGeneralError(err?.response?.data?.message || 'Failed to claim request.');
    }
  };

  const handleOpenTransitionModal = (
    targetStatus: string,
    actionLabel: string,
    requiresReason: boolean
  ) => {
    setActiveModal({
      type: 'transition',
      targetStatus,
      actionLabel,
      requiresReason,
    });
  };

  const handleConfirmTransition = async (reason?: string) => {
    if (!activeModal.targetStatus) return;
    setGeneralError(null);
    try {
      await transitionMutate({
        requestId: request.id,
        to: activeModal.targetStatus,
        version: request.version,
        reason,
      });
      setActiveModal({ type: null });
      onRefresh?.();
    } catch (err: any) {
      setGeneralError(err?.response?.data?.message || 'Failed to complete transition.');
    }
  };

  const handleReassign = async (userId: string | number, reason: string) => {
    setAssignLoading(true);
    setGeneralError(null);
    try {
      await assignRequest(request.id, userId, request.version, reason);
      setActiveModal({ type: null });
      onRefresh?.();
    } finally {
      setAssignLoading(false);
    }
  };

  const isProcessing = isClaiming || isTransitioning || assignLoading;

  return (
    <div className="space-y-3">
      {/* Error Banners */}
      {(claimError || generalError) && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-800 text-xs flex items-start justify-between">
          <span>{claimError?.message || generalError}</span>
          <button
            onClick={() => {
              clearClaimError();
              setGeneralError(null);
            }}
            className="text-red-500 hover:text-red-700 font-bold ml-2"
          >
            &times;
          </button>
        </div>
      )}

      {/* Action Buttons Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Claim button */}
        {canClaim && (
          <button
            type="button"
            onClick={handleClaim}
            disabled={isProcessing}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            {isClaiming ? (
              <LoadingSpinner size="sm" className="text-white" />
            ) : (
              <span>Take Ownership (Claim)</span>
            )}
          </button>
        )}

        {/* Lead Reassign button */}
        {isUserLead && request.status !== 'done' && request.status !== 'cancelled' && (
          <button
            type="button"
            onClick={() => setActiveModal({ type: 'assign' })}
            disabled={isProcessing}
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            <span>Assign Owner</span>
          </button>
        )}

        {/* Dynamic Transition Actions */}
        {/* Triage transition */}
        {(allowedActions.includes('triage') || request.status === 'new') && (
          <button
            type="button"
            onClick={() => handleOpenTransitionModal('triage', 'Move to Triage', false)}
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            Start Triage
          </button>
        )}

        {/* Submit for Start Approval */}
        {(allowedActions.includes('submit_start_approval') ||
          allowedActions.includes('awaiting_start_approval')) && (
          <button
            type="button"
            onClick={() =>
              handleOpenTransitionModal(
                'awaiting_start_approval',
                'Submit for Start Approval',
                false
              )
            }
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            Submit for Start Approval
          </button>
        )}

        {/* Start Work / In Progress */}
        {(allowedActions.includes('start') || allowedActions.includes('in_progress')) && (
          <button
            type="button"
            onClick={() =>
              handleOpenTransitionModal('in_progress', 'Start Working (In Progress)', false)
            }
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            Start Working
          </button>
        )}

        {/* Approvals (Approve / Reject) */}
        {(allowedActions.includes('approve') ||
          request.status === 'awaiting_start_approval' ||
          request.status === 'awaiting_completion_approval') && (
          <>
            <button
              type="button"
              onClick={() => {
                const target =
                  request.status === 'awaiting_start_approval' ? 'in_progress' : 'done';
                handleOpenTransitionModal(target, 'Approve', false);
              }}
              disabled={isProcessing}
              className="inline-flex items-center px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
            >
              Approve
            </button>

            <button
              type="button"
              onClick={() => {
                const target =
                  request.status === 'awaiting_start_approval' ? 'triage' : 'in_progress';
                handleOpenTransitionModal(target, 'Reject with Reason', true);
              }}
              disabled={isProcessing}
              className="inline-flex items-center px-3 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
            >
              Reject
            </button>
          </>
        )}

        {/* Submit for Completion Approval */}
        {(allowedActions.includes('submit_completion_approval') ||
          (request.status === 'in_progress' && allowedActions.includes('awaiting_completion_approval'))) && (
          <button
            type="button"
            onClick={() =>
              handleOpenTransitionModal(
                'awaiting_completion_approval',
                'Submit for Completion Approval',
                false
              )
            }
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            Submit for Completion Approval
          </button>
        )}

        {/* Mark Done directly (when no completion approval needed) */}
        {(allowedActions.includes('done') ||
          (request.status === 'in_progress' && !allowedActions.includes('awaiting_completion_approval'))) && (
          <button
            type="button"
            onClick={() => handleOpenTransitionModal('done', 'Mark as Done', false)}
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            Mark Done
          </button>
        )}

        {/* Cancel request */}
        {request.status !== 'done' && request.status !== 'cancelled' && (
          <button
            type="button"
            onClick={() =>
              handleOpenTransitionModal('cancelled', 'Cancel Request', true)
            }
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 border border-red-300 text-red-700 hover:bg-red-50 text-xs font-medium rounded-md shadow-sm disabled:opacity-50 transition-colors"
          >
            Cancel Request
          </button>
        )}
      </div>

      {/* Transition Modal */}
      {activeModal.type === 'transition' && (
        <TransitionModal
          isOpen={true}
          targetStatus={activeModal.targetStatus || ''}
          actionLabel={activeModal.actionLabel || 'Confirm'}
          requiresReason={activeModal.requiresReason}
          isLoading={isTransitioning}
          onConfirm={handleConfirmTransition}
          onCancel={() => setActiveModal({ type: null })}
        />
      )}

      {/* Assign Modal */}
      {activeModal.type === 'assign' && (
        <AssignModal
          isOpen={true}
          teamId={request.team_id}
          currentOwnerId={request.owner_id}
          isLoading={assignLoading}
          onAssign={handleReassign}
          onClose={() => setActiveModal({ type: null })}
        />
      )}
    </div>
  );
};

export default ActionButtons;
