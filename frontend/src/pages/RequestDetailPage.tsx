import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import { RequestPriority } from '../types';
import { useRequest } from '../hooks/useRequest';
import { useAuth } from '../hooks/useAuth';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import ActionButtons from '../components/ActionButtons';
import Timeline from '../components/Timeline';
import CommentSection from '../components/CommentSection';
import ConflictDialog from '../components/ConflictDialog';
import LoadingSpinner from '../components/LoadingSpinner';

export const RequestDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const requestId = id || '';
  const { user, isLead, hasRoleInTeam } = useAuth();

  const {
    request,
    isLoading,
    isError,
    error,
    events,
    isLoadingEvents,
    refetch,
    editMutation,
    editError,
  } = useRequest(requestId);

  // Form edit state
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editPriority, setEditPriority] = useState<RequestPriority>('medium');
  const [editDueAt, setEditDueAt] = useState('');

  // Conflict state
  const [showConflictDialog, setShowConflictDialog] = useState(false);

  // Populate edit fields when request is loaded
  useEffect(() => {
    if (request) {
      setEditTitle(request.title);
      setEditDescription(request.description || '');
      setEditPriority(request.priority);
      setEditDueAt(request.due_at ? request.due_at.substring(0, 16) : '');
    }
  }, [request]);

  // Check 409 from edit
  useEffect(() => {
    if (editError && (editError.code === '409' || editError.current_state)) {
      setShowConflictDialog(true);
    }
  }, [editError]);

  if (isLoading) {
    return (
      <div className="py-28 flex justify-center">
        <LoadingSpinner size="lg" label="Loading request details..." />
      </div>
    );
  }

  if (isError || !request) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-12 text-center max-w-lg mx-auto shadow-sm">
        <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-3">
          ✕
        </div>
        <h2 className="text-base font-bold text-gray-900 mb-1">
          Request Not Found or Inaccessible
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          {error?.message ||
            'You might not have membership permissions in the team for this request.'}
        </p>
        <Link
          to="/requests"
          className="inline-flex px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded hover:bg-indigo-700 transition-colors"
        >
          &larr; Back to Work List
        </Link>
      </div>
    );
  }

  const canEdit =
    request.status !== 'done' &&
    request.status !== 'cancelled' &&
    (isLead ||
      hasRoleInTeam(request.team_id, ['lead']) ||
      (request.owner_id && String(request.owner_id) === String(user?.id)));

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await editMutation.mutateAsync({
        data: {
          title: editTitle.trim(),
          description: editDescription.trim(),
          priority: editPriority,
          due_at: editDueAt ? new Date(editDueAt).toISOString() : null,
        },
        version: request.version,
      });
      setIsEditing(false);
    } catch {
      // Handled by editError effect
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditTitle(request.title);
    setEditDescription(request.description || '');
    setEditPriority(request.priority);
    setEditDueAt(request.due_at ? request.due_at.substring(0, 16) : '');
  };

  let createdFormatted = '';
  let updatedFormatted = '';
  try {
    createdFormatted = format(new Date(request.created_at), 'PPP p');
    updatedFormatted = formatDistanceToNow(new Date(request.last_activity_at), {
      addSuffix: true,
    });
  } catch {
    createdFormatted = request.created_at;
    updatedFormatted = request.last_activity_at;
  }

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to="/requests"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
        >
          &larr; Back to Work List
        </Link>

        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
            Version: v{request.version}
          </span>
          <button
            onClick={() => refetch()}
            className="text-xs text-gray-500 hover:text-gray-800 p-1 rounded hover:bg-gray-100 transition-colors"
            title="Refresh"
          >
            ↻ Reload
          </button>
        </div>
      </div>

      {/* Main Request Header & Actions */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-2 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-gray-400 font-bold">
                #{request.id}
              </span>
              <StatusBadge status={request.status} />
              <PriorityBadge priority={request.priority} />
              <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2.5 py-0.5 rounded-full">
                {request.team_name || `Team ${request.team_id}`}
              </span>
              {request.type_name && (
                <span className="text-xs font-medium text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                  {request.type_name}
                </span>
              )}
            </div>

            {!isEditing ? (
              <div>
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight">
                  {request.title}
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  Created by{' '}
                  <strong className="text-gray-600">
                    {request.created_by_name || `User #${request.created_by}`}
                  </strong>{' '}
                  on {createdFormatted} &bull; Active {updatedFormatted}
                </p>
              </div>
            ) : null}
          </div>

          {canEdit && !isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="self-start px-3 py-1.5 border border-gray-300 text-xs font-medium text-gray-700 rounded hover:bg-gray-50 transition-colors"
            >
              Edit Details
            </button>
          )}
        </div>

        {/* Edit Form or Read-only description */}
        {isEditing ? (
          <form
            onSubmit={handleSaveEdit}
            className="p-4 bg-gray-50 border border-indigo-100 rounded-lg space-y-4"
          >
            <div className="flex items-center justify-between pb-2 border-b border-gray-200">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Editing Request # {request.id} (Optimistic Locking: v{request.version})
              </h3>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Title
              </label>
              <input
                type="text"
                required
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full p-2 text-sm border border-gray-300 rounded bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Priority
                </label>
                <select
                  value={editPriority}
                  onChange={(e) => setEditPriority(e.target.value as RequestPriority)}
                  className="w-full p-2 text-sm border border-gray-300 rounded bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Due Date
                </label>
                <input
                  type="datetime-local"
                  value={editDueAt}
                  onChange={(e) => setEditDueAt(e.target.value)}
                  className="w-full p-2 text-sm border border-gray-300 rounded bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Description
              </label>
              <textarea
                rows={4}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="w-full p-2 text-sm border border-gray-300 rounded bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleCancelEdit}
                disabled={editMutation.isPending}
                className="px-3 py-1.5 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={editMutation.isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded shadow-sm flex items-center gap-1.5"
              >
                {editMutation.isPending ? (
                  <LoadingSpinner size="sm" className="text-white" label="Saving..." />
                ) : (
                  'Save Changes'
                )}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">
                Description
              </h4>
              <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                {request.description || <span className="italic text-gray-400">No description provided.</span>}
              </p>
            </div>

            {/* Meta summary card */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-3 bg-gray-50 rounded-lg border border-gray-100 text-xs">
              <div>
                <span className="text-gray-400 block text-[11px]">Assigned Owner</span>
                <span className="font-semibold text-gray-800">
                  {request.owner_name || <span className="text-amber-600">Unowned</span>}
                </span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Due Date</span>
                <span className="font-semibold text-gray-800">
                  {request.due_at ? format(new Date(request.due_at), 'MMM d, yyyy') : 'No SLA'}
                </span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Last Activity</span>
                <span className="font-semibold text-gray-800">{updatedFormatted}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Allowed Actions</span>
                <span className="font-semibold text-gray-800">
                  {request.allowed_actions && request.allowed_actions.length > 0
                    ? request.allowed_actions.join(', ')
                    : 'None available'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Operational Action Buttons */}
        <div className="pt-4 border-t border-gray-200">
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            Available Operations
          </h4>
          <ActionButtons request={request} onRefresh={() => refetch()} />
        </div>
      </div>

      {/* Grid: Timeline and Comments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Timeline (RequestEvents) */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
              "Why?" Timeline & Audit History
            </h3>
            <span className="text-xs text-gray-400 font-medium">
              {events.length} event{events.length === 1 ? '' : 's'}
            </span>
          </div>

          <Timeline events={events} isLoading={isLoadingEvents} />
        </div>

        {/* Discussion & Comments */}
        <CommentSection requestId={request.id} events={events} />
      </div>

      {/* Conflict Dialog */}
      <ConflictDialog
        isOpen={showConflictDialog}
        error={editError}
        onReload={() => {
          refetch();
          setShowConflictDialog(false);
        }}
        onClose={() => setShowConflictDialog(false)}
      />
    </div>
  );
};

export default RequestDetailPage;
