import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, TeamMembership, Role } from '../types';
import { login as apiLogin, getMe, logout as apiLogout } from '../api/auth';

export interface AuthContextType {
  user: User | null;
  memberships: TeamMembership[];
  isAuthenticated: boolean;
  isLoading: boolean;
  isApprover: boolean;
  isLead: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
  hasRoleInTeam: (teamId: string | number, roles: Role | Role[]) => boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [memberships, setMemberships] = useState<TeamMembership[]>(() => {
    const saved = localStorage.getItem('memberships');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [];
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshMe = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setUser(null);
      setMemberships([]);
      setIsLoading(false);
      return;
    }

    try {
      const data: any = await getMe();
      const resolvedUser: User = data?.user || {
        id: data?.id,
        email: data?.email,
        name: data?.name,
      };

      const rawTeams = data?.memberships || data?.teams || [];
      const resolvedMemberships: TeamMembership[] = rawTeams.map((t: any) => ({
        team_id: t.team_id || t.id,
        team: t.team || { id: t.team_id || t.id, name: t.team_name || t.name },
        role: (t.role?.value || t.role) as Role,
      }));

      setUser(resolvedUser);
      setMemberships(resolvedMemberships);
      localStorage.setItem('user', JSON.stringify(resolvedUser));
      localStorage.setItem('memberships', JSON.stringify(resolvedMemberships));
    } catch (err) {
      console.error('Failed to fetch current user profile:', err);
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('memberships');
      setUser(null);
      setMemberships([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const resp: any = await apiLogin(email, password);
      if (resp?.user) {
        const u = resp.user;
        const resolvedUser: User = { id: u.id, email: u.email, name: u.name };
        const rawTeams = u.teams || u.memberships || [];
        const resolvedMemberships: TeamMembership[] = rawTeams.map((t: any) => ({
          team_id: t.team_id || t.id,
          team: t.team || { id: t.team_id || t.id, name: t.team_name || t.name },
          role: (t.role?.value || t.role) as Role,
        }));
        setUser(resolvedUser);
        setMemberships(resolvedMemberships);
        localStorage.setItem('user', JSON.stringify(resolvedUser));
        localStorage.setItem('memberships', JSON.stringify(resolvedMemberships));
      }
      await refreshMe();
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    apiLogout();
    localStorage.removeItem('user');
    localStorage.removeItem('memberships');
    setUser(null);
    setMemberships([]);
  };

  const hasRoleInTeam = (teamId: string | number, roles: Role | Role[]): boolean => {
    const targetRoles = Array.isArray(roles) ? roles : [roles];
    return memberships.some(
      (m) => String(m.team_id) === String(teamId) && targetRoles.includes(m.role)
    );
  };

  const isApprover = memberships.some((m) => m.role === 'approver' || m.role === 'lead');
  const isLead = memberships.some((m) => m.role === 'lead');

  const value: AuthContextType = {
    user,
    memberships,
    isAuthenticated: !!user,
    isLoading,
    isApprover,
    isLead,
    login,
    logout,
    refreshMe,
    hasRoleInTeam,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
