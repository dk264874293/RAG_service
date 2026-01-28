import axios from 'axios';
import {
  MarkdownFileList,
  MarkdownContent,
  MarkdownSaveRequest,
  MarkdownSaveResponse
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const markdownApi = {
  getFiles: async (): Promise<MarkdownFileList> => {
    const response = await api.get<MarkdownFileList>('/markdown/files');
    return response.data;
  },

  getFile: async (filePath: string): Promise<MarkdownContent> => {
    const response = await api.get<MarkdownContent>(`/markdown/file/${filePath}`);
    return response.data;
  },

  saveFile: async (filePath: string, content: string): Promise<MarkdownSaveResponse> => {
    const request: MarkdownSaveRequest = { content };
    const response = await api.post<MarkdownSaveResponse>(`/markdown/file/${filePath}`, request);
    return response.data;
  },
};

export default api;
