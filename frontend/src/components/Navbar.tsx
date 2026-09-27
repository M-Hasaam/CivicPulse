import React from 'react';
import { NavLink } from 'react-router-dom';
import { Send, LayoutDashboard, BarChart3 } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="navbar">
      <div className="container nav-container">
        <NavLink to="/submit" className="nav-brand" style={{ textDecoration: 'none' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.1rem',
            }}
          >
            CP
          </div>
          <span>
            Civic<span style={{ color: 'var(--primary)' }}>Pulse</span>
          </span>
        </NavLink>

        <nav className="nav-links">
          <NavLink
            id="nav-submit-btn"
            to="/submit"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <Send size={16} /> Submit
            </span>
          </NavLink>

          <NavLink
            id="nav-dashboard-btn"
            to="/dashboard"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <LayoutDashboard size={16} /> Operations
            </span>
          </NavLink>

          <NavLink
            id="nav-stats-btn"
            to="/stats"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <BarChart3 size={16} /> Statistics
            </span>
          </NavLink>
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
