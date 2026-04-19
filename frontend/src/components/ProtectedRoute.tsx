import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <Loader2 size={32} className="text-acid animate-spin" />
        <p className="font-mono text-sm text-secondary">Checking session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to home or login page, but since we use OAuth, maybe just home
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
