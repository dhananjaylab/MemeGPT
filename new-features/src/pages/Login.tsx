
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { LogIn, Loader2, Wand2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

export function Login() {
  const { loginWithGoogle, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleGoogleLogin = async () => {
    try {
      await loginWithGoogle();
      toast.success('Deployed Identity Successfully');
      navigate('/dashboard');
    } catch (error) {
      toast.error('Failed to link neural identity.');
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card w-full max-w-md p-10 text-center space-y-8"
      >
        <div className="space-y-4">
          <div className="w-20 h-20 bg-acid rounded-3xl flex items-center justify-center text-black mx-auto shadow-[0_0_30px_rgba(176,255,0,0.3)]">
            <Wand2 size={40} />
          </div>
          <h2 className="text-4xl font-display font-bold tracking-tight">Access Lab</h2>
          <p className="text-muted">Return to your memetic synthesis dashboard.</p>
        </div>

        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className="btn-primary w-full py-5 text-lg flex items-center justify-center gap-3"
        >
          {isLoading ? (
            <Loader2 size={24} className="animate-spin" />
          ) : (
            <>
              <LogIn size={24} />
              Deploy Google Identity
            </>
          )}
        </button>

        <p className="text-[10px] text-muted uppercase tracking-widest leading-loose">
          Secure connection established. All neural patterns are encrypted via Firebase Auth.
        </p>
      </motion.div>
    </div>
  );
}
