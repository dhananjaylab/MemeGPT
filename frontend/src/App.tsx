
import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AnimatePresence } from 'framer-motion';
import { AuthProvider } from './context/AuthContext';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { ProtectedRoute } from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';

const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })));
const Gallery = lazy(() => import('./pages/Gallery').then(m => ({ default: m.Gallery })));
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const AuthCallback = lazy(() => import('./pages/AuthCallback').then(m => ({ default: m.AuthCallback })));
const Synthesize = lazy(() => import('./pages/Synthesize').then(m => ({ default: m.Synthesize })));

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <Suspense fallback={<div className="p-6 flex justify-center text-muted">Loading...</div>}>
            <Home />
          </Suspense>
        } />
        <Route path="/synthesize" element={
          <Suspense fallback={<div className="p-6 flex justify-center text-muted">Loading...</div>}>
            <Synthesize />
          </Suspense>
        } />
        <Route path="/gallery" element={
          <Suspense fallback={<div className="p-6 flex justify-center text-muted">Loading...</div>}>
            <Gallery />
          </Suspense>
        } />
        <Route path="/auth/callback" element={
          <Suspense fallback={<div className="p-6 flex justify-center text-muted">Loading...</div>}>
            <AuthCallback />
          </Suspense>
        } />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Suspense fallback={<div className="p-6 flex justify-center text-muted">Loading...</div>}>
                <Dashboard />
              </Suspense>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <div className="flex flex-col min-h-screen">
            <Header />
            <main className="flex-1 page-container py-6 md:py-8">
              <AnimatedRoutes />
            </main>
            <Footer />
          </div>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: '#1a1a1a',
                color: '#fff',
                border: '1px solid #27272a',
                borderRadius: '12px',
                fontSize: '14px',
              },
              success: {
                iconTheme: { primary: '#B0FF00', secondary: '#111111' },
              },
            }}
          />
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
