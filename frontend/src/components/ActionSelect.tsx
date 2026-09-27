import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ArrowRight, Loader2 } from 'lucide-react';

export interface ActionOption {
  value: string;
  label: string;
}

interface ActionSelectProps {
  options: ActionOption[];
  onSelect: (value: string) => void;
  ariaLabel?: string;
  disabled?: boolean;
}

/**
 * A stateless action dropdown — opens a themed panel, fires onSelect on click,
 * then closes. Does NOT track a persistent selected value (unlike CustomSelect).
 * Used for status transition actions in the dashboard table.
 */
export function ActionSelect({ options, onSelect, ariaLabel, disabled = false }: ActionSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  if (disabled) {
    return (
      <button type="button" className="action-select-trigger" disabled
        style={{ opacity: 0.55, cursor: 'not-allowed' }}>
        <Loader2 size={12} className="spinner" /> Updating…
      </button>
    );
  }

  if (options.length === 0) return <span className="col-terminal">—</span>;

  return (
    <div ref={ref} className="action-select-root" aria-label={ariaLabel}>
      <button
        type="button"
        className={`action-select-trigger${open ? ' open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        Move to…
        <ChevronDown
          size={12}
          className={`action-select-chevron${open ? ' rotated' : ''}`}
        />
      </button>

      {open && (
        <ul className="action-select-dropdown" role="menu">
          {options.map((o) => (
            <li
              key={o.value}
              role="menuitem"
              className="action-select-option"
              onClick={() => {
                onSelect(o.value);
                setOpen(false);
              }}
            >
              <ArrowRight size={11} className="action-select-icon" />
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
