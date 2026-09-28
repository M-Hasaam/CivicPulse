/**
 * Typed API client generated from the backend's OpenAPI schema.
 *
 * HOW THE TYPES ARE GENERATED
 * ─────────────────────────────────────────────────────────────────────────────
 * 1. Start the backend:  python -m uvicorn app.main:app --reload
 * 2. Fetch the schema:   curl http://localhost:8000/openapi.json -o src/api/openapi.json
 * 3. Generate types:     npm run generate:api
 *    (runs: openapi-typescript src/api/openapi.json -o src/api/schema.ts)
 *
 * src/api/schema.ts is committed so the frontend can be built without the
 * backend running, but it must be regenerated whenever the backend schema
 * changes (new fields, new endpoints, changed enums).
 *
 * WHY openapi-fetch
 * ─────────────────────────────────────────────────────────────────────────────
 * openapi-fetch wraps the generated schema in a fetch client that enforces the
 * correct request body shape and response type for every endpoint at compile
 * time. A mismatched path, wrong body field or missing required param is a
 * TypeScript error, not a runtime 422.
 */
import createClient from 'openapi-fetch';
import type { components, paths } from './schema';


// Same-origin, resolved at runtime from window.location - never a baked-in
// backend host. Every operation path in the generated schema already starts
// with /api, so the base must not add it again. In dev, Vite's server.proxy
// forwards /api to the backend; in production, nginx does the same. The
// frontend never bakes in a backend URL, so one built image runs anywhere.
export const apiClient = createClient<paths>({
  baseUrl: typeof window !== 'undefined' ? window.location.origin : '',
  // Look up globalThis.fetch at call time rather than binding it once here,
  // so tests can stub it after this module has already been imported.
  fetch: (...args: Parameters<typeof fetch>) => globalThis.fetch(...args),
});

export type Complaint = components['schemas']['ComplaintOut'];
export type ComplaintCreate = components['schemas']['ComplaintCreate'];
export type ComplaintPage = components['schemas']['ComplaintPage'];
export type StatsOut = components['schemas']['StatsOut'];
export type ProviderMeta = components['schemas']['ProviderMeta'];
export type Category = components['schemas']['Category'];
export type Priority = components['schemas']['Priority'];
export type Status = components['schemas']['Status'];
export type ValidationErrorOut = components['schemas']['ValidationErrorOut'];

/** A validation failure the caller can map straight onto form fields. */
export class ApiValidationError extends Error {
  readonly fields: Record<string, string>;

  constructor(body: ValidationErrorOut) {
    super(body.detail);
    this.fields = Object.fromEntries(body.errors.map((e) => [e.field, e.message]));
  }
}

/** An invalid status transition: the server's own message, verbatim. */
export class ApiConflictError extends Error {
  currentStatus: string;
  attemptedStatus: string;

  constructor(message: string, currentStatus: string, attemptedStatus: string) {
    super(message);
    this.currentStatus = currentStatus;
    this.attemptedStatus = attemptedStatus;
  }
}

/** The caller hit the rate limit; secondsUntilRetry comes from Retry-After. */
export class ApiRateLimitError extends Error {
  secondsUntilRetry: number;

  constructor(secondsUntilRetry: number) {
    super('Too many requests. Please try again later.');
    this.secondsUntilRetry = secondsUntilRetry;
  }
}

/** Anything else the API rejected (404, or a shape we did not special-case). */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function createComplaint(body: ComplaintCreate): Promise<Complaint> {
  const { data, response, error } = await apiClient.POST('/api/complaints', { body });
  if (data) return data;

  if (response.status === 400) throw new ApiValidationError(error as ValidationErrorOut);
  if (response.status === 429) {
    const retryAfter = Number(response.headers.get('Retry-After') ?? '60');
    throw new ApiRateLimitError(retryAfter);
  }
  throw new ApiError(errorDetail(error), response.status);
}

export async function getComplaint(id: string): Promise<Complaint> {
  const { data, response, error } = await apiClient.GET('/api/complaints/{complaint_id}', {
    params: { path: { complaint_id: id } },
  });
  if (data) return data;
  throw new ApiError(errorDetail(error), response.status);
}

export interface ListComplaintsParams {
  category?: Category;
  priority?: Priority;
  status?: Status;
  page?: number;
  page_size?: number;
}

export async function listComplaints(params: ListComplaintsParams = {}): Promise<ComplaintPage> {
  const { data, response, error } = await apiClient.GET('/api/complaints', {
    params: { query: params },
  });
  if (data) return data;
  throw new ApiError(errorDetail(error), response.status);
}

export async function updateComplaintStatus(id: string, status: Status): Promise<Complaint> {
  const { data, response, error } = await apiClient.PATCH('/api/complaints/{complaint_id}/status', {
    params: { path: { complaint_id: id } },
    body: { status },
  });
  if (data) return data;

  if (response.status === 409) {
    const body = error as { detail: string; current_status: string; attempted_status: string };
    throw new ApiConflictError(body.detail, body.current_status, body.attempted_status);
  }
  throw new ApiError(errorDetail(error), response.status);
}

/** Returns the stats plus the X-Cache header value (HIT | MISS | BYPASS). */
export async function getStats(): Promise<{ stats: StatsOut; cacheState: string }> {
  const { data, response, error } = await apiClient.GET('/api/stats', {});
  if (!data) throw new ApiError(errorDetail(error), response.status);
  return { stats: data, cacheState: response.headers.get('X-Cache') ?? 'UNKNOWN' };
}

export async function getProviderMeta(): Promise<ProviderMeta> {
  const { data, response, error } = await apiClient.GET('/api/meta/providers', {});
  if (data) return data;
  throw new ApiError(errorDetail(error), response.status);
}

function errorDetail(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    return String((error as { detail: unknown }).detail);
  }
  return 'Request failed';
}
