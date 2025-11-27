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
import { useNotifications } from '../../hooks/useNotifications'

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
  created_at: string
  candidate_name?: string
  interview_title?: string
}

interface InterviewSession {
  id: number
  interview_id: number
  candidate_id: number
  candidate_name: string
  interview_title: string
  application_status?: string
}

export default function HRTestTasksPage() {
  const router = useRouter()
  const { showError, showSuccess } = useNotifications()
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [tasks, setTasks] = useState<TestTask[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    task_type: 'coding',
    deadline_days: 7,
  })

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
      const data = await apiClient.get('/api/user/sessions') as any[]
      setSessions(data.filter((s: any) => s.status === 'completed' || s.application_status))
    } catch (error) {
      showError('Не удалось загрузить список сессий')
    } finally {
      setIsLoading(false)
    }
  }

  const loadTasks = async (sessionId: number) => {
    try {
      const data = await apiClient.get(`/api/test-tasks/session/${sessionId}`) as any
      setTasks(data.tasks || [])
    } catch (error) {
      showError('Не удалось загрузить список заданий')
    }
  }

  const handleCreateTask = async () => {
    if (!selectedSessionId || !newTask.title || !newTask.description) {
      alert('Заполните все поля')
      return
    }

    try {
      await apiClient.post('/api/test-tasks', {
        session_id: selectedSessionId,
        ...newTask,
      })
      setShowCreateModal(false)
      setNewTask({ title: '', description: '', task_type: 'coding', deadline_days: 7 })
      if (selectedSessionId) {
        loadTasks(selectedSessionId)
      }
    } catch (error) {
      showError('Ошибка при создании задания')
      alert('Ошибка при создании задания')
    }
  }

  const handleReviewTask = async (taskId: number, score: number, feedback: string) => {
    try {
      await apiClient.post(`/api/test-tasks/${taskId}/review`, { score, feedback })
      if (selectedSessionId) {
        loadTasks(selectedSessionId)
      }
      loadSessions()
    } catch (error) {
      showError('Ошибка при проверке задания')
      alert('Ошибка при проверке задания')
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
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
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Сессии с интервью */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Сессии интервью</h2>
              {sessions.length === 0 ? (
                <p className="text-text-tertiary text-sm">Нет доступных сессий</p>
              ) : (
                <div className="space-y-2">
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
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-text-primary">
                            {session.interview_title} - {session.candidate_name}
                          </div>
                          <div className="text-sm text-text-tertiary">Сессия #{session.id}</div>
                        </div>
                        {session.application_status && (
                          <StatusBadge status={session.application_status} size="sm" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Тестовые задания */}
            {selectedSessionId && (
              <div className="bg-bg-secondary rounded-lg border border-border-color p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-text-primary">Тестовые задания</h2>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="px-4 py-2 bg-[#AF52DE] text-white rounded-lg hover:bg-[#8E44AD] transition-all"
                  >
                    Создать задание
                  </button>
                </div>

                {tasks.length === 0 ? (
                  <p className="text-text-tertiary text-sm">Нет тестовых заданий</p>
                ) : (
                  <div className="space-y-4">
                    {tasks.map((task) => (
                      <div
                        key={task.id}
                        className="border border-border-color rounded-lg p-4 space-y-3"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="font-semibold text-text-primary mb-1">{task.title}</h3>
                            <p className="text-sm text-text-tertiary mb-2">{task.description}</p>
                            <div className="flex items-center gap-4 text-sm text-text-tertiary">
                              <span>Тип: {task.task_type}</span>
                              <span>Дедлайн: {formatDate(task.deadline)}</span>
                              <StatusBadge status={task.status as any} size="sm" />
                            </div>
                          </div>
                        </div>

                        {task.status === 'completed' && task.score === null && (
                          <div className="border-t border-border-color pt-3">
                            <h4 className="font-medium text-text-primary mb-2">Проверка задания</h4>
                            <div className="space-y-2">
                              <div>
                                <label className="text-sm text-text-tertiary">Оценка (0-100)</label>
                                <input
                                  type="number"
                                  min="0"
                                  max="100"
                                  id={`score-${task.id}`}
                                  className="w-full mt-1 px-3 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary"
                                />
                              </div>
                              <div>
                                <label className="text-sm text-text-tertiary">Обратная связь</label>
                                <textarea
                                  id={`feedback-${task.id}`}
                                  rows={3}
                                  className="w-full mt-1 px-3 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary"
                                />
                              </div>
                              <button
                                onClick={() => {
                                  const scoreInput = document.getElementById(`score-${task.id}`) as HTMLInputElement
                                  const feedbackInput = document.getElementById(`feedback-${task.id}`) as HTMLTextAreaElement
                                  if (scoreInput && feedbackInput) {
                                    handleReviewTask(task.id, parseFloat(scoreInput.value), feedbackInput.value)
                                  }
                                }}
                                className="px-4 py-2 bg-[#AF52DE] text-white rounded-lg hover:bg-[#8E44AD] transition-all"
                              >
                                Отправить оценку
                              </button>
                            </div>
                          </div>
                        )}

                        {task.score !== null && (
                          <div className="border-t border-border-color pt-3">
                            <div className="flex items-center gap-4">
                              <span className="text-text-primary font-medium">
                                Оценка: {task.score}/100
                              </span>
                              {task.feedback && (
                                <span className="text-sm text-text-tertiary">{task.feedback}</span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>

        {/* Модальное окно создания задания */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-bg-secondary border border-border-color rounded-lg p-6 w-full max-w-2xl">
              <h2 className="text-xl font-semibold text-text-primary mb-4">Создать тестовое задание</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-text-tertiary mb-1 block">Название</label>
                  <input
                    type="text"
                    value={newTask.title}
                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                    className="w-full px-3 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary"
                  />
                </div>
                <div>
                  <label className="text-sm text-text-tertiary mb-1 block">Описание</label>
                  <textarea
                    value={newTask.description}
                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                    rows={5}
                    className="w-full px-3 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary"
                  />
                </div>
                <div>
                  <label className="text-sm text-text-tertiary mb-1 block">Тип задания</label>
                  <select
                    value={newTask.task_type}
                    onChange={(e) => setNewTask({ ...newTask, task_type: e.target.value })}
                    className="w-full px-3 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary"
                  >
                    <option value="coding">Программирование</option>
                    <option value="algorithm">Алгоритмы</option>
                    <option value="design">Дизайн</option>
                    <option value="essay">Эссе</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-text-tertiary mb-1 block">Дедлайн (дней)</label>
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={newTask.deadline_days}
                    onChange={(e) => setNewTask({ ...newTask, deadline_days: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleCreateTask}
                    className="flex-1 px-4 py-2 bg-[#AF52DE] text-white rounded-lg hover:bg-[#8E44AD] transition-all"
                  >
                    Создать
                  </button>
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-4 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary hover:bg-bg-quaternary transition-all"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}






