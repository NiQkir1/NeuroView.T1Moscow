'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../../../components/Sidebar'
import MenuButton from '../../../components/MenuButton'
import Logo from '../../../components/Logo'
import SoftSkillsCard from '../../../components/SoftSkillsCard'
import SuccessPredictionCard from '../../../components/SuccessPredictionCard'
import LoadingSpinner from '../../../components/LoadingSpinner'
import ReportViewer from '@/app/components/ReportViewer'
import { useNotifications } from '../../../hooks/useNotifications'

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
  role_type?: string
  experience_level?: string
  programming_languages?: string[]
  // v3.0.0: Данные из HH.ru
  work_experience?: Array<{
    company?: string
    position?: string
    start_date?: string
    end_date?: string | null
    description?: string
    skills?: string[]
  }>
  education?: Array<{
    institution?: string
    faculty?: string
    year?: string
  }>
  hh_metrics?: {
    profile_views?: number
    last_activity?: string
  }
  hh_resume_id?: string
  hh_profile_synced_at?: string
}

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

export default function HRCandidateProfilePage() {
  const router = useRouter()
  const { showError } = useNotifications()
  const params = useParams()
  const userId = params?.userId ? parseInt(params.userId as string) : null

  const [profile, setProfile] = useState<CandidateProfile | null>(null)
  const [interviewReports, setInterviewReports] = useState<InterviewReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null)
  const [selectedReportTitle, setSelectedReportTitle] = useState<string>('')

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    if (!auth.isHR()) {
      router.push('/dashboard')
      return
    }

    if (userId) {
      loadCandidateProfile(userId)
      loadInterviewReports(userId)
    }
  }, [router, userId])

  const loadCandidateProfile = async (id: number) => {
    try {
      const data = await apiClient.get(`/api/candidates/${id}/profile`)
      setProfile(data as CandidateProfile)
    } catch (err) {
      setError('Не удалось загрузить профиль кандидата')
      showError('Не удалось загрузить профиль кандидата')
    } finally {
      setLoading(false)
    }
  }

  const loadInterviewReports = async (id: number) => {
    try {
      const data = await apiClient.get(`/api/admin/users/${id}/profile`) as any
      setInterviewReports(data.interview_reports || [])
    } catch (error) {
      showError('Не удалось загрузить отчеты интервью')
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

  const getLevelBadgeColor = (level?: string) => {
    switch (level) {
      case 'junior':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50'
      case 'middle':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50'
      case 'senior':
        return 'bg-green-500/20 text-green-400 border-green-500/50'
      case 'lead':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/50'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50'
    }
  }

  const getLevelLabel = (level?: string) => {
    const levels: { [key: string]: string } = {
      junior: 'Junior',
      middle: 'Middle',
      senior: 'Senior',
      lead: 'Lead',
    }
    return levels[level || ''] || level || 'Не указан'
  }

  const getRoleTypeLabel = (roleType?: string) => {
    const roles: { [key: string]: string } = {
      fullstack: 'Fullstack',
      backend: 'Backend',
      frontend: 'Frontend',
      devops: 'DevOps',
      mobile: 'Mobile',
      data_science: 'Data Science',
      qa: 'QA',
      other: 'Другое',
    }
    return roles[roleType || ''] || roleType || 'Не указан'
  }

  const handleViewReport = (reportId: number, reportTitle: string) => {
    setSelectedReportId(reportId)
    setSelectedReportTitle(reportTitle)
  }

  const handleDownloadPDF = async (sessionId: number, reportTitle: string) => {
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
      let filename = `${reportTitle.replace(/[^a-z0-9]/gi, '_')}_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      
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
      showError('Не удалось скачать отчет')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-text-primary text-xl tracking-tight">Загрузка...</div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-red-400 text-xl">Кандидат не найден</div>
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
            <button
              onClick={() => router.push('/hr/candidates')}
              className="text-text-tertiary hover:text-text-primary transition-colors text-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
              </svg>
              Назад к поиску
            </button>
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
              Профиль кандидата
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {error && (
              <div className="mb-8 bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Candidate Info */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8 mb-8">
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-xl font-semibold text-text-primary tracking-tight">
                  Информация о кандидате
                </h2>
                <button
                  onClick={() => {
                    // Сохраняем ID кандидата в sessionStorage для предзаполнения формы
                    if (typeof window !== 'undefined' && userId) {
                      sessionStorage.setItem('hr_selected_candidate_id', userId.toString())
                    }
                    router.push('/hr/create-interview')
                  }}
                  className="px-6 py-2.5 bg-purple-apple text-white rounded-lg hover:bg-purple-apple/80 transition-all font-medium flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                  </svg>
                  Пригласить на интервью
                </button>
              </div>
              
              <div className="flex items-center gap-6 mb-8">
                <div className="w-24 h-24 rounded-full flex items-center justify-center overflow-hidden">
                  <Image 
                    src="/pic/profile.png" 
                    alt="Profile" 
                    width={96} 
                    height={96} 
                    className="w-full h-full object-cover"
                  />
                </div>
                <div>
                  <h3 className="text-2xl font-semibold text-text-primary mb-2 tracking-tight">
                    {profile.full_name || profile.username}
                  </h3>
                  <p className="text-text-tertiary">@{profile.username}</p>
                  {profile.email && <p className="text-text-tertiary">{profile.email}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Имя пользователя</label>
                  <div className="text-text-primary text-base font-medium">{profile.username}</div>
                </div>
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Email</label>
                  <div className="text-text-primary text-base">{profile.email || '-'}</div>
                </div>
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Полное имя</label>
                  <div className="text-text-primary text-base">{profile.full_name || '-'}</div>
                </div>
                {profile.github_username && (
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">GitHub</label>
                    <div className="text-text-primary text-base">
                      <a
                        href={`https://github.com/${profile.github_username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-apple hover:underline"
                      >
                        {profile.github_username}
                      </a>
                    </div>
                  </div>
                )}
                {profile.linkedin_url && (
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">LinkedIn</label>
                    <div className="text-text-primary text-base">
                      <a
                        href={profile.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-apple hover:underline"
                      >
                        Профиль LinkedIn
                      </a>
                    </div>
                  </div>
                )}
                {profile.role_type && (
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Тип роли</label>
                    <div className="text-text-primary text-base">{getRoleTypeLabel(profile.role_type)}</div>
                  </div>
                )}
                {profile.experience_level && (
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Уровень опыта</label>
                    <span className={`px-2.5 py-1 rounded text-xs border ${getLevelBadgeColor(profile.experience_level)}`}>
                      {getLevelLabel(profile.experience_level)}
                    </span>
                  </div>
                )}
              </div>

              {/* Skills */}
              {profile.skills && profile.skills.length > 0 && (
                <div className="mt-8 pt-8 border-t border-border-color">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">Навыки</label>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills.map((skill, index) => (
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

              {/* Programming Languages */}
              {profile.programming_languages && profile.programming_languages.length > 0 && (
                <div className="mt-8 pt-8 border-t border-border-color">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">
                    Языки программирования
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {profile.programming_languages.map((lang, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-bg-tertiary border border-border-color rounded-lg text-text-primary text-sm"
                      >
                        {lang}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Skill Matrix */}
              {profile.skill_matrix && Object.keys(profile.skill_matrix).length > 0 && (
                <div className="mt-8 pt-8 border-t border-border-color">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">Матрица навыков</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(profile.skill_matrix).map(([skill, data]) => (
                      <div key={skill} className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-text-primary font-medium text-sm">{skill}</span>
                          <span className="text-text-tertiary text-xs">{data.level}</span>
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
                        <div className="text-xs text-text-tertiary mt-1">
                          {data.questions_count} вопросов
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* v3.0.0: Опыт работы из HH.ru */}
              {profile.work_experience && profile.work_experience.length > 0 && (
                <div className="mt-8 pt-8 border-t border-border-color">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">
                    Опыт работы {profile.hh_resume_id && <span className="text-green-400 text-xs">(из HH.ru)</span>}
                  </label>
                  <div className="space-y-4">
                    {profile.work_experience.map((exp, index) => (
                      <div key={index} className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <h4 className="text-text-primary font-semibold mb-1">
                              {exp.position || 'Должность не указана'}
                            </h4>
                            <p className="text-text-primary text-sm mb-1">
                              {exp.company || 'Компания не указана'}
                            </p>
                            <p className="text-text-tertiary text-xs">
                              {exp.start_date && (
                                <>
                                  {new Date(exp.start_date).toLocaleDateString('ru-RU', { year: 'numeric', month: 'long' })}
                                  {' - '}
                                  {exp.end_date 
                                    ? new Date(exp.end_date).toLocaleDateString('ru-RU', { year: 'numeric', month: 'long' })
                                    : 'По настоящее время'}
                                </>
                              )}
                            </p>
                          </div>
                        </div>
                        {exp.description && (
                          <p className="text-text-tertiary text-sm mt-2">{exp.description}</p>
                        )}
                        {exp.skills && exp.skills.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-3">
                            {exp.skills.map((skill, skillIndex) => (
                              <span
                                key={skillIndex}
                                className="px-2 py-1 bg-bg-quaternary border border-border-color rounded text-xs text-text-tertiary"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* v3.0.0: Образование из HH.ru */}
              {profile.education && profile.education.length > 0 && (
                <div className="mt-8 pt-8 border-t border-border-color">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">
                    Образование {profile.hh_resume_id && <span className="text-green-400 text-xs">(из HH.ru)</span>}
                  </label>
                  <div className="space-y-3">
                    {profile.education.map((edu, index) => (
                      <div key={index} className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
                        <h4 className="text-text-primary font-semibold mb-1">
                          {edu.institution || 'Учебное заведение не указано'}
                        </h4>
                        {edu.faculty && (
                          <p className="text-text-primary text-sm mb-1">{edu.faculty}</p>
                        )}
                        {edu.year && (
                          <p className="text-text-tertiary text-xs">Год: {edu.year}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* v3.0.0: Метрики HH.ru */}
              {profile.hh_metrics && (
                <div className="mt-8 pt-8 border-t border-border-color">
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">
                    Метрики HeadHunter.ru
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {profile.hh_metrics.profile_views !== undefined && (
                      <div className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
                        <div className="text-text-tertiary text-xs mb-1">Просмотры профиля</div>
                        <div className="text-text-primary text-xl font-semibold">
                          {profile.hh_metrics.profile_views}
                        </div>
                      </div>
                    )}
                    {profile.hh_profile_synced_at && (
                      <div className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
                        <div className="text-text-tertiary text-xs mb-1">Последняя синхронизация</div>
                        <div className="text-text-primary text-sm">
                          {new Date(profile.hh_profile_synced_at).toLocaleDateString('ru-RU', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Soft Skills Analysis */}
            {profile.soft_skills_score && (
              <div className="mb-8">
                <SoftSkillsCard data={profile.soft_skills_score} loading={false} />
              </div>
            )}

            {/* Success Prediction */}
            {profile.success_prediction && (
              <div className="mb-8">
                <SuccessPredictionCard data={profile.success_prediction} loading={false} />
              </div>
            )}

            {/* Interview Reports */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">
                Отчеты о собеседованиях ({interviewReports.length})
              </h2>

              {interviewReports.length === 0 ? (
                <div className="text-center py-16 text-text-tertiary text-sm">
                  У кандидата пока нет пройденных собеседований
                </div>
              ) : (
                <div className="space-y-3">
                  {interviewReports.map((report) => (
                    <div
                      key={report.id}
                      className="bg-bg-tertiary rounded-lg p-6 border border-border-color hover:border-purple-apple transition-all"
                    >
                      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-text-primary mb-2 tracking-tight">
                            {report.candidate_name || profile?.full_name || profile?.username}
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
                              <span className="text-text-tertiary text-xs uppercase tracking-wider">Статус:</span>
                              <div className="mt-1">
                                <span
                                  className={`inline-block px-2.5 py-1 rounded text-xs font-medium tracking-tight border ${getStatusBadgeColor(report.status)}`}
                                >
                                  {getStatusLabel(report.status)}
                                </span>
                              </div>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs uppercase tracking-wider">Оценка:</span>
                              <div className="mt-1 text-text-primary font-medium text-sm">
                                {report.total_score !== null
                                  ? `${report.total_score.toFixed(1)}%`
                                  : 'Нет оценки'}
                              </div>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs uppercase tracking-wider">Вопросов:</span>
                              <div className="mt-1 text-text-primary font-medium text-sm">
                                {report.answered_count} / {report.questions_count}
                              </div>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs uppercase tracking-wider">Дата:</span>
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
                            className="px-4 py-2 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg font-medium transition-all duration-200 flex items-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                            </svg>
                            Скачать
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
        </main>
      </div>
    </div>
  )
}

