import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import NotificationDropdown from './NotificationDropdown';

export const Navbar: React.FC = () => {
  const { user, isApprover, isLead, logout, memberships } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-50 text-indigo-700 font-semibold'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
    }`;

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Left Navigation */}
          <div className="flex items-center gap-8">
            <Link to="/requests" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-sm">
                OP
              </div>
              <span className="font-bold text-gray-900 tracking-tight text-base sm:text-lg">
                Operations Under Pressure
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-1">
              <NavLink to="/requests" className={navLinkClass}>
                Work List
              </NavLink>

              {isApprover && (
                <NavLink to="/approvals" className={navLinkClass}>
                  Approval Queue
                </NavLink>
              )}

              {isLead && (
                <NavLink to="/attention" className={navLinkClass}>
                  Needs Attention
                </NavLink>
              )}
            </nav>
          </div>

          {/* Right section: Notifications & User profile */}
          <div className="flex items-center gap-4">
            <NotificationDropdown />

            {user && (
              <div className="flex items-center gap-3 pl-2 border-l border-gray-200">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-semibold text-gray-900 truncate max-w-[140px]">
                    {user.name}
                  </span>
                  <span className="text-[11px] text-gray-500 truncate max-w-[140px]">
                    {memberships.length > 0
                      ? memberships.map((m) => m.team?.name || `Team ${m.team_id}`).join(', ')
                      : user.email}
                  </span>
                </div>

                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-xs">
                  {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                </div>

                <button
                  onClick={handleLogout}
                  className="text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 px-2 py-1.5 rounded transition-colors"
                  title="Sign out"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Sub-Navigation */}
        <div className="flex md:hidden items-center gap-2 py-2 border-t border-gray-100 overflow-x-auto">
          <NavLink to="/requests" className={navLinkClass}>
            Work List
          </NavLink>
          {isApprover && (
            <NavLink to="/approvals" className={navLinkClass}>
              Approvals
            </NavLink>
          )}
          {isLead && (
            <NavLink to="/attention" className={navLinkClass}>
              Attention
            </NavLink>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
