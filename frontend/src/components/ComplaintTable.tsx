import type { Complaint, Status } from '../api/client';
import { StatusBadge } from './StatusBadge';
import { ActionSelect, type ActionOption } from './ActionSelect';

const PRIORITY_CONFIG: Record<string, { label: string; cls: string }> = {
  high:   { label: 'High',   cls: 'priority-high' },
  normal: { label: 'Normal', cls: 'priority-normal' },
  low:    { label: 'Low',    cls: 'priority-low' },
};

const CATEGORY_CONFIG: Record<string, { emoji: string; cls: string }> = {
  water:        { emoji: '💧', cls: 'cat-water' },
  electricity:  { emoji: '⚡', cls: 'cat-electricity' },
  sanitation:   { emoji: '🗑️', cls: 'cat-sanitation' },
  roads:        { emoji: '🚧', cls: 'cat-roads' },
  streetlights: { emoji: '🔦', cls: 'cat-streetlights' },
  other:        { emoji: '📋', cls: 'cat-other' },
};

function formatRelative(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const NEXT_STATUSES: Record<Status, Status[]> = {
  open:        ['in_progress', 'rejected'],
  in_progress: ['resolved', 'rejected'],
  resolved:    [],
  rejected:    [],
};

const STATUS_LABELS: Record<Status, string> = {
  open: 'Open', in_progress: 'In Progress', resolved: 'Resolved', rejected: 'Rejected',
};

interface ComplaintTableProps {
  items: Complaint[];
  onStatusChange: (id: string, status: Status) => void;
}

export function ComplaintTable({ items, onStatusChange }: ComplaintTableProps) {
  if (items.length === 0) {
    return (
      <div className="table-empty">
        <span className="table-empty-icon">🗂️</span>
        <p className="table-empty-title">No complaints found</p>
        <p className="table-empty-sub">Try adjusting or clearing your filters</p>
      </div>
    );
  }

  return (
    <div className="complaints-table-wrap">
      <div className="complaints-table-accent" />
      <div className="complaints-table-scroll">
        <table className="complaints-table">
          <thead>
            <tr>
              <th>Location / Summary</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Submitted</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <ComplaintRow key={c.id} complaint={c} onStatusChange={onStatusChange} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ComplaintRow({ complaint: c, onStatusChange }: { complaint: Complaint; onStatusChange: (id: string, s: Status) => void }) {
  const next = NEXT_STATUSES[c.status];
  const cat  = CATEGORY_CONFIG[c.category];
  const pri  = PRIORITY_CONFIG[c.priority];

  return (
    <tr className="complaint-row">
      <td className="col-location">
        <span className="col-location-name" title={c.location}>{c.location}</span>
        {c.ai_summary && (
          <span className="col-location-summary" title={c.ai_summary}>{c.ai_summary}</span>
        )}
      </td>

      <td>
        <span className={`cat-badge ${cat?.cls ?? 'cat-other'}`}>
          {cat?.emoji} {c.category}
        </span>
      </td>

      <td>
        <span className={`pri-badge ${pri?.cls ?? ''}`}>{pri?.label ?? c.priority}</span>
      </td>

      <td><StatusBadge status={c.status} /></td>

      <td className="col-date">{formatRelative(c.created_at)}</td>

      <td>
        <ActionSelect
          options={next.map((s): ActionOption => ({ value: s, label: STATUS_LABELS[s] }))}
          onSelect={(v) => onStatusChange(c.id, v as Status)}
          ariaLabel={`Change status for ${c.location}`}
        />
      </td>
    </tr>
  );
}
