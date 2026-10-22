import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Brain } from 'lucide-react';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { session, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF8F5] flex items-center justify-center">
        <div className="flex items-center space-x-3 bg-white px-5 py-3 rounded-2xl border border-[#EAE6DF] shadow-xs">
          <Brain className="h-5 w-5 text-emerald-600 animate-spin" />
          <span className="text-sm font-medium text-slate-600">Loading StudyMind...</span>
        </div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
