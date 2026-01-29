export interface MarkdownFile {
  name: string;
  path: string;
  folder_name: string;
  url: string;
  size: number;
  modified_time: string;
}

export interface MarkdownFileList {
  files: MarkdownFile[];
}

export interface MarkdownContent {
  content: string;
  path: string;
  name: string;
  folder_name: string;
}

export interface MarkdownSaveRequest {
  content: string;
}

export interface MarkdownSaveResponse {
  status: string;
  message: string;
  path: string;
}

export interface EditorState {
  currentFile: MarkdownContent | null;
  content: string;
  isModified: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  error: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthTokens {
  accessToken: string;
  tokenType: string;
  expiresAt: number;
}

export interface UploadedFile {
  file_id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  processing_status: string;
  content_preview: string;
  uploaded_at: string;
}

export interface UploadResponse {
  status: string;
  message: string;
  file_id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  processing_status: string;
  content_preview: string;
}

export interface BatchUploadResponse {
  status: string;
  message: string;
  results: UploadResponse[];
  total: number;
  success: number;
  failed: number;
}

export interface SearchRequest {
  query: string;
  k: number;
  filters?: Record<string, any>;
}

export interface SearchResult {
  doc_id: string;
  content: string;
  metadata: Record<string, any>;
  score?: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
}

export interface ExpandedSearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
  query_info: {
    original: string;
    rewritten: string;
    expanded_count: number;
    variants: string[];
  };
  expansion_used: boolean;
}

export interface RerankedSearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
  reranking_used: boolean;
  reranking_scores: number[];
}

export interface IndexStats {
  total_vectors: number;
  active_vectors: number;
  deleted_vectors: number;
  index_path: string;
  dimension: number;
}

export interface PerformanceMetrics {
  request_count: number;
  avg_duration: number;
  min_duration: number;
  max_duration: number;
  dashscope_calls: number;
}
