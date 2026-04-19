import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, RefreshCcw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  componentName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Uncaught error in ${this.props.componentName || 'component'}:`, error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center bg-surface border border-border rounded-2xl">
          <div className="p-4 bg-red-500/10 rounded-full text-red-500 mb-6">
            <AlertTriangle size={48} />
          </div>
          
          <h2 className="text-2xl font-display font-bold text-primary mb-2">
            Something went wrong
          </h2>
          
          <p className="text-secondary mb-8 max-w-md mx-auto">
            {this.state.error?.message || "An unexpected error occurred while rendering this component."}
          </p>
          
          <div className="flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={this.handleReset}
              className="btn-acid flex items-center gap-2"
            >
              <RefreshCcw size={18} />
              Try Again
            </button>
            
            <Link to="/" className="btn-ghost flex items-center gap-2">
              <Home size={18} />
              Go Home
            </Link>
          </div>
          
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-8 p-4 bg-black/40 rounded-lg text-left overflow-auto max-w-full">
              <pre className="text-xs font-mono text-red-300">
                {this.state.error?.stack}
              </pre>
            </div>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
