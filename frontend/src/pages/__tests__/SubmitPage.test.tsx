import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiConflictError,
  ApiRateLimitError,
  ApiValidationError,
  createComplaint,
} from '../../api/client';
import { SubmitPage } from '../SubmitPage';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return { ...actual, createComplaint: vi.fn() };
});

const mockCreateComplaint = vi.mocked(createComplaint);

const VALID_TEXT = 'Main water pipeline burst near Street 12 flooding basements';
const VALID_LOCATION = 'Sector G-10, Street 12';

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/what happened/i), VALID_TEXT);
  await user.type(screen.getByLabelText(/location/i), VALID_LOCATION);
}

beforeEach(() => {
  mockCreateComplaint.mockReset();
});

describe('SubmitPage', () => {
  it('rejects a too-short complaint before calling the API', async () => {
    const user = userEvent.setup();
    render(<SubmitPage />);

    await user.type(screen.getByLabelText(/what happened/i), 'too short');
    await user.type(screen.getByLabelText(/location/i), VALID_LOCATION);
    await user.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(await screen.findByText(/at least 10 characters/i)).toBeInTheDocument();
    expect(mockCreateComplaint).not.toHaveBeenCalled();
  });

  it('clears a field error as soon as the citizen edits that field', async () => {
    const user = userEvent.setup();
    render(<SubmitPage />);

    await user.type(screen.getByLabelText(/location/i), VALID_LOCATION);
    await user.click(screen.getByRole('button', { name: /submit complaint/i }));
    expect(await screen.findByText(/at least 10 characters/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/what happened/i), VALID_TEXT);
    expect(screen.queryByText(/at least 10 characters/i)).not.toBeInTheDocument();
  });

  it('renders an honest loading state while the AI call is in flight', async () => {
    type CreatedComplaint = Awaited<ReturnType<typeof createComplaint>>;
    let resolveCreate: (value: CreatedComplaint) => void = () => {};
    mockCreateComplaint.mockReturnValue(
      new Promise<CreatedComplaint>((resolve) => {
        resolveCreate = resolve;
      }),
    );
    const user = userEvent.setup();
    render(<SubmitPage />);
    await fillValidForm(user);

    await user.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(screen.getByRole('button', { name: /analysing complaint/i })).toBeDisabled();
    expect(screen.getByText(/can take a few seconds/i)).toBeInTheDocument();

    resolveCreate({
      id: '1',
      text: VALID_TEXT,
      location: VALID_LOCATION,
      reporter_contact: null,
      category: 'water',
      priority: 'high',
      status: 'open',
      ai_summary: 'x',
      triaged_by: 'llm:groq',
      triage_latency_ms: 500,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /analysing/i })).not.toBeInTheDocument(),
    );
  });

  it('renders category, priority, AI summary and provider on success', async () => {
    mockCreateComplaint.mockResolvedValue({
      id: '1',
      text: VALID_TEXT,
      location: VALID_LOCATION,
      reporter_contact: null,
      category: 'water',
      priority: 'high',
      status: 'open',
      ai_summary: 'Burst water pipeline flooding basements',
      triaged_by: 'llm:groq',
      triage_latency_ms: 732,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    } as unknown as Awaited<ReturnType<typeof createComplaint>>);
    const user = userEvent.setup();
    render(<SubmitPage />);
    await fillValidForm(user);

    await user.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(await screen.findByText('water')).toBeInTheDocument();
    expect(screen.getByText(/high priority/i)).toBeInTheDocument();
    expect(screen.getByText('Burst water pipeline flooding basements')).toBeInTheDocument();
    expect(screen.getByText(/llm:groq/i)).toBeInTheDocument();
  });

  it('surfaces the server\'s field-level validation errors, not a generic message', async () => {
    mockCreateComplaint.mockRejectedValue(
      new ApiValidationError({
        detail: 'Validation failed',
        errors: [{ field: 'text', in: 'body', message: 'Server says: too many URLs' }],
      }),
    );
    const user = userEvent.setup();
    render(<SubmitPage />);
    await fillValidForm(user);

    await user.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(await screen.findByText('Server says: too many URLs')).toBeInTheDocument();
  });

  it('shows the retry time from a 429 response', async () => {
    mockCreateComplaint.mockRejectedValue(new ApiRateLimitError(42));
    const user = userEvent.setup();
    render(<SubmitPage />);
    await fillValidForm(user);

    await user.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(await screen.findByText(/42 seconds/)).toBeInTheDocument();
  });

  it('shows a generic API error message for anything else', async () => {
    mockCreateComplaint.mockRejectedValue(new ApiConflictError('boom', 'open', 'resolved'));
    const user = userEvent.setup();
    render(<SubmitPage />);
    await fillValidForm(user);

    await user.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(await screen.findByText('boom')).toBeInTheDocument();
  });
});
