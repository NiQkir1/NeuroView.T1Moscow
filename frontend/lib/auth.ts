/**
 * Система аутентификации с бэкендом
 */

export type UserRole = 'candidate' | 'hr' | 'admin' | 'moderator';

export interface User {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

const AUTH_KEY = 'neuroview_auth';
const TOKEN_KEY = 'neuroview_token';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const auth = {
  async login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Ошибка подключения к серверу' }));
        return { success: false, error: errorData.detail || `Ошибка ${response.status}` };
      }

      const data = await response.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_KEY, JSON.stringify(data.user));
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Не удалось подключиться к серверу. Проверьте, что бэкенд запущен на http://localhost:8000' };
    }
  },

  async register(
    username: string,
    password: string,
    email?: string,
    full_name?: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password, email, full_name }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Ошибка подключения к серверу' }));
        return { success: false, error: errorData.detail || `Ошибка ${response.status}` };
      }

      const data = await response.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_KEY, JSON.stringify(data.user));
      return { success: true };
    } catch (error) {
      console.error('Register error:', error);
      return { success: false, error: 'Не удалось подключиться к серверу. Проверьте, что бэкенд запущен на http://localhost:8000' };
    }
  },

  logout: (): void => {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(TOKEN_KEY);
  },

  isAuthenticated: (): boolean => {
    if (typeof window === 'undefined') return false;
    const token = localStorage.getItem(TOKEN_KEY);
    const authData = localStorage.getItem(AUTH_KEY);
    return !!(token && authData);
  },

  getToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  getUser: (): User | null => {
    if (typeof window === 'undefined') return null;
    const authData = localStorage.getItem(AUTH_KEY);
    if (!authData) return null;
    try {
      return JSON.parse(authData);
    } catch {
      return null;
    }
  },

  async refreshUser(): Promise<User | null> {
    try {
      const token = this.getToken();
      if (!token) return null;

      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        this.logout();
        return null;
      }

      const user = await response.json();
      localStorage.setItem(AUTH_KEY, JSON.stringify(user));
      return user;
    } catch (error) {
      console.error('Refresh user error:', error);
      return null;
    }
  },

  isHR: (): boolean => {
    const user = auth.getUser();
    return user?.role === 'hr';
  },

  isAdmin: (): boolean => {
    const user = auth.getUser();
    return user?.role === 'admin';
  },

  getAuthHeaders: (): HeadersInit => {
    const token = auth.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    };
  },
};

