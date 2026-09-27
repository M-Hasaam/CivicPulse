import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Zap, BarChart2, Activity, Clock, Database } from 'lucide-react';
import {
  type ProviderMeta,
  type StatsOut,
  getProviderMeta,
  getStats,
} from '../api/client';

// ─── Cache badge ────────────────────────────────────────────────────────────

function CacheBadge({
  state,
  loading,
  lastRefreshed,
  onRefresh,
}: {
  state: string;
  loading: boolean;
  lastRefreshed: Date | null;
  onRefresh: () => void;
}) {
  const isHit = state === 'HIT';
  const isMiss = state === 'MISS';

  return (
    <div className="cache-badge-row">
      <div className={`cache-badge ${isHit ? 'cache-hit' : isMiss ? 'cache-miss' : 'cache-unknown'}`}>
        <span className="cache-dot" />
        <span className="cache-label">X-Cache</span>
        <span className="cache-value">{state}</span>
      </div>

      {lastRefreshed && (
        <span className="cache-timestamp">
          Last fetched {lastRefreshed.toLocaleTimeString()}
        </span>
      )}

      <button
        type="button"
        className="btn btn-secondary stats-refresh-btn"
        onClick={onRefresh}
        disabled={loading}
      >
        <RefreshCw size={13} className={loading ? 'spinner' : ''} />
        Refresh stats
      </button>
    </div>
  );
}

