import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
}

interface CustomSelectProps {
  id?: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  ariaLabel?: string;
}

export function CustomSelect({ id, value, options, onChange, ariaLabel }: CustomSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);

  const selected = options.find((o) => o.value === value) ?? options[0];
  const selectedIndex = options.findIndex((o) => o.value === selected.value);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close on Escape
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  // Move focus onto the currently selected option when the listbox opens,
  // matching how a native <select> behaves for keyboard users.
  useEffect(() => {
    if (open) itemRefs.current[selectedIndex < 0 ? 0 : selectedIndex]?.focus();
  }, [open, selectedIndex]);

  function closeAndRefocusTrigger() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  function chooseAt(index: number) {
    const option = options[index];
    if (!option) return;
    onChange(option.value);
    closeAndRefocusTrigger();
  }

  function handleTriggerKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setOpen(true);
    }
  }

  function handleItemKeyDown(e: React.KeyboardEvent<HTMLLIElement>, index: number) {
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault();
        chooseAt(index);
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

  return (
    <div ref={ref} className="custom-select-root" aria-label={ariaLabel}>
      <button
        ref={triggerRef}
        id={id}
        type="button"
        className={`custom-select-trigger${open ? ' open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={handleTriggerKeyDown}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>{selected.label}</span>
        <ChevronDown size={13} className={`custom-select-chevron${open ? ' rotated' : ''}`} />
      </button>

      {open && (
        <ul className="custom-select-dropdown" role="listbox">
          {options.map((o, index) => (
            <li
              key={o.value}
              ref={(el) => { itemRefs.current[index] = el; }}
              role="option"
              tabIndex={-1}
              aria-selected={o.value === value}
              className={`custom-select-option${o.value === value ? ' selected' : ''}`}
              onClick={() => chooseAt(index)}
              onKeyDown={(e) => handleItemKeyDown(e, index)}
            >
              <span>{o.label}</span>
              {o.value === value && <Check size={12} className="custom-select-check" />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
