'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import Sidebar from '../../components/Sidebar'
import MenuButton from '../../components/MenuButton'
import Logo from '../../components/Logo'

import { useTheme } from '../../hooks/useTheme'

interface TrainingConfig {
  position: string
  difficulty: string
  level: string  // junior, middle, senior
  topics: string[]
  programmingLanguages: string[]
  questionsPerStage: {
    introduction: number
    softSkills: number
    technical: number
    liveCoding: number
  }
  timer: {
    enabled: boolean
    technical_minutes: number  // Таймер для технических вопросов
    liveCoding_minutes: number  // Таймер для лайвкодинга
  }
}

export default function TrainingConfigPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const { theme: currentTheme } = useTheme()
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [config, setConfig] = useState<TrainingConfig>({
    position: 'frontend',
    difficulty: 'medium',
    level: 'middle',
    topics: [],
    programmingLanguages: ['python'],
    questionsPerStage: {
      introduction: 2,
      softSkills: 1,
      technical: 2,
      liveCoding: 1,
    },
    timer: {
      enabled: true,
      technical_minutes: 10,  // 10 минут на каждый технический вопрос
      liveCoding_minutes: 30,  // 30 минут на каждую задачу лайвкодинга
    },
  })

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    if (auth.isHR()) {
      router.push('/dashboard')
      return
    }
    setIsLoading(false)
  }, [router])

  const translations = {
    ru: {
      title: 'Настройка тренировочного интервью',
      position: 'Позиция',
      difficulty: 'Сложность',
      level: 'Уровень',
      topics: 'Темы',
      programmingLanguages: 'Языки программирования',
      introduction: 'Вопросы знакомства',
      softSkills: 'Вопросы софт-скиллов',
      technical: 'Технические вопросы',
      liveCoding: 'Задачи лайвкодинга',
      questionsCount: 'Количество вопросов',
      timer: 'Таймер',
      timerEnabled: 'Включить таймер',
      technicalTime: 'Время на технические вопросы (мин)',
      liveCodingTime: 'Время на лайвкодинг (мин)',
      start: 'Начать тренировку',
      cancel: 'Отмена',
    },
    en: {
      title: 'Training Interview Configuration',
      position: 'Position',
      difficulty: 'Difficulty',
      level: 'Level',
      topics: 'Topics',
      programmingLanguages: 'Programming Languages',
      introduction: 'Introduction Questions',
      softSkills: 'Soft Skills Questions',
      technical: 'Technical Questions',
      liveCoding: 'Live Coding Tasks',
      questionsCount: 'Number of Questions',
      timer: 'Timer',
      timerEnabled: 'Enable timer',
      technicalTime: 'Time for technical questions (min)',
      liveCodingTime: 'Time for live coding (min)',
      start: 'Start Training',
      cancel: 'Cancel',
    },
  }

  const t = translations[language]

  const positions = [
    { value: 'frontend', label: 'Frontend Developer' },
    { value: 'backend', label: 'Backend Developer' },
    { value: 'devops', label: 'DevOps Engineer' },
    { value: 'fullstack', label: 'Full Stack Developer' },
  ]

  const difficulties = [
    { value: 'easy', label: 'Easy' },
    { value: 'medium', label: 'Medium' },
    { value: 'hard', label: 'Hard' },
  ]

  const levels = [
    { value: 'junior', label: 'Junior' },
    { value: 'middle', label: 'Middle' },
    { value: 'senior', label: 'Senior' },
  ]

  const programmingLanguages = [
    { value: 'python', label: 'Python' },
    { value: 'javascript', label: 'JavaScript' },
    { value: 'typescript', label: 'TypeScript' },
    { value: 'java', label: 'Java' },
    { value: 'cpp', label: 'C++' },
    { value: 'csharp', label: 'C#' },
    { value: 'go', label: 'Go' },
    { value: 'rust', label: 'Rust' },
    { value: 'php', label: 'PHP' },
    { value: 'ruby', label: 'Ruby' },
  ]

  const availableTopics = [
    'Алгоритмы и структуры данных',
    'ООП и паттерны проектирования',
    'Базы данных',
    'API и REST',
    'Тестирование',
    'Git и CI/CD',
    'Безопасность',
    'Производительность',
    'Архитектура',
    'Асинхронное программирование',
  ]

  const handleTopicToggle = (topic: string) => {
    setConfig((prev) => ({
      ...prev,
      topics: prev.topics.includes(topic)
        ? prev.topics.filter((t) => t !== topic)
        : [...prev.topics, topic],
    }))
  }

  const handleLanguageToggle = (language: string) => {
    setConfig((prev) => ({
      ...prev,
      programmingLanguages: prev.programmingLanguages.includes(language)
        ? prev.programmingLanguages.filter((l) => l !== language)
        : [...prev.programmingLanguages, language],
    }))
  }

  const handleStart = () => {
    // Сохраняем конфигурацию в sessionStorage и переходим к тренировке
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('training_config', JSON.stringify(config))
      
      // Очищаем старые данные таймера и флаг завершения перед началом нового интервью
      localStorage.removeItem('training_start_time')
      localStorage.removeItem('training_time_remaining')
      localStorage.removeItem('training_finished')
    }
    router.push('/training')
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
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="sticky top-0 bg-bg-secondary border-b border-border-color px-12 py-6 flex items-center justify-between relative z-[55] backdrop-blur-xl flex-shrink-0">
          <div className="flex items-center gap-4">
            <MenuButton />
            <button
              onClick={() => router.push('/dashboard')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-bg-tertiary hover:bg-bg-quaternary text-text-primary transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              <span>Назад</span>
            </button>
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">{t.title}</h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-12 overflow-y-auto min-h-0">
          <div className="max-w-7xl mx-auto space-y-8">
            {/* Position Selection */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.position}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {positions.map((pos) => (
                  <button
                    key={pos.value}
                    onClick={() => setConfig((prev) => ({ ...prev, position: pos.value }))}
                    className={`px-4 py-3 rounded-lg border-2 transition-all duration-200 ${
                      config.position === pos.value
                        ? 'bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] border-[#AF52DE] text-white font-medium shadow-md'
                        : 'bg-bg-tertiary border-border-color text-text-primary hover:border-[#AF52DE]'
                    }`}
                  >
                    {pos.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty and Level */}
            <div className="grid grid-cols-2 gap-6">
              {/* Difficulty Selection */}
              <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
                <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.difficulty}</h2>
                <div className="grid grid-cols-3 gap-3">
                  {difficulties.map((diff) => (
                    <button
                      key={diff.value}
                      onClick={() => setConfig((prev) => ({ ...prev, difficulty: diff.value }))}
                      className={`px-4 py-3 rounded-lg border-2 transition-all duration-200 ${
                        config.difficulty === diff.value
                          ? 'bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] border-[#AF52DE] text-white font-medium shadow-md'
                          : 'bg-bg-tertiary border-border-color text-text-primary hover:border-[#AF52DE]'
                      }`}
                    >
                      {diff.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Level Selection */}
              <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
                <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.level}</h2>
                <div className="grid grid-cols-3 gap-3">
                  {levels.map((lvl) => (
                    <button
                      key={lvl.value}
                      onClick={() => setConfig((prev) => ({ ...prev, level: lvl.value }))}
                      className={`px-4 py-3 rounded-lg border-2 transition-all duration-200 ${
                        config.level === lvl.value
                          ? 'bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] border-[#AF52DE] text-white font-medium shadow-md'
                          : 'bg-bg-tertiary border-border-color text-text-primary hover:border-[#AF52DE]'
                      }`}
                    >
                      {lvl.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Programming Languages Selection */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.programmingLanguages}</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {programmingLanguages.map((lang) => (
                  <button
                    key={lang.value}
                    onClick={() => handleLanguageToggle(lang.value)}
                    className={`px-4 py-2 rounded-lg border-2 transition-all duration-200 text-sm ${
                      config.programmingLanguages.includes(lang.value)
                        ? 'bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] border-[#AF52DE] text-white font-medium shadow-md'
                        : 'bg-bg-tertiary border-border-color text-text-primary hover:border-[#AF52DE]'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Questions Per Stage */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.questionsCount}</h2>
              <div className="space-y-6">
                {/* Introduction Questions */}
                <div>
                  <label className="text-sm text-text-tertiary mb-3 block">{t.introduction}</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="5"
                      value={config.questionsPerStage.introduction}
                      onChange={(e) =>
                        setConfig((prev) => ({
                          ...prev,
                          questionsPerStage: { ...prev.questionsPerStage, introduction: parseInt(e.target.value) },
                        }))
                      }
                      className="flex-1"
                    />
                    <span className="text-2xl font-semibold text-text-primary w-12 text-center tracking-tight">
                      {config.questionsPerStage.introduction}
                    </span>
                  </div>
                </div>

                {/* Soft Skills Questions */}
                <div>
                  <label className="text-sm text-text-tertiary mb-3 block">{t.softSkills}</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="5"
                      value={config.questionsPerStage.softSkills}
                      onChange={(e) =>
                        setConfig((prev) => ({
                          ...prev,
                          questionsPerStage: { ...prev.questionsPerStage, softSkills: parseInt(e.target.value) },
                        }))
                      }
                      className="flex-1"
                    />
                    <span className="text-2xl font-semibold text-text-primary w-12 text-center tracking-tight">
                      {config.questionsPerStage.softSkills}
                    </span>
                  </div>
                </div>

                {/* Technical Questions */}
                <div>
                  <label className="text-sm text-text-tertiary mb-3 block">{t.technical}</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="10"
                      value={config.questionsPerStage.technical}
                      onChange={(e) =>
                        setConfig((prev) => ({
                          ...prev,
                          questionsPerStage: { ...prev.questionsPerStage, technical: parseInt(e.target.value) },
                        }))
                      }
                      className="flex-1"
                    />
                    <span className="text-2xl font-semibold text-text-primary w-12 text-center tracking-tight">
                      {config.questionsPerStage.technical}
                    </span>
                  </div>
                </div>

                {/* Live Coding Tasks */}
                <div>
                  <label className="text-sm text-text-tertiary mb-3 block">{t.liveCoding}</label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="5"
                      value={config.questionsPerStage.liveCoding}
                      onChange={(e) =>
                        setConfig((prev) => ({
                          ...prev,
                          questionsPerStage: { ...prev.questionsPerStage, liveCoding: parseInt(e.target.value) },
                        }))
                      }
                      className="flex-1"
                    />
                    <span className="text-2xl font-semibold text-text-primary w-12 text-center tracking-tight">
                      {config.questionsPerStage.liveCoding}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Topics Selection */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.topics}</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {availableTopics.map((topic) => (
                  <button
                    key={topic}
                    onClick={() => handleTopicToggle(topic)}
                    className={`px-4 py-2 rounded-lg border-2 transition-all duration-200 text-sm ${
                      config.topics.includes(topic)
                        ? 'bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] border-[#AF52DE] text-white font-medium shadow-md'
                        : 'bg-bg-tertiary border-border-color text-text-primary hover:border-[#AF52DE]'
                    }`}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>

            {/* Timer Settings */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <div className="flex items-center gap-3 mb-6">
                <input
                  type="checkbox"
                  checked={config.timer.enabled}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      timer: { ...prev.timer, enabled: e.target.checked },
                    }))
                  }
                  className="w-5 h-5 rounded border-border-color bg-bg-tertiary text-[#AF52DE] focus:ring-[#AF52DE]"
                />
                <h2 className="text-xl font-semibold text-text-primary tracking-tight">{t.timerEnabled}</h2>
              </div>
              
              {config.timer.enabled && (
                <div className="ml-8 space-y-6">
                  {/* Technical Questions Timer */}
                  <div>
                    <label className="text-sm text-text-tertiary mb-3 block">{t.technicalTime}</label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="5"
                        max="30"
                        step="5"
                        value={config.timer.technical_minutes}
                        onChange={(e) =>
                          setConfig((prev) => ({
                            ...prev,
                            timer: { ...prev.timer, technical_minutes: parseInt(e.target.value) },
                          }))
                        }
                        className="flex-1 slider"
                        style={{
                          background: `linear-gradient(to right, #AF52DE 0%, #AF52DE ${((config.timer.technical_minutes - 5) / 25) * 100}%, var(--bg-quaternary) ${((config.timer.technical_minutes - 5) / 25) * 100}%, var(--bg-quaternary) 100%)`
                        }}
                      />
                      <span className="text-2xl font-semibold text-text-primary w-20 text-center tracking-tight">
                        {config.timer.technical_minutes}
                      </span>
                    </div>
                  </div>

                  {/* Live Coding Timer */}
                  <div>
                    <label className="text-sm text-text-tertiary mb-3 block">{t.liveCodingTime}</label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="15"
                        max="90"
                        step="15"
                        value={config.timer.liveCoding_minutes}
                        onChange={(e) =>
                          setConfig((prev) => ({
                            ...prev,
                            timer: { ...prev.timer, liveCoding_minutes: parseInt(e.target.value) },
                          }))
                        }
                        className="flex-1 slider"
                        style={{
                          background: `linear-gradient(to right, #AF52DE 0%, #AF52DE ${((config.timer.liveCoding_minutes - 15) / 75) * 100}%, var(--bg-quaternary) ${((config.timer.liveCoding_minutes - 15) / 75) * 100}%, var(--bg-quaternary) 100%)`
                        }}
                      />
                      <span className="text-2xl font-semibold text-text-primary w-20 text-center tracking-tight">
                        {config.timer.liveCoding_minutes}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="px-6 py-3 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg transition-all duration-200 font-medium"
              >
                {t.cancel}
              </button>
              <button
                onClick={handleStart}
                disabled={config.programmingLanguages.length === 0 || config.topics.length === 0}
                className="px-6 py-3 bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] text-white hover:from-[#8E44AD] hover:to-[#AF52DE] disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all duration-200 font-semibold shadow-md"
              >
                {t.start}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}



