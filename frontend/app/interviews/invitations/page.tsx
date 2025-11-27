'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../../components/Sidebar'
import MenuButton from '../../components/MenuButton'
import Logo from '../../components/Logo'
import LoadingSpinner from '../../components/LoadingSpinner'
import { useNotifications } from '../../hooks/useNotifications'

interface InterviewInvitation {
  id: number
  interview_id: number
  interview_title: string
  interview_description?: string
  hr_name: string
  hr_id: number
  message?: string
  status: string
  created_at: string
  expires_at?: string
  responded_at?: string
  is_completed?: boolean  // Флаг завершенности интервью
}

export default function InvitationsPage() {
  const router = useRouter()
  const { showError, showSuccess } = useNotifications()
  const [invitations, setInvitations] = useState<InterviewInvitation[]>([])
  const [loading, setLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [completedSessions, setCompletedSessions] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    
    const init = async () => {
      try {
        await loadInvitations()
      } catch (error) {
        console.error('Error loading invitations:', error)
        setLoading(false)
      }
    }
    
    init()
  }, [router])

  // Обновляем список при возврате на страницу (например, после завершения интервью)
  useEffect(() => {
    const handleFocus = () => {
      if (auth.isAuthenticated()) {
        loadInvitations()
      }
    }
    
    const handleVisibilityChange = () => {
      if (!document.hidden && auth.isAuthenticated()) {
        loadInvitations()
      }
    }
    
    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  const loadInvitations = async () => {
    try {
      // ОПТИМИЗАЦИЯ: Загружаем все данные параллельно одним батчем запросов
      const [invitationsData, sessionsData] = await Promise.all([
        apiClient.get<InterviewInvitation[]>('/api/invitations/my-invitations'),
        apiClient.get<Array<{ status: string; interview_id: number }>>('/api/user/sessions')
      ])
      
      setInvitations(invitationsData)
      
      // Создаем Set из ID завершенных интервью
      const completed = new Set<number>()
      sessionsData.forEach((session) => {
        if (session.status === 'completed' && session.interview_id) {
          completed.add(session.interview_id)
        }
      })
      setCompletedSessions(completed)
    } catch (error) {
      showError('Не удалось загрузить приглашения')
    } finally {
      setLoading(false)
    }
  }

  const handleAccept = async (invitationId: number) => {
    try {
      await apiClient.post(`/api/invitations/${invitationId}/accept`)
      await loadInvitations()
      alert('Приглашение принято! Теперь вы можете пройти собеседование.')
    } catch (error) {
      showError('Ошибка при принятии приглашения')
      alert('Ошибка при принятии приглашения')
    }
  }

  const handleDecline = async (invitationId: number) => {
    if (!confirm('Вы уверены, что хотите отклонить это приглашение?')) {
      return
    }

    try {
      await apiClient.post(`/api/invitations/${invitationId}/decline`)
      await loadInvitations()
      alert('Приглашение отклонено')
    } catch (error) {
      showError('Ошибка при отклонении приглашения')
      alert('Ошибка при отклонении приглашения')
    }
  }

  const getStatusBadge = (status: string, expiresAt?: string) => {
    // SSR safe - используем проверку только на клиенте
    const now = typeof window !== 'undefined' ? new Date() : new Date(0)
    const expires = expiresAt ? new Date(expiresAt) : null
    const isExpired = expires && expires < now

    if (isExpired && status === 'pending') {
      return (
        <span className="px-2.5 py-1 bg-gray-500/20 text-gray-400 border border-gray-500/50 rounded text-xs">
          Истекло
        </span>
      )
    }

    switch (status) {
      case 'pending':
        return (
          <span className="px-2.5 py-1 bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 rounded text-xs">
            Ожидает ответа
          </span>
        )
      case 'accepted':
        return (
          <span className="px-2.5 py-1 bg-green-500/20 text-green-400 border border-green-500/50 rounded text-xs">
            Принято
          </span>
        )
      case 'declined':
        return (
          <span className="px-2.5 py-1 bg-red-500/20 text-red-400 border border-red-500/50 rounded text-xs">
            Отклонено
          </span>
        )
      default:
        return (
          <span className="px-2.5 py-1 bg-gray-500/20 text-gray-400 border border-gray-500/50 rounded text-xs">
            {status}
          </span>
        )
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-text-primary text-xl tracking-tight">Загрузка...</div>
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
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
              Мои собеседования
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-5xl mx-auto">
            {invitations.length === 0 ? (
              <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                <svg
                  className="w-16 h-16 mx-auto mb-4 text-text-tertiary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="text-text-tertiary text-lg mb-2">Нет приглашений</p>
                <p className="text-text-tertiary text-sm">
                  Когда HR отправит вам приглашение на собеседование, оно появится здесь
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {invitations.map((invitation) => {
                  const expiresAt = invitation.expires_at ? new Date(invitation.expires_at) : null
                  const isExpired = expiresAt && expiresAt < new Date()
                  const canRespond = invitation.status === 'pending' && !isExpired
                  const isCompleted = completedSessions.has(invitation.interview_id)

                  return (
                    <div
                      key={invitation.id}
                      className="bg-bg-secondary rounded-lg border border-border-color p-6 hover:border-purple-apple transition-all"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <h3 className="text-xl font-semibold text-text-primary mb-2 tracking-tight">
                            {invitation.interview_title}
                          </h3>
                          {invitation.interview_description && (
                            <p className="text-text-tertiary text-sm mb-4">
                              {invitation.interview_description}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mb-4">
                            <span className="text-text-tertiary text-sm">От:</span>
                            <span className="text-text-primary font-medium">{invitation.hr_name}</span>
                            {getStatusBadge(invitation.status, invitation.expires_at)}
                          </div>
                          {invitation.message && (
                            <div className="bg-bg-tertiary rounded-lg p-4 mb-4 border border-border-color">
                              <p className="text-text-primary text-sm whitespace-pre-wrap">
                                {invitation.message}
                              </p>
                            </div>
                          )}
                          <div className="flex items-center gap-4 text-xs text-text-tertiary">
                            <span>
                              Получено: {new Date(invitation.created_at).toLocaleString('ru-RU')}
                            </span>
                            {invitation.expires_at && (
                              <span>
                                Действует до: {new Date(invitation.expires_at).toLocaleString('ru-RU')}
                              </span>
                            )}
                            {invitation.responded_at && (
                              <span>
                                Ответ дан: {new Date(invitation.responded_at).toLocaleString('ru-RU')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {canRespond && (
                        <div className="flex gap-3 pt-4 border-t border-border-color">
                          <button
                            onClick={() => handleAccept(invitation.id)}
                            className="px-6 py-2.5 bg-green-500/20 text-green-400 border border-green-500/50 rounded-lg hover:bg-green-500/30 transition-all font-medium"
                          >
                            Принять приглашение
                          </button>
                          <button
                            onClick={() => handleDecline(invitation.id)}
                            className="px-6 py-2.5 bg-red-500/20 text-red-400 border border-red-500/50 rounded-lg hover:bg-red-500/30 transition-all font-medium"
                          >
                            Отклонить
                          </button>
                        </div>
                      )}

                      {(() => {
                        // Проверяем, завершено ли интервью для этого приглашения
                        const isCompleted = completedSessions.has(invitation.interview_id)
                        
                        // Дополнительная проверка через localStorage (на случай, если интервью только что завершено)
                        const interviewCompleted = typeof window !== 'undefined' 
                          ? localStorage.getItem(`interview_${invitation.interview_id}_completed`) === 'true'
                          : false
                        
                        const isInterviewCompleted = isCompleted || interviewCompleted
                        
                        if (invitation.status === 'accepted' && !isInterviewCompleted) {
                          return (
                            <div className="pt-4 border-t border-border-color">
                              <button
                                onClick={async () => {
                                  try {
                                    // Начинаем сессию через приглашение (без кода)
                                    const data = await apiClient.post(`/api/invitations/${invitation.id}/start-interview`)
                                    // Сохраняем информацию о том, что доступ через приглашение
                                    if (typeof window !== 'undefined') {
                                      sessionStorage.setItem(`interview_${invitation.interview_id}_invitation`, 'true')
                                      sessionStorage.setItem(`interview_${invitation.interview_id}_verified`, 'true')
                                    }
                                    router.push(`/interview?id=${invitation.interview_id}`)
                                  } catch (error) {
                                    showError('Ошибка при начале собеседования')
                                    alert('Ошибка при начале собеседования')
                                  }
                                }}
                                className="px-6 py-2.5 bg-purple-apple text-white rounded-lg hover:bg-purple-apple/80 transition-all font-medium"
                              >
                                Пройти собеседование
                              </button>
                            </div>
                          )
                        }
                        
                        if (invitation.status === 'accepted' && isInterviewCompleted) {
                          return (
                            <div className="pt-4 border-t border-border-color">
                              <div className="px-6 py-2.5 bg-green-500/20 text-green-400 border border-green-500/50 rounded-lg text-center font-medium">
                                Собеседование пройдено
                              </div>
                            </div>
                          )
                        }
                        
                        return null
                      })()}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

