import { useState } from 'react';
import { Navbar, type Tab } from './components/Navbar';

export function App() {
  const [currentTab, setCurrentTab] = useState<Tab>('submit');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar currentTab={currentTab} onSelectTab={setCurrentTab} />

      <main style={{ flex: 1 }}>
        <div className="container" style={{ padding: '2rem 1.5rem' }}>
          {currentTab === 'submit' && <h2>Submit</h2>}
          {currentTab === 'dashboard' && <h2>Dashboard</h2>}
          {currentTab === 'stats' && <h2>Stats</h2>}
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
  );
}

export default App;
