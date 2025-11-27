/**
 * Централизованный API клиент для работы с бекендом
 * Обеспечивает единую точку доступа к API, обработку ошибок и авторизацию
 */

import { auth } from './auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ApiError {
  detail: string
  status?: number
}

export class ApiClientError extends Error {
  status?: number
  detail?: string

  constructor(message: string, status?: number, detail?: string) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.detail = detail
  }
}

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit & { requireAuth?: boolean }
  ): Promise<T> {
    const { requireAuth = true, ...fetchOptions } = options || {}

    const token = auth.getToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(requireAuth && token ? { Authorization: `Bearer ${token}` } : {}),
      ...fetchOptions.headers,
    }

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...fetchOptions,
        headers,
      })

      if (!response.ok) {
        let errorData: ApiError
        try {
          errorData = await response.json()
        } catch {
          errorData = {
            detail: `HTTP ${response.status}: ${response.statusText}`,
            status: response.status,
          }
        }

        // Если токен истек, очищаем авторизацию
        if (response.status === 401) {
          auth.logout()
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
        }

        throw new ApiClientError(
          errorData.detail || `HTTP ${response.status}`,
          response.status,
          errorData.detail
        )
      }

      // Если ответ пустой, возвращаем пустой объект
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        return {} as T
      }

      return response.json()
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error
      }

      // Сетевые ошибки
      throw new ApiClientError(
        'Не удалось подключиться к серверу. Проверьте, что бэкенд запущен.',
        0,
        error instanceof Error ? error.message : 'Unknown error'
      )
    }
  }

  // GET запрос
  get<T>(endpoint: string, requireAuth = true): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', requireAuth })
  }

  // POST запрос
  post<T>(endpoint: string, data?: any, requireAuth = true): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      requireAuth,
    })
  }

  // PUT запрос
  put<T>(endpoint: string, data?: any, requireAuth = true): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      requireAuth,
    })
  }

  // PATCH запрос
  patch<T>(endpoint: string, data?: any, requireAuth = true): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
      requireAuth,
    })
  }

  // DELETE запрос
  delete<T>(endpoint: string, requireAuth = true): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', requireAuth })
  }
}

export const apiClient = new ApiClient(API_URL)

// Экспортируем базовый URL для случаев, когда нужен прямой доступ
export { API_URL }

