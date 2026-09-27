import { type FormEvent, useState } from 'react';
import { Loader2, Send } from 'lucide-react';
import {
  ApiConflictError,
  ApiError,
  ApiRateLimitError,
  ApiValidationError,
  type Complaint,
  createComplaint,
} from '../api/client';

// Mirrors the server's rules (backend/app/schemas.py) so the citizen sees a
// problem before submitting - the server is still the one that decides.
// Never the other way around: these numbers are read from the contract, not
// invented here, and the server's answer always wins if it disagrees.
const TEXT_MIN = 10;
const TEXT_MAX = 2000;
const LOCATION_MIN = 3;
const LOCATION_MAX = 200;
const CONTACT_MAX = 100;

interface FormState {
  text: string;
  location: string;
  contact: string;
}

const emptyForm: FormState = { text: '', location: '', contact: '' };

function validate(form: FormState): Record<string, string> {
  const errors: Record<string, string> = {};
  const text = form.text.trim();
  const location = form.location.trim();
  const contact = form.contact.trim();

  if (text.length < TEXT_MIN) {
    errors.text = `Describe the complaint in at least ${TEXT_MIN} characters.`;
  } else if (text.length > TEXT_MAX) {
    errors.text = `Keep it under ${TEXT_MAX} characters.`;
  }

  if (location.length < LOCATION_MIN) {
    errors.location = `Enter a location of at least ${LOCATION_MIN} characters.`;
  } else if (location.length > LOCATION_MAX) {
    errors.location = `Keep the location under ${LOCATION_MAX} characters.`;
  }

  if (contact.length > CONTACT_MAX) {
    errors.contact = `Keep the contact under ${CONTACT_MAX} characters.`;
  }

  return errors;
}

const PRIORITY_BADGE: Record<string, string> = {
  high: 'badge-high',
  normal: 'badge-normal',
  low: 'badge-low',
};

export function SubmitPage() {
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Complaint | null>(null);

  function updateField(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    // Clear that field's error the moment the citizen edits it, rather than
    // leaving a stale complaint on screen after they've already fixed it.
    setFieldErrors((prev) => {
      if (!(field in prev)) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    const clientErrors = validate(form);
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setSubmitting(true);
    try {
      const complaint = await createComplaint({
        text: form.text.trim(),
        location: form.location.trim(),
        reporter_contact: form.contact.trim() || null,
      });
      setResult(complaint);
      setForm(emptyForm);
      setFieldErrors({});
    } catch (error) {
      if (error instanceof ApiValidationError) {
        // The server's own field-level errors - what the client checked was
        // only a mirror, and the server's answer always wins.
        setFieldErrors(error.fields);
      } else if (error instanceof ApiRateLimitError) {
        setFormError(
          `Too many complaints submitted. Try again in ${error.secondsUntilRetry} seconds.`,
        );
      } else if (error instanceof ApiConflictError || error instanceof ApiError) {
        setFormError(error.message);
      } else {
        setFormError('Something went wrong submitting your complaint. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '1.5rem' }}>Submit a complaint</h2>

      {result && (
        <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }} role="status">
          <p style={{ fontWeight: 600, marginBottom: '0.75rem' }}>Complaint received.</p>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
              {result.category}
            </span>
            <span className={`badge ${PRIORITY_BADGE[result.priority] ?? ''}`}>
              {result.priority} priority
            </span>
          </div>
          {result.ai_summary && (
            <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              {result.ai_summary}
            </p>
          )}
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            Triaged by <span className="mono">{result.triaged_by}</span> in{' '}
            {result.triage_latency_ms} ms
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <label className="form-label" htmlFor="complaint-text">
            What happened?
          </label>
          <textarea
            id="complaint-text"
            className="form-textarea"
            value={form.text}
            onChange={(e) => updateField('text', e.target.value)}
            disabled={submitting}
            placeholder="Describe the complaint - what, where, and since when."
            aria-invalid={Boolean(fieldErrors.text)}
            aria-describedby={fieldErrors.text ? 'complaint-text-error' : undefined}
          />
          {fieldErrors.text && (
            <p className="form-error" id="complaint-text-error">
              {fieldErrors.text}
            </p>
          )}
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="complaint-location">
            Location
          </label>
          <input
            id="complaint-location"
            className="form-input"
            type="text"
            value={form.location}
            onChange={(e) => updateField('location', e.target.value)}
            disabled={submitting}
            placeholder="Sector, street or landmark"
            aria-invalid={Boolean(fieldErrors.location)}
            aria-describedby={fieldErrors.location ? 'complaint-location-error' : undefined}
          />
          {fieldErrors.location && (
            <p className="form-error" id="complaint-location-error">
              {fieldErrors.location}
            </p>
          )}
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="complaint-contact">
            Contact (optional)
          </label>
          <input
            id="complaint-contact"
            className="form-input"
            type="text"
            value={form.contact}
            onChange={(e) => updateField('contact', e.target.value)}
            disabled={submitting}
            placeholder="Phone number, so operations can follow up"
            aria-invalid={Boolean(fieldErrors.contact)}
            aria-describedby={fieldErrors.contact ? 'complaint-contact-error' : undefined}
          />
          {fieldErrors.contact && (
            <p className="form-error" id="complaint-contact-error">
              {fieldErrors.contact}
            </p>
          )}
        </div>

        {formError && (
          <p className="form-error" role="alert" style={{ marginBottom: '1rem' }}>
            {formError}
          </p>
        )}

        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? (
            <>
              <Loader2 size={16} className="spinner" /> Analysing complaint&hellip;
            </>
          ) : (
            <>
              <Send size={16} /> Submit complaint
            </>
          )}
        </button>
        {submitting && (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', marginTop: '0.5rem' }}>
            This calls an AI model to triage your complaint - it can take a few seconds.
          </p>
        )}
      </form>
    </div>
  );
}

export default SubmitPage;
