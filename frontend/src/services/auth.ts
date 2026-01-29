import axios from 'axios';
import { LoginRequest, LoginResponse, AuthTokens } from '../types';

const TOKEN_KEY = 'auth_tokens';
const USER_KEY = 'user_info';

export const getStoredTokens = (): AuthTokens | null => {
  const tokensStr = localStorage.getItem(TOKEN_KEY);
  if (tokensStr) {
    return JSON.parse(tokensStr);
  }
  return null;
};

export const setStoredTokens = (tokens: AuthTokens): void => {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
};

export const clearStoredTokens = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getStoredUserInfo = (): any => {
  const userStr = localStorage.getItem(USER_KEY);
  if (userStr) {
    return JSON.parse(userStr);
  }
  return null;
};

export const setStoredUserInfo = (userInfo: any): void => {
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
};

const authApi = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

authApi.interceptors.request.use(
  (config) => {
    const tokens = getStoredTokens();
    if (tokens && tokens.accessToken) {
      config.headers.Authorization = `Bearer ${tokens.accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

authApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      clearStoredTokens();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await authApi.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    const tokens: AuthTokens = {
      accessToken: response.data.access_token,
      tokenType: response.data.token_type,
      expiresAt: Date.now() + response.data.expires_in * 1000,
    };

    setStoredTokens(tokens);
    setStoredUserInfo({ username });

    return response.data;
  },

  loginJson: async (request: LoginRequest): Promise<LoginResponse> => {
    const response = await authApi.post<LoginResponse>('/auth/login/json', request);

    const tokens: AuthTokens = {
      accessToken: response.data.access_token,
      tokenType: response.data.token_type,
      expiresAt: Date.now() + response.data.expires_in * 1000,
    };

    setStoredTokens(tokens);
    setStoredUserInfo({ username: request.username });

    return response.data;
  },

  logout: async (): Promise<void> => {
    clearStoredTokens();
  },

  verifyToken: async (): Promise<any> => {
    const response = await authApi.get('/auth/verify-token');
    return response.data;
  },

  isAuthenticated: (): boolean => {
    const tokens = getStoredTokens();
    if (!tokens) return false;

    return Date.now() < tokens.expiresAt;
  },
};

export default authApi;
