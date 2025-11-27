'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import AdminSidebar from '../components/AdminSidebar'
import MenuButton from '../../components/MenuButton'
import Logo from '../../components/Logo'
import { useSidebar } from '../../components/SidebarContext'
import LoadingSpinner from '../../components/LoadingSpinner'
import ReportViewer from '@/app/components/ReportViewer'
import { useNotifications } from '../../hooks/useNotifications'

interface Report {
  id: number
  interview_id: number
  interview_title: string
  candidate_id: number
  candidate_username: string
  candidate_full_name: string | null
  status: string
  started_at: string | null
  completed_at: string | null
  total_score: number | null
  created_at: string
  questions_count: number
  answered_count: number
}

export default function ReportsPage() {
  const router = useRouter()
  const { closeSidebar } = useSidebar()
  const { showError } = useNotifications()
  const [reports, setReports] = useState<Report[]>([])
  const [filteredReports, setFilteredReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sortBy, setSortBy] = useState<'created_at' | 'username'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null)
  const [selectedReportTitle, setSelectedReportTitle] = useState<string>('')
  const [downloadingReportId, setDownloadingReportId] = useState<number | null>(null)
  
  // Закрываем сайдбар при загрузке страницы
  useEffect(() => {
    closeSidebar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  
  // Фильтры
  const [filterStatus, setFilterStatus] = useState<{
    completed: boolean
    in_progress: boolean
    cancelled: boolean
    scheduled: boolean
  }>({
    completed: true,
    in_progress: true,
    cancelled: true,
    scheduled: true,
  })

  useEffect(() => {
    // Проверка прав доступа
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }

    const user = auth.getUser()
    if (!user || user.role !== 'admin') {
      router.push('/dashboard')
      return
    }

    loadReports()
  }, [router, sortBy, sortOrder])

  const loadReports = async () => {
    try {
      const data = await apiClient.get<Report[]>(
        `/api/admin/reports?sort_by=${sortBy}&sort_order=${sortOrder}`
      )
      setReports(data)
    } catch (err) {
      setError('Не удалось загрузить отчеты')
      showError('Не удалось загрузить отчеты')
    } finally {
      setLoading(false)
    }
  }

  // Применяем фильтры и поиск
  useEffect(() => {
    let filtered = [...reports]

    // Поиск по имени пользователя
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim()
      filtered = filtered.filter(report => 
        report.candidate_username.toLowerCase().includes(query) ||
        (report.candidate_full_name && report.candidate_full_name.toLowerCase().includes(query))
      )
    }

    // Фильтр по статусу
    filtered = filtered.filter(report => {
      if (report.status === 'completed' && !filterStatus.completed) return false
      if (report.status === 'in_progress' && !filterStatus.in_progress) return false
      if (report.status === 'cancelled' && !filterStatus.cancelled) return false
      if (report.status === 'scheduled' && !filterStatus.scheduled) return false
      return true
    })

    setFilteredReports(filtered)
  }, [reports, searchQuery, filterStatus])

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/50'
      case 'in_progress':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50'
      case 'cancelled':
        return 'bg-red-500/20 text-red-400 border-red-500/50'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Завершено'
      case 'in_progress':
        return 'В процессе'
      case 'cancelled':
        return 'Отменено'
      case 'scheduled':
        return 'Запланировано'
      default:
        return status
    }
  }

  const handleReportClick = (candidateId: number) => {
    router.push(`/admin/users/${candidateId}`)
  }

  const handleViewReport = (reportId: number, reportTitle: string) => {
    setSelectedReportId(reportId)
    setSelectedReportTitle(reportTitle)
  }

  const handleDownloadPDF = async (sessionId: number, reportTitle: string) => {
    try {
      setError('')
      setDownloadingReportId(sessionId)
      const token = auth.getToken()
      if (!token) {
        setError('Требуется авторизация')
        setDownloadingReportId(null)
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
        // Пытаемся прочитать ошибку из ответа
        let errorMessage = `Ошибка ${response.status}: ${response.statusText}`
        try {
          const contentType = response.headers.get('Content-Type')
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json()
            errorMessage = errorData.detail || errorData.message || errorMessage
          } else {
            const text = await response.text()
            if (text) {
              errorMessage = text.substring(0, 200) // Ограничиваем длину
            }
          }
        } catch (parseError) {
          // Если не удалось распарсить ошибку, используем дефолтное сообщение
        }
        throw new Error(errorMessage)
      }
      
      // Проверяем, что ответ действительно PDF
      const contentType = response.headers.get('Content-Type')
      if (contentType && !contentType.includes('application/pdf')) {
        throw new Error('Получен неверный тип файла. Ожидался PDF.')
      }
      
      // Получаем имя файла из заголовков или используем дефолтное
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `${reportTitle.replace(/[^a-z0-9]/gi, '_')}_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '')
          // Декодируем URL-encoded имя файла
          try {
            filename = decodeURIComponent(filename)
          } catch (e) {
            // Если декодирование не удалось, используем как есть
          }
        }
      }
      
      // Создаем blob и скачиваем
      const blob = await response.blob()
      
      // Проверяем, что blob не пустой
      if (blob.size === 0) {
        throw new Error('Получен пустой файл')
      }
      
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      // Очищаем ошибку при успешном скачивании
      setError('')
    } catch (err: any) {
      const errorMessage = err.message || 'Не удалось скачать отчет'
      setError(errorMessage)
      showError(errorMessage)
    } finally {
      setDownloadingReportId(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-text-primary text-xl">Загрузка...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary flex">
      <AdminSidebar currentPage="reports" />
      
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="sticky top-0 bg-bg-secondary border-b border-border-color px-12 py-6 flex items-center justify-between relative z-[55] backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <MenuButton />
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
              Отчеты о собеседованиях
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>
        
        <div className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {/* Description */}
            <div className="mb-12">
              <p className="text-text-tertiary text-sm font-normal tracking-wide">Все отчеты о пройденных собеседованиях</p>
            </div>

          {error && (
            <div className="mb-8 bg-bg-quaternary border border-border-hover rounded-lg p-4 text-red-500 text-sm">
              {error}
            </div>
          )}

          {/* Search and Filter Controls */}
          <div className="bg-bg-secondary rounded-lg p-6 border border-border-color mb-8">
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between mb-6">
              {/* Search */}
              <div className="flex-1 max-w-md">
                <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Поиск по имени пользователя</label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Введите имя пользователя..."
                    className="w-full px-4 py-2.5 pl-10 bg-bg-tertiary border border-border-color text-text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all placeholder-text-muted"
                  />
                  <svg
                    className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-muted"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                </div>
              </div>

              {/* Filter Button */}
              <div className="relative">
                <button
                  onClick={() => setShowFilterMenu(!showFilterMenu)}
                  className="flex items-center gap-2.5 px-5 py-2.5 bg-bg-tertiary text-text-primary border border-border-color rounded-lg hover:bg-bg-quaternary hover:border-border-hover transition-all duration-200 text-sm font-medium tracking-tight"
                >
                  <Image src="/pic/filter.png" alt="Filters" width={16} height={16} className="w-4 h-4" />
                  Фильтры
                  {(!filterStatus.completed || !filterStatus.in_progress || !filterStatus.cancelled || !filterStatus.scheduled) && (
                    <span className="ml-1 px-2 py-0.5 bg-white text-black text-xs rounded-full font-medium">
                      {Object.values(filterStatus).filter(Boolean).length}
                    </span>
                  )}
                </button>

                {/* Filter Menu */}
                {showFilterMenu && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowFilterMenu(false)}
                    />
                    <div className="absolute right-0 top-full mt-2 bg-bg-secondary rounded-lg p-6 border border-border-color shadow-2xl z-20 min-w-[300px] backdrop-blur-xl">
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="text-base font-semibold text-text-primary tracking-tight">Фильтры по статусу</h3>
                        <button
                          onClick={() => setShowFilterMenu(false)}
                          className="text-text-muted hover:text-text-primary transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                      
                      <div className="space-y-2.5">
                        <label className="flex items-center gap-3 cursor-pointer group py-2">
                          <input
                            type="checkbox"
                            checked={filterStatus.completed}
                            onChange={(e) => setFilterStatus(prev => ({ ...prev, completed: e.target.checked }))}
                            className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-white focus:ring-offset-0 focus:ring-offset-transparent"
                          />
                          <div className="flex items-center gap-2.5">
                            <span className={`inline-block w-2 h-2 rounded-full ${filterStatus.completed ? 'bg-white' : 'bg-bg-hover'}`}></span>
                            <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">Завершено</span>
                          </div>
                        </label>
                        
                        <label className="flex items-center gap-3 cursor-pointer group py-2">
                          <input
                            type="checkbox"
                            checked={filterStatus.in_progress}
                            onChange={(e) => setFilterStatus(prev => ({ ...prev, in_progress: e.target.checked }))}
                            className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-white focus:ring-offset-0 focus:ring-offset-transparent"
                          />
                          <div className="flex items-center gap-2.5">
                            <span className={`inline-block w-2 h-2 rounded-full ${filterStatus.in_progress ? 'bg-white' : 'bg-bg-hover'}`}></span>
                            <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">В процессе</span>
                          </div>
                        </label>
                        
                        <label className="flex items-center gap-3 cursor-pointer group py-2">
                          <input
                            type="checkbox"
                            checked={filterStatus.cancelled}
                            onChange={(e) => setFilterStatus(prev => ({ ...prev, cancelled: e.target.checked }))}
                            className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-white focus:ring-offset-0 focus:ring-offset-transparent"
                          />
                          <div className="flex items-center gap-2.5">
                            <span className={`inline-block w-2 h-2 rounded-full ${filterStatus.cancelled ? 'bg-white' : 'bg-bg-hover'}`}></span>
                            <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">Отменено</span>
                          </div>
                        </label>
                        
                        <label className="flex items-center gap-3 cursor-pointer group py-2">
                          <input
                            type="checkbox"
                            checked={filterStatus.scheduled}
                            onChange={(e) => setFilterStatus(prev => ({ ...prev, scheduled: e.target.checked }))}
                            className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-white focus:ring-offset-0 focus:ring-offset-transparent"
                          />
                          <div className="flex items-center gap-2.5">
                            <span className={`inline-block w-2 h-2 rounded-full ${filterStatus.scheduled ? 'bg-white' : 'bg-bg-hover'}`}></span>
                            <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">Запланировано</span>
                          </div>
                        </label>
                      </div>

                      <div className="mt-6 pt-4 border-t border-border-color">
                        <button
                          onClick={() => {
                            setFilterStatus({
                              completed: true,
                              in_progress: true,
                              cancelled: true,
                              scheduled: true,
                            })
                          }}
                          className="w-full px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors tracking-tight"
                        >
                          Сбросить фильтры
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Sort Controls */}
            <div>
              <h2 className="text-sm font-semibold text-text-primary mb-4 tracking-tight uppercase text-xs text-text-muted">Сортировка</h2>
              <div className="flex gap-4 flex-wrap items-center">
                <div className="flex items-center gap-3">
                  <label className="text-text-tertiary text-sm">Сортировать по:</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as 'created_at' | 'username')}
                    className="px-4 py-2 bg-bg-tertiary border border-border-hover rounded-lg text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-white focus:border-border-hover transition-all"
                  >
                    <option value="created_at">Времени собеседования</option>
                    <option value="username">Имени пользователя</option>
                  </select>
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-text-tertiary text-sm">Порядок:</label>
                  <select
                    value={sortOrder}
                    onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                    className="px-4 py-2 bg-bg-tertiary border border-border-hover rounded-lg text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-white focus:border-border-hover transition-all"
                  >
                    <option value="desc">По убыванию</option>
                    <option value="asc">По возрастанию</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Reports List */}
          <div className="space-y-3">
            {filteredReports.length === 0 ? (
              <div className="bg-bg-secondary rounded-lg p-16 border border-border-color text-center text-text-muted text-sm">
                {reports.length === 0 ? 'Отчеты не найдены' : 'Нет отчетов, соответствующих фильтрам'}
              </div>
            ) : (
              filteredReports.map((report) => (
                <div
                    key={report.id}
                    className="bg-bg-secondary rounded-lg p-6 border border-border-color hover:border-[#AF52DE] transition-all duration-200 hover:shadow-md"
                  >
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex-1">
                      <div className="mb-2">
                        <h3 className="text-lg font-semibold text-text-primary tracking-tight">
                          {report.candidate_full_name || report.candidate_username}
                        </h3>
                        <div className="text-sm text-text-muted mt-1">
                          {report.interview_title}
                          {report.started_at && (
                            <span className="ml-2">
                              • {new Date(report.started_at).toLocaleDateString('ru-RU', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                              })} в {new Date(report.started_at).toLocaleTimeString('ru-RU', {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3 mb-4">
                        <span
                          className={`inline-block px-2.5 py-1 rounded text-xs font-medium tracking-tight ${
                            report.status === 'completed'
                              ? 'bg-white text-black'
                              : report.status === 'in_progress'
                              ? 'bg-bg-quaternary text-yellow-500 border border-border-hover'
                              : 'bg-bg-quaternary text-red-500 border border-border-hover'
                          }`}
                        >
                          {getStatusLabel(report.status)}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-text-muted text-xs uppercase tracking-wider">Оценка:</span>
                          <div className="mt-1 text-text-primary font-medium text-sm">
                            {report.total_score !== null
                              ? `${report.total_score.toFixed(1)}%`
                              : 'Нет оценки'}
                          </div>
                        </div>
                        <div>
                          <span className="text-text-muted text-xs uppercase tracking-wider">Вопросов:</span>
                          <div className="mt-1 text-text-primary font-medium text-sm">
                            {report.answered_count} / {report.questions_count}
                          </div>
                        </div>
                      </div>
                      {report.completed_at && (
                        <div className="mt-1 text-xs text-text-muted">
                          Завершено: {new Date(report.completed_at).toLocaleString('ru-RU')}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <button
                        onClick={() => handleViewReport(report.id, report.interview_title)}
                        className="px-4 py-2 bg-[#AF52DE] hover:bg-[#8E44AD] text-white rounded-lg font-medium transition-all duration-200 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        Просмотр
                      </button>
                      <button
                        onClick={() => handleDownloadPDF(report.id, report.interview_title)}
                        disabled={downloadingReportId === report.id}
                        className="px-4 py-2 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {downloadingReportId === report.id ? (
                          <>
                            <LoadingSpinner size="sm" />
                            <span>Загрузка...</span>
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                            </svg>
                            Скачать
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => handleReportClick(report.candidate_id)}
                        className="px-4 py-2 text-text-tertiary hover:text-text-primary transition-colors text-sm"
                        title="Перейти к профилю кандидата"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        </div>
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

