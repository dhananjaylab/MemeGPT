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
  MemeStats
} from './types';

// ─── Quick generation types ───────────────────────────────────────────────────

export interface QuickMemeRequest {
  prompt?: string;
  template_id?: number;
  captions?: string[];
  ai_provider?: 'gemini';
}

export interface QuickMemeResponse {
  meme_id: string;
  image_url: string;
  template_name: string;
  meme_text: string[];
  cache_hit: boolean;
  generation_time_ms: number;
}

// ─── In-memory access-token store ─────────────────────────────────────────────
//
// SECURITY (Phase 1 remediation): the JWT used to live in localStorage,
// which means any successful XSS on this app could read it and exfiltrate
// a long-lived session token. It now lives only in this module-level
// variable (cleared on full page reload) — the actual session-continuity
// mechanism is the httpOnly refresh cookie the backend sets on
// /api/auth/login and /api/auth/refresh, which JavaScript can never read.
// AuthContext is the only thing that should call setAccessToken().
let inMemoryAccessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

class APIClient {
  private baseURL: string;
  private defaultHeaders: HeadersInit;

  constructor(baseURL: string = '') {
    // Phase 2: switched to the versioned /api/v1 prefix now that the
    // backend mounts both /api/v1 (canonical) and /api (legacy alias, kept
    // for any other existing integrations — see backend/main.py). Vite's
    // dev proxy (vite.config.ts) forwards both unchanged.
    this.baseURL = baseURL || '/api/v1';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    // Auto-inject auth headers from the in-memory token
    const authHeaders = this.getAuthHeaders();
    
    const config: RequestInit = {
      ...options,
      // Required so the browser sends/receives the httpOnly refresh cookie
      // on /api/auth/* calls. Harmless for every other endpoint, which
      // doesn't rely on cookies at all.
      credentials: 'include',
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
        let errorDetails = null;

        try {
          const errorData = await response.json();
          // FastAPI often uses 'detail' for error messages
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
          errorDetails = errorData.details || null;
        } catch (e) {
          // Fallback if response is not JSON
        }

        const error = new Error(errorMessage) as any;
        error.status = response.status;
        error.details = errorDetails;
        
        // Specific handling for 429
        if (response.status === 429) {
          error.isRateLimit = true;
        }

        throw error;
      }

      return await response.json();
    } catch (error) {
      if (!(error as any).status) {
        console.error(`API request network error: ${endpoint}`, error);
      }
      throw error;
    }
  }

  private getAuthHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = {};

    // Explicit per-call token (some pages still pass the context token
    // through directly — kept for backward compatibility) takes priority,
    // otherwise fall back to the in-memory token set by AuthContext.
    const effectiveToken = token || inMemoryAccessToken;
    if (effectiveToken) {
      headers.Authorization = `Bearer ${effectiveToken}`;
    }

    return headers;
  }

  // Meme generation
  async generateMemes(request: GenerateMemeRequest): Promise<GenerateMemeResponse> {
    return this.request<GenerateMemeResponse>('/memes/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Fast generation — returns the image URL directly if cached (~5ms),
   * otherwise returns 202 Accepted with job_id for SSE streaming.
   */
  async generateMemeQuick(request: QuickMemeRequest): Promise<QuickMemeResponse | { job_id: string; status: string }> {
    return this.request<QuickMemeResponse | { job_id: string; status: string }>('/memes/generate/quick', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Job status polling
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return this.request<JobStatusResponse>(`/jobs/${jobId}`);
  }

  // Meme management
  async getMemes(params: {
    page?: number;
    limit?: number;
    sort?: string;
    search?: string;
    user?: string;
  } = {}): Promise<MemeListResponse> {
    const searchParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });

    const query = searchParams.toString();
    return this.request<MemeListResponse>(`/memes${query ? `?${query}` : ''}`);
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

  // Trending topics
  async getTrendingTopics(): Promise<TrendingResponse> {
    return this.request<TrendingResponse>('/trending/topics');
  }

  // User management
  async getCurrentUser(token?: string): Promise<User> {
    return this.request<User>('/auth/me', {
      headers: this.getAuthHeaders(token),
    });
  }

  async getUserMe(token?: string): Promise<User> {
    return this.request<User>('/users/me', {
      headers: this.getAuthHeaders(token),
    });
  }

  async updateUser(updates: Partial<User>, token?: string): Promise<User> {
    return this.request<User>('/auth/me', {
      method: 'PATCH',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(updates),
    });
  }

  async rotateApiKey(token?: string): Promise<{ api_key: string; api_key_prefix: string; warning?: string }> {
    return this.request<{ api_key: string; api_key_prefix: string; warning?: string }>('/auth/rotate-key', {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
  }

  /**
   * Silently mint a new access token from the httpOnly refresh cookie.
   * Called once on app boot (and can be retried on a 401) instead of
   * ever reading a persisted token out of localStorage.
   */
  async refreshAccessToken(): Promise<{ access_token: string; token_type: string; user: User }> {
    return this.request('/auth/refresh', { method: 'POST' });
  }

  /** Clears the httpOnly refresh cookie server-side. */
  async logout(): Promise<{ message: string }> {
    return this.request('/auth/logout', { method: 'POST' });
  }

  // Billing/Stripe
  async createCheckoutSession(plan: 'pro' | 'api', options: {
    success_url: string;
    cancel_url: string;
  }, token?: string): Promise<CheckoutResponse> {
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

  // Analytics
  async getMemeStats(token?: string): Promise<MemeStats> {
    return this.request<MemeStats>('/analytics/stats', {
      headers: this.getAuthHeaders(token),
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request<{ status: string; version: string }>('/health');
  }
}

// Create singleton instance
export const apiClient = new APIClient();

// Convenience functions
export const generateMemes = (prompt: string, options: Partial<GenerateMemeRequest> = {}) => {
  return apiClient.generateMemes({ prompt, ...options });
};

export const generateMemeQuick = (request: QuickMemeRequest) => {
  return apiClient.generateMemeQuick(request);
};

export const getMemes = (params?: Parameters<typeof apiClient.getMemes>[0]) => {
  return apiClient.getMemes(params);
};

export const getMeme = (id: string) => {
  return apiClient.getMeme(id);
};

export const getTrendingTopics = () => {
  return apiClient.getTrendingTopics();
};

export const likeMeme = (id: string) => {
  return apiClient.likeMeme(id);
};

export const shareMeme = (id: string, platform: ShareMemeRequest['platform']) => {
  return apiClient.shareMeme(id, { platform });
};

// Error handling utility
export const isAPIError = (error: any): error is APIError => {
  return error && typeof error === 'object' && 'error' in error;
};

// Rate limiting utility
class RateLimiter {
  private requests: number[] = [];
  private maxRequests: number;
  private windowMs: number;

  constructor(maxRequests: number = 10, windowMs: number = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
  }

  canMakeRequest(): boolean {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    return this.requests.length < this.maxRequests;
  }

  recordRequest(): void {
    this.requests.push(Date.now());
  }
}

export const rateLimiter = new RateLimiter();

// Retry utility for failed requests
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (i === maxRetries) {
        throw lastError;
      }
      
      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
    }
  }

  throw lastError!;
}
