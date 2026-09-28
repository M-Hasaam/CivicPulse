import type { Status } from '../api/client';

const STATUS_CLS: Record<Status, string> = {
  open:        'status-open',
  in_progress: 'status-in-progress',
  resolved:    'status-resolved',
  rejected:    'status-rejected',
};

const STATUS_LABEL: Record<Status, string> = {
  open: 'Open', in_progress: 'In Progress', resolved: 'Resolved', rejected: 'Rejected',
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`status-badge ${STATUS_CLS[status]}`}>
      <span className="status-dot" />
      {STATUS_LABEL[status]}
    </span>
  );
}
