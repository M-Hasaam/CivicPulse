import { NavLink } from "react-router-dom";
import {
  Activity,
  ArrowUpRight,
  Send,
  LayoutDashboard,
  BarChart3,
} from "lucide-react";

export function Navbar() {
  return (
    <header className="navbar">
      <div className="container nav-container">
        <NavLink
          to="/submit"
          className="nav-brand"
          aria-label="CivicPulse home"
        >
          <span className="brand-mark">
            <Activity size={23} />
          </span>
          <span>
            CivicPulse<small>COMMUNITY SERVICES</small>
          </span>
        </NavLink>
        <nav className="nav-links" aria-label="Main navigation">
          <NavLink
            id="nav-submit-btn"
            to="/submit"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <Send size={16} /> Submit
          </NavLink>
          <NavLink
            id="nav-dashboard-btn"
            to="/dashboard"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <LayoutDashboard size={16} /> Operations
          </NavLink>
          <NavLink
            id="nav-stats-btn"
            to="/stats"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <BarChart3 size={16} /> Statistics
          </NavLink>
        </nav>
        <span className="nav-caption">
          A better place, together <ArrowUpRight size={15} />
        </span>
      </div>
    </header>
  );
}
export default Navbar;
