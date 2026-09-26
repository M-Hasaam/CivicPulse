import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
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
    console.error('Uncaught error in React ErrorBoundary:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>
            <h2 style={{ color: 'var(--danger)', marginBottom: '1rem' }}>Something went wrong</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              {this.state.error?.message || 'An unexpected rendering error occurred.'}
            </p>
            <button
              className="btn btn-primary"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
