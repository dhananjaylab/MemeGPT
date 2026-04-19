// Core meme data structure
export interface MemeTemplate {
  id: number;
  name: string;
  alternative_names: string[];
  file_path: string;
  font_path: string;
  text_color: string;
  text_stroke: boolean;
  usage_instructions: string;
  number_of_text_fields: number;
  text_coordinates_xy_wh: number[][];
  example_output: string[];
}

// Generated meme from API
export interface GeneratedMeme {
  id: string;
  template_id: number;
  template_name: string;
  prompt: string;
  meme_text: string[];
  image_url: string;
  thumbnail_url?: string;
  created_at: string;
  updated_at: string;
  user_id?: string;
  is_public: boolean;
  view_count: number;
  like_count: number;
  share_count: number;
  metadata?: {
    generation_time_ms?: number;
    model_used?: string;
    template_confidence?: number;
  };
}

// API response types
export interface GenerateMemeResponse {
  job_id?: string;
  memes?: GeneratedMeme[];
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: {
    memes: GeneratedMeme[];
  };
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface MemeListResponse {
  memes: GeneratedMeme[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// User and auth types
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  plan: 'free' | 'pro' | 'api';
  daily_limit: number;
  daily_used: number;
  api_key?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}

// Trending topics
export interface TrendingTopic {
  id: string;
  title: string;
  source: 'reddit' | 'news' | 'twitter';
  url?: string;
  score?: number;
  created_at: string;
  category?: string;
}

export interface TrendingResponse {
  topics: TrendingTopic[];
  updated_at: string;
}

// API error response
export interface APIError {
  error: string;
  message: string;
  details?: any;
  code?: string;
}

// Stripe/billing types
export interface SubscriptionPlan {
  id: string;
  name: string;
  price: number;
  currency: string;
  interval: 'month' | 'year';
  features: string[];
  daily_limit: number;
  api_access: boolean;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

// Analytics types
export interface MemeStats {
  total_memes: number;
  total_views: number;
  total_likes: number;
  total_shares: number;
  top_templates: Array<{
    template_name: string;
    count: number;
  }>;
  daily_stats: Array<{
    date: string;
    memes_generated: number;
    views: number;
    likes: number;
    shares: number;
  }>;
}

// Form types
export interface GenerateMemeRequest {
  prompt: string;
  template_ids?: number[];
  max_memes?: number;
  style_preferences?: {
    humor_level?: 'mild' | 'moderate' | 'spicy';
    target_audience?: 'general' | 'tech' | 'gaming' | 'business';
  };
}

export interface ShareMemeRequest {
  platform: 'twitter' | 'facebook' | 'reddit' | 'whatsapp' | 'copy' | 'download';
  metadata?: {
    user_agent?: string;
    referrer?: string;
  };
}

// Component prop types
export interface MemeCardProps {
  meme: GeneratedMeme;
  priority?: boolean;
  showStats?: boolean;
  className?: string;
  onDelete?: (id: string) => void;
  onLike?: (id: string, liked: boolean) => void;
}

export interface ShareMenuProps {
  meme: GeneratedMeme;
  className?: string;
  onShare?: (platform: string) => void;
}

// Utility types
export type SortOrder = 'recent' | 'popular' | 'trending' | 'top';

export interface PaginationParams {
  page?: number;
  limit?: number;
  sort?: SortOrder;
  search?: string;
  template_id?: number;
  user_id?: string;
}

export interface APIResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}

// WebSocket types for real-time updates
export interface WebSocketMessage {
  type: 'job_update' | 'meme_generated' | 'error';
  payload: any;
  timestamp: string;
}

export interface JobUpdateMessage extends WebSocketMessage {
  type: 'job_update';
  payload: {
    job_id: string;
    status: JobStatusResponse['status'];
    progress?: number;
    result?: JobStatusResponse['result'];
    error?: string;
  };
}