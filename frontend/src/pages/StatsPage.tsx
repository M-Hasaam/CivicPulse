import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, RefreshCw, Server, Zap } from 'lucide-react';
import { ApiError, getProviderMeta, getStats, type ProviderMeta, type StatsOut } from '../api/client';
import './StatsPage.css';

const CATEGORY_LABELS: Record<string, string> = {
  water: 'Water',
  electricity: 'Electricity',
  sanitation: 'Sanitation',
  roads: 'Roads',
  streetlights: 'Streetlights',
  other: 'Other',
};

const PRIORITY_LABELS: Record<string, string> = {
  high: 'High',
  normal: 'Normal',
  low: 'Low',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  rejected: 'Rejected',
};

interface StatsState {
  stats: StatsOut;
  cacheState: string;
}

function labelFor(map: Record<string, string>, key: string): string {
  return map[key] ?? key.replaceAll('_', ' ');
}

function pct(value: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((value / total) * 100);
}

function formatLatency(ms: number): string {
  if (!Number.isFinite(ms)) return '0 ms';
  return `${Math.round(ms).toLocaleString()} ms`;
}

function formatRate(value: number | null): string {
  if (value === null) return 'No lookups yet';
  return `${Math.round(value * 100)}%`;
}

function CountBars({
  title,
  values,
  labels,
}: {
  title: string;
  values: Record<string, number>;
  labels: Record<string, string>;
}) {
  const total = Object.values(values).reduce((sum, value) => sum + value, 0);
  const rows = Object.entries(values).sort((a, b) => b[1] - a[1]);

  return (
    <section className="stats-panel" aria-label={title}>
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p className="stats-empty">No data yet</p>
      ) : (
        <div className="stats-bars">
          {rows.map(([key, value]) => {
            const width = pct(value, total);
            return (
              <div className="stats-bar-row" key={key}>
                <div className="stats-bar-label">
                  <span>{labelFor(labels, key)}</span>
                  <strong>{value.toLocaleString()}</strong>
                </div>
                <div className="stats-bar-track" aria-hidden="true">
                  <div className="stats-bar-fill" style={{ width: `${width}%` }} />
                </div>
                <span className="stats-bar-pct">{width}%</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function RecentOutcomes({ meta }: { meta: ProviderMeta }) {
  const recent = meta.recent_outcomes.slice(0, 6);
  return (
    <section className="stats-panel" aria-label="Recent triage outcomes">
      <h3>Recent triage outcomes</h3>
      {recent.length === 0 ? (
        <p className="stats-empty">No triage calls recorded yet</p>
      ) : (
        <div className="outcome-list">
          {recent.map((outcome, index) => (
            <div className="outcome-row" key={`${outcome.at}-${index}`}>
              <div>
                <strong>{outcome.provider}</strong>
                <span>{new Date(outcome.at).toLocaleString()}</span>
              </div>
              <div className="outcome-meta">
                <span>{formatLatency(outcome.latency_ms)}</span>
                {outcome.cached && <span className="cache-pill cache-hit">cached</span>}
                {outcome.fallback && <span className="cache-pill cache-bypass">fallback</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function StatsPage() {
  const [statsState, setStatsState] = useState<StatsState | null>(null);
  const [providerMeta, setProviderMeta] = useState<ProviderMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsResult, metaResult] = await Promise.all([getStats(), getProviderMeta()]);
      setStatsState(statsResult);
      setProviderMeta(metaResult);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load stats. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const cacheClass = useMemo(() => {
    const value = statsState?.cacheState.toUpperCase();
    if (value === 'HIT') return 'cache-hit';
    if (value === 'MISS') return 'cache-miss';
    if (value === 'BYPASS') return 'cache-bypass';
    return 'cache-unknown';
  }, [statsState?.cacheState]);

  return (
    <div className="stats-page">
      <div className="dashboard-header">
        <div>
          <h2 className="dashboard-title">Statistics</h2>
          <p className="dashboard-subtitle">
            Aggregate complaint counts, cache state and triage provider health.
          </p>
        </div>
        <button
          id="stats-refresh-btn"
          type="button"
          className="btn btn-secondary dashboard-refresh-btn"
          onClick={() => void loadStats()}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'spinner' : ''} />
          Refresh
        </button>
      </div>

      {error && <div role="alert" className="dashboard-error">{error}</div>}

      {loading && !statsState && (
        <div className="skeleton-list" aria-label="Loading statistics">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton-row" style={{ opacity: 1 - i * 0.12 }} />
          ))}
        </div>
      )}

      {statsState && (
        <>
          <section className="stats-summary-grid" aria-label="Stats summary">
            <div className="stats-summary-card">
              <BarChart3 size={18} />
              <span>Total complaints</span>
              <strong>{statsState.stats.total_complaints.toLocaleString()}</strong>
            </div>
            <div className="stats-summary-card">
              <Activity size={18} />
              <span>Average triage latency</span>
              <strong>{formatLatency(statsState.stats.avg_triage_latency_ms)}</strong>
            </div>
            <div className="stats-summary-card">
              <Zap size={18} />
              <span>Stats cache</span>
              <strong className={`cache-pill ${cacheClass}`}>{statsState.cacheState}</strong>
            </div>
            <div className="stats-summary-card">
              <Server size={18} />
              <span>Active provider</span>
              <strong>{providerMeta?.active_provider ?? 'Unknown'}</strong>
            </div>
          </section>

          <div className="stats-grid">
            <CountBars
              title="By category"
              values={statsState.stats.by_category}
              labels={CATEGORY_LABELS}
            />
            <CountBars
              title="By priority"
              values={statsState.stats.by_priority}
              labels={PRIORITY_LABELS}
            />
            <CountBars
              title="By status"
              values={statsState.stats.by_status}
              labels={STATUS_LABELS}
            />
            {providerMeta && (
              <section className="stats-panel" aria-label="Provider and triage cache">
                <h3>Provider and triage cache</h3>
                <dl className="meta-list">
                  <div>
                    <dt>Active provider</dt>
                    <dd>{providerMeta.active_provider}</dd>
                  </div>
                  <div>
                    <dt>Fallback provider</dt>
                    <dd>{providerMeta.fallback_provider}</dd>
                  </div>
                  <div>
                    <dt>Triage cache hits</dt>
                    <dd>{providerMeta.triage_cache.hits.toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>Triage cache misses</dt>
                    <dd>{providerMeta.triage_cache.misses.toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>Triage hit rate</dt>
                    <dd>{formatRate(providerMeta.triage_cache.hit_rate)}</dd>
                  </div>
                </dl>
              </section>
            )}
          </div>

          {providerMeta && <RecentOutcomes meta={providerMeta} />}
        </>
      )}
    </div>
  );
}

export default StatsPage;
