'use client'

import { useEffect } from 'react'

export interface NotificationType {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

interface NotificationProps {
  notification: NotificationType
  onClose: (id: string) => void
}

export default function Notification({ notification, onClose }: NotificationProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose(notification.id)
    }, notification.duration || 5000)

    return () => clearTimeout(timer)
  }, [notification, onClose])

  const getStyles = () => {
    switch (notification.type) {
      case 'success':
        return 'bg-green-500/20 border-green-500/50 text-green-400'
      case 'error':
        return 'bg-red-500/20 border-red-500/50 text-red-400'
      case 'warning':
        return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
      case 'info':
        return 'bg-blue-500/20 border-blue-500/50 text-blue-400'
      default:
        return 'bg-bg-tertiary border-border-color text-text-primary'
    }
  }

  const getIcon = () => {
    switch (notification.type) {
      case 'success':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'error':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      case 'warning':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        )
      case 'info':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
    }
  }

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-xl shadow-lg transition-all duration-300 ${getStyles()}`}
      role="alert"
    >
      <div className="flex-shrink-0">{getIcon()}</div>
      <p className="text-sm font-medium tracking-tight flex-1">{notification.message}</p>
      <button
        onClick={() => onClose(notification.id)}
        className="flex-shrink-0 ml-2 text-current hover:opacity-70 transition-opacity"
        aria-label="Закрыть"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

