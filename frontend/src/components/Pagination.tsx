import React from 'react';
import LoadingSpinner from './LoadingSpinner';

interface PaginationProps {
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
  loadedCount?: number;
}

export const Pagination: React.FC<PaginationProps> = ({
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  loadedCount,
}) => {
  if (!hasNextPage && (loadedCount ?? 0) > 0) {
    return (
      <div className="py-6 text-center text-xs text-gray-500 font-medium">
        All items loaded ({loadedCount} total)
      </div>
    );
  }

  if (!hasNextPage) {
    return null;
  }

  return (
    <div className="py-6 flex flex-col items-center justify-center gap-2">
      <button
        onClick={onLoadMore}
        disabled={isFetchingNextPage}
        className="inline-flex items-center justify-center px-5 py-2.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isFetchingNextPage ? (
          <LoadingSpinner size="sm" label="Loading more..." />
        ) : (
          <span>Load more</span>
        )}
      </button>
      {loadedCount !== undefined && (
        <span className="text-xs text-gray-400">Showing {loadedCount} items</span>
      )}
    </div>
  );
};

export default Pagination;
