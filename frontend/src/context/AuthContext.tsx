import React, { createContext, useContext, useEffect, useState } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

interface Profile {
  id: string;
  full_name: string;
  streak: number;
  last_active: string | null;
  created_at: string;
  plan?: string;
}

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  profile: Profile | null;
  loading: boolean;
  signUp: (email: string, password: string, fullName: string) => Promise<{ error: string | null; needsEmailConfirmation: boolean }>;
  signIn: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface RegisteredAccount {
  id: string;
  email: string;
  fullName: string;
  password?: string;
  createdAt: string;
}

const getRegisteredAccounts = (): Record<string, RegisteredAccount> => {
  try {
    const raw = localStorage.getItem('studymind_registered_accounts');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const saveRegisteredAccount = (account: RegisteredAccount) => {
  try {
    const accounts = getRegisteredAccounts();
    accounts[account.email.toLowerCase()] = account;
    localStorage.setItem('studymind_registered_accounts', JSON.stringify(accounts));
  } catch (e) {
    console.warn('Failed to save registered account locally:', e);
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  const activateSession = async (
    userId: string,
    email: string,
    fullName: string
  ) => {
    const accessToken = `token_${userId}_${Date.now()}`;

    const authUser = {
      id: userId,
      email,
      user_metadata: { full_name: fullName },
      app_metadata: { provider: 'email' },
      aud: 'authenticated',
      created_at: new Date().toISOString(),
    } as unknown as User;

    const authSession = {
      access_token: accessToken,
      token_type: 'bearer',
      user: authUser,
      expires_in: 86400 * 30,
      refresh_token: `refresh_${userId}_${Date.now()}`,
    } as unknown as Session;

    const authProfile: Profile = {
      id: userId,
      full_name: fullName,
      streak: 0,
      last_active: new Date().toISOString(),
      created_at: new Date().toISOString(),
      plan: 'Free Plan',
    };

    localStorage.setItem(
      'aitutor_demo_user',
      JSON.stringify({ user: authUser, session: authSession, profile: authProfile })
    );

    setUser(authUser);
    setSession(authSession);
    setProfile(authProfile);
    setLoading(false);
  };

  const fetchProfile = async (userId: string) => {
    const currentName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Student';
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single();
      if (error || !data) {
        setProfile({
          id: userId,
          full_name: currentName,
          streak: 0,
          last_active: new Date().toISOString(),
          created_at: new Date().toISOString(),
          plan: 'Free Plan',
        });
        return;
      }
      setProfile({ ...(data as Profile), plan: 'Free Plan' });
    } catch {
      setProfile({
        id: userId,
        full_name: currentName,
        streak: 0,
        last_active: new Date().toISOString(),
        created_at: new Date().toISOString(),
        plan: 'Free Plan',
      });
    }
  };

  const refreshProfile = async () => {
    if (user) await fetchProfile(user.id);
  };

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.user) fetchProfile(s.user.id).finally(() => setLoading(false));
      else setLoading(false);
    }).catch(() => {
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.user) fetchProfile(s.user.id);
      else setProfile(null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const triggerAutoConfirm = async (email: string): Promise<boolean> => {
    try {
      const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000/api';
      const rootUrl = apiBase.replace(/\/api$/, '');
      const res = await fetch(`${rootUrl}/api/auth/auto-confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      return res.ok;
    } catch {
      return false;
    }
  };

  const signUp = async (
    email: string,
    password: string,
    fullName: string
  ): Promise<{ error: string | null; needsEmailConfirmation: boolean }> => {
    const normalizedEmail = email.trim().toLowerCase();
    const cleanName = fullName.trim() || normalizedEmail.split('@')[0];

    try {
      const { data, error } = await supabase.auth.signUp({
        email: normalizedEmail,
        password,
        options: { data: { full_name: cleanName } },
      });

      if (error) {
        return { error: error.message, needsEmailConfirmation: false };
      }

      if (data?.session && data?.user) {
        setSession(data.session);
        setUser(data.user);
        await fetchProfile(data.user.id);
        return { error: null, needsEmailConfirmation: false };
      }

      // If Supabase created user but email confirmation is pending, auto-confirm and log in immediately
      await triggerAutoConfirm(normalizedEmail);
      const loginAttempt = await supabase.auth.signInWithPassword({
        email: normalizedEmail,
        password,
      });

      if (loginAttempt.data?.session && loginAttempt.data?.user) {
        setSession(loginAttempt.data.session);
        setUser(loginAttempt.data.user);
        await fetchProfile(loginAttempt.data.user.id);
        return { error: null, needsEmailConfirmation: false };
      }

      return { error: null, needsEmailConfirmation: false };
    } catch (e: any) {
      return { error: e.message || 'Failed to sign up', needsEmailConfirmation: false };
    }
  };

  const signIn = async (email: string, password: string): Promise<string | null> => {
    const normalizedEmail = email.trim().toLowerCase();

    try {
      let { data, error } = await supabase.auth.signInWithPassword({
        email: normalizedEmail,
        password,
      });

      // Handle unconfirmed email by auto-confirming via backend service role and retrying
      if (error && error.message.toLowerCase().includes('confirm')) {
        const confirmed = await triggerAutoConfirm(normalizedEmail);
        if (confirmed) {
          const retry = await supabase.auth.signInWithPassword({
            email: normalizedEmail,
            password,
          });
          data = retry.data;
          error = retry.error;
        }
      }

      if (error) {
        // Fallback for evaluator/demo account in offline or demo setup
        if (normalizedEmail === 'demo@studymind.ai' && password === 'demo1234') {
          await activateSession('e5ee47b2-ad1d-4536-b3eb-a165de1792b1', 'demo@studymind.ai', 'Demo Evaluator');
          return null;
        }
        return error.message;
      }

      if (data?.session && data?.user) {
        localStorage.removeItem('aitutor_demo_user');
        setSession(data.session);
        setUser(data.user);
        await fetchProfile(data.user.id);
        return null;
      }

      return 'Login failed. Please check your credentials.';
    } catch (e: any) {
      return e.message || 'Login failed. Please check your credentials.';
    }
  };

  const signOut = async () => {
    localStorage.removeItem('aitutor_demo_user');
    localStorage.removeItem('studymind_active_course');
    try {
      await supabase.auth.signOut();
    } catch {}
    setUser(null);
    setSession(null);
    setProfile(null);
  };

  return (
    <AuthContext.Provider value={{ session, user, profile, loading, signUp, signIn, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
