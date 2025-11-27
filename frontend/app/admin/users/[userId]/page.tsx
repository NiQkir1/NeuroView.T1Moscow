'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { auth, User } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import LoadingSpinner from '@/app/components/LoadingSpinner'
import ReportViewer from '@/app/components/ReportViewer'
import { useNotifications } from '@/app/hooks/useNotifications'
import { useTheme } from '@/app/hooks/useTheme'

interface InterviewReport {
  id: number
  interview_id: number
  interview_title: string
  status: string
  started_at: string | null
  completed_at: string | null
  total_score: number | null
  created_at: string
  questions_count: number
  answered_count: number
  candidate_name?: string
  candidate_position?: string
}

interface CandidateProfile {
  id: number
  username: string
  email?: string
  full_name?: string
  github_username?: string
  linkedin_url?: string
  skills?: string[]
  skill_matrix?: { [key: string]: { score: number; questions_count: number; level: string } }
  soft_skills_score?: any
  success_prediction?: any
}

interface UserProfile {
  user: User
  interview_reports: InterviewReport[]
}

export default function UserProfilePage() {
  const router = useRouter()
  const { showError } = useNotifications()
  const { theme: currentTheme } = useTheme()
  const params = useParams()
  const userId = params?.userId ? parseInt(params.userId as string) : null

  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [candidateProfile, setCandidateProfile] = useState<CandidateProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingProfile, setLoadingProfile] = useState(false)
  const [error, setError] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null)
  const [selectedReportTitle, setSelectedReportTitle] = useState<string>('')
  const [downloadingReportId, setDownloadingReportId] = useState<number | null>(null)

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

    if (userId) {
      loadUserProfile(userId)
    }
  }, [router, userId])

  const loadUserProfile = async (id: number) => {
    try {
      const data = await apiClient.get(`/api/admin/users/${id}/profile`) as UserProfile
      setProfile(data)
      
      // Загружаем расширенный профиль для кандидатов
      if (data.user.role === 'candidate') {
        loadCandidateProfile(id)
      }
    } catch (err) {
      setError('Не удалось загрузить профиль пользователя')
      showError('Не удалось загрузить профиль пользователя')
    } finally {
      setLoading(false)
    }
  }

  const loadCandidateProfile = async (id: number) => {
    setLoadingProfile(true)
    try {
      const data = await apiClient.get(`/api/candidates/${id}/profile`) as CandidateProfile
      setCandidateProfile(data)
    } catch (error) {
      showError('Не удалось загрузить профиль кандидата')
    } finally {
      setLoadingProfile(false)
    }
  }

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

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-500/20 text-red-400 border-red-500/50'
      case 'hr':
        return 'bg-purple-apple/20 text-purple-apple border-purple-apple/50'
      case 'moderator':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50'
    }
  }

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'admin':
        return 'Администратор'
      case 'hr':
        return 'HR'
      case 'moderator':
        return 'Модератор'
      default:
        return 'Кандидат'
    }
  }

  const handleDeleteUser = async () => {
    if (!userId) return

    setIsDeleting(true)
    setError('')

    try {
      await apiClient.delete(`/api/admin/users/${userId}`)

      // Успешно удалено, перенаправляем на страницу со списком пользователей
      router.push('/admin')
    } catch (err: any) {
      const errorMessage = err.message || 'Не удалось удалить пользователя'
      setError(errorMessage)
      showError(errorMessage)
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  const handleViewReport = (reportId: number, reportTitle: string) => {
    setSelectedReportId(reportId)
    setSelectedReportTitle(reportTitle)
  }

  const handleDownloadPDF = async (sessionId: number, reportTitle: string) => {
    try {
      setError('')
      setDownloadingReportId(sessionId)
      const { auth } = await import('@/lib/auth')
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

  if (!profile) {
    return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center">
      <div className="text-red-400 text-xl">Пользователь не найден</div>
    </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary p-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <button
            onClick={() => router.push('/admin')}
            className="mb-6 text-text-tertiary hover:text-text-primary transition-colors text-sm flex items-center gap-2 tracking-tight"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            Назад к списку пользователей
          </button>
          <h1 className="text-5xl font-semibold text-text-primary mb-3 tracking-tight">
            Профиль пользователя
          </h1>
        </div>

        {error && (
          <div className="mb-8 bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 text-[#ff4444] text-sm">
            {error}
          </div>
        )}

        {/* User Info */}
        <div className="bg-bg-secondary rounded-lg p-8 border border-border-color mb-8">
          <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">Информация о пользователе</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Имя пользователя</label>
              <div className="text-text-primary text-base font-medium">{profile.user.username}</div>
            </div>
            <div>
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Email</label>
              <div className="text-text-primary text-base">{profile.user.email || '-'}</div>
            </div>
            <div>
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Полное имя</label>
              <div className="text-text-primary text-base">{profile.user.full_name || '-'}</div>
            </div>
            <div>
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Роль</label>
              <span
                className={`inline-block px-2.5 py-1 rounded text-xs font-medium tracking-tight ${
                  profile.user.role === 'admin'
                    ? 'bg-white text-black'
                    : profile.user.role === 'hr'
                    ? 'bg-white text-black'
                    : 'bg-bg-quaternary text-text-tertiary border border-border-hover'
                }`}
              >
                {getRoleLabel(profile.user.role)}
              </span>
            </div>
            <div>
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Дата регистрации</label>
              <div className="text-text-primary text-base">
                {new Date(profile.user.created_at).toLocaleDateString('ru-RU', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </div>
            </div>
            <div>
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Статус</label>
              <div className="text-text-primary text-base">
                {profile.user.is_active ? 'Активен' : 'Неактивен'}
              </div>
            </div>
          </div>

          {/* Mercor AI v2.0.0: Расширенная информация о кандидате */}
          {candidateProfile && (
            <div className="mt-8 pt-8 border-t border-border-color">
              <h3 className="text-lg font-semibold text-text-primary mb-6 tracking-tight">
                Расширенный профиль (Mercor AI v2.0.0)
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {candidateProfile.github_username && (
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">GitHub</label>
                    <div className="text-text-primary text-base">
                      <a
                        href={`https://github.com/${candidateProfile.github_username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-apple hover:underline"
                      >
                        {candidateProfile.github_username}
                      </a>
                    </div>
                  </div>
                )}
                {candidateProfile.linkedin_url && (
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">LinkedIn</label>
                    <div className="text-text-primary text-base">
                      <a
                        href={candidateProfile.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-apple hover:underline"
                      >
                        Профиль LinkedIn
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {candidateProfile.skills && candidateProfile.skills.length > 0 && (
                <div className="mb-6">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-3 block">Навыки</label>
                  <div className="flex flex-wrap gap-2">
                    {candidateProfile.skills.map((skill, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-bg-tertiary border border-border-color rounded-lg text-text-primary text-sm"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {candidateProfile.skill_matrix && Object.keys(candidateProfile.skill_matrix).length > 0 && (
                <div className="mb-6">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-3 block">Матрица навыков</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.entries(candidateProfile.skill_matrix).map(([skill, data]) => (
                      <div key={skill} className="p-3 bg-bg-tertiary rounded-lg border border-border-color">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-text-primary font-medium text-sm">{skill}</span>
                          <span className="text-text-muted text-xs">{data.level}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-bg-quaternary rounded-full overflow-hidden">
                            <div
                              className="h-full bg-purple-apple transition-all"
                              style={{ width: `${(data.score / 100) * 100}%` }}
                            />
                          </div>
                          <span className="text-text-tertiary text-xs w-12 text-right">
                            {data.score != null ? data.score.toFixed(0) : 'N/A'}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Delete Button */}
          {profile.user.role !== 'admin' && profile.user.id !== auth.getUser()?.id && (
            <div className="mt-8 pt-8 border-t border-border-color">
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={isDeleting}
                className="w-full md:w-auto px-6 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/50 rounded-xl font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Удалить пользователя
              </button>
            </div>
          )}

          {/* Delete Confirmation Modal */}
          {showDeleteConfirm && (
            <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
              <div className="bg-bg-secondary rounded-xl p-8 border border-border-color max-w-md w-full">
                <h3 className="text-xl font-semibold text-text-primary mb-4">Подтверждение удаления</h3>
                <p className="text-text-tertiary mb-6">
                  Вы уверены, что хотите удалить пользователя <span className="text-text-primary font-medium">{profile.user.username}</span>? 
                  Это действие нельзя отменить. Все связанные данные (собеседования, ответы) также будут удалены.
                </p>
                <div className="flex gap-4">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={isDeleting}
                    className="flex-1 px-4 py-2 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Отмена
                  </button>
                  <button
                    onClick={handleDeleteUser}
                    disabled={isDeleting}
                    className="flex-1 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/50 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isDeleting ? 'Удаление...' : 'Удалить'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Interview Reports */}
        <div className="bg-bg-secondary rounded-lg p-8 border border-border-color">
          <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">
            Отчеты о собеседованиях ({profile.interview_reports.length})
          </h2>

          {profile.interview_reports.length === 0 ? (
            <div className="text-center py-16 text-text-tertiary text-sm">
              У пользователя пока нет пройденных собеседований
            </div>
          ) : (
            <div className="space-y-3">
              {profile.interview_reports.map((report) => (
                <div
                  key={report.id}
                  className="bg-bg-tertiary rounded-lg p-6 border border-border-color hover:border-border-hover transition-all duration-200"
                >
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-text-primary mb-2 tracking-tight">
                        {report.candidate_name || profile.user.full_name || profile.user.username}
                      </h3>
                      <div className="text-sm text-text-tertiary mb-4">
                        {report.candidate_position || report.interview_title}
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
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-text-muted text-xs uppercase tracking-wider">Статус:</span>
                          <div className="mt-1">
                            <span
                              className={`inline-block px-2.5 py-1 rounded text-xs font-medium tracking-tight ${
                                report.status === 'completed'
                                  ? 'bg-white text-black'
                                  : report.status === 'in_progress'
                                  ? 'bg-bg-quaternary text-[#ffaa00] border border-border-hover'
                                  : 'bg-bg-quaternary text-[#ff4444] border border-border-hover'
                              }`}
                            >
                              {getStatusLabel(report.status)}
                            </span>
                          </div>
                        </div>
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
                        <div>
                          <span className="text-text-muted text-xs uppercase tracking-wider">Дата:</span>
                          <div className="mt-1 text-text-primary text-sm">
                            {new Date(report.created_at).toLocaleDateString('ru-RU')}
                          </div>
                        </div>
                      </div>
                      {report.completed_at && (
                        <div className="mt-1 text-xs text-text-tertiary">
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
                        className="px-4 py-2 bg-bg-tertiary hover:bg-bg-hover text-text-primary border border-border-color rounded-lg font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
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

