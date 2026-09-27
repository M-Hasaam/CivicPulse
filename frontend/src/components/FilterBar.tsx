import type { Category, Priority, Status } from '../api/client';
import { CustomSelect, type SelectOption } from './CustomSelect';

const CATEGORIES: SelectOption[] = [
  { value: '', label: 'All categories' },
  { value: 'water',        label: '💧 Water' },
  { value: 'electricity',  label: '⚡ Electricity' },
  { value: 'sanitation',   label: '🗑️ Sanitation' },
  { value: 'roads',        label: '🚧 Roads' },
  { value: 'streetlights', label: '🔦 Streetlights' },
  { value: 'other',        label: '📋 Other' },
];

const PRIORITIES: SelectOption[] = [
  { value: '', label: 'All priorities' },
  { value: 'high',   label: '🔴 High' },
  { value: 'normal', label: '🟡 Normal' },
  { value: 'low',    label: '🔵 Low' },
];

const STATUSES: SelectOption[] = [
  { value: '',            label: 'All statuses' },
  { value: 'open',        label: '🔵 Open' },
  { value: 'in_progress', label: '🟡 In Progress' },
  { value: 'resolved',    label: '🟢 Resolved' },
  { value: 'rejected',    label: '🔴 Rejected' },
];

export interface FilterValues {
  category: Category | '';
  priority: Priority | '';
  status: Status | '';
}

interface FilterBarProps {
  filters: FilterValues;
  onChange: (next: FilterValues) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  function set<K extends keyof FilterValues>(key: K, value: FilterValues[K]) {
    onChange({ ...filters, [key]: value });
  }

  const active =
    filters.category !== '' || filters.priority !== '' || filters.status !== '';

  return (
    <div className="filter-bar">
      <CustomSelect
        id="filter-category"
        value={filters.category}
        options={CATEGORIES}
        onChange={(v) => set('category', v as Category | '')}
        ariaLabel="Filter by category"
      />
      <CustomSelect
        id="filter-priority"
        value={filters.priority}
        options={PRIORITIES}
        onChange={(v) => set('priority', v as Priority | '')}
        ariaLabel="Filter by priority"
      />
      <CustomSelect
        id="filter-status"
        value={filters.status}
        options={STATUSES}
        onChange={(v) => set('status', v as Status | '')}
        ariaLabel="Filter by status"
      />

      {active && (
        <button
          id="filter-clear-btn"
          type="button"
          className="filter-clear"
          onClick={() => onChange({ category: '', priority: '', status: '' })}
        >
          ✕ Clear
        </button>
      )}
    </div>
  );
}
