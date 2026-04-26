
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
}

export interface MemeTemplate {
  id: string;
  name: string;
  url: string;
  description: string;
  textFields: number;
}

export interface GeneratedMeme {
  id: string;
  template_id: string;
  template_name: string;
  prompt: string;
  meme_text: string[];
  image_url: string;
  created_at: string;
  user_id?: string;
  like_count: number;
  share_count: number;
  view_count: number;
  settings?: MemeSettings;
}

export interface TextPosition {
  x: number;
  y: number;
}

export interface MemeSettings {
  fontSize: number;
  color: string;
  uppercase: boolean;
  templateName?: string;
  imageUrl?: string;
  positions?: TextPosition[];
  manualLayout?: boolean;
  autoResize?: boolean;
}

export interface TrendingTopic {
  id: string;
  title: string;
  source: 'reddit' | 'news' | 'twitter';
  score?: number;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
