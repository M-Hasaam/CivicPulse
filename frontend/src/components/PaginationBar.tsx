import { ChevronLeft, ChevronRight } from 'lucide-react';
import { CustomSelect, type SelectOption } from './CustomSelect';

const PAGE_SIZE_OPTIONS: SelectOption[] = [
  { value: '5',  label: '5 / page' },
  { value: '10', label: '10 / page' },
  { value: '20', label: '20 / page' },
  { value: '50', label: '50 / page' },
];

interface PaginationBarProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

export function PaginationBar({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: PaginationBarProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (total === 0) return null;

  const from = Math.min((page - 1) * pageSize + 1, total);
  const to   = Math.min(page * pageSize, total);

  return (
    <div className="pagination-bar">
      {/* Left: range label */}
      <span className="pagination-info">
        {from}–{to} of {total.toLocaleString()} complaint{total !== 1 ? 's' : ''}
      </span>

      {/* Center: prev / page indicator / next */}
      <div className="pagination-controls">
        <button
          id="pagination-prev-btn"
          type="button"
          className="pagination-btn"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft size={15} /> Prev
        </button>

        <span className="pagination-pages">{page} / {totalPages}</span>

        <button
          id="pagination-next-btn"
          type="button"
          className="pagination-btn"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          Next <ChevronRight size={15} />
        </button>
      </div>

      {/* Right: page-size picker */}
      <CustomSelect
        id="pagination-page-size"
        value={String(pageSize)}
        options={PAGE_SIZE_OPTIONS}
        onChange={(v) => {
          onPageSizeChange(Number(v));
          onPageChange(1); // reset to first page when size changes
        }}
        ariaLabel="Complaints per page"
      />
    </div>
  );
}
