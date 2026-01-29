import axios from 'axios';
import {
  SearchRequest,
  SearchResponse,
  ExpandedSearchResponse,
  RerankedSearchResponse,
  IndexStats
} from '../types';
import { getStoredTokens } from './auth';

const retrievalApi = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

retrievalApi.interceptors.request.use(
  (config) => {
    const tokens = getStoredTokens();
    if (tokens && tokens.accessToken) {
      config.headers.Authorization = `Bearer ${tokens.accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const retrievalService = {
  search: async (query: string, k: number = 5, filters?: Record<string, any>): Promise<SearchResponse> => {
    const request: SearchRequest = { query, k, filters };
    const response = await retrievalApi.post<SearchResponse>('/retrieval/search', request);
    return response.data;
  },

  searchWithScores: async (query: string, k: number = 5): Promise<SearchResponse> => {
    const response = await retrievalApi.post<SearchResponse>(
      `/retrieval/search-with-scores?query=${encodeURIComponent(query)}&k=${k}`
    );
    return response.data;
  },

  searchExpanded: async (
    query: string,
    k: number = 5,
    filters?: Record<string, any>
  ): Promise<ExpandedSearchResponse> => {
    const request: SearchRequest = { query, k, filters };
    const response = await retrievalApi.post<ExpandedSearchResponse>('/retrieval/search-expanded', request);
    return response.data;
  },

  searchReranked: async (
    query: string,
    k: number = 5,
    filters?: Record<string, any>
  ): Promise<RerankedSearchResponse> => {
    const request: SearchRequest = { query, k, filters };
    const response = await retrievalApi.post<RerankedSearchResponse>('/retrieval/search-reranked', request);
    return response.data;
  },

  getStats: async (): Promise<IndexStats> => {
    const response = await retrievalApi.get<IndexStats>('/retrieval/stats');
    return response.data;
  },
};

export default retrievalApi;