// ─── Stat card ───────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon">{icon}</div>
      <div>
        <p className="stat-card-value">{value}</p>
        <p className="stat-card-label">{label}</p>
        {sub && <p className="stat-card-sub">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Breakdown bar ───────────────────────────────────────────────────────────

const BREAKDOWN_COLORS: Record<string, string> = {
  // categories
  water: '#60a5fa',
  electricity: '#fde047',
  sanitation: '#86efac',
  roads: '#fdba74',
  streetlights: '#d8b4fe',
  other: '#9ca3af',
  // priorities
  high: '#fca5a5',
  normal: '#fcd34d',
  low: '#93c5fd',
  // statuses
  open: '#60a5fa',
  in_progress: '#fbbf24',
  resolved: '#34d399',
  rejected: '#f87171',
};

function BreakdownChart({
  title,
  data,
  total,
}: {
  title: string;
  data: Record<string, number>;
  total: number;
}) {
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a);

  return (
    <div className="breakdown-chart">
      <p className="breakdown-title">{title}</p>
      <div className="breakdown-rows">
        {entries.map(([key, count]) => {
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          const color = BREAKDOWN_COLORS[key] ?? '#6b7280';
          return (
            <div key={key} className="breakdown-row">
              <span className="breakdown-key">{key.replace('_', ' ')}</span>
              <div className="breakdown-bar-track">
                <div
                  className="breakdown-bar-fill"
                  style={{ width: `${pct}%`, background: color }}
                />
              </div>
              <span className="breakdown-count">{count}</span>
              <span className="breakdown-pct">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Provider panel ──────────────────────────────────────────────────────────

function ProviderPanel({ meta }: { meta: ProviderMeta }) {
  const { hits, misses, hit_rate } = meta.triage_cache;
  const hitRatePct = hit_rate != null ? `${(hit_rate * 100).toFixed(1)}%` : 'N/A';

  return (
    <div className="provider-panel">
      <p className="provider-title">
        <Activity size={14} /> Triage Provider
      </p>

      <div className="provider-meta-grid">
        <div className="provider-meta-item">
          <span className="provider-meta-label">Active</span>
          <span className="provider-meta-value mono">{meta.active_provider}</span>
        </div>
        <div className="provider-meta-item">
          <span className="provider-meta-label">Fallback</span>
          <span className="provider-meta-value mono">{meta.fallback_provider}</span>
        </div>
        <div className="provider-meta-item">
          <span className="provider-meta-label">Cache hits</span>
          <span className="provider-meta-value">{hits}</span>
        </div>
        <div className="provider-meta-item">
          <span className="provider-meta-label">Cache misses</span>
          <span className="provider-meta-value">{misses}</span>
        </div>
        <div className="provider-meta-item">
          <span className="provider-meta-label">Hit rate</span>
          <span className={`provider-meta-value ${hit_rate != null && hit_rate >= 0.5 ? 'text-success' : 'text-warning'}`}>
            {hitRatePct}
          </span>
        </div>
      </div>

      {meta.recent_outcomes.length > 0 && (
        <>
          <p className="provider-outcomes-label">Recent triage outcomes</p>
          <div className="provider-outcomes-table-wrap">
            <table className="provider-outcomes-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Latency</th>
                  <th>Cached</th>
                  <th>Fallback</th>
                  <th>At</th>
                </tr>
              </thead>
              <tbody>
                {meta.recent_outcomes.slice(0, 20).map((o, i) => (
                  <tr key={i}>
                    <td className="mono">{o.provider}</td>
                    <td>{o.latency_ms.toLocaleString()} ms</td>
                    <td>
                      <span className={`outcome-pill ${o.cached ? 'pill-hit' : 'pill-miss'}`}>
                        {o.cached ? 'HIT' : 'MISS'}
                      </span>
                    </td>
                    <td>
                      {o.fallback ? (
                        <span className="outcome-pill pill-warning">Yes</span>
                      ) : (
                        <span className="outcome-pill pill-ok">No</span>
                      )}
                    </td>
                    <td className="outcome-at">
                      {new Date(o.at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ─── StatsPage ───────────────────────────────────────────────────────────────

export function StatsPage() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [cacheState, setCacheState] = useState<string>('UNKNOWN');
  const [providerMeta, setProviderMeta] = useState<ProviderMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [{ stats: s, cacheState: cs }, meta] = await Promise.all([
        getStats(),
        getProviderMeta(),
      ]);
      setStats(s);
      // X-Cache header: HIT means Redis served the response, MISS means it
      // was freshly computed. This is a key portfolio differentiator per the brief.
      setCacheState(cs);
      setProviderMeta(meta);
      setLastRefreshed(new Date());
    } catch {
      setError('Failed to load statistics. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchAll(); }, [fetchAll]);

  return (
    <div className="stats-page">

      {/* ── Header ─────────────────────────────── */}
      <div className="dashboard-header">
        <div>
          <h2 className="dashboard-title">Statistics</h2>
          <p className="dashboard-subtitle">Aggregate complaint metrics and triage intelligence</p>
        </div>
      </div>

      {/* ── X-Cache badge (portfolio differentiator) ── */}
      <CacheBadge
        state={cacheState}
        loading={loading}
        lastRefreshed={lastRefreshed}
        onRefresh={() => void fetchAll()}
      />

      {/* ── Error ──────────────────────────────── */}
      {error && <div role="alert" className="dashboard-error">{error}</div>}

      {/* ── Loading ────────────────────────────── */}
      {loading && !stats && (
        <div className="skeleton-list">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton-row" style={{ height: '80px', opacity: 1 - i * 0.15 }} />
          ))}
        </div>
      )}

      {stats && (
        <>
          {/* ── Summary stat cards ─────────────── */}
          <div className="stat-cards-grid">
            <StatCard
              icon={<BarChart2 size={18} />}
              label="Total complaints"
              value={stats.total_complaints.toLocaleString()}
            />
            <StatCard
              icon={<Clock size={18} />}
              label="Avg triage latency"
              value={`${stats.avg_triage_latency_ms.toLocaleString()} ms`}
              sub="across all AI providers"
            />
            <StatCard
              icon={<Zap size={18} />}
              label="Open"
              value={(stats.by_status['open'] ?? 0).toLocaleString()}
              sub="awaiting action"
            />
            <StatCard
              icon={<Database size={18} />}
              label="Resolved"
              value={(stats.by_status['resolved'] ?? 0).toLocaleString()}
              sub="completed"
            />
          </div>

          {/* ── Breakdowns ─────────────────────── */}
          <div className="breakdowns-grid">
            <BreakdownChart
              title="By category"
              data={stats.by_category}
              total={stats.total_complaints}
            />
            <BreakdownChart
              title="By priority"
              data={stats.by_priority}
              total={stats.total_complaints}
            />
            <BreakdownChart
              title="By status"
              data={stats.by_status}
              total={stats.total_complaints}
            />
          </div>

          {/* ── Provider panel ─────────────────── */}
          {providerMeta && <ProviderPanel meta={providerMeta} />}
        </>
      )}
    </div>
  );
}

export default StatsPage;
