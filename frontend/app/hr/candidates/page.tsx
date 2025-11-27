'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../../components/Sidebar'
import MenuButton from '../../components/MenuButton'
import Logo from '../../components/Logo'
import LoadingSpinner from '../../components/LoadingSpinner'
import { useNotifications } from '../../hooks/useNotifications'

interface Candidate {
  id: number
  username: string
  email?: string
  full_name?: string
  github_username?: string
  linkedin_url?: string
  skills?: string[]
  programming_languages?: string[]
  role_type?: string
  experience_level?: string
  success_prediction?: any
  average_score?: number
  interviews_count: number
  created_at?: string
}

export default function HRCandidatesPage() {
  const router = useRouter()
  const { showError, showInfo, showWarning } = useNotifications()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  
  // Поиск и фильтры
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([])
  const [selectedRoleType, setSelectedRoleType] = useState<string>('')
  const [selectedLevel, setSelectedLevel] = useState<string>('')
  const [showFilters, setShowFilters] = useState(false)

  // Доступные опции
  const programmingLanguages = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust',
    'PHP', 'Ruby', 'Swift', 'Kotlin', 'Dart', 'Scala', 'R', 'SQL'
  ]

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
        await loadCandidates()
      } catch (error) {
        console.error('Error loading candidates:', error)
        setLoading(false)
      }
    }
    
    init()
  }, [router, searchQuery, selectedLanguages, selectedRoleType, selectedLevel])

  const loadCandidates = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim())
      }
      if (selectedLanguages.length > 0) {
        params.append('programming_languages', selectedLanguages.join(','))
      }
      if (selectedRoleType) {
        params.append('role_type', selectedRoleType)
      }
      if (selectedLevel) {
        params.append('experience_level', selectedLevel)
      }
      params.append('limit', '100')
      
      const url = `/api/hr/candidates/search?${params.toString()}`
      
      const data = await apiClient.get(url) as { candidates?: Candidate[], total?: number, limit?: number, offset?: number }
      
      if (data && data.candidates) {
        setCandidates(data.candidates)
      } else {
        showWarning('Кандидаты не найдены')
        setCandidates([])
      }
    } catch (error) {
      showError('Не удалось загрузить список кандидатов')
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }

  const toggleLanguage = (lang: string) => {
    setSelectedLanguages(prev =>
      prev.includes(lang)
        ? prev.filter(l => l !== lang)
        : [...prev, lang]
    )
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
    return experienceLevels.find(l => l.value === level)?.label || level || 'Не указан'
  }

  const getRoleTypeLabel = (roleType?: string) => {
    return roleTypes.find(r => r.value === roleType)?.label || roleType || 'Не указан'
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
              Поиск кандидатов
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
            {/* Search and Filters */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-6 mb-8">
              {/* Search Bar */}
              <div className="mb-6">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Поиск по нику, имени или email..."
                  className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:border-purple-apple transition-all"
                />
              </div>

              {/* Filter Toggle */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="mb-4 px-4 py-2 bg-bg-tertiary border border-border-color rounded-lg text-text-primary hover:bg-bg-quaternary transition-all text-sm font-medium"
              >
                {showFilters ? 'Скрыть фильтры' : 'Показать фильтры'}
              </button>

              {/* Filters */}
              {showFilters && (
                <div className="space-y-6 pt-6 border-t border-border-color">
                  {/* Programming Languages */}
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-3 block">
                      Языки программирования
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {programmingLanguages.map((lang) => (
                        <button
                          key={lang}
                          onClick={() => toggleLanguage(lang)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                            selectedLanguages.includes(lang)
                              ? 'bg-purple-apple text-white'
                              : 'bg-bg-tertiary text-text-primary border border-border-color hover:bg-bg-quaternary'
                          }`}
                        >
                          {lang}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Role Type */}
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-3 block">
                      Тип роли
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {roleTypes.map((role) => (
                        <button
                          key={role.value}
                          onClick={() => setSelectedRoleType(selectedRoleType === role.value ? '' : role.value)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                            selectedRoleType === role.value
                              ? 'bg-purple-apple text-white'
                              : 'bg-bg-tertiary text-text-primary border border-border-color hover:bg-bg-quaternary'
                          }`}
                        >
                          {role.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Experience Level */}
                  <div>
                    <label className="text-text-muted text-xs uppercase tracking-wider mb-3 block">
                      Уровень опыта
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {experienceLevels.map((level) => (
                        <button
                          key={level.value}
                          onClick={() => setSelectedLevel(selectedLevel === level.value ? '' : level.value)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                            selectedLevel === level.value
                              ? 'bg-purple-apple text-white'
                              : 'bg-bg-tertiary text-text-primary border border-border-color hover:bg-bg-quaternary'
                          }`}
                        >
                          {level.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Clear Filters */}
                  {(selectedLanguages.length > 0 || selectedRoleType || selectedLevel) && (
                    <button
                      onClick={() => {
                        setSelectedLanguages([])
                        setSelectedRoleType('')
                        setSelectedLevel('')
                      }}
                      className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/50 rounded-lg hover:bg-red-500/30 transition-all text-sm font-medium"
                    >
                      Сбросить фильтры
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Results */}
            {loading ? (
              <div className="text-center py-16">
                <div className="text-text-tertiary text-sm">Загрузка...</div>
              </div>
            ) : candidates.length === 0 ? (
              <div className="bg-bg-secondary rounded-lg border border-border-color p-12 text-center">
                <p className="text-text-tertiary text-sm">Кандидаты не найдены</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="text-text-tertiary text-sm mb-4">
                  Найдено кандидатов: {candidates.length}
                </div>
                {candidates.map((candidate) => (
                  <div
                    key={candidate.id}
                    className="bg-bg-secondary rounded-lg border border-border-color p-6 hover:border-purple-apple transition-all cursor-pointer"
                    onClick={() => router.push(`/hr/candidates/${candidate.id}`)}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold text-text-primary mb-2 tracking-tight">
                          {candidate.full_name || candidate.username}
                        </h3>
                        <div className="flex items-center gap-4 text-sm text-text-tertiary mb-3">
                          <span>@{candidate.username}</span>
                          {candidate.email && <span>{candidate.email}</span>}
                        </div>
                        
                        {/* Badges */}
                        <div className="flex flex-wrap gap-2 mb-4">
                          {candidate.role_type && (
                            <span className="px-2.5 py-1 bg-bg-tertiary border border-border-color rounded text-xs text-text-primary">
                              {getRoleTypeLabel(candidate.role_type)}
                            </span>
                          )}
                          {candidate.experience_level && (
                            <span className={`px-2.5 py-1 rounded text-xs border ${getLevelBadgeColor(candidate.experience_level)}`}>
                              {getLevelLabel(candidate.experience_level)}
                            </span>
                          )}
                          {candidate.average_score !== undefined && candidate.average_score !== null && (
                            <span className="px-2.5 py-1 bg-green-500/20 text-green-400 border border-green-500/50 rounded text-xs">
                              Оценка: {candidate.average_score != null ? candidate.average_score.toFixed(1) : 'N/A'}%
                            </span>
                          )}
                        </div>

                        {/* Skills */}
                        {candidate.programming_languages && candidate.programming_languages.length > 0 && (
                          <div className="mb-3">
                            <div className="text-text-muted text-xs uppercase tracking-wider mb-2">
                              Языки программирования
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {candidate.programming_languages.map((lang, index) => (
                                <span
                                  key={index}
                                  className="px-2 py-1 bg-bg-tertiary border border-border-color rounded text-xs text-text-primary"
                                >
                                  {lang}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Stats */}
                        <div className="flex items-center gap-6 text-sm text-text-tertiary">
                          {candidate.interviews_count > 0 && (
                            <span>Интервью: {candidate.interviews_count}</span>
                          )}
                          {candidate.github_username && (
                            <a
                              href={`https://github.com/${candidate.github_username}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-purple-apple hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              GitHub
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

