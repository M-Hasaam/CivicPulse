import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiConflictError,
  type Complaint,
  type ComplaintPage,
  listComplaints,
  updateComplaintStatus,
} from '../../api/client';
import { DashboardPage } from '../DashboardPage';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    listComplaints: vi.fn(),
    updateComplaintStatus: vi.fn(),
  };
});

const mockListComplaints = vi.mocked(listComplaints);
const mockUpdateComplaintStatus = vi.mocked(updateComplaintStatus);

const complaint: Complaint = {
  id: '11111111-1111-1111-1111-111111111111',
  text: 'Main water pipeline burst near Street 12 flooding basements',
  location: 'Sector G-10, Street 12',
  reporter_contact: null,
  category: 'water',
  priority: 'high',
  status: 'open',
  ai_summary: 'Burst water pipeline flooding basements',
  triaged_by: 'rules',
  triage_latency_ms: 3,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const page: ComplaintPage = {
  items: [complaint],
  total: 1,
  page: 1,
  page_size: 10,
};

beforeEach(() => {
  mockListComplaints.mockReset();
  mockUpdateComplaintStatus.mockReset();
  mockListComplaints.mockResolvedValue(page);
  mockUpdateComplaintStatus.mockResolvedValue({ ...complaint, status: 'in_progress' });
});

describe('DashboardPage', () => {
  it('loads complaints and sends filters to the API', async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);

    expect(await screen.findByText('Sector G-10, Street 12')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /all statuses/i }));
    await user.click(screen.getByRole('option', { name: /open/i }));

    await waitFor(() =>
      expect(mockListComplaints).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 10,
        status: 'open',
      }),
    );
  });

  it('does not encode valid transition rules in the frontend', async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);

    const row = (await screen.findByText('Sector G-10, Street 12')).closest('tr');
    expect(row).not.toBeNull();

    await user.click(within(row as HTMLElement).getByRole('button', { name: /move to/i }));

    expect(screen.getByRole('menuitem', { name: /in progress/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /resolved/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /rejected/i })).toBeInTheDocument();
  });

  it('surfaces the server 409 message verbatim during status updates', async () => {
    mockUpdateComplaintStatus.mockRejectedValue(
      new ApiConflictError(
        "Cannot change status from 'open' to 'resolved'. Allowed from 'open': in_progress, rejected.",
        'open',
        'resolved',
      ),
    );
    const user = userEvent.setup();
    render(<DashboardPage />);

    const row = (await screen.findByText('Sector G-10, Street 12')).closest('tr');
    expect(row).not.toBeNull();

    await user.click(within(row as HTMLElement).getByRole('button', { name: /move to/i }));
    await user.click(screen.getByRole('menuitem', { name: /resolved/i }));

    expect(
      await screen.findByText(
        "Cannot change status from 'open' to 'resolved'. Allowed from 'open': in_progress, rejected.",
      ),
    ).toBeInTheDocument();
  });
});
