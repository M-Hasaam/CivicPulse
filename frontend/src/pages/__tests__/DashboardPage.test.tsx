import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
  ApiConflictError,
  ApiRateLimitError,
  type Complaint,
  listComplaints,
  updateComplaintStatus,
} from '../../api/client';
import { DashboardPage } from '../DashboardPage';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return { ...actual, listComplaints: vi.fn(), updateComplaintStatus: vi.fn() };
});

const mockList   = vi.mocked(listComplaints);
const mockUpdate = vi.mocked(updateComplaintStatus);

const COMPLAINT_OPEN: Complaint = {
  id: 'c-open-1',
  text: 'Water pipe burst near the main junction',
  location: 'Sector G-10, Street 12',
  reporter_contact: null,
  category: 'water' as const,
  priority: 'high'  as const,
  status:   'open'  as const,
  ai_summary: 'Burst pipe flooding area',
  triaged_by: 'llm:groq',
  triage_latency_ms: 450,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const COMPLAINT_RESOLVED = {
  ...COMPLAINT_OPEN,
  id: 'c-resolved-1',
  status: 'resolved' as const,
  location: 'Sector F-8, Street 4',
};

const PAGE = (items = [COMPLAINT_OPEN]) => ({
  items, total: items.length, page: 1, page_size: 10,
});

function renderDash() {
  return render(<MemoryRouter><DashboardPage /></MemoryRouter>);
}

beforeEach(() => {
  mockList.mockReset();
  mockUpdate.mockReset();
  mockList.mockResolvedValue(PAGE());
});

describe('DashboardPage', () => {
  it('renders a row for each complaint returned by the API', async () => {
    mockList.mockResolvedValue(PAGE([COMPLAINT_OPEN, COMPLAINT_RESOLVED]));
    renderDash();

    expect(await screen.findByText('Sector G-10, Street 12')).toBeInTheDocument();
    expect(screen.getByText('Sector F-8, Street 4')).toBeInTheDocument();
  });

  it('shows the empty state when the API returns no items', async () => {
    mockList.mockResolvedValue(PAGE([]));
    renderDash();

    expect(await screen.findByText(/no complaints found/i)).toBeInTheDocument();
  });

  it('shows an error banner when listComplaints rejects', async () => {
    mockList.mockRejectedValue(new Error('network down'));
    renderDash();

    expect(await screen.findByText(/failed to load complaints/i)).toBeInTheDocument();
  });

  it('calls updateComplaintStatus and shows a success toast after a valid transition', async () => {
    mockUpdate.mockResolvedValue({ ...COMPLAINT_OPEN, status: 'in_progress' });
    renderDash();

    // Wait for data to load
    await screen.findByText('Sector G-10, Street 12');

    // Open the action dropdown (ActionSelect trigger button)
    const moveBtn = screen.getByRole('button', { name: /move to/i });
    await userEvent.click(moveBtn);

    // The dropdown renders options as <li role="menuitem">
    const inProgressItem = await screen.findByRole('menuitem', { name: /in progress/i });
    await userEvent.click(inProgressItem);

    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith('c-open-1', 'in_progress'),
    );

    expect(await screen.findByText(/status updated/i)).toBeInTheDocument();
    // List should be re-fetched after success (initial + post-update)
    expect(mockList).toHaveBeenCalledTimes(2);
  });

  it('surfaces the server\'s 409 message verbatim — never a generic string', async () => {
    const SERVER_MSG = 'Cannot transition from open to resolved directly.';
    mockUpdate.mockRejectedValue(
      new ApiConflictError(SERVER_MSG, 'open', 'resolved'),
    );
    renderDash();

    await screen.findByText('Sector G-10, Street 12');
    await userEvent.click(screen.getByRole('button', { name: /move to/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: /in progress/i }));

    expect(await screen.findByText(SERVER_MSG)).toBeInTheDocument();
    // List must NOT be re-fetched on error
    expect(mockList).toHaveBeenCalledTimes(1);
  });

  it('shows the Retry-After seconds from a 429 rate-limit response', async () => {
    mockUpdate.mockRejectedValue(new ApiRateLimitError(30));
    renderDash();

    await screen.findByText('Sector G-10, Street 12');
    await userEvent.click(screen.getByRole('button', { name: /move to/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: /in progress/i }));

    expect(await screen.findByText(/rate limited.*30s/i)).toBeInTheDocument();
  });

  it('does not encode terminal-state transition rules in the frontend', async () => {
    mockList.mockResolvedValue(PAGE([COMPLAINT_RESOLVED]));
    renderDash();

    await screen.findByText('Sector F-8, Street 4');
    await userEvent.click(screen.getByRole('button', { name: /move to/i }));

    expect(screen.getByRole('menuitem', { name: /open/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /in progress/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /rejected/i })).toBeInTheDocument();
  });

  it('passes the active filter to listComplaints when category is changed', async () => {
    renderDash();
    await screen.findByText('Sector G-10, Street 12');

    // Open the category CustomSelect — its accessible name is the current selected label
    const categoryBtn = screen.getByRole('button', { name: /all categories/i });
    await userEvent.click(categoryBtn);

    // Options are <li role="option"> inside the custom dropdown
    const waterOption = await screen.findByRole('option', { name: /water/i });
    await userEvent.click(waterOption);

    await waitFor(() =>
      expect(mockList).toHaveBeenLastCalledWith(
        expect.objectContaining({ category: 'water', page: 1 }),
      ),
    );
  });
});
