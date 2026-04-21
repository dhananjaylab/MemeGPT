import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../lib/api';
import { Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

export function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
      // Fetch user data with this token to verify it
      apiClient.getCurrentUser(token)
        .then(user => {
          login(token, user);
          toast.success('Successfully signed in!');
          navigate('/dashboard');
        })
        .catch(err => {
          console.error('Auth verification failed:', err);
          toast.error('Authentication failed. Please try again.');
          navigate('/');
        });
    } else {
      navigate('/');
    }
  }, [searchParams, login, navigate]);

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
      <Loader2 size={40} className="text-acid animate-spin" />
      <h2 className="font-display text-2xl font-bold">Authenticating...</h2>
      <p className="font-mono text-sm text-secondary">Finalizing your secure session</p>
    </div>
  );
}
