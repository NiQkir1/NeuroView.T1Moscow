'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../../components/Sidebar'
import MenuButton from '../../components/MenuButton'
import Logo from '../../components/Logo'
import StatusBadge from '../../components/StatusBadge'
import LoadingSpinner from '../../components/LoadingSpinner'
import ReportViewer from '../../components/ReportViewer'
import { useNotifications } from '../../hooks/useNotifications'

interface InterviewReport {
  id: number
  interview_id: number
  candidate_name: string
  position: string
  difficulty: string
  status: string
  application_status?: string  // v3.0.0
  started_at: string | null
  completed_at: string | null
  total_score: number | null
  created_at: string
  questions_count: number
  answered_count: number
}

export default function HRInterviewsPage() {
  const router = useRouter()
  const { showError } = useNotifications()
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [interviews, setInterviews] = useState<InterviewReport[]>([])
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null)
  const [selectedReportTitle, setSelectedReportTitle] = useState<string>('')
  const [downloadingReportId, setDownloadingReportId] = useState<number | null>(null)

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    if (!auth.isHR()) {
      router.push('/dashboard')
      return
    }
    
    const init = async () => {
      try {
        await loadInterviews()
      } catch (error) {
        console.error('Error loading interviews:', error)
        setIsLoading(false)
      }
    }
    
    init()
  }, [router])

  const loadInterviews = async () => {
    try {
      // Загружаем все сессии интервью
      const data = await apiClient.get('/api/user/sessions')
      setInterviews(data as InterviewReport[])
    } catch (error) {
      showError('Не удалось загрузить список интервью')
    } finally {
      setIsLoading(false)
    }
  }

  const translations = {
    ru: {
      title: 'Проведенные интервью',
      noInterviews: 'Пока не проведено интервью',
      candidate: 'Кандидат',
      position: 'Позиция',
      difficulty: 'Уровень',
      status: 'Статус',
      score: 'Оценка',
      completed: 'Завершено',
      inProgress: 'В процессе',
      questions: 'Вопросов',
      answered: 'Отвечено',
      date: 'Дата',
      viewDetails: 'Подробнее',
    },
    en: {
      title: 'Conducted Interviews',
      noInterviews: 'No interviews conducted yet',
      candidate: 'Candidate',
      position: 'Position',
      difficulty: 'Level',
      status: 'Status',
      score: 'Score',
      completed: 'Completed',
      inProgress: 'In Progress',
      questions: 'Questions',
      answered: 'Answered',
      date: 'Date',
      viewDetails: 'View Details',
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
      default:
        return status
    }
  }

  const handleViewReport = (reportId: number, reportTitle: string) => {
    setSelectedReportId(reportId)
    setSelectedReportTitle(reportTitle)
  }

  const handleDownloadPDF = async (sessionId: number, reportTitle: string) => {
    try {
      setDownloadingReportId(sessionId)
      const token = auth.getToken()
      if (!token) {
        showError('Требуется авторизация')
        setDownloadingReportId(null)
        return
      }
      
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const pdfUrl = `${API_URL}/api/sessions/${sessionId}/report/pdf`
      
      const response = await fetch(pdfUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Ошибка при скачивании PDF' }))
        throw new Error(errorData.detail || `Ошибка ${response.status}`)
      }
      
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `${reportTitle.replace(/[^a-z0-9]/gi, '_')}_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/i)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
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
      showError(err.message || 'Не удалось скачать отчет')
    } finally {
      setDownloadingReportId(null)
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
            {interviews.length === 0 ? (
              <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                <p className="text-text-tertiary text-sm font-normal tracking-wide">{t.noInterviews}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {interviews.map((interview) => (
                  <div
                    key={interview.id}
                    className="bg-bg-secondary rounded-lg border border-border-color p-6 hover:border-[#AF52DE] transition-all duration-200 hover:shadow-md"
                  >
                    <div className="flex items-start justify-between mb-6">
                      <div className="flex-1">
                        <div className="flex items-center gap-4 mb-3">
                          <h3 className="text-xl font-semibold text-text-primary tracking-tight">
                            {interview.candidate_name || 'Кандидат не указан'}
                          </h3>
                          <span
                            className={`px-2.5 py-1 rounded text-xs font-medium tracking-tight ${
                              interview.status === 'completed'
                                ? 'bg-bg-tertiary text-green-500 border border-border-color'
                                : interview.status === 'in_progress'
                                ? 'bg-bg-tertiary text-yellow-500 border border-border-color'
                                : 'bg-bg-tertiary text-text-tertiary border border-border-color'
                            }`}
                          >
                            {getStatusText(interview.status)}
                          </span>
                          {interview.application_status && (
                            <StatusBadge 
                              status={interview.application_status} 
                              size="sm"
                            />
                          )}
                        </div>
                        <div className="text-sm text-text-tertiary mb-3">
                          {interview.position || 'Должность не указана'}
                          {interview.started_at && (
                            <span className="ml-2">
                              • {new Date(interview.started_at).toLocaleDateString('ru-RU', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                              })} в {new Date(interview.started_at).toLocaleTimeString('ru-RU', {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-text-tertiary space-y-1">
                          <div>
                            {t.difficulty}: {interview.difficulty || 'Не указан'}
                          </div>
                          {interview.completed_at && (
                            <div>{t.completed}: {formatDate(interview.completed_at)}</div>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-3xl font-semibold text-text-primary mb-1 tracking-tight">
                          {interview.total_score !== null
                            ? Math.round(interview.total_score)
                            : '-'}
                          <span className="text-lg text-text-tertiary">/100</span>
                        </div>
                        <div className="text-sm text-text-tertiary">{t.score}</div>
                      </div>
                    </div>

                    {/* Statistics */}
                    <div className="grid md:grid-cols-2 gap-4 mb-4">
                      <div className="bg-bg-tertiary rounded-lg p-4 border border-border-color">
                        <div className="text-2xl font-semibold text-text-primary mb-1 tracking-tight">
                          {interview.questions_count}
                        </div>
                        <div className="text-sm text-text-tertiary">{t.questions}</div>
                      </div>
                      <div className="bg-bg-tertiary rounded-lg p-4 border border-border-color">
                        <div className="text-2xl font-semibold text-text-primary mb-1 tracking-tight">
                          {interview.answered_count}
                        </div>
                        <div className="text-sm text-text-tertiary">{t.answered}</div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-3 pt-4 border-t border-border-color">
                      <button
                        onClick={() => handleViewReport(interview.id, interview.candidate_name || 'Отчет')}
                        className="px-4 py-2 bg-[#AF52DE] hover:bg-[#8E44AD] text-white rounded-lg font-medium transition-all duration-200 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        Просмотр отчета
                      </button>
                      <button
                        onClick={() => handleDownloadPDF(interview.id, interview.candidate_name || 'Отчет')}
                        disabled={downloadingReportId === interview.id}
                        className="px-4 py-2 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {downloadingReportId === interview.id ? (
                          <>
                            <LoadingSpinner size="sm" />
                            <span>Загрузка...</span>
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                            </svg>
                            Скачать PDF
                          </>
                        )}
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



