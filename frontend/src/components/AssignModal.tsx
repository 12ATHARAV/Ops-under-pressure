import React, { useState, useEffect } from 'react';
import { User } from '../types';
import { fetchTeamMembers } from '../api/requests';
import LoadingSpinner from './LoadingSpinner';

interface AssignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAssign: (userId: string | number, reason: string) => Promise<void>;
  teamId: string | number;
  currentOwnerId?: string | number | null;
  isLoading?: boolean;
}

export const AssignModal: React.FC<AssignModalProps> = ({
  isOpen,
  onClose,
  onAssign,
  teamId,
  currentOwnerId,
  isLoading = false,
}) => {
  const [members, setMembers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [fetchingMembers, setFetchingMembers] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && teamId) {
      setFetchingMembers(true);
      fetchTeamMembers(teamId)
        .then((data) => {
          setMembers(data || []);
          if (data && data.length > 0) {
            setSelectedUserId(String(data[0].id));
          }
        })
        .catch((err) => {
          console.error('Failed to fetch team members:', err);
          setError('Could not load team members.');
        })
        .finally(() => setFetchingMembers(false));
    }
  }, [isOpen, teamId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      setError('Please select a member to assign.');
      return;
    }
    if (!reason.trim()) {
      setError('A reason for reassignment is required.');
      return;
    }

    try {
      await onAssign(selectedUserId, reason.trim());
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to reassign request.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full overflow-hidden border border-gray-200">
        <form onSubmit={handleSubmit}>
          <div className="p-6">
            <h3 className="text-base font-bold text-gray-900 mb-2">
              Reassign Request
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              As a team lead, assign this operational request to a member of the team.
            </p>

            {error && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 text-xs rounded">
                {error}
              </div>
            )}

            {fetchingMembers ? (
              <div className="py-6 flex justify-center">
                <LoadingSpinner size="md" label="Loading team members..." />
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    Select Assignee <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={selectedUserId}
                    onChange={(e) => setSelectedUserId(e.target.value)}
                    className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  >
                    <option value="">-- Choose Member --</option>
                    {members.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.email})
                        {String(m.id) === String(currentOwnerId) ? ' [Current Owner]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    Reason for Assignment <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Workload rebalancing, specialist handover, or triage..."
                    className="w-full p-2.5 text-xs sm:text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || fetchingMembers}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center gap-1.5"
            >
              {isLoading ? <LoadingSpinner size="sm" className="text-white" /> : 'Reassign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AssignModal;
