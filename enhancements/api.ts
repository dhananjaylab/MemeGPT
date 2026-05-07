import type {
  GeneratedMeme,
  GenerateMemeResponse,
  JobStatusResponse,
  MemeListResponse,
  TrendingResponse,
  User,
  APIError,
  GenerateMemeRequest,
  ShareMemeRequest,
  CheckoutResponse,
  MemeStats,
} from './types';

// ─── Quick generation types ───────────────────────────────────────────────────

export interface QuickMemeRequest {
  prompt?: string;
  template_id?: number;
  captions?: string[];
  ai_provider?: 'openai' | 'gemini';
}

export interface QuickMemeResponse {
  meme_id: string;
  image_url: string;
  template_name: string;
  meme_text: string[];
  cache_hit: boolean;
  generation_time_ms: number;
}

// ─── API client ───────────────────────────────────────────────────────────────

class APIClient {
  private baseURL: string;
  private defaultHeaders: HeadersInit;

  constructor(baseURL = '') {
    this.baseURL = baseURL || '/api';
    this.defaultHeaders = { 'Content-Type': 'application/json' };
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const authHeaders = this.getAuthHeaders();

    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...authHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
        } catch (_) {}

        const error = new Error(errorMessage) as any;
        error.status = response.status;
        if (response.status === 429) error.isRateLimit = true;
        throw error;
      }

      return await response.json();
    } catch (error) {
      if (!(error as any).status) {
        console.error(`API network error: ${endpoint}`, error);
      }
      throw error;
    }
  }

  private getAuthHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = {};
    const stored = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const t = token || stored;
    if (t) headers.Authorization = `Bearer ${t}`;
    return headers;
  }

  // ── Meme generation ────────────────────────────────────────────────────────

  async generateMemes(request: GenerateMemeRequest): Promise<GenerateMemeResponse> {
    return this.request<GenerateMemeResponse>('/memes/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Fast synchronous generation — no queue, single HTTP round-trip.
   * Returns the image URL directly (cache-aware: ~5ms on cache hit).
   */
  async generateMemeQuick(request: QuickMemeRequest): Promise<QuickMemeResponse> {
    return this.request<QuickMemeResponse>('/memes/generate/quick', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // ── Job polling ────────────────────────────────────────────────────────────

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return this.request<JobStatusResponse>(`/jobs/${jobId}`);
  }

  // ── Meme CRUD ──────────────────────────────────────────────────────────────

  async getMemes(
    params: {
      page?: number;
      limit?: number;
      sort?: string;
      search?: string;
      user?: string;
    } = {},
  ): Promise<MemeListResponse> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) searchParams.append(k, v.toString());
    });
    const q = searchParams.toString();
    return this.request<MemeListResponse>(`/memes${q ? `?${q}` : ''}`);
  }

  async getMeme(id: string): Promise<GeneratedMeme> {
    return this.request<GeneratedMeme>(`/memes/${id}`);
  }

  async deleteMeme(id: string, token?: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/memes/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    });
  }

  async likeMeme(id: string): Promise<{ liked: boolean; like_count: number }> {
    return this.request<{ liked: boolean; like_count: number }>(`/memes/${id}/like`, {
      method: 'POST',
    });
  }

  async shareMeme(id: string, request: ShareMemeRequest): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/memes/${id}/share`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // ── Trending ───────────────────────────────────────────────────────────────

  async getTrendingTopics(): Promise<TrendingResponse> {
    return this.request<TrendingResponse>('/trending/topics');
  }

  // ── Users ──────────────────────────────────────────────────────────────────

  async getCurrentUser(token?: string): Promise<User> {
    return this.request<User>('/auth/me', { headers: this.getAuthHeaders(token) });
  }

  async getUserMe(token?: string): Promise<User> {
    return this.request<User>('/users/me', { headers: this.getAuthHeaders(token) });
  }

  async updateUser(updates: Partial<User>, token?: string): Promise<User> {
    return this.request<User>('/auth/me', {
      method: 'PATCH',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(updates),
    });
  }

  async rotateApiKey(token?: string): Promise<{ api_key: string }> {
    return this.request<{ api_key: string }>('/auth/rotate-key', {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
  }

  // ── Billing ────────────────────────────────────────────────────────────────

  async createCheckoutSession(
    plan: 'pro' | 'api',
    options: { success_url: string; cancel_url: string },
    token?: string,
  ): Promise<CheckoutResponse> {
    return this.request<CheckoutResponse>('/stripe/checkout', {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify({ plan, ...options }),
    });
  }

  async createPortalSession(token?: string): Promise<{ portal_url: string }> {
    return this.request<{ portal_url: string }>('/stripe/portal', {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
  }

  // ── Analytics ──────────────────────────────────────────────────────────────

  async getMemeStats(token?: string): Promise<MemeStats> {
    return this.request<MemeStats>('/analytics/stats', {
      headers: this.getAuthHeaders(token),
    });
  }

  // ── Health ─────────────────────────────────────────────────────────────────

  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request<{ status: string; version: string }>('/health');
  }
}

// ─── Singleton ────────────────────────────────────────────────────────────────

export const apiClient = new APIClient();

// ─── Convenience wrappers ─────────────────────────────────────────────────────

export const generateMemes = (
  prompt: string,
  options: Partial<GenerateMemeRequest> = {},
) => apiClient.generateMemes({ prompt, ...options });

export const generateMemeQuick = (request: QuickMemeRequest) =>
  apiClient.generateMemeQuick(request);

export const getMemes = (params?: Parameters<typeof apiClient.getMemes>[0]) =>
  apiClient.getMemes(params);

export const getMeme = (id: string) => apiClient.getMeme(id);

export const getTrendingTopics = () => apiClient.getTrendingTopics();

export const likeMeme = (id: string) => apiClient.likeMeme(id);

export const shareMeme = (id: string, platform: ShareMemeRequest['platform']) =>
  apiClient.shareMeme(id, { platform });

export const isAPIError = (error: any): error is APIError =>
  error && typeof error === 'object' && 'error' in error;

// ─── Rate limiter ─────────────────────────────────────────────────────────────

class RateLimiter {
  private requests: number[] = [];
  constructor(
    private maxRequests = 10,
    private windowMs = 60_000,
  ) {}

  canMakeRequest(): boolean {
    const now = Date.now();
    this.requests = this.requests.filter((t) => now - t < this.windowMs);
    return this.requests.length < this.maxRequests;
  }

  recordRequest(): void {
    this.requests.push(Date.now());
  }
}

export const rateLimiter = new RateLimiter();

// ─── Retry helper ─────────────────────────────────────────────────────────────

export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  delay = 1000,
): Promise<T> {
  let lastError!: Error;
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i === maxRetries) throw lastError;
      await new Promise((r) => setTimeout(r, delay * Math.pow(2, i)));
    }
  }
  throw lastError;
}
