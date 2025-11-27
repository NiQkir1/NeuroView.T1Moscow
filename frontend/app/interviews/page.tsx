'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../components/Sidebar'
import MenuButton from '../components/MenuButton'
import Logo from '../components/Logo'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ReportViewer from '@/app/components/ReportViewer'
import { useNotifications } from '../hooks/useNotifications'

interface InterviewSession {
  id: number
  interview_id: number
  status: string
  application_status?: string  // v3.0.0
  started_at: string | null
  completed_at: string | null
  total_score: number | null
  created_at: string
  questions_count: number
  answered_count: number
  summary: {
    average_score: number
    total_questions: number
    answered_questions: number
    answers: Array<{
      question: string
      answer: string
      score: number | null
      evaluation: any
    }>
  }
}

export default function InterviewsPage() {
  const router = useRouter()
  const { showError } = useNotifications()
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null)
  const [selectedReportTitle, setSelectedReportTitle] = useState<string>('')

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    
    const init = async () => {
      try {
        await loadSessions()
      } catch (error) {
        console.error('Error loading sessions:', error)
        setIsLoading(false)
      }
    }
    
    init()
  }, [router])

  const loadSessions = async () => {
    try {
      const data = await apiClient.get('/api/user/sessions')
      setSessions(data as InterviewSession[])
    } catch (error) {
      showError('Не удалось загрузить список интервью')
    } finally {
      setIsLoading(false)
    }
  }

  const translations = {
    ru: {
      title: 'Отчеты по интервью',
      noInterviews: 'У вас пока нет завершенных интервью',
      status: 'Статус',
      score: 'Оценка',
      completed: 'Завершено',
      inProgress: 'В процессе',
      scheduled: 'Запланировано',
      started: 'Начато',
      completedAt: 'Завершено',
      questions: 'Вопросов',
      answered: 'Отвечено',
      averageScore: 'Средний балл',
      summary: 'Краткий отчет',
      viewDetails: 'Подробнее',
      date: 'Дата',
    },
    en: {
      title: 'Interview History',
      noInterviews: 'You have no completed interviews yet',
      status: 'Status',
      score: 'Score',
      completed: 'Completed',
      inProgress: 'In Progress',
      scheduled: 'Scheduled',
      started: 'Started',
      completedAt: 'Completed At',
      questions: 'Questions',
      answered: 'Answered',
      averageScore: 'Average Score',
      summary: 'Summary',
      viewDetails: 'View Details',
      date: 'Date',
    },
  }

  const t = translations[language]

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-600'
      case 'in_progress':
        return 'bg-yellow-600'
      case 'scheduled':
        return 'bg-blue-600'
      default:
        return 'bg-gray-600'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return t.completed
      case 'in_progress':
        return t.inProgress
      case 'scheduled':
        return t.scheduled
      default:
        return status
    }
  }

  const handleViewReport = (sessionId: number, interviewTitle: string) => {
    setSelectedReportId(sessionId)
    setSelectedReportTitle(interviewTitle || `Интервью #${sessionId}`)
  }

  const handleDownloadPDF = async (sessionId: number, interviewTitle: string) => {
    try {
      const { auth } = await import('@/lib/auth')
      const token = auth.getToken()
      if (!token) {
        showError('Требуется авторизация')
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
        showError(errorData.detail || `Ошибка скачивания PDF: ${response.status}`)
        return
      }
      
      // Получаем имя файла из заголовков или используем дефолтное
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `${interviewTitle.replace(/[^a-z0-9]/gi, '_')}_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      
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
      showError('Ошибка при скачивании PDF')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary flex">
      <Sidebar language={language} />
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="sticky top-0 bg-bg-secondary border-b border-border-color px-12 py-6 flex items-center justify-between relative z-[55] backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <MenuButton />
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">{t.title}</h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {sessions.length === 0 ? (
              <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                <p className="text-text-tertiary text-sm font-normal tracking-wide">{t.noInterviews}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className="bg-bg-secondary rounded-lg border border-border-color p-6 hover:border-[#AF52DE] transition-all duration-200 hover:shadow-md"
                  >
                    <div className="flex items-start justify-between mb-6">
                      <div className="flex-1">
                        <div className="flex items-center gap-4 mb-3">
                          <h3 className="text-xl font-semibold text-text-primary tracking-tight">
                            Интервью #{session.id}
                          </h3>
                          <span
                            className={`px-2.5 py-1 rounded text-xs font-medium tracking-tight ${
                              session.status === 'completed'
                                ? 'bg-white text-black'
                                : session.status === 'in_progress'
                                ? 'bg-bg-quaternary text-yellow-500 border border-border-hover'
                                : 'bg-bg-quaternary text-text-tertiary border border-border-hover'
                            }`}
                          >
                            {getStatusText(session.status)}
                          </span>
                          {session.application_status && (
                            <StatusBadge 
                              status={session.application_status} 
                              size="sm"
                            />
                          )}
                        </div>
                        <div className="text-sm text-text-tertiary space-y-1">
                          <div>{t.date}: {formatDate(session.created_at)}</div>
                          {session.completed_at && (
                            <div>{t.completedAt}: {formatDate(session.completed_at)}</div>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-3xl font-semibold text-text-primary mb-1 tracking-tight">
                          {session.total_score !== null
                            ? Math.round(session.total_score)
                            : session.summary.average_score
                            ? Math.round(session.summary.average_score)
                            : '-'}
                          <span className="text-lg text-text-tertiary">/100</span>
                        </div>
                        <div className="text-sm text-text-tertiary">{t.score}</div>
                      </div>
                    </div>

                    {/* Statistics */}
                    <div className="grid md:grid-cols-3 gap-4 mb-6">
                      <div className="bg-bg-tertiary rounded-lg p-4 border border-border-color">
                        <div className="text-2xl font-semibold text-text-primary mb-1 tracking-tight">
                          {session.summary.total_questions}
                        </div>
                        <div className="text-sm text-text-tertiary">{t.questions}</div>
                      </div>
                      <div className="bg-bg-tertiary rounded-lg p-4 border border-border-color">
                        <div className="text-2xl font-semibold text-text-primary mb-1 tracking-tight">
                          {session.summary.answered_questions}
                        </div>
                        <div className="text-sm text-text-tertiary">{t.answered}</div>
                      </div>
                      <div className="bg-bg-tertiary rounded-lg p-4 border border-border-color">
                        <div className="text-2xl font-semibold text-text-primary mb-1 tracking-tight">
                          {session.summary?.average_score != null ? session.summary.average_score.toFixed(1) : '-'}
                        </div>
                        <div className="text-sm text-text-tertiary">{t.averageScore}</div>
                      </div>
                    </div>

                    {/* Summary */}
                    {session.summary.answers.length > 0 && (
                      <div className="mt-6 pt-6 border-t border-border-color">
                        <h4 className="text-sm font-semibold text-text-primary mb-4 tracking-tight">{t.summary}</h4>
                        <div className="space-y-3">
                          {session.summary.answers.map((answer, idx) => (
                            <div
                              key={idx}
                              className="bg-bg-tertiary rounded-lg p-4 border border-border-color"
                            >
                              <div className="text-sm text-text-primary mb-2 line-clamp-2">
                                <span className="font-medium">Q:</span> {answer.question.substring(0, 100)}
                                {answer.question.length > 100 ? '...' : ''}
                              </div>
                              <div className="text-sm text-text-tertiary mb-2 line-clamp-2">
                                <span className="font-medium">A:</span> {answer.answer?.substring(0, 100) || 'Нет ответа'}
                                {answer.answer && answer.answer.length > 100 ? '...' : ''}
                              </div>
                              {answer.score !== null && (
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-text-muted">
                                    {answer.evaluation?.feedback?.substring(0, 80) || ''}
                                    {answer.evaluation?.feedback && answer.evaluation.feedback.length > 80 ? '...' : ''}
                                  </span>
                                  <span
                                    className={`text-sm font-semibold ${
                                      answer.score >= 70
                                        ? 'text-text-primary'
                                        : answer.score >= 50
                                        ? 'text-yellow-500'
                                        : 'text-red-500'
                                    }`}
                                  >
                                    {Math.round(answer.score)}/100
                                  </span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="mt-6 pt-6 border-t border-border-color flex items-center gap-3">
                      <button
                        onClick={() => handleViewReport(session.id, `Интервью #${session.id}`)}
                        className="px-4 py-2 bg-[#AF52DE] hover:bg-[#8E44AD] text-white rounded-lg font-medium transition-all duration-200 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        Просмотр отчета
                      </button>
                      <button
                        onClick={() => handleDownloadPDF(session.id, `Интервью #${session.id}`)}
                        className="px-4 py-2 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg font-medium transition-all duration-200 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                        </svg>
                        Скачать PDF
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Report Viewer Modal */}
      {selectedReportId && (
        <ReportViewer
          sessionId={selectedReportId}
          isOpen={!!selectedReportId}
          onClose={() => setSelectedReportId(null)}
          reportTitle={selectedReportTitle}
        />
      )}
    </div>
  )
}

