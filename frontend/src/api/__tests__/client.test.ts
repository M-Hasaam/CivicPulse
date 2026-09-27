import { describe, expect, it, vi } from 'vitest';
import {
  ApiConflictError,
  ApiRateLimitError,
  ApiValidationError,
  createComplaint,
  updateComplaintStatus,
} from '../client';

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

describe('createComplaint', () => {
  it('returns the created complaint on 201', async () => {
    const complaint = { id: '1', category: 'water', priority: 'high' };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(201, complaint)));

    const result = await createComplaint({ text: 'x'.repeat(20), location: 'Street 1' });
    expect(result).toEqual(complaint);
  });

  it('throws ApiValidationError with a field map on 400', async () => {
    const body = {
      detail: 'Validation failed',
      errors: [{ field: 'text', in: 'body', message: 'too short' }],
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(400, body)));

    await expect(createComplaint({ text: 'short', location: 'Street 1' })).rejects.toMatchObject({
      fields: { text: 'too short' },
    });
  });

  it('throws ApiRateLimitError with the Retry-After value on 429', async () => {
    const body = { detail: 'Too many requests. Please try again later.' };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(429, body, { 'Retry-After': '37' })),
    );

    const error = await createComplaint({ text: 'x'.repeat(20), location: 'Street 1' }).catch(
      (e: unknown) => e,
    );
    expect(error).toBeInstanceOf(ApiRateLimitError);
    expect((error as ApiRateLimitError).secondsUntilRetry).toBe(37);
  });
});

describe('updateComplaintStatus', () => {
  it('throws ApiConflictError with the server message verbatim on 409', async () => {
    const body = {
      detail: "Cannot change status from 'open' to 'resolved'. Allowed from 'open': in_progress, rejected.",
      current_status: 'open',
      attempted_status: 'resolved',
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(409, body)));

    const error = await updateComplaintStatus('1', 'resolved').catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiConflictError);
    expect((error as ApiConflictError).message).toBe(body.detail);
    expect((error as ApiConflictError).currentStatus).toBe('open');
  });
});

it('is exported as a class hierarchy usable with instanceof', () => {
  expect(new ApiValidationError({ detail: 'x', errors: [] })).toBeInstanceOf(Error);
});
