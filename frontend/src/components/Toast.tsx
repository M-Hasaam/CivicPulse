import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, X } from 'lucide-react';

export type ToastVariant = 'success' | 'error';

export interface ToastMessage {
  id: number;
  variant: ToastVariant;
  message: string;
}

interface ToastProps {
  toast: ToastMessage;
  onDismiss: (id: number) => void;
}

/** Auto-dismisses after 5 s; can also be dismissed manually. */
export function Toast({ toast, onDismiss }: ToastProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setVisible(false), 5000);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!visible) {
      const t = setTimeout(() => onDismiss(toast.id), 300);
      return () => clearTimeout(t);
    }
  }, [visible, toast.id, onDismiss]);

  const isError = toast.variant === 'error';

  return (
    <div className={`toast toast-${toast.variant}${visible ? ' toast-in' : ' toast-out'}`} role="alert">
      <span className="toast-icon">
        {isError ? <XCircle size={16} /> : <CheckCircle2 size={16} />}
      </span>
      <span className="toast-message">{toast.message}</span>
      <button
        type="button"
        className="toast-close"
        onClick={() => setVisible(false)}
        aria-label="Dismiss"
      >
        <X size={13} />
      </button>
    </div>
  );
}

/** Renders a stack of toasts. Place once near the content that generates them. */
interface ToastStackProps {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}

export function ToastStack({ toasts, onDismiss }: ToastStackProps) {
  if (toasts.length === 0) return null;
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
