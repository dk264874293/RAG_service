import axios from 'axios';
import {
  UploadResponse,
  BatchUploadResponse,
  UploadedFile,
  IndexStats
} from '../types';
import { getStoredTokens } from './auth';

const documentsApi = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

documentsApi.interceptors.request.use(
  (config) => {
    const tokens = getStoredTokens();
    if (tokens && tokens.accessToken) {
      config.headers.Authorization = `Bearer ${tokens.accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const documentService = {
  uploadFile: async (file: File, metadata?: Record<string, any>): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await documentsApi.post<UploadResponse>('/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  uploadBatch: async (files: File[], metadata?: Record<string, any>): Promise<BatchUploadResponse> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await documentsApi.post<BatchUploadResponse>('/upload/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  getUploadHistory: async (limit: number = 50): Promise<{ items: UploadedFile[]; total: number }> => {
    const response = await documentsApi.get<{ items: UploadedFile[]; total: number }>(
      `/upload/?limit=${limit}`
    );
    return response.data;
  },

  getFileStatus: async (fileId: string): Promise<UploadedFile> => {
    const response = await documentsApi.get<UploadedFile>(`/upload/${fileId}`);
    return response.data;
  },

  getFileContent: async (fileId: string): Promise<any> => {
    const response = await documentsApi.get(`/upload/${fileId}/content`);
    return response.data;
  },

  deleteFile: async (fileId: string): Promise<{ status: string; message: string; deleted_vectors: number }> => {
    const response = await documentsApi.delete<{ status: string; message: string; deleted_vectors: number }>(
      `/upload/${fileId}`
    );
    return response.data;
  },

  updateFile: async (fileId: string, file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await documentsApi.put<UploadResponse>(`/upload/${fileId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  getIndexStats: async (): Promise<IndexStats> => {
    const response = await documentsApi.get<IndexStats>('/retrieval/stats');
    return response.data;
  },
};

export default documentsApi;
