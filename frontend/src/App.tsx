import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import WorkListPage from './pages/WorkListPage';
import RequestDetailPage from './pages/RequestDetailPage';
import ApprovalQueuePage from './pages/ApprovalQueuePage';
import AttentionPage from './pages/AttentionPage';
import LoadingSpinner from './components/LoadingSpinner';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Do not retry 401, 403, 404, or 409
        const status = error?.response?.status;
        if (status === 401 || status === 403 || status === 404 || status === 409) {
          return false;
        }
        return failureCount < 2;
      },
      refetchOnWindowFocus: true,
      staleTime: 5000,
    },
    mutations: {
      retry: false,
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="lg" label="Authenticating session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes wrapped in Layout */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/requests" replace />} />
              <Route path="requests" element={<WorkListPage />} />
              <Route path="requests/:id" element={<RequestDetailPage />} />
              <Route path="approvals" element={<ApprovalQueuePage />} />
              <Route path="attention" element={<AttentionPage />} />
            </Route>

            {/* Catch-all route */}
            <Route path="*" element={<Navigate to="/requests" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
