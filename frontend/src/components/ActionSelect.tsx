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
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);

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

  // Move focus onto the first option the moment the menu opens, so keyboard
  // users landing here via Enter/Space/ArrowDown can immediately navigate it.
  useEffect(() => {
    if (open) itemRefs.current[0]?.focus();
  }, [open]);

  function closeAndRefocusTrigger() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  function selectAt(index: number) {
    const option = options[index];
    if (!option) return;
    onSelect(option.value);
    closeAndRefocusTrigger();
  }

  function handleTriggerKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setOpen(true);
    }
  }

  function handleItemKeyDown(e: React.KeyboardEvent<HTMLLIElement>, index: number) {
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault();
        selectAt(index);
        break;
      case 'ArrowDown':
        e.preventDefault();
        itemRefs.current[(index + 1) % options.length]?.focus();
        break;
      case 'ArrowUp':
        e.preventDefault();
        itemRefs.current[(index - 1 + options.length) % options.length]?.focus();
        break;
      case 'Home':
        e.preventDefault();
        itemRefs.current[0]?.focus();
        break;
      case 'End':
        e.preventDefault();
        itemRefs.current[options.length - 1]?.focus();
        break;
      case 'Escape':
        e.preventDefault();
        closeAndRefocusTrigger();
        break;
      case 'Tab':
        setOpen(false);
        break;
    }
  }

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
        ref={triggerRef}
        type="button"
        className={`action-select-trigger${open ? ' open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={handleTriggerKeyDown}
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
          {options.map((o, index) => (
            <li
              key={o.value}
              ref={(el) => { itemRefs.current[index] = el; }}
              role="menuitem"
              tabIndex={-1}
              className="action-select-option"
              onClick={() => selectAt(index)}
              onKeyDown={(e) => handleItemKeyDown(e, index)}
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
