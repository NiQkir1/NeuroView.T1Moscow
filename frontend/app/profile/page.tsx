'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../components/Sidebar'
import MenuButton from '../components/MenuButton'
import Logo from '../components/Logo'
import SoftSkillsCard from '../components/SoftSkillsCard'
import SuccessPredictionCard from '../components/SuccessPredictionCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { useNotifications } from '../hooks/useNotifications'
import { useTheme } from '../hooks/useTheme'

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

export default function ProfilePage() {
  const router = useRouter()
  const { showError, showSuccess, showWarning } = useNotifications()
  const { theme: currentTheme } = useTheme()
  const [user, setUser] = useState<{ id: number; username: string; email?: string; full_name?: string } | null>(null)
  const [profile, setProfile] = useState<CandidateProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingProfile, setIsLoadingProfile] = useState(false)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [githubUsername, setGithubUsername] = useState('')
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [roleType, setRoleType] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('')
  const [programmingLanguages, setProgrammingLanguages] = useState<string[]>([])
  const [isUpdating, setIsUpdating] = useState(false)
  const [hhConnected, setHhConnected] = useState(false)
  const [hhSyncing, setHhSyncing] = useState(false)

  const roleTypes = [
    { value: 'fullstack', label: 'Fullstack' },
    { value: 'backend', label: 'Backend' },
    { value: 'frontend', label: 'Frontend' },
    { value: 'devops', label: 'DevOps' },
    { value: 'mobile', label: 'Mobile' },
    { value: 'data_science', label: 'Data Science' },
    { value: 'qa', label: 'QA' },
    { value: 'other', label: 'Другое' },
  ]

  const experienceLevels = [
    { value: 'junior', label: 'Junior' },
    { value: 'middle', label: 'Middle' },
    { value: 'senior', label: 'Senior' },
    { value: 'lead', label: 'Lead' },
  ]

  const availableLanguages = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust',
    'PHP', 'Ruby', 'Swift', 'Kotlin', 'Dart', 'Scala', 'R', 'SQL'
  ]

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    
    // Загружаем актуальные данные пользователя с сервера
    const loadUser = async () => {
      try {
        const refreshedUser = await auth.refreshUser()
        if (refreshedUser && refreshedUser.id) {
          setUser(refreshedUser)
          // Загружаем расширенный профиль
          await loadCandidateProfile(refreshedUser.id)
        } else {
          // Если не удалось загрузить с сервера, используем данные из localStorage
          const localUser = auth.getUser()
          setUser(localUser)
          if (localUser && localUser.id) {
            await loadCandidateProfile(localUser.id)
          }
        }
      } catch (error) {
        console.error('Error loading user:', error)
        // В случае ошибки используем данные из localStorage
        const localUser = auth.getUser()
        setUser(localUser)
        if (localUser && localUser.id) {
          await loadCandidateProfile(localUser.id)
        }
      } finally {
        setIsLoading(false)
      }
    }
    
    loadUser()
  }, [router])

  const loadCandidateProfile = async (userId: number) => {
    setIsLoadingProfile(true)
    try {
      const data = await apiClient.get(`/api/candidates/${userId}/profile`) as any
      setProfile(data)
      setGithubUsername(data.github_username || '')
      setLinkedinUrl(data.linkedin_url || '')
      setRoleType(data.role_type || '')
      setExperienceLevel(data.experience_level || '')
      setProgrammingLanguages(data.programming_languages || [])
      // v3.0.0: Проверяем подключение HH.ru
      setHhConnected(!!data.hh_resume_id)
    } catch (error) {
      showError('Не удалось загрузить профиль')
    } finally {
      setIsLoadingProfile(false)
    }
  }

  const updateProfile = async () => {
    if (!user) return
    
    setIsUpdating(true)
    try {
      // Обновляем профиль
      await apiClient.post(`/api/candidates/${user.id}/profile/update`, {
        github_username: githubUsername || null,
        linkedin_url: linkedinUrl || null,
      })

      // Обновляем метаданные
      await apiClient.put(`/api/candidates/${user.id}/profile/metadata`, {
        role_type: roleType || null,
        experience_level: experienceLevel || null,
        programming_languages: programmingLanguages,
      })

      await loadCandidateProfile(user.id)
      showSuccess('Профиль успешно обновлен')
    } catch (error) {
      showError('Ошибка обновления профиля')
    } finally {
      setIsUpdating(false)
    }
  }

  const toggleLanguage = (lang: string) => {
    setProgrammingLanguages(prev =>
      prev.includes(lang)
        ? prev.filter(l => l !== lang)
        : [...prev, lang]
    )
  }

  // v3.0.0: HH.ru интеграция
  const handleHHConnect = async () => {
    try {
      const data = await apiClient.get('/auth/hh/login') as any
      window.location.href = data.auth_url
    } catch (error) {
      showError('Ошибка подключения к HH.ru')
    }
  }

  const handleHHSync = async () => {
    setHhSyncing(true)
    try {
      await apiClient.post('/api/hh/sync-profile')
      showSuccess('Профиль синхронизирован с HH.ru')
      if (user) {
        await loadCandidateProfile(user.id)
      }
    } catch (error) {
      showError('Ошибка синхронизации с HH.ru')
    } finally {
      setHhSyncing(false)
    }
  }

  const translations = {
    ru: {
      title: 'Профиль',
    },
    en: {
      title: 'Profile',
    },
  }

  const t = translations[language]

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
            {/* Profile Card */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8 mb-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">Информация о профиле</h2>
              <div className="mb-8">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-apple to-[#8E44AD] flex items-center justify-center text-white text-2xl font-bold">
                    {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h2 className="text-2xl font-semibold text-text-primary mb-1 tracking-tight">
                      {user?.full_name || user?.username || 'User'}
                    </h2>
                    <p className="text-text-tertiary text-sm">{user?.email || 'Email не указан'}</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Mercor AI v2.0.0: Новые поля профиля */}
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">GitHub</label>
                  <input
                    type="text"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
                    placeholder="username"
                    className="w-full px-4 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary focus:outline-none focus:border-purple-apple"
                  />
                </div>
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">LinkedIn</label>
                  <input
                    type="text"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="https://linkedin.com/in/..."
                    className="w-full px-4 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary focus:outline-none focus:border-purple-apple"
                  />
                </div>
                {/* HR Search & Filter v2.0.0: Метаданные для поиска */}
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Тип роли</label>
                  <select
                    value={roleType}
                    onChange={(e) => setRoleType(e.target.value)}
                    className="w-full px-4 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary focus:outline-none focus:border-purple-apple"
                  >
                    <option value="">Не указан</option>
                    {roleTypes.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Уровень опыта</label>
                  <select
                    value={experienceLevel}
                    onChange={(e) => setExperienceLevel(e.target.value)}
                    className="w-full px-4 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary focus:outline-none focus:border-purple-apple"
                  >
                    <option value="">Не указан</option>
                    {experienceLevels.map((level) => (
                      <option key={level.value} value={level.value}>
                        {level.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Programming Languages */}
              <div className="mt-8 pt-8 border-t border-border-color">
                <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">
                  Языки программирования
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableLanguages.map((lang) => (
                    <button
                      key={lang}
                      onClick={() => toggleLanguage(lang)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                        programmingLanguages.includes(lang)
                          ? 'bg-purple-apple text-white'
                          : 'bg-bg-tertiary text-text-primary border border-border-color hover:bg-bg-quaternary'
                      }`}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
                {programmingLanguages.length > 0 && (
                  <div className="mt-4 text-sm text-text-tertiary">
                    Выбрано: {programmingLanguages.join(', ')}
                  </div>
                )}
              </div>

              {/* Skills */}
              {profile?.skills && profile.skills.length > 0 && (
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

              {/* v3.0.0: Опыт работы из HH.ru */}
              {profile?.work_experience && profile.work_experience.length > 0 && (
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
              {profile?.education && profile.education.length > 0 && (
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
              {profile?.hh_metrics && (
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

              {/* Skill Matrix */}
              {profile?.skill_matrix && Object.keys(profile.skill_matrix).length > 0 && (
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

              {/* v3.0.0: HH.ru интеграция */}
              <div className="mt-8 pt-8 border-t border-border-color">
                <label className="text-text-muted text-xs uppercase tracking-wider mb-4 block">
                  Интеграция с HeadHunter.ru
                </label>
                <div className="flex items-center gap-4">
                  {hhConnected ? (
                    <>
                      <span className="text-green-400 text-sm">✓ Подключено</span>
                      <button
                        onClick={handleHHSync}
                        disabled={hhSyncing}
                        className="px-4 py-2 bg-[#AF52DE] text-white rounded-lg hover:bg-[#8E44AD] transition-all disabled:opacity-50"
                      >
                        {hhSyncing ? 'Синхронизация...' : 'Синхронизировать'}
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="text-text-tertiary text-sm">Не подключено</span>
                      <button
                        onClick={handleHHConnect}
                        className="px-4 py-2 bg-[#AF52DE] text-white rounded-lg hover:bg-[#8E44AD] transition-all"
                      >
                        Подключить HH.ru
                      </button>
                    </>
                  )}
                </div>
                <p className="text-xs text-text-tertiary mt-2">
                  Подключите свой профиль HH.ru для автоматического импорта резюме
                </p>
              </div>

              <div className="mt-8 pt-8 border-t border-border-color">
                <button
                  onClick={updateProfile}
                  disabled={isUpdating}
                  className="px-6 py-2.5 bg-text-primary text-bg-primary rounded-lg font-medium hover:opacity-90 transition-all duration-200 disabled:opacity-50"
                >
                  {isUpdating ? 'Сохранение...' : 'Сохранить изменения'}
                </button>
              </div>
            </div>

            {/* Mercor AI v2.0.0: Soft Skills Analysis */}
            {profile?.soft_skills_score && (
              <div className="mb-8">
                <SoftSkillsCard data={profile.soft_skills_score} loading={isLoadingProfile} />
              </div>
            )}

            {/* Mercor AI v2.0.0: Success Prediction */}
            {profile?.success_prediction && (
              <div className="mb-8">
                <SuccessPredictionCard data={profile.success_prediction} loading={isLoadingProfile} />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

