import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { SubmitPage } from "./pages/SubmitPage";
import { DashboardPage } from "./pages/DashboardPage";
import { StatsPage } from "./pages/StatsPage";

export function App() {
  return (
    <BrowserRouter>
      <div
        style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}
      >
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <Navbar />

        <main id="main-content" style={{ flex: 1 }}>
          <div className="container page-container">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Navigate to="/submit" replace />} />
                <Route path="/submit" element={<SubmitPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/stats" element={<StatsPage />} />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>

        <footer
          style={{
            borderTop: "1px solid var(--border-color)",
            padding: "1.5rem 0",
            textAlign: "center",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          <div className="container footer-content">
            <span>CivicPulse &copy; {new Date().getFullYear()}</span>
            <span>Better neighbourhoods begin with you.</span>
            <span>Community reporting &amp; operations</span>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
