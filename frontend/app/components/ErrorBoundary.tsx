'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
          <div className="bg-bg-secondary rounded-lg border border-border-color p-8 max-w-md w-full">
            <h2 className="text-2xl font-semibold text-text-primary mb-4 tracking-tight">
              Произошла ошибка
            </h2>
            <p className="text-text-tertiary text-sm mb-6">
              {this.state.error?.message || 'Неизвестная ошибка'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: undefined })
                window.location.reload()
              }}
              className="w-full bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] text-white py-3 rounded-lg font-semibold hover:from-[#8E44AD] hover:to-[#AF52DE] transition-all duration-200"
            >
              Перезагрузить страницу
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

