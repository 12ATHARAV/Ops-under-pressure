import React, { useState, useEffect } from 'react';
import { RequestFilters, Team, RequestStatus, RequestPriority } from '../types';

interface FilterBarProps {
  filters: RequestFilters;
  onFilterChange: (newFilters: RequestFilters) => void;
  teams?: Team[];
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  teams = [],
}) => {
  const [searchTerm, setSearchTerm] = useState(filters.q || '');

  // Debounce search input by 300ms
  useEffect(() => {
    const handler = setTimeout(() => {
      if ((filters.q || '') !== searchTerm) {
        onFilterChange({
          ...filters,
          q: searchTerm || undefined,
        });
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [searchTerm, filters, onFilterChange]);

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onFilterChange({
      ...filters,
      status: val ? (val as RequestStatus) : undefined,
    });
  };

  const handlePriorityChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onFilterChange({
      ...filters,
      priority: val ? (val as RequestPriority) : undefined,
    });
  };

  const handleOwnerChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onFilterChange({
      ...filters,
      owner: val ? (val as 'me' | 'none') : undefined,
    });
  };

  const handleTeamChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onFilterChange({
      ...filters,
      team: val || undefined,
    });
  };

  const handleQuickFilterMyWork = () => {
    onFilterChange({
      ...filters,
      owner: filters.owner === 'me' ? undefined : 'me',
    });
  };

  const handleQuickFilterUnowned = () => {
    onFilterChange({
      ...filters,
      owner: filters.owner === 'none' ? undefined : 'none',
    });
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    onFilterChange({});
  };

  const hasActiveFilters = Boolean(
    filters.q ||
      filters.status ||
      filters.priority ||
      filters.owner ||
      filters.team
  );

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm mb-6 space-y-3">
      {/* Search and Quick Filters Row */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search title, description, or ID..."
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              &times;
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleQuickFilterMyWork}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md border transition-colors ${
              filters.owner === 'me'
                ? 'bg-indigo-600 border-indigo-600 text-white'
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            My Work
          </button>

          <button
            type="button"
            onClick={handleQuickFilterUnowned}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md border transition-colors ${
              filters.owner === 'none'
                ? 'bg-indigo-600 border-indigo-600 text-white'
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            Unowned
          </button>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Dropdown Filters Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-gray-100">
        <div>
          <label className="block text-[11px] font-medium text-gray-500 mb-1">
            Status
          </label>
          <select
            value={filters.status || ''}
            onChange={handleStatusChange}
            className="w-full py-1.5 px-2 text-xs border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="triage">Triage</option>
            <option value="awaiting_start_approval">Awaiting Start Approval</option>
            <option value="in_progress">In Progress</option>
            <option value="awaiting_completion_approval">Awaiting Completion</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-medium text-gray-500 mb-1">
            Priority
          </label>
          <select
            value={filters.priority || ''}
            onChange={handlePriorityChange}
            className="w-full py-1.5 px-2 text-xs border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-medium text-gray-500 mb-1">
            Owner
          </label>
          <select
            value={filters.owner || ''}
            onChange={handleOwnerChange}
            className="w-full py-1.5 px-2 text-xs border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Owners</option>
            <option value="me">Assigned to Me</option>
            <option value="none">Unowned (Inbox)</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-medium text-gray-500 mb-1">
            Team
          </label>
          <select
            value={filters.team || ''}
            onChange={handleTeamChange}
            className="w-full py-1.5 px-2 text-xs border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Teams</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

export default FilterBar;
