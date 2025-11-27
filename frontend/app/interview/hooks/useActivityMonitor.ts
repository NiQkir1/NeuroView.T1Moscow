'use client'

import { useEffect, useRef, useCallback } from 'react'
import { apiClient } from '@/lib/api'

interface ActivityEvent {
  type: 'visibility_change' | 'focus_change' | 'tab_switch' | 'copy' | 'paste' | 'keydown' | 'keyup'
  timestamp: number
  details?: any
}

interface UseActivityMonitorOptions {
  sessionId: number | null
  enabled?: boolean
  onSuspiciousActivity?: (event: ActivityEvent) => void
}

export function useActivityMonitor({
  sessionId,
  enabled = true,
  onSuspiciousActivity
}: UseActivityMonitorOptions) {
  const activityLog = useRef<ActivityEvent[]>([])
  const lastActivityTime = useRef<number>(Date.now())
  const isMonitoring = useRef<boolean>(false)
  
  const logActivity = useCallback(async (event: ActivityEvent) => {
    if (!enabled || !sessionId) return
    
    activityLog.current.push(event)
    lastActivityTime.current = Date.now()
    
    // Вызываем callback если есть
    if (onSuspiciousActivity) {
      onSuspiciousActivity(event)
    }
    
    // Отправляем на сервер (батчинг для производительности)
    try {
      await apiClient.post(
        `/api/sessions/${sessionId}/activity`,
        {
          type: event.type,
          timestamp: event.timestamp,
          details: event.details
        },
        false
      )
    } catch (error) {
      // Не показываем уведомление, чтобы не отвлекать пользователя
    }
  }, [sessionId, enabled, onSuspiciousActivity])
  
  useEffect(() => {
    if (!enabled || !sessionId || isMonitoring.current) return
    
    isMonitoring.current = true
    
    // Отслеживание переключения вкладок
    const handleVisibilityChange = () => {
      if (document.hidden) {
        const event: ActivityEvent = {
          type: 'visibility_change',
          timestamp: Date.now(),
          details: { hidden: true }
        }
        logActivity(event)
      } else {
        const event: ActivityEvent = {
          type: 'visibility_change',
          timestamp: Date.now(),
          details: { hidden: false }
        }
        logActivity(event)
      }
    }
    
    // Отслеживание потери фокуса
    const handleBlur = () => {
      const event: ActivityEvent = {
        type: 'focus_change',
        timestamp: Date.now(),
        details: { focused: false }
      }
      logActivity(event)
    }
    
    const handleFocus = () => {
      const event: ActivityEvent = {
        type: 'focus_change',
        timestamp: Date.now(),
        details: { focused: true }
      }
      logActivity(event)
    }
    
    // Отслеживание копирования
    const handleCopy = (e: ClipboardEvent) => {
      const event: ActivityEvent = {
        type: 'copy',
        timestamp: Date.now(),
        details: { 
          text: window.getSelection()?.toString().substring(0, 100) // Ограничиваем длину
        }
      }
      logActivity(event)
    }
    
    // Отслеживание вставки
    const handlePaste = (e: ClipboardEvent) => {
      const event: ActivityEvent = {
        type: 'paste',
        timestamp: Date.now(),
        details: { 
          text: e.clipboardData?.getData('text').substring(0, 100) // Ограничиваем длину
        }
      }
      logActivity(event)
    }
    
    // Отслеживание нажатий клавиш (для детекции Ctrl+C, Ctrl+V)
    const handleKeyDown = (e: KeyboardEvent) => {
      // Логируем только комбинации клавиш
      if (e.ctrlKey || e.metaKey) {
        const event: ActivityEvent = {
          type: 'keydown',
          timestamp: Date.now(),
          details: { 
            key: e.key,
            ctrlKey: e.ctrlKey,
            metaKey: e.metaKey,
            code: e.code
          }
        }
        logActivity(event)
      }
    }
    
    // Подписываемся на события
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('blur', handleBlur)
    window.addEventListener('focus', handleFocus)
    document.addEventListener('copy', handleCopy)
    document.addEventListener('paste', handlePaste)
    document.addEventListener('keydown', handleKeyDown)
    
    return () => {
      isMonitoring.current = false
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('blur', handleBlur)
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('copy', handleCopy)
      document.removeEventListener('paste', handlePaste)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [enabled, sessionId, logActivity])
  
  return {
    activityLog: activityLog.current,
    getActivityCount: () => activityLog.current.length,
    getLastActivityTime: () => lastActivityTime.current
  }
}

