import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { RequestEvent } from '../types';
import { useAuth } from '../hooks/useAuth';
import { useComments } from '../hooks/useComments';
import LoadingSpinner from './LoadingSpinner';

interface CommentSectionProps {
  requestId: string | number;
  events?: RequestEvent[];
}

export const CommentSection: React.FC<CommentSectionProps> = ({ requestId, events = [] }) => {
  const { user } = useAuth();
  const { addCommentMutation } = useComments(requestId);
  const [commentText, setCommentText] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Extract comments from events or direct items
  const commentEvents = events.filter((e) => e.type === 'commented');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;

    setErrorMessage(null);
    try {
      await addCommentMutation.mutateAsync({
        body: commentText.trim(),
        user: user || undefined,
      });
      setCommentText('');
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.message || 'Failed to submit comment');
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-4">
      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider flex items-center justify-between">
        <span>Comments & Discussion</span>
        <span className="text-xs font-normal text-gray-500">
          {commentEvents.length} comment{commentEvents.length === 1 ? '' : 's'}
        </span>
      </h3>

      {/* List of comments */}
      <div className="space-y-3">
        {commentEvents.length === 0 ? (
          <p className="text-xs text-gray-400 italic py-2">
            No comments yet. Start the conversation below.
          </p>
        ) : (
          commentEvents.map((c) => {
            let timeAgo = '';
            try {
              timeAgo = formatDistanceToNow(new Date(c.created_at), { addSuffix: true });
            } catch {
              timeAgo = c.created_at;
            }

            const body =
              typeof c.to_value === 'object' && c.to_value !== null
                ? c.to_value.body || JSON.stringify(c.to_value)
                : String(c.to_value || c.reason || '');

            return (
              <div
                key={c.id}
                className="p-3 bg-gray-50 rounded-md border border-gray-100 flex flex-col gap-1"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">
                      {(c.actor_name || 'U').charAt(0).toUpperCase()}
                    </span>
                    <span className="text-xs font-semibold text-gray-900">
                      {c.actor_name || `User #${c.actor_id}`}
                    </span>
                  </div>
                  <span className="text-[11px] text-gray-400">{timeAgo}</span>
                </div>
                <p className="text-xs text-gray-700 whitespace-pre-wrap pl-6">{body}</p>
              </div>
            );
          })
        )}
      </div>

      {/* Comment Input Box */}
      <form onSubmit={handleSubmit} className="pt-2 border-t border-gray-100">
        {errorMessage && (
          <div className="mb-2 p-2 bg-red-50 border border-red-200 text-red-700 text-xs rounded">
            {errorMessage}
          </div>
        )}

        <div className="flex flex-col gap-2">
          <textarea
            rows={3}
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Add an update, operational note, or question..."
            disabled={addCommentMutation.isPending}
            className="w-full p-2.5 text-xs sm:text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 transition-colors"
          />

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!commentText.trim() || addCommentMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {addCommentMutation.isPending ? (
                <>
                  <LoadingSpinner size="sm" className="text-white" />
                  <span>Posting...</span>
                </>
              ) : (
                <span>Post Comment</span>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default CommentSection;
