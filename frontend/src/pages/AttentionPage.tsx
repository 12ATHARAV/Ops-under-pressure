import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { useAttention } from '../hooks/useAttention';
import { useAuth } from '../hooks/useAuth';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const BUCKET_METADATA: Record<
  string,
  { label: string; description: string; badgeColor: string }
> = {
  unowned: {
    label: 'Unowned Work',
    description: 'Requests sitting in triage without an assigned owner',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
  },
  stale: {
    label: 'Stale Operations',
    description: 'Active items with no progress or activity in over 24 hours',
    badgeColor: 'bg-gray-100 text-gray-800 border-gray-200',
  },
  overdue: {
    label: 'Overdue Items',
    description: 'Requests that have surpassed their target SLA due date',
    badgeColor: 'bg-red-100 text-red-800 border-red-200',
  },
  stuck_in_approval: {
    label: 'Stuck in Approval',
    description: 'Items awaiting reviewer sign-off for over 8 hours',
    badgeColor: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  },
  urgent: {
    label: 'Urgent Priority',
    description: 'High-severity items requiring immediate lead oversight',
    badgeColor: 'bg-rose-100 text-rose-800 border-rose-200',
  },
};

export const AttentionPage: React.FC = () => {
  const { isLead } = useAuth();
  const navigate = useNavigate();
  const { buckets, isLoading, isError, error, refetch, isRefetching } = useAttention(isLead);

  const [selectedBucketName, setSelectedBucketName] = useState<string | null>(null);

  if (!isLead) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-12 text-center max-w-lg mx-auto shadow-sm">
        <div className="w-12 h-12 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto mb-3">
          🔒
        </div>
        <h2 className="text-base font-bold text-gray-900 mb-1">
          Lead Access Required
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          The 'Needs Attention' operations overview is reserved for team leads and managers.
        </p>
        <Link
          to="/requests"
          className="inline-flex px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded hover:bg-indigo-700 transition-colors"
        >
          &larr; Go to Work List
        </Link>
      </div>
    );
  }

  // Preselect first bucket if none selected
  const activeBucket =
    buckets.find((b) => b.name === selectedBucketName) || buckets[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight">
            Manager Attention Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-gray-500">
            Real-time operational triage for stuck, overdue, and high-risk items
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

      {isLoading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" label="Analyzing operational attention buckets..." />
        </div>
      ) : isError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center text-red-700">
          <p className="font-semibold text-sm mb-1">Failed to load attention metrics</p>
          <p className="text-xs mb-3">{error?.message || 'Server error occurred'}</p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Bucket Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {buckets.map((bucket) => {
              const meta = BUCKET_METADATA[bucket.name.toLowerCase()] || {
                label: bucket.name.replace(/_/g, ' '),
                description: '',
                badgeColor: 'bg-gray-100 text-gray-800',
              };
              const isSelected = activeBucket?.name === bucket.name;

              return (
                <div
                  key={bucket.name}
                  onClick={() => setSelectedBucketName(bucket.name)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-indigo-600 bg-indigo-50/50 shadow-sm ring-2 ring-indigo-500/20'
                      : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-2xs'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-gray-700 truncate capitalize">
                      {meta.label}
                    </span>
                    <span
                      className={`text-xs font-black px-2 py-0.5 rounded-full border ${meta.badgeColor}`}
                    >
                      {bucket.count}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-500 line-clamp-2">
                    {meta.description}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Active Bucket Item List */}
          {activeBucket ? (
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-900 capitalize">
                    {BUCKET_METADATA[activeBucket.name.toLowerCase()]?.label ||
                      activeBucket.name.replace(/_/g, ' ')}{' '}
                    ({activeBucket.count})
                  </h3>
                  <p className="text-xs text-gray-500">
                    {BUCKET_METADATA[activeBucket.name.toLowerCase()]?.description}
                  </p>
                </div>
              </div>

              {activeBucket.items.length === 0 ? (
                <div className="p-12 text-center text-xs text-gray-400">
                  No items in this category currently.
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {activeBucket.items.map((req) => {
                    let timeAgo = '';
                    try {
                      timeAgo = formatDistanceToNow(new Date(req.last_activity_at), {
                        addSuffix: true,
                      });
                    } catch {
                      timeAgo = req.last_activity_at;
                    }

                    return (
                      <div
                        key={req.id}
                        onClick={() => navigate(`/requests/${req.id}`)}
                        className="p-4 hover:bg-gray-50 cursor-pointer flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 transition-colors"
                      >
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono font-medium text-gray-400">
                              #{req.id}
                            </span>
                            <StatusBadge status={req.status} size="sm" />
                            <PriorityBadge priority={req.priority} size="sm" />
                            <span className="text-xs text-gray-500">
                              {req.team_name || `Team ${req.team_id}`}
                            </span>
                          </div>

                          <div className="text-sm font-semibold text-gray-900 hover:text-indigo-600 transition-colors">
                            {req.title}
                          </div>

                          <div className="text-xs text-gray-500 flex items-center gap-2">
                            <span>Owner: {req.owner_name || <strong className="text-amber-700">Unowned</strong>}</span>
                            <span>&bull;</span>
                            <span>Last activity: {timeAgo}</span>
                          </div>
                        </div>

                        <div className="shrink-0 flex items-center gap-2 text-xs font-medium text-indigo-600">
                          <span>View Detail &rarr;</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default AttentionPage;
