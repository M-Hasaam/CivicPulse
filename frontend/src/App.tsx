import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SubmitPage } from './pages/SubmitPage';
import { DashboardPage } from './pages/DashboardPage';

export function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />

        <main style={{ flex: 1 }}>
          <div className="container" style={{ padding: '2rem 1.5rem' }}>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Navigate to="/submit" replace />} />
                <Route path="/submit" element={<SubmitPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/stats" element={<h2>Stats</h2>} />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>

        <footer
          style={{
            borderTop: '1px solid var(--border-color)',
            padding: '1.5rem 0',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.8125rem',
          }}
        >
          <div className="container">CivicPulse &copy; {new Date().getFullYear()}</div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
