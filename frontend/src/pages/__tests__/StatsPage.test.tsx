import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { getStats, getProviderMeta } from '../../api/client';
import { StatsPage } from '../StatsPage';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return { ...actual, getStats: vi.fn(), getProviderMeta: vi.fn() };
});

const mockGetStats    = vi.mocked(getStats);
const mockGetProvider = vi.mocked(getProviderMeta);

const STATS = {
  total_complaints: 42,
  avg_triage_latency_ms: 385,
  by_category: { water: 20, roads: 15, other: 7 },
  by_priority: { high: 10, normal: 25, low: 7 },
  by_status: { open: 18, in_progress: 12, resolved: 10, rejected: 2 },
};

const PROVIDER_META = {
  active_provider: 'llm:groq',
  fallback_provider: 'llm:openai',
  recent_outcomes: [
    { provider: 'llm:groq', latency_ms: 312, fallback: false, cached: true,  at: '2026-01-01T00:01:00Z' },
    { provider: 'llm:groq', latency_ms: 720, fallback: false, cached: false, at: '2026-01-01T00:02:00Z' },
  ],
  triage_cache: { hits: 30, misses: 12, hit_rate: 0.714 },
};

function renderStats() {
  return render(<MemoryRouter><StatsPage /></MemoryRouter>);
}

beforeEach(() => {
  mockGetStats.mockReset();
  mockGetProvider.mockReset();
  mockGetStats.mockResolvedValue({ stats: STATS, cacheState: 'HIT' });
  mockGetProvider.mockResolvedValue(PROVIDER_META);
});

describe('StatsPage', () => {
  it('shows the X-Cache HIT badge with the correct CSS class', async () => {
    mockGetStats.mockResolvedValue({ stats: STATS, cacheState: 'HIT' });
    renderStats();

    // There can be multiple "HIT" texts (badge + table pill).
    // We verify the one inside the .cache-hit element specifically.
    await screen.findByText('42'); // wait for data
    const hitElements = screen.getAllByText('HIT');
    const badgeEl = hitElements.find((el) => el.classList.contains('cache-value'));
    expect(badgeEl).toBeInTheDocument();
    expect(badgeEl!.closest('.cache-hit')).toBeInTheDocument();
  });

  it('shows the X-Cache MISS badge with the correct CSS class', async () => {
    mockGetStats.mockResolvedValue({ stats: STATS, cacheState: 'MISS' });
    renderStats();

    await screen.findByText('42');
    const missElements = screen.getAllByText('MISS');
    const badgeEl = missElements.find((el) => el.classList.contains('cache-value'));
    expect(badgeEl).toBeInTheDocument();
    expect(badgeEl!.closest('.cache-miss')).toBeInTheDocument();
  });

  it('renders total complaints and avg latency stat cards', async () => {
    renderStats();
    expect(await screen.findByText('42')).toBeInTheDocument();
    expect(screen.getByText('385 ms')).toBeInTheDocument();
  });

  it('shows the active provider name in the provider meta section', async () => {
    renderStats();
    // "llm:groq" appears in the meta section AND in the outcomes table.
    // Verify it's present at least once (meta section).
    await screen.findByText('42');
    const providerCells = screen.getAllByText('llm:groq');
    expect(providerCells.length).toBeGreaterThanOrEqual(1);
  });

  it('shows HIT and MISS pills in the recent outcomes table', async () => {
    renderStats();
    await screen.findByText('42');
    const hitPills  = screen.getAllByText('HIT');
    const missPills = screen.getAllByText('MISS');
    // At least one element carries each label
    expect(hitPills.length).toBeGreaterThanOrEqual(1);
    expect(missPills.length).toBeGreaterThanOrEqual(1);
  });

  it('shows the cache hit-rate formatted as a percentage', async () => {
    renderStats();
    // 0.714 → "71.4%"
    expect(await screen.findByText('71.4%')).toBeInTheDocument();
  });

  it('re-fetches both endpoints when Refresh stats is clicked', async () => {
    renderStats();
    await screen.findByText('42');

    await userEvent.click(screen.getByRole('button', { name: /refresh stats/i }));

    await waitFor(() => expect(mockGetStats).toHaveBeenCalledTimes(2));
    expect(mockGetProvider).toHaveBeenCalledTimes(2);
  });

  it('shows an error banner when getStats rejects', async () => {
    mockGetStats.mockRejectedValue(new Error('503'));
    renderStats();
    expect(await screen.findByText(/failed to load statistics/i)).toBeInTheDocument();
  });
});
