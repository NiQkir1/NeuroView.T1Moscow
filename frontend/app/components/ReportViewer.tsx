'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import { auth } from '@/lib/auth'
import LoadingSpinner from './LoadingSpinner'
import { useNotifications } from '../hooks/useNotifications'

interface ReportViewerProps {
  sessionId: number
  isOpen: boolean
  onClose: () => void
  reportTitle?: string
}

interface ReportData {
  candidate_name?: string
  candidate_email?: string
  interview_title?: string
  interview_date?: string
  total_score?: number | null
  questions_answers?: Array<{
    question_id: number
    question_text: string
    question_type: string
    answer_text?: string | null
    code_solution?: string | null
    score?: number | null
    evaluation?: {
      score?: number | null
      correctness?: number | null
      feedback?: string
    }
  }>
}

export default function ReportViewer({ sessionId, isOpen, onClose, reportTitle }: ReportViewerProps) {
  const { showError } = useNotifications()
  const [reportData, setReportData] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // ОПТИМИЗАЦИЯ: Кешируем загруженные отчеты
  const [cachedReports, setCachedReports] = useState<Map<number, ReportData>>(new Map())

  useEffect(() => {
    if (isOpen && sessionId) {
      // Проверяем кеш перед загрузкой
      const cached = cachedReports.get(sessionId)
      if (cached) {
        setReportData(cached)
      } else {
        loadReport()
      }
    } else {
      setReportData(null)
      setError('')
    }
  }, [isOpen, sessionId])

  const loadReport = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiClient.get(`/api/sessions/${sessionId}/report/json`)
      const reportData = data as ReportData
      setReportData(reportData)
      // Сохраняем в кеш
      setCachedReports(prev => new Map(prev).set(sessionId, reportData))
    } catch (err: any) {
      setError(err.message || 'Не удалось загрузить отчет')
      showError(err.message || 'Не удалось загрузить отчет')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPDF = async () => {
    try {
      setError('')
      const token = auth.getToken()
      if (!token) {
        setError('Требуется авторизация')
        return
      }
      
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const pdfUrl = `${API_URL}/api/sessions/${sessionId}/report/pdf`
      
      // Скачиваем PDF файл напрямую
      const response = await fetch(pdfUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Ошибка при скачивании PDF' }))
        throw new Error(errorData.detail || `Ошибка ${response.status}`)
      }
      
      // Получаем имя файла из заголовков или используем дефолтное
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `report_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/i)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      // Создаем blob и скачиваем
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err.message || 'Не удалось скачать отчет')
      showError(err.message || 'Не удалось скачать отчет')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[9999] p-4" onClick={onClose}>
      <div
        className="bg-bg-secondary rounded-lg border border-border-color max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-border-color flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight mb-1">
              {reportTitle || 'Отчет о собеседовании'}
            </h2>
            {reportData && (
              <p className="text-text-tertiary text-sm">
                {reportData.candidate_name || 'N/A'} • {reportData.interview_date 
                  ? new Date(reportData.interview_date).toLocaleDateString('ru-RU')
                  : 'N/A'}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {reportData && (
              <button
                onClick={handleDownloadPDF}
                className="px-4 py-2 bg-[#AF52DE] hover:bg-[#8E44AD] text-white rounded-lg font-medium transition-all duration-200 flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                  />
                </svg>
                Скачать PDF
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
              aria-label="Закрыть"
            >
              <svg className="w-6 h-6 text-text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          )}

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-400 text-sm mb-4">
              {error}
            </div>
          )}

          {reportData && !loading && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-bg-tertiary rounded-lg p-6 border border-border-color">
                <h3 className="text-lg font-semibold text-text-primary mb-4 tracking-tight">Общая информация</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-text-tertiary text-xs uppercase tracking-wider">Кандидат</span>
                    <div className="mt-1 text-text-primary font-medium">{reportData.candidate_name}</div>
                  </div>
                  <div>
                    <span className="text-text-tertiary text-xs uppercase tracking-wider">Email</span>
                    <div className="mt-1 text-text-primary font-medium">{reportData.candidate_email}</div>
                  </div>
                  <div>
                    <span className="text-text-tertiary text-xs uppercase tracking-wider">Интервью</span>
                    <div className="mt-1 text-text-primary font-medium">{reportData.interview_title}</div>
                  </div>
                  <div>
                    <span className="text-text-tertiary text-xs uppercase tracking-wider">Общая оценка</span>
                    <div className="mt-1 text-text-primary font-medium text-2xl">
                      {reportData.total_score != null ? reportData.total_score.toFixed(1) : 'N/A'}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Questions and Answers */}
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-4 tracking-tight">
                  Вопросы и ответы ({reportData.questions_answers?.length || 0})
                </h3>
                <div className="space-y-4">
                  {(reportData.questions_answers || []).map((qa, index) => (
                    <div
                      key={qa.question_id}
                      className="bg-bg-tertiary rounded-lg p-6 border border-border-color"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-text-tertiary text-xs font-medium">Вопрос {index + 1}</span>
                            <span className="px-2 py-0.5 bg-bg-quaternary text-text-tertiary text-xs rounded">
                              {qa.question_type}
                            </span>
                          </div>
                          <p className="text-text-primary font-medium">{qa.question_text}</p>
                        </div>
                        <div className="ml-4 text-right">
                          <div className="text-2xl font-semibold text-[#AF52DE]">
                            {qa.score != null ? qa.score.toFixed(1) : 'N/A'}%
                          </div>
                          <div className="text-text-tertiary text-xs mt-1">Оценка</div>
                        </div>
                      </div>

                      <div className="mt-4 pt-4 border-t border-border-color">
                        <div className="mb-2">
                          <span className="text-text-tertiary text-xs uppercase tracking-wider">Ответ кандидата:</span>
                        </div>
                        {qa.code_solution ? (
                          <div>
                            <pre className="bg-bg-quaternary p-4 rounded-lg border border-border-color overflow-x-auto">
                              <code className="text-text-primary text-sm font-mono whitespace-pre-wrap">
                                {qa.code_solution}
                              </code>
                            </pre>
                          </div>
                        ) : (
                          <p className="text-text-primary text-sm leading-relaxed whitespace-pre-wrap">
                            {qa.answer_text || 'Ответ не предоставлен'}
                          </p>
                        )}
                      </div>

                      {qa.evaluation && (
                        <div className="mt-4 pt-4 border-t border-border-color">
                          <div className="mb-2">
                            <span className="text-text-tertiary text-xs uppercase tracking-wider">Оценка:</span>
                          </div>
                          <div className="grid grid-cols-2 gap-4 mb-3">
                            <div>
                              <span className="text-text-tertiary text-xs">Правильность:</span>
                              <div className="text-text-primary font-medium">
                                {qa.evaluation?.correctness != null ? qa.evaluation.correctness.toFixed(1) : 'N/A'}/10
                              </div>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Общая оценка:</span>
                              <div className="text-text-primary font-medium">
                                {qa.evaluation?.score != null ? qa.evaluation.score.toFixed(1) : 'N/A'}/10
                              </div>
                            </div>
                          </div>
                          {qa.evaluation.feedback && (
                            <div>
                              <span className="text-text-tertiary text-xs uppercase tracking-wider mb-2 block">
                                Обратная связь:
                              </span>
                              <p className="text-text-primary text-sm leading-relaxed whitespace-pre-wrap">
                                {qa.evaluation.feedback}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

