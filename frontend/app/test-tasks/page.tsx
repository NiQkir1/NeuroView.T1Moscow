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
import { useNotifications } from '../hooks/useNotifications'

interface TestTask {
  id: number
  session_id: number
  title: string
  description: string
  task_type: string
  deadline: string | null
  status: string
  score: number | null
  feedback: string | null
  solution?: string | null
  created_at: string
}

interface InterviewSession {
  id: number
  interview_id: number
  interview_title: string
  application_status?: string
  status?: string
}

interface TasksResponse {
  tasks: TestTask[]
}

export default function TestTasksPage() {
  const router = useRouter()
  const { showError, showSuccess } = useNotifications()
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [tasks, setTasks] = useState<TestTask[]>([])
  const [selectedTask, setSelectedTask] = useState<TestTask | null>(null)
  const [solution, setSolution] = useState('')

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
      const data = await apiClient.get('/api/user/sessions') as InterviewSession[]
      // Фильтруем сессии с тестовыми заданиями
      const sessionsWithTasks = data.filter((s) => 
        s.application_status === 'test_task' || s.status === 'completed'
      )
      setSessions(sessionsWithTasks)
    } catch (error) {
      showError('Не удалось загрузить список сессий')
    } finally {
      setIsLoading(false)
    }
  }

  const loadTasks = async (sessionId: number) => {
    try {
      const data = await apiClient.get(`/api/test-tasks/session/${sessionId}`) as TasksResponse
      setTasks(data.tasks || [])
      if (data.tasks && data.tasks.length > 0) {
        const pendingTask = data.tasks.find((t) => t.status === 'pending' || t.status === 'in_progress')
        if (pendingTask) {
          setSelectedTask(pendingTask)
          setSolution(pendingTask.solution || '')
        }
      }
    } catch (error) {
      showError('Не удалось загрузить список заданий')
    }
  }

  const handleSubmitSolution = async () => {
    if (!selectedTask || !solution.trim()) {
      alert('Введите решение')
      return
    }

    try {
      await apiClient.post(`/api/test-tasks/${selectedTask.id}/submit`, {
        solution: solution.trim(),
      })
      alert('Решение отправлено!')
      if (selectedSessionId) {
        loadTasks(selectedSessionId)
      }
    } catch (error) {
      showError('Ошибка при отправке решения')
      alert('Ошибка при отправке решения')
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    if (typeof window === 'undefined') return '-' // SSR safe
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const isDeadlinePassed = (deadline: string | null) => {
    if (!deadline) return false
    if (typeof window === 'undefined') return false // SSR safe
    return new Date(deadline) < new Date()
  }

  if (isLoading) {
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
        <header className="sticky top-0 bg-bg-secondary border-b border-border-color px-12 py-6 flex items-center justify-between relative z-[55] backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <MenuButton />
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
              Тестовые задания
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>

        <main className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {sessions.length === 0 ? (
              <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                <p className="text-text-tertiary text-sm">У вас нет тестовых заданий</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Список сессий */}
                <div className="lg:col-span-1 space-y-3">
                  <h2 className="text-lg font-semibold text-text-primary mb-4">Интервью</h2>
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      onClick={() => {
                        setSelectedSessionId(session.id)
                        loadTasks(session.id)
                      }}
                      className={`w-full text-left p-4 rounded-lg border transition-all ${
                        selectedSessionId === session.id
                          ? 'border-[#AF52DE] bg-[#AF52DE]/10'
                          : 'border-border-color hover:border-[#AF52DE]/50'
                      }`}
                    >
                      <div className="font-medium text-text-primary mb-1">
                        {session.interview_title}
                      </div>
                      <div className="text-sm text-text-tertiary">Сессия #{session.id}</div>
                      {session.application_status && (
                        <div className="mt-2">
                          <StatusBadge status={session.application_status} size="sm" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>

                {/* Задания */}
                <div className="lg:col-span-2 space-y-4">
                  {selectedSessionId ? (
                    tasks.length === 0 ? (
                      <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                        <p className="text-text-tertiary text-sm">Нет тестовых заданий</p>
                      </div>
                    ) : (
                      tasks.map((task) => (
                        <div
                          key={task.id}
                          className="bg-bg-secondary rounded-lg border border-border-color p-6 space-y-4"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h3 className="text-xl font-semibold text-text-primary mb-2">
                                {task.title}
                              </h3>
                              <p className="text-text-tertiary mb-4">{task.description}</p>
                              <div className="flex items-center gap-4 text-sm text-text-tertiary mb-4">
                                <span>Тип: {task.task_type}</span>
                                <span>Дедлайн: {formatDate(task.deadline)}</span>
                                {isDeadlinePassed(task.deadline) && (
                                  <span className="text-red-400">Просрочено</span>
                                )}
                                <StatusBadge status={task.status as any} size="sm" />
                              </div>
                            </div>
                          </div>

                          {(task.status === 'pending' || task.status === 'in_progress') && (
                            <div className="border-t border-border-color pt-4">
                              <label className="text-sm text-text-tertiary mb-2 block">
                                Ваше решение
                              </label>
                              <textarea
                                value={solution}
                                onChange={(e) => setSolution(e.target.value)}
                                rows={10}
                                className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary font-mono text-sm"
                                placeholder="Введите ваше решение здесь..."
                              />
                              <button
                                onClick={() => {
                                  setSelectedTask(task)
                                  handleSubmitSolution()
                                }}
                                disabled={!solution.trim() || isDeadlinePassed(task.deadline)}
                                className="mt-4 px-6 py-2 bg-[#AF52DE] text-white rounded-lg hover:bg-[#8E44AD] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                Отправить решение
                              </button>
                            </div>
                          )}

                          {task.status === 'completed' && task.score === null && (
                            <div className="border-t border-border-color pt-4">
                              <p className="text-text-tertiary">Решение отправлено, ожидается проверка</p>
                            </div>
                          )}

                          {task.score !== null && (
                            <div className="border-t border-border-color pt-4">
                              <div className="space-y-2">
                                <div className="flex items-center gap-4">
                                  <span className="text-text-primary font-medium">
                                    Оценка: {task.score}/100
                                  </span>
                                </div>
                                {task.feedback && (
                                  <div className="bg-bg-tertiary rounded-lg p-4">
                                    <p className="text-sm text-text-tertiary">{task.feedback}</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))
                    )
                  ) : (
                    <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                      <p className="text-text-tertiary text-sm">Выберите интервью для просмотра заданий</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}






