'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { NotificationType } from '../components/Notification'

interface NotificationContextType {
  notifications: NotificationType[]
  addNotification: (type: NotificationType['type'], message: string, duration?: number) => void
  removeNotification: (id: string) => void
  showSuccess: (message: string, duration?: number) => void
  showError: (message: string, duration?: number) => void
  showWarning: (message: string, duration?: number) => void
  showInfo: (message: string, duration?: number) => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<NotificationType[]>([])

  const addNotification = useCallback((type: NotificationType['type'], message: string, duration = 5000) => {
    const id = `${Date.now()}-${Math.random()}`
    setNotifications((prev) => [...prev, { id, type, message, duration }])
  }, [])

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }, [])

  const showSuccess = useCallback((message: string, duration?: number) => {
    addNotification('success', message, duration)
  }, [addNotification])

  const showError = useCallback((message: string, duration?: number) => {
    addNotification('error', message, duration)
  }, [addNotification])

  const showWarning = useCallback((message: string, duration?: number) => {
    addNotification('warning', message, duration)
  }, [addNotification])

  const showInfo = useCallback((message: string, duration?: number) => {
    addNotification('info', message, duration)
  }, [addNotification])

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        addNotification,
        removeNotification,
        showSuccess,
        showError,
        showWarning,
        showInfo,
      }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}

