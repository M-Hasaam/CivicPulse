import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, SlidersHorizontal } from 'lucide-react';
import {
  type Category,
  type Complaint,
  type ComplaintPage,
  type Priority,
  type Status,
  listComplaints,
} from '../api/client';
import { FilterBar, type FilterValues } from '../components/FilterBar';
import { ComplaintTable } from '../components/ComplaintTable';
import { PaginationBar } from '../components/PaginationBar';

const DEFAULT_PAGE_SIZE = 10;
const emptyFilters: FilterValues = { category: '', priority: '', status: '' };

export function DashboardPage() {
  const [filters, setFilters] = useState<FilterValues>(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [data, setData] = useState<ComplaintPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComplaints = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: {
        category?: Category;
        priority?: Priority;
        status?: Status;
        page: number;
        page_size: number;
      } = { page, page_size: pageSize };
      if (filters.category) params.category = filters.category;
      if (filters.priority) params.priority = filters.priority;
      if (filters.status) params.status = filters.status;
      setData(await listComplaints(params));
    } catch {
      setError('Failed to load complaints. Check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);

  useEffect(() => { void fetchComplaints(); }, [fetchComplaints]);

  function handleFilterChange(next: FilterValues) {
    setFilters(next);
    setPage(1);
  }

  function handleStatusChange(_id: string, _status: Status) { /* Commit 4 */ }

  const items: Complaint[] = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="dashboard-page">

      {/* ── Header ─────────────────────────────── */}
      <div className="dashboard-header">
        <div>
          <h2 className="dashboard-title">Operations Dashboard</h2>
          <p className="dashboard-subtitle">
            {data
              ? `${total.toLocaleString()} complaint${total !== 1 ? 's' : ''} in the system`
              : 'Loading…'}
          </p>
        </div>
        <button
          id="dashboard-refresh-btn"
          type="button"
          onClick={() => void fetchComplaints()}
          disabled={loading}
          className="btn btn-secondary dashboard-refresh-btn"
        >
          <RefreshCw size={14} className={loading ? 'spinner' : ''} />
          Refresh
        </button>
      </div>

      {/* ── Filter panel ───────────────────────── */}
      <div className="filter-panel">
        <div className="filter-panel-label">
          <SlidersHorizontal size={13} />
          Filters
        </div>
        <FilterBar filters={filters} onChange={handleFilterChange} />
      </div>

      {/* ── Error ──────────────────────────────── */}
      {error && (
        <div role="alert" className="dashboard-error">
          {error}
        </div>
      )}

      {/* ── Skeleton ───────────────────────────── */}
      {loading && !data && (
        <div className="skeleton-list">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="skeleton-row" style={{ opacity: 1 - i * 0.1 }} />
          ))}
        </div>
      )}

      {/* ── Table + pagination ─────────────────── */}
      {data && (
        <div className="table-section">
          <ComplaintTable items={items} onStatusChange={handleStatusChange} />
          <PaginationBar
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
            onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
          />
        </div>
      )}
    </div>
  );
}

export default DashboardPage;
