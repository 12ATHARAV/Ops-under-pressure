import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import ErrorBoundary from './ErrorBoundary';

export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col text-gray-900">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <footer className="bg-white border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        Operations Under Pressure &bull; Newtonite Software Engineering Challenge
      </footer>
    </div>
  );
};

export default Layout;
