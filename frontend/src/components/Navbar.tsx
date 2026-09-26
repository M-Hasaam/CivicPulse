import React from 'react';
import { Send, LayoutDashboard, BarChart3 } from 'lucide-react';

export type Tab = 'submit' | 'dashboard' | 'stats';

interface NavbarProps {
  currentTab: Tab;
  onSelectTab: (tab: Tab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onSelectTab }) => {
  return (
    <header className="navbar">
      <div className="container nav-container">
        <button type="button" className="nav-brand" onClick={() => onSelectTab('submit')}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '1.1rem'
          }}>
            CP
          </div>
          <span>Civic<span style={{ color: 'var(--primary)' }}>Pulse</span></span>
        </button>

        <nav className="nav-links">
          <button
            id="nav-submit-btn"
            className={`nav-link ${currentTab === 'submit' ? 'active' : ''}`}
            onClick={() => onSelectTab('submit')}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <Send size={16} /> Submit
            </span>
          </button>
          <button
            id="nav-dashboard-btn"
            className={`nav-link ${currentTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => onSelectTab('dashboard')}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <LayoutDashboard size={16} /> Operations
            </span>
          </button>
          <button
            id="nav-stats-btn"
            className={`nav-link ${currentTab === 'stats' ? 'active' : ''}`}
            onClick={() => onSelectTab('stats')}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <BarChart3 size={16} /> Statistics
            </span>
          </button>
        </nav>
      </div>
    </header>
  );
};
