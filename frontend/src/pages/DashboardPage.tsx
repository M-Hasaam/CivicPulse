import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, SlidersHorizontal } from 'lucide-react';
import {
  ApiConflictError,
  ApiRateLimitError,
  type Category,
  type Complaint,
  type ComplaintPage,
  type Priority,
  type Status,
  listComplaints,
  updateComplaintStatus,
} from '../api/client';
import { FilterBar, type FilterValues } from '../components/FilterBar';
import { ComplaintTable } from '../components/ComplaintTable';
import { PaginationBar } from '../components/PaginationBar';
import { ToastStack, type ToastMessage } from '../components/Toast';

const DEFAULT_PAGE_SIZE = 10;
const emptyFilters: FilterValues = { category: '', priority: '', status: '' };

let toastCounter = 0;
function nextToastId() { return ++toastCounter; }

export function DashboardPage() {
  const [filters, setFilters] = useState<FilterValues>(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [data, setData] = useState<ComplaintPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  // Track in-flight status changes to show a spinner on the relevant row
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());

  // Stable ref so that toast helpers don't recreate fetchComplaints
  const addToast = useCallback((variant: ToastMessage['variant'], message: string) => {
    setToasts((prev) => [...prev, { id: nextToastId(), variant, message }]);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

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

  /**
   * Status transition handler — this is the heart of Commit 4.
   *
   * Success path  → re-fetches the page so the row reflects the new status.
   * 409 path      → surfaces the server's `detail` string verbatim. The
   *                 frontend never decides what is or isn't a valid transition;
   *                 the server's message is the only source of truth.
   * 429 path      → shows the retry-after time from the response header.
   * Other errors  → generic fallback message.
   */
  async function handleStatusChange(id: string, status: Status) {
    setPendingIds((prev) => new Set(prev).add(id));
    try {
      await updateComplaintStatus(id, status);
      addToast('success', `Status updated to "${status.replace('_', ' ')}".`);
      // Re-fetch so the updated row appears without a full page reload
      await fetchComplaints();
    } catch (err) {
      if (err instanceof ApiConflictError) {
        // Server's verbatim message — never a generic frontend string
        addToast('error', err.message);
      } else if (err instanceof ApiRateLimitError) {
        addToast('error', `Rate limited — try again in ${err.secondsUntilRetry}s.`);
      } else {
        addToast('error', 'Failed to update status. Please try again.');
      }
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

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

      {/* ── Fetch error ────────────────────────── */}
      {error && (
        <div role="alert" className="dashboard-error">{error}</div>
      )}

      {/* ── Toast stack (status transition feedback) ── */}
      <ToastStack toasts={toasts} onDismiss={dismissToast} />

      {/* ── Loading skeleton ───────────────────── */}
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
          <ComplaintTable
            items={items}
            pendingIds={pendingIds}
            onStatusChange={handleStatusChange}
          />
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
