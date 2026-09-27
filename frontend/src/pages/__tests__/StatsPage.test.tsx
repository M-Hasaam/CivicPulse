import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getProviderMeta, getStats, type ProviderMeta, type StatsOut } from '../../api/client';
import { StatsPage } from '../StatsPage';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    getStats: vi.fn(),
    getProviderMeta: vi.fn(),
  };
});

const mockGetStats = vi.mocked(getStats);
const mockGetProviderMeta = vi.mocked(getProviderMeta);

const stats: StatsOut = {
  total_complaints: 32,
  by_category: { water: 12, roads: 8, electricity: 5 },
  by_priority: { high: 6, normal: 20, low: 6 },
  by_status: { open: 18, in_progress: 6, resolved: 6, rejected: 2 },
  avg_triage_latency_ms: 42.4,
};

const providerMeta: ProviderMeta = {
  active_provider: 'rules',
  fallback_provider: 'rules',
  triage_cache: { hits: 3, misses: 7, hit_rate: 0.3 },
  recent_outcomes: [
    {
      provider: 'rules',
      latency_ms: 4,
      fallback: false,
      cached: true,
      at: '2026-09-27T12:00:00Z',
    },
  ],
};

beforeEach(() => {
  mockGetStats.mockReset();
  mockGetProviderMeta.mockReset();
  mockGetStats.mockResolvedValue({ stats, cacheState: 'HIT' });
  mockGetProviderMeta.mockResolvedValue(providerMeta);
});

describe('StatsPage', () => {
  it('renders aggregate counts and the X-Cache state', async () => {
    render(<StatsPage />);

    expect(await screen.findByText('32')).toBeInTheDocument();
    expect(screen.getByText('HIT')).toBeInTheDocument();
    expect(screen.getByText('Water')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getAllByText('rules').length).toBeGreaterThan(0);
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('refreshes stats on request', async () => {
    const user = userEvent.setup();
    render(<StatsPage />);

    await screen.findByText('32');
    await user.click(screen.getByRole('button', { name: /refresh/i }));

    expect(mockGetStats).toHaveBeenCalledTimes(2);
    expect(mockGetProviderMeta).toHaveBeenCalledTimes(2);
  });
});
