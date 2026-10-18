import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { useNotifications } from '../hooks/useNotifications';

export const NotificationDropdown: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { notifications, unreadCount, markAsRead } = useNotifications();

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNotificationClick = (id: string | number, requestId: string | number) => {
    markAsRead(id);
    setIsOpen(false);
    navigate(`/requests/${requestId}`);
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
        aria-label="View notifications"
      >
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
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform bg-red-600 rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="origin-top-right absolute right-0 mt-2 w-80 md:w-96 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50 divide-y divide-gray-100 focus:outline-none">
          <div className="p-3 bg-gray-50 rounded-t-md flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-800">Notifications</span>
            {unreadCount > 0 && (
              <span className="text-xs bg-indigo-100 text-indigo-700 font-medium px-2 py-0.5 rounded-full">
                {unreadCount} unread
              </span>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-500">
                No notifications yet
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {notifications.map((n) => {
                  const isUnread = !n.read_at;
                  let timeAgo = '';
                  try {
                    timeAgo = formatDistanceToNow(new Date(n.created_at), { addSuffix: true });
                  } catch {
                    timeAgo = n.created_at;
                  }

                  return (
                    <li
                      key={n.id}
                      onClick={() => handleNotificationClick(n.id, n.request_id)}
                      className={`p-3 text-left hover:bg-gray-50 cursor-pointer transition-colors flex items-start gap-3 ${
                        isUnread ? 'bg-indigo-50/40' : ''
                      }`}
                    >
                      <span
                        className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                          isUnread ? 'bg-indigo-600' : 'bg-transparent'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs ${isUnread ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
                          {n.body}
                        </p>
                        <div className="mt-1 flex items-center gap-2 text-[10px] text-gray-400">
                          <span className="capitalize">{n.kind.replace(/_/g, ' ')}</span>
                          <span>•</span>
                          <span>{timeAgo}</span>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {notifications.length > 0 && (
            <div className="p-2 text-center bg-gray-50 rounded-b-md">
              <span className="text-xs text-gray-400">
                Auto-polled every 15 seconds
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationDropdown;
