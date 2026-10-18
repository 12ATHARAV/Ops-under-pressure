import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { RequestFilters, Team, Request } from '../types';
import { fetchTeams } from '../api/requests';
import { useRequests } from '../hooks/useRequests';
import FilterBar from '../components/FilterBar';
import RequestCard from '../components/RequestCard';
import Pagination from '../components/Pagination';
import CreateRequestModal from '../components/CreateRequestModal';
import LoadingSpinner from '../components/LoadingSpinner';

export const WorkListPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<RequestFilters>({});
  const [teams, setTeams] = useState<Team[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Load teams for filtering
  useEffect(() => {
    fetchTeams()
      .then((data) => setTeams(data || []))
      .catch((err) => console.error('Failed to load teams:', err));
  }, []);

  const {
    requests,
    isLoading,
    isError,
    error,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    refetch,
    isRefetching,
  } = useRequests(filters);

  const handleCreateSuccess = (_newRequest: Request) => {
    queryClient.invalidateQueries({ queryKey: ['requests'] });
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight">
            Work List
          </h1>
          <p className="text-xs sm:text-sm text-gray-500">
            Active operational requests across all assigned teams
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-2 border border-gray-300 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 text-xs font-medium transition-colors"
            title="Refresh list"
          >
            <svg
              className={`w-4 h-4 ${isRefetching ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>

          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold rounded-md shadow-sm transition-colors"
          >
            <span>+</span>
            <span>Create Request</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onFilterChange={setFilters}
        teams={teams}
      />

      {/* Request List Content */}
      {isLoading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" label="Loading operational requests..." />
        </div>
      ) : isError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center text-red-700">
          <p className="font-semibold text-sm mb-1">Failed to load requests</p>
          <p className="text-xs mb-3">{error?.message || 'Server error occurred'}</p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center shadow-2xs">
          <div className="w-12 h-12 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center mx-auto mb-3">
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-gray-900 mb-1">No requests found</h3>
          <p className="text-xs text-gray-500 max-w-sm mx-auto mb-4">
            {Object.keys(filters).length > 0
              ? 'Try modifying or clearing your filters to see more results.'
              : 'There are no active requests in your team workspace.'}
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm transition-colors"
          >
            Create First Request
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {requests.map((req) => (
              <RequestCard key={req.id} request={req} />
            ))}
          </div>

          <Pagination
            hasNextPage={!!hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            onLoadMore={() => fetchNextPage()}
            loadedCount={requests.length}
          />
        </div>
      )}

      {/* Create Request Modal */}
      <CreateRequestModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
};

export default WorkListPage;
