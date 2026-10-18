import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import LoadingSpinner from '../components/LoadingSpinner';

const DEMO_ACCOUNTS = [
  {
    role: 'Team Lead',
    email: 'alice@example.com',
    password: 'Newtonite2026!Ops',
    desc: 'Platform Lead: full administrative access, reassignment, and attention views',
  },
  {
    role: 'Team Approver',
    email: 'bob@example.com',
    password: 'Newtonite2026!Ops',
    desc: 'Platform Approver: can approve or reject transitions in the queue',
  },
  {
    role: 'Team Member',
    email: 'charlie@example.com',
    password: 'Newtonite2026!Ops',
    desc: 'Platform Member: can create, claim, and work on operational requests',
  },
  {
    role: 'Ops Lead',
    email: 'emma@example.com',
    password: 'Newtonite2026!Ops',
    desc: 'Customer Operations Lead: cross-team lead triage and assignment',
  },
];

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('alice@example.com');
  const [password, setPassword] = useState('Newtonite2026!Ops');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate('/requests', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login(email, password);
      navigate('/requests');
    } catch (err: any) {
      const msg =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        'Invalid credentials. Please try again.';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black text-xl shadow-md mx-auto mb-3">
          OP
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight">
          Operations Under Pressure
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Sign in to coordinate mission-critical team operations
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 shadow-sm rounded-xl border border-gray-200 sm:px-10">
          {errorMessage && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs sm:text-sm rounded-md flex items-center gap-2">
              <svg className="w-5 h-5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1"
              >
                Work Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-2xs placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-2xs placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
              >
                {isSubmitting ? (
                  <LoadingSpinner size="sm" className="text-white" label="Signing in..." />
                ) : (
                  'Sign In'
                )}
              </button>
            </div>
          </form>

          {/* Seeded Demo Accounts */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              Quick Test Demo Credentials:
            </h3>
            <div className="space-y-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => handleSelectDemoAccount(acc.email, acc.password)}
                  className="w-full text-left p-2.5 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all text-xs flex flex-col group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-900 group-hover:text-indigo-600">
                      {acc.role}
                    </span>
                    <span className="text-[11px] font-mono text-gray-500">{acc.email}</span>
                  </div>
                  <span className="text-gray-500 text-[11px] mt-0.5">{acc.desc}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
