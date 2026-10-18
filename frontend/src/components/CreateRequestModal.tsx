import React, { useState, useEffect } from 'react';
import { RequestPriority, Team, RequestType, Request } from '../types';
import { createRequest, fetchTeams, fetchRequestTypes } from '../api/requests';
import { generateIdempotencyKey, parseApiError } from '../api/client';
import LoadingSpinner from './LoadingSpinner';

interface CreateRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (request: Request) => void;
  initialTeamId?: string | number;
}

export const CreateRequestModal: React.FC<CreateRequestModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialTeamId,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [teamId, setTeamId] = useState<string>(initialTeamId ? String(initialTeamId) : '');
  const [typeId, setTypeId] = useState<string>('');
  const [priority, setPriority] = useState<RequestPriority>('medium');
  const [dueAt, setDueAt] = useState<string>('');

  const [teams, setTeams] = useState<Team[]>([]);
  const [allTypes, setAllTypes] = useState<RequestType[]>([]);
  const [filteredTypes, setFilteredTypes] = useState<RequestType[]>([]);

  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load teams and request types on modal open
  useEffect(() => {
    if (isOpen) {
      setIsLoadingMetadata(true);
      Promise.all([fetchTeams(), fetchRequestTypes()])
        .then(([teamsData, typesData]) => {
          setTeams(teamsData || []);
          setAllTypes(typesData || []);

          const defaultTeam = initialTeamId ? String(initialTeamId) : teamsData?.[0]?.id ? String(teamsData[0].id) : '';
          setTeamId(defaultTeam);
        })
        .catch((err) => {
          console.error('Failed to load teams/types:', err);
          setError('Could not load teams or request categories.');
        })
        .finally(() => setIsLoadingMetadata(false));
    }
  }, [isOpen, initialTeamId]);

  // Filter types when selected team changes
  useEffect(() => {
    if (teamId) {
      const matching = allTypes.filter((t) => String(t.team_id) === String(teamId));
      setFilteredTypes(matching);
      if (matching.length > 0) {
        setTypeId(String(matching[0].id));
      } else {
        setTypeId('');
      }
    } else {
      setFilteredTypes([]);
      setTypeId('');
    }
  }, [teamId, allTypes]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required.');
      return;
    }
    if (!teamId) {
      setError('Please select a team.');
      return;
    }
    if (!typeId) {
      setError('Please select a request type.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const idempotencyKey = generateIdempotencyKey();
      const newRequest = await createRequest(
        {
          team_id: teamId,
          type_id: typeId,
          title: title.trim(),
          description: description.trim(),
          priority,
          due_at: dueAt ? new Date(dueAt).toISOString() : null,
        },
        idempotencyKey
      );

      // Reset form
      setTitle('');
      setDescription('');
      setPriority('medium');
      setDueAt('');
      onSuccess(newRequest);
      onClose();
    } catch (err) {
      const parsed = parseApiError(err);
      setError(parsed.message || 'Failed to create request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full overflow-hidden border border-gray-200">
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100">
              <h3 className="text-base font-bold text-gray-900">
                Create Operational Request
              </h3>
              <button
                type="button"
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            {error && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded">
                {error}
              </div>
            )}

            {isLoadingMetadata ? (
              <div className="py-8 flex justify-center">
                <LoadingSpinner size="md" label="Loading configuration..." />
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Brief description of the operational task or incident"
                    className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">
                      Target Team <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={teamId}
                      onChange={(e) => setTeamId(e.target.value)}
                      className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">-- Select Team --</option>
                      {teams.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">
                      Request Type <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={typeId}
                      onChange={(e) => setTypeId(e.target.value)}
                      disabled={filteredTypes.length === 0}
                      className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
                    >
                      <option value="">-- Select Type --</option>
                      {filteredTypes.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name} (Approval: {t.approval_mode})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">
                      Priority <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={priority}
                      onChange={(e) => setPriority(e.target.value as RequestPriority)}
                      className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="low">Low (Routine)</option>
                      <option value="medium">Medium (Standard)</option>
                      <option value="high">High (Urgent operational attention)</option>
                      <option value="urgent">Urgent (Critical blocker / incident)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">
                      Target Due Date (Optional)
                    </label>
                    <input
                      type="datetime-local"
                      value={dueAt}
                      onChange={(e) => setDueAt(e.target.value)}
                      className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                    </input>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    Description & Context
                  </label>
                  <textarea
                    rows={4}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Provide full context, reproduction steps, required outcomes, or relevant links..."
                    className="w-full p-2 text-xs sm:text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </>
            )}
          </div>

          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || isLoadingMetadata}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <LoadingSpinner size="sm" className="text-white" label="Submitting..." />
              ) : (
                'Create Request'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateRequestModal;
