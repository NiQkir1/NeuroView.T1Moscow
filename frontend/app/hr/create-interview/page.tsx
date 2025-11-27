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

import { useTheme } from '../../hooks/useTheme'

interface InterviewConfig {
  position: string
  difficulty: string
  level: string  // junior, middle, senior
  questionCount: number
  topics: string[]
  programmingLanguages: string[]
  accessCode: string
  hrPrompt: string
  questionsPerStage: {
    introduction: string[]  // Массив выбранных вопросов
    softSkills: string[]    // Массив выбранных вопросов
    technical: number
    liveCoding: number
  }
  customQuestions: {
    introduction: string[]  // Пользовательские вопросы
    softSkills: string[]    // Пользовательские вопросы
  }
  stages: {
    introduction: boolean
    softSkills: boolean
    technical: boolean
    liveCoding: boolean
  }
  duration_minutes: number
  timer: {
    enabled: boolean
    technical_minutes: number  // Таймер для технических вопросов
    liveCoding_minutes: number  // Таймер для лайвкодинга
  }
}

type ConfigSection = 'basic' | 'stages' | 'advanced'

export default function CreateInterviewPage() {
  const router = useRouter()
  const { showError, showSuccess } = useNotifications()
  const { theme: currentTheme } = useTheme()
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [activeSection, setActiveSection] = useState<ConfigSection>('basic')
  const [candidates, setCandidates] = useState<Array<{id: number, username: string, full_name?: string}>>([])
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null)
  const [invitationMessage, setInvitationMessage] = useState('')
  const [loadingCandidates, setLoadingCandidates] = useState(false)
  const [config, setConfig] = useState<InterviewConfig>({
    position: 'frontend',
    difficulty: 'medium',
    level: 'middle',
    questionCount: 5,
    topics: [],
    programmingLanguages: ['python'],
    accessCode: '',
    hrPrompt: '',
    questionsPerStage: {
      introduction: [],
      softSkills: [],
      technical: 2,
      liveCoding: 1,
    },
    customQuestions: {
      introduction: [],
      softSkills: [],
    },
    stages: {
      introduction: true,
      softSkills: true,
      technical: true,
      liveCoding: true,
    },
    duration_minutes: 60,
    timer: {
      enabled: true,
      technical_minutes: 10,  // 10 минут на каждый технический вопрос (макс 15)
      liveCoding_minutes: 30,  // 30 минут на каждую задачу лайвкодинга (макс 60)
    },
  })

  // Предустановленные вопросы для этапов
  const defaultIntroductionQuestions = [
    'Расскажите о себе',
    'Почему вы хотите работать в нашей компании?',
    'Каковы ваши сильные стороны?',
    'Каковы ваши слабые стороны?',
    'Где вы видите себя через 5 лет?',
    'Почему вы ушли с предыдущего места работы?',
    'Что вас мотивирует в работе?',
    'Расскажите о вашем образовании',
    'Какие у вас ожидания от этой позиции?',
    'Как вы справляетесь со стрессом?',
  ]

  const defaultSoftSkillsQuestions = [
    'Расскажите о ситуации, когда вам пришлось работать в команде',
    'Как вы решаете конфликты в команде?',
    'Опишите ситуацию, когда вам пришлось взять на себя лидерство',
    'Как вы справляетесь с критикой?',
    'Расскажите о вашем опыте работы с трудными клиентами',
    'Как вы расставляете приоритеты при большом объеме задач?',
    'Опишите ситуацию, когда вам пришлось быстро адаптироваться к изменениям',
    'Как вы даете обратную связь коллегам?',
    'Расскажите о вашем опыте менторства',
    'Как вы поддерживаете баланс между работой и личной жизнью?',
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
      setIsLoading(false)
      
      try {
        await loadCandidates()
      } catch (error) {
        console.error('Error loading candidates:', error)
      }
      
      // Проверяем, есть ли предвыбранный кандидат из профиля
      if (typeof window !== 'undefined') {
        const preselectedCandidateId = sessionStorage.getItem('hr_selected_candidate_id')
        if (preselectedCandidateId) {
          const candidateId = parseInt(preselectedCandidateId)
          setSelectedCandidateId(candidateId)
          // Очищаем после использования
          sessionStorage.removeItem('hr_selected_candidate_id')
        }
      }
    }
    
    init()
  }, [router])

  const loadCandidates = async () => {
    setLoadingCandidates(true)
    try {
      const data = await apiClient.get('/api/hr/candidates/search?limit=100') as { candidates?: Array<{id: number, username: string, full_name?: string}> }
      setCandidates(data.candidates || [])
    } catch (error) {
      showError('Не удалось загрузить список кандидатов')
    } finally {
      setLoadingCandidates(false)
    }
  }

  // Автоматическая генерация кода доступа при загрузке, если он пустой
  useEffect(() => {
    if (!config.accessCode || config.accessCode.trim() === '') {
      const code = Math.floor(100000 + Math.random() * 900000).toString()
      setConfig((prev) => ({ ...prev, accessCode: code }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Автоматический расчет длительности на основе количества вопросов
  useEffect(() => {
    const introductionCount = Array.isArray(config.questionsPerStage.introduction) 
      ? config.questionsPerStage.introduction.length 
      : 0
    const softSkillsCount = Array.isArray(config.questionsPerStage.softSkills) 
      ? config.questionsPerStage.softSkills.length 
      : 0
    const technicalCount = typeof config.questionsPerStage.technical === 'number' 
      ? config.questionsPerStage.technical 
      : 0
    const liveCodingCount = typeof config.questionsPerStage.liveCoding === 'number' 
      ? config.questionsPerStage.liveCoding 
      : 0
    const totalQuestions = introductionCount + softSkillsCount + technicalCount + liveCodingCount
    const estimatedDuration = Math.max(30, totalQuestions * 8) // Минимум 30 минут, ~8 минут на вопрос
    setConfig((prev) => ({ ...prev, duration_minutes: estimatedDuration, questionCount: totalQuestions }))
  }, [config.questionsPerStage])

  const translations = {
    ru: {
      title: 'Создание интервью',
      basic: 'Основные параметры',
      stages: 'Этапы интервью',
      advanced: 'Дополнительно',
      position: 'Позиция',
      difficulty: 'Сложность',
      level: 'Уровень',
      questionCount: 'Всего вопросов',
      duration: 'Примерная длительность',
      minutes: 'минут',
      estimatedDuration: 'Примерная длительность',
      topics: 'Темы',
      programmingLanguages: 'Языки программирования',
      accessCode: 'Код доступа',
      accessCodeDesc: 'Код для доступа кандидата к интервью (обязательно)',
      generateCode: 'Сгенерировать',
      timer: 'Таймер',
      timerEnabled: 'Включить таймер',
      timerDesc: 'Таймер применяется к каждой задаче/вопросу отдельно. Например, если 3 задачи и таймер 10 минут, то на каждую задачу дается 10 минут.',
      technicalTimer: 'Время на каждый технический вопрос (минут)',
      liveCodingTimer: 'Время на каждую задачу лайвкодинга (минут)',
      hrPrompt: 'Описание вакансии',
      hrPromptDesc: 'Опишите требования к кандидату. Это поможет AI адаптировать вопросы.',
      introduction: 'Знакомство',
      introductionDesc: 'Общие вопросы о опыте и мотивации',
      softSkills: 'Софт-скиллы',
      softSkillsDesc: 'Коммуникация, работа в команде',
      technical: 'Технические вопросы',
      technicalDesc: 'Теоретические вопросы по технологиям',
      liveCoding: 'Лайвкодинг',
      liveCodingDesc: 'Практические задачи по программированию',
      questionsPerStage: 'Вопросов на этап',
      create: 'Создать интервью',
      cancel: 'Отмена',
      created: 'Интервью успешно создано',
      preview: 'Предпросмотр',
      validation: {
        noStages: 'Выберите хотя бы один этап',
        noTopics: 'Выберите хотя бы одну тему',
        noLanguages: 'Выберите хотя бы один язык',
        noAccessCode: 'Код доступа обязателен для заполнения',
      },
    },
    en: {
      title: 'Create Interview',
      basic: 'Basic Settings',
      stages: 'Interview Stages',
      advanced: 'Advanced',
      position: 'Position',
      difficulty: 'Difficulty',
      level: 'Level',
      questionCount: 'Total Questions',
      duration: 'Estimated Duration',
      minutes: 'minutes',
      estimatedDuration: 'Estimated Duration',
      topics: 'Topics',
      programmingLanguages: 'Programming Languages',
      accessCode: 'Access Code',
      accessCodeDesc: 'Code for candidate access (required)',
      generateCode: 'Generate',
      timer: 'Timer',
      timerEnabled: 'Enable timer',
      timerDesc: 'Timer applies to each task/question separately. For example, if there are 3 tasks and timer is 10 minutes, each task gets 10 minutes.',
      technicalTimer: 'Time per technical question (minutes)',
      liveCodingTimer: 'Time per live coding task (minutes)',
      hrPrompt: 'Job Description',
      hrPromptDesc: 'Describe candidate requirements. This helps AI adapt questions.',
      introduction: 'Introduction',
      introductionDesc: 'General questions about experience and motivation',
      softSkills: 'Soft Skills',
      softSkillsDesc: 'Communication, teamwork',
      technical: 'Technical Questions',
      technicalDesc: 'Theoretical questions about technologies',
      liveCoding: 'Live Coding',
      liveCodingDesc: 'Practical programming tasks',
      questionsPerStage: 'Questions per Stage',
      create: 'Create Interview',
      cancel: 'Cancel',
      created: 'Interview created successfully',
      preview: 'Preview',
      validation: {
        noStages: 'Select at least one stage',
        noTopics: 'Select at least one topic',
        noLanguages: 'Select at least one language',
        noAccessCode: 'Access code is required',
      },
    },
  }

  const t = translations[language]

  const positions = [
    { value: 'frontend', label: 'Frontend' },
    { value: 'backend', label: 'Backend' },
    { value: 'devops', label: 'DevOps' },
    { value: 'fullstack', label: 'Full Stack' },
    { value: 'mobile', label: 'Mobile' },
    { value: 'data', label: 'Data Science' },
  ]

  const difficulties = [
    { value: 'easy', label: 'Легкий', color: 'green' },
    { value: 'medium', label: 'Средний', color: 'yellow' },
    { value: 'hard', label: 'Сложный', color: 'red' },
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
    { value: 'go', label: 'Go' },
    { value: 'rust', label: 'Rust' },
    { value: 'sql', label: 'SQL' },
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
    'Микросервисы',
    'Контейнеризация',
  ]

  const handleTopicToggle = (topic: string) => {
    setConfig((prev) => ({
      ...prev,
      topics: prev.topics.includes(topic)
        ? prev.topics.filter((t) => t !== topic)
        : [...prev.topics, topic],
    }))
  }

  const handleStageToggle = (stage: keyof InterviewConfig['stages']) => {
    setConfig((prev) => ({
      ...prev,
      stages: {
        ...prev.stages,
        [stage]: !prev.stages[stage],
      },
    }))
  }

  const generateAccessCode = () => {
    const code = Math.floor(100000 + Math.random() * 900000).toString()
    setConfig((prev) => ({ ...prev, accessCode: code }))
  }

  const validateConfig = () => {
    const errors: string[] = []
    if (!Object.values(config.stages).some((stage) => stage)) {
      errors.push(t.validation.noStages)
    }
    if (config.topics.length === 0) {
      errors.push(t.validation.noTopics)
    }
    if (config.programmingLanguages.length === 0) {
      errors.push(t.validation.noLanguages)
    }
    // Код доступа не обязателен, если отправляется приглашение кандидату
    if (!selectedCandidateId && (!config.accessCode || config.accessCode.trim() === '')) {
      errors.push(t.validation.noAccessCode)
    }
    return errors
  }

  const handleCreate = async () => {
    const errors = validateConfig()
    if (errors.length > 0) {
      alert(errors.join('\n'))
      return
    }

    try {
      // Преобразуем вопросы из строк в объекты с ID для backend
      const transformQuestions = (questions: string[], stage: string) => {
        return questions.map((text, index) => ({
          id: `hr_${stage}_${index}`,
          text: text,
          category: stage === 'introduction' ? 'custom' : 'soft_skills',
        }))
      }

      const interview_config = {
        level: config.level,
        position: config.position,
        programming_languages: config.programmingLanguages,
        required_skills: config.topics,
        question_count: config.questionCount,
        questions_per_stage: config.questionsPerStage,  // Оставляем для совместимости
        template_questions: {  // ✅ Правильная структура для backend
          introduction: config.questionsPerStage.introduction.length > 0
            ? transformQuestions(config.questionsPerStage.introduction, 'introduction')
            : [],
          softSkills: config.questionsPerStage.softSkills.length > 0
            ? transformQuestions(config.questionsPerStage.softSkills, 'softSkills')
            : [],
        },
      }

      const requestBody = {
        title: `Интервью ${positions.find((p) => p.value === config.position)?.label} - ${levels.find((l) => l.value === config.level)?.label}`,
        description: `Интервью для позиции ${positions.find((p) => p.value === config.position)?.label} уровня ${levels.find((l) => l.value === config.level)?.label}`,
        topics: config.topics.length > 0 ? config.topics : null,
        difficulty: config.difficulty,
        duration_minutes: config.duration_minutes,
        position: config.position,
        question_count: config.questionCount,
        stages: config.stages,
        access_code: config.accessCode.trim(),
        hr_prompt: config.hrPrompt.trim() || null,
        timer: config.timer,
        interview_config: interview_config,
        candidate_id: selectedCandidateId || null,
        invitation_message: invitationMessage.trim() || null,
      }

      const data = await apiClient.post('/api/interviews', requestBody)
      showSuccess('Интервью успешно создано')
      alert(t.created)
      router.push('/hr/interviews')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Неизвестная ошибка'
      showError(`Ошибка при создании интервью: ${errorMessage}`)
      alert(`Ошибка при создании интервью: ${errorMessage}`)
    }
  }

  const getTotalQuestions = () => {
    return Object.entries(config.questionsPerStage).reduce((sum, [key, value]) => {
      if (key === 'introduction' || key === 'softSkills') {
        return sum + (Array.isArray(value) ? value.length : 0)
      }
      return sum + (typeof value === 'number' ? value : 0)
    }, 0)
  }

  // Расчет примерной длительности интервью
  const calculateEstimatedDuration = () => {
    let totalMinutes = 0
    
    // Знакомство: ~5 минут на вопрос
    if (config.stages.introduction && Array.isArray(config.questionsPerStage.introduction)) {
      totalMinutes += config.questionsPerStage.introduction.length * 5
    }
    
    // Софт-скиллы: ~7 минут на вопрос
    if (config.stages.softSkills && Array.isArray(config.questionsPerStage.softSkills)) {
      totalMinutes += config.questionsPerStage.softSkills.length * 7
    }
    
    // Технические вопросы
    if (config.stages.technical && typeof config.questionsPerStage.technical === 'number') {
      const technicalCount = config.questionsPerStage.technical
      if (config.timer.enabled) {
        // Если таймер включен, используем время из таймера
        totalMinutes += technicalCount * config.timer.technical_minutes
      } else {
        // Иначе ~10 минут на вопрос
        totalMinutes += technicalCount * 10
      }
    }
    
    // Лайвкодинг
    if (config.stages.liveCoding && typeof config.questionsPerStage.liveCoding === 'number') {
      const liveCodingCount = config.questionsPerStage.liveCoding
      if (config.timer.enabled) {
        // Если таймер включен, используем время из таймера
        totalMinutes += liveCodingCount * config.timer.liveCoding_minutes
      } else {
        // Иначе ~30 минут на задачу
        totalMinutes += liveCodingCount * 30
      }
    }
    
    // Добавляем время на переходы между этапами (~3 минуты на этап)
    const activeStagesCount = Object.values(config.stages).filter(Boolean).length
    totalMinutes += (activeStagesCount - 1) * 3
    
    // Минимум 15 минут
    return Math.max(15, totalMinutes)
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
        <main className="flex-1 overflow-y-auto bg-bg-primary min-h-0">
          <div className="max-w-7xl mx-auto">
            {/* Navigation Tabs */}
            <div className="sticky top-0 z-20 bg-bg-primary mb-8 -mx-8 px-8 pt-8 pb-4 flex gap-2 border-b border-border-color shadow-lg">
              {(['basic', 'stages', 'advanced'] as ConfigSection[]).map((section) => (
                <button
                  key={section}
                  onClick={() => setActiveSection(section)}
                  className={`px-6 py-3 font-medium transition-all ${
                    activeSection === section
                      ? 'text-text-primary border-b-2 border-[#AF52DE]'
                      : 'text-text-tertiary hover:text-text-primary'
                  }`}
                >
                  {t[section]}
                </button>
              ))}
            </div>

            <div className="px-8">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Configuration */}
              <div className="lg:col-span-2 space-y-6">
                {/* Basic Section */}
                {activeSection === 'basic' && (
                  <div className="space-y-6">
                    {/* Position Selection */}
                    <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                      <h3 className="text-lg font-semibold text-text-primary mb-4">{t.position}</h3>
                      <div className="grid grid-cols-3 gap-3">
                        {positions.map((pos) => (
                          <button
                            key={pos.value}
                            onClick={() => setConfig((prev) => ({ ...prev, position: pos.value }))}
                            className={`px-4 py-3 rounded-lg border-2 transition-all ${
                              config.position === pos.value
                                ? 'bg-[#AF52DE]/20 border-[#AF52DE] text-text-primary'
                                : 'bg-bg-tertiary border-border-color text-text-tertiary hover:border-[#AF52DE]/50'
                            }`}
                          >
                            <div className="text-sm font-medium">{pos.label}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Level and Difficulty */}
                    <div className="grid grid-cols-2 gap-6">
                      <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                        <h3 className="text-lg font-semibold text-text-primary mb-4">{t.level}</h3>
                        <div className="space-y-2">
                          {levels.map((level) => (
                            <button
                              key={level.value}
                              onClick={() => setConfig((prev) => ({ ...prev, level: level.value }))}
                              className={`w-full px-4 py-3 rounded-lg border-2 transition-all flex items-center gap-3 ${
                                config.level === level.value
                                  ? 'bg-[#AF52DE]/20 border-[#AF52DE] text-text-primary'
                                  : 'bg-bg-tertiary border-border-color text-text-tertiary hover:border-[#AF52DE]/50'
                              }`}
                            >
                              <span className="font-medium">{level.label}</span>
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                        <h3 className="text-lg font-semibold text-text-primary mb-4">{t.difficulty}</h3>
                        <div className="space-y-2">
                          {difficulties.map((diff) => (
                            <button
                              key={diff.value}
                              onClick={() => setConfig((prev) => ({ ...prev, difficulty: diff.value }))}
                              className={`w-full px-4 py-3 rounded-lg border-2 transition-all ${
                                config.difficulty === diff.value
                                  ? 'bg-[#AF52DE]/20 border-[#AF52DE] text-text-primary'
                                  : 'bg-bg-tertiary border-border-color text-text-tertiary hover:border-[#AF52DE]/50'
                              }`}
                            >
                              {diff.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Programming Languages */}
                    <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                      <h3 className="text-lg font-semibold text-text-primary mb-4">{t.programmingLanguages}</h3>
                      <div className="grid grid-cols-4 gap-2">
                        {programmingLanguages.map((lang) => (
                          <button
                            key={lang.value}
                            onClick={() => {
                              setConfig((prev) => ({
                                ...prev,
                                programmingLanguages: prev.programmingLanguages.includes(lang.value)
                                  ? prev.programmingLanguages.filter((l) => l !== lang.value)
                                  : [...prev.programmingLanguages, lang.value],
                              }))
                            }}
                            className={`px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                              config.programmingLanguages.includes(lang.value)
                                ? 'bg-[#AF52DE]/20 border-[#AF52DE] text-text-primary'
                                : 'bg-bg-tertiary border-border-color text-text-tertiary hover:border-[#AF52DE]/50'
                            }`}
                          >
                            <span>{lang.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Topics */}
                    <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                      <h3 className="text-lg font-semibold text-text-primary mb-4">{t.topics}</h3>
                      <div className="grid grid-cols-2 gap-2">
                        {availableTopics.map((topic) => (
                          <button
                            key={topic}
                            onClick={() => handleTopicToggle(topic)}
                            className={`px-3 py-2 rounded-lg border-2 transition-all text-sm text-left ${
                              config.topics.includes(topic)
                                ? 'bg-[#AF52DE]/20 border-[#AF52DE] text-text-primary'
                                : 'bg-bg-tertiary border-border-color text-text-tertiary hover:border-[#AF52DE]/50'
                            }`}
                          >
                            {topic}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Stages Section */}
                {activeSection === 'stages' && (
                  <div className="space-y-6">
                    {Object.entries(config.stages).map(([stage, enabled]) => {
                      const stageKey = stage as keyof InterviewConfig['stages']
                      const stageLabels: Record<string, { title: string; desc: string }> = {
                        introduction: { title: t.introduction, desc: t.introductionDesc },
                        softSkills: { title: t.softSkills, desc: t.softSkillsDesc },
                        technical: { title: t.technical, desc: t.technicalDesc },
                        liveCoding: { title: t.liveCoding, desc: t.liveCodingDesc },
                      }
                      const stageInfo = stageLabels[stage]

                      return (
                        <div
                          key={stage}
                          className={`bg-bg-secondary rounded-xl border-2 p-6 transition-all ${
                            enabled ? 'border-[#AF52DE] bg-[#AF52DE]/10' : 'border-border-color'
                          }`}
                        >
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <input
                                  type="checkbox"
                                  checked={enabled}
                                  onChange={() => handleStageToggle(stageKey)}
                                  className="w-5 h-5 rounded border-border-color bg-bg-tertiary text-[#AF52DE] focus:ring-[#AF52DE]"
                                />
                                <h3 className="text-lg font-semibold text-text-primary">{stageInfo.title}</h3>
                              </div>
                              <p className="text-sm text-text-tertiary ml-8">{stageInfo.desc}</p>
                            </div>
                          </div>
                          {enabled && (
                            <div className="ml-8 mt-4">
                              {(stageKey === 'introduction' || stageKey === 'softSkills') ? (
                                <div className="space-y-4">
                                  <label className="text-sm text-text-tertiary mb-2 block">
                                    Выберите вопросы:
                                  </label>
                                  
                                  {/* Предустановленные вопросы */}
                                  <div className="space-y-2">
                                    {(stageKey === 'introduction' ? defaultIntroductionQuestions : defaultSoftSkillsQuestions).map((question, index) => {
                                      const isSelected = config.questionsPerStage[stageKey].includes(question)
                                      return (
                                        <label
                                          key={index}
                                          className="flex items-start gap-3 p-3 rounded-lg border border-border-color bg-bg-tertiary hover:border-[#AF52DE]/50 cursor-pointer transition-all"
                                        >
                                          <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => {
                                              setConfig((prev) => ({
                                                ...prev,
                                                questionsPerStage: {
                                                  ...prev.questionsPerStage,
                                                  [stageKey]: isSelected
                                                    ? prev.questionsPerStage[stageKey].filter((q) => q !== question)
                                                    : [...prev.questionsPerStage[stageKey], question],
                                                },
                                              }))
                                            }}
                                            className="mt-1 w-4 h-4 rounded border-border-color bg-bg-tertiary text-[#AF52DE] focus:ring-[#AF52DE]"
                                          />
                                          <span className="text-sm text-text-primary flex-1">{question}</span>
                                        </label>
                                      )
                                    })}
                                  </div>

                                  {/* Пользовательские вопросы */}
                                  {config.customQuestions[stageKey].length > 0 && (
                                    <div className="mt-4 space-y-2">
                                      <label className="text-sm text-text-tertiary mb-2 block">
                                        Ваши вопросы:
                                      </label>
                                      {config.customQuestions[stageKey].map((question, index) => {
                                        const isSelected = config.questionsPerStage[stageKey].includes(question)
                                        return (
                                          <div
                                            key={`custom-${index}`}
                                            className="flex items-start gap-3 p-3 rounded-lg border border-border-color bg-bg-tertiary"
                                          >
                                            <input
                                              type="checkbox"
                                              checked={isSelected}
                                              onChange={() => {
                                                setConfig((prev) => ({
                                                  ...prev,
                                                  questionsPerStage: {
                                                    ...prev.questionsPerStage,
                                                    [stageKey]: isSelected
                                                      ? prev.questionsPerStage[stageKey].filter((q) => q !== question)
                                                      : [...prev.questionsPerStage[stageKey], question],
                                                  },
                                                }))
                                              }}
                                              className="mt-1 w-4 h-4 rounded border-border-color bg-bg-tertiary text-[#AF52DE] focus:ring-[#AF52DE]"
                                            />
                                            <span className="text-sm text-text-primary flex-1">{question}</span>
                                            <button
                                              onClick={() => {
                                                setConfig((prev) => ({
                                                  ...prev,
                                                  customQuestions: {
                                                    ...prev.customQuestions,
                                                    [stageKey]: prev.customQuestions[stageKey].filter((_, i) => i !== index),
                                                  },
                                                  questionsPerStage: {
                                                    ...prev.questionsPerStage,
                                                    [stageKey]: prev.questionsPerStage[stageKey].filter((q) => q !== question),
                                                  },
                                                }))
                                              }}
                                              className="text-text-tertiary hover:text-red-500 transition-colors"
                                            >
                                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                              </svg>
                                            </button>
                                          </div>
                                        )
                                      })}
                                    </div>
                                  )}

                                  {/* Добавить вопрос */}
                                  <div className="mt-4">
                                    <div className="flex gap-2">
                                      <input
                                        type="text"
                                        placeholder="Добавить свой вопрос..."
                                        onKeyDown={(e) => {
                                          if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                                            const newQuestion = e.currentTarget.value.trim()
                                            setConfig((prev) => ({
                                              ...prev,
                                              customQuestions: {
                                                ...prev.customQuestions,
                                                [stageKey]: [...prev.customQuestions[stageKey], newQuestion],
                                              },
                                              questionsPerStage: {
                                                ...prev.questionsPerStage,
                                                [stageKey]: [...prev.questionsPerStage[stageKey], newQuestion],
                                              },
                                            }))
                                            e.currentTarget.value = ''
                                          }
                                        }}
                                        className="flex-1 bg-bg-tertiary border border-border-color text-text-primary px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#AF52DE] text-sm"
                                      />
                                      <button
                                        onClick={(e) => {
                                          const input = e.currentTarget.previousElementSibling as HTMLInputElement
                                          if (input && input.value.trim()) {
                                            const newQuestion = input.value.trim()
                                            setConfig((prev) => ({
                                              ...prev,
                                              customQuestions: {
                                                ...prev.customQuestions,
                                                [stageKey]: [...prev.customQuestions[stageKey], newQuestion],
                                              },
                                              questionsPerStage: {
                                                ...prev.questionsPerStage,
                                                [stageKey]: [...prev.questionsPerStage[stageKey], newQuestion],
                                              },
                                            }))
                                            input.value = ''
                                          }
                                        }}
                                        className="px-4 py-2 bg-[#AF52DE]/20 hover:bg-[#AF52DE]/30 text-text-primary border border-[#AF52DE] rounded-lg transition-all text-sm font-medium"
                                      >
                                        Добавить
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="space-y-4">
                                  <div className="flex items-center justify-between mb-4">
                                    <label className="text-sm text-text-tertiary">
                                      {t.questionsPerStage}
                                    </label>
                                    <div className="flex items-center gap-3">
                                      <button
                                        onClick={() => {
                                          const currentValue = config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number
                                          if (currentValue > 0) {
                                            setConfig((prev) => ({
                                              ...prev,
                                              questionsPerStage: {
                                                ...prev.questionsPerStage,
                                                [stageKey]: currentValue - 1,
                                              },
                                            }))
                                          }
                                        }}
                                        disabled={(config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number) === 0}
                                        className="w-8 h-8 rounded-lg border-2 border-border-color bg-bg-tertiary text-text-primary hover:border-[#AF52DE] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center"
                                      >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                                          <path strokeLinecap="round" strokeLinejoin="round" d="M20 12H4" />
                                        </svg>
                                      </button>
                                      <div className="min-w-[60px] text-center">
                                        <span className="text-2xl font-bold text-text-primary">
                                          {config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number}
                                        </span>
                                        <span className="text-sm text-text-tertiary ml-1">
                                          {(() => {
                                            const count = config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number
                                            return count === 1 ? 'вопрос' : count < 5 ? 'вопроса' : 'вопросов'
                                          })()}
                                        </span>
                                      </div>
                                      <button
                                        onClick={() => {
                                          const currentValue = config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number
                                          if (currentValue < 10) {
                                            setConfig((prev) => ({
                                              ...prev,
                                              questionsPerStage: {
                                                ...prev.questionsPerStage,
                                                [stageKey]: currentValue + 1,
                                              },
                                            }))
                                          }
                                        }}
                                        disabled={(config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number) === 10}
                                        className="w-8 h-8 rounded-lg border-2 border-border-color bg-bg-tertiary text-text-primary hover:border-[#AF52DE] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center"
                                      >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                                        </svg>
                                      </button>
                                    </div>
                                  </div>
                                  <div className="relative">
                                    <input
                                      type="range"
                                      min="0"
                                      max="10"
                                      step="1"
                                      value={config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number}
                                      onChange={(e) =>
                                        setConfig((prev) => ({
                                          ...prev,
                                          questionsPerStage: {
                                            ...prev.questionsPerStage,
                                            [stageKey]: parseInt(e.target.value),
                                          },
                                        }))
                                      }
                                  className="w-full h-2 bg-bg-quaternary rounded-lg appearance-none cursor-pointer slider"
                                  style={{
                                    background: `linear-gradient(to right, #AF52DE 0%, #AF52DE ${((config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number) / 10) * 100}%, var(--bg-quaternary) ${((config.questionsPerStage[stageKey as keyof typeof config.questionsPerStage] as number) / 10) * 100}%, var(--bg-quaternary) 100%)`
                                  }}
                                    />
                                    <div className="flex justify-between mt-2 text-xs text-[#555]">
                                      {[0, 2, 4, 6, 8, 10].map((val) => (
                                        <span key={val} className="w-4 text-center">{val}</span>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Advanced Section */}
                {activeSection === 'advanced' && (
                  <div className="space-y-6">
                    {/* HR Prompt */}
                    <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                      <h3 className="text-lg font-semibold text-text-primary mb-2">{t.hrPrompt}</h3>
                      <p className="text-sm text-text-tertiary mb-4">{t.hrPromptDesc}</p>
                      <textarea
                        value={config.hrPrompt}
                        onChange={(e) => setConfig((prev) => ({ ...prev, hrPrompt: e.target.value }))}
                        placeholder="Например: Ищем опытного Python разработчика с опытом работы с Django и PostgreSQL..."
                        className="w-full bg-bg-tertiary border border-border-color text-text-primary px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#AF52DE] focus:border-transparent min-h-[150px] resize-y"
                      />
                    </div>

                    {/* Timer Settings */}
                    <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                      <div className="flex items-center gap-3 mb-4">
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
                        <div>
                          <h3 className="text-lg font-semibold text-text-primary">{t.timer}</h3>
                          <p className="text-sm text-text-tertiary">{t.timerDesc}</p>
                        </div>
                      </div>
                      
                      {config.timer.enabled && (
                        <div className="ml-8 space-y-6">
                          {/* Technical Timer */}
                          <div>
                            <div className="flex items-center justify-between mb-4">
                              <label className="text-sm text-text-tertiary">{t.technicalTimer}</label>
                              <div className="flex items-center gap-3">
                                <button
                                  onClick={() => {
                                    if (config.timer.technical_minutes > 1) {
                                      setConfig((prev) => ({
                                        ...prev,
                                        timer: {
                                          ...prev.timer,
                                          technical_minutes: prev.timer.technical_minutes - 1,
                                        },
                                      }))
                                    }
                                  }}
                                  disabled={config.timer.technical_minutes <= 1}
                                  className="w-8 h-8 rounded-lg border-2 border-border-color bg-bg-tertiary text-text-primary hover:border-[#AF52DE] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M20 12H4" />
                                  </svg>
                                </button>
                                <div className="min-w-[60px] text-center">
                                  <span className="text-2xl font-bold text-text-primary">
                                    {config.timer.technical_minutes}
                                  </span>
                                  <span className="text-sm text-text-tertiary ml-1">мин</span>
                                </div>
                                <button
                                  onClick={() => {
                                    if (config.timer.technical_minutes < 15) {
                                      setConfig((prev) => ({
                                        ...prev,
                                        timer: {
                                          ...prev.timer,
                                          technical_minutes: prev.timer.technical_minutes + 1,
                                        },
                                      }))
                                    }
                                  }}
                                  disabled={config.timer.technical_minutes >= 15}
                                  className="w-8 h-8 rounded-lg border-2 border-border-color bg-bg-tertiary text-text-primary hover:border-[#AF52DE] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                            <div className="relative">
                              <input
                                type="range"
                                min="1"
                                max="15"
                                step="1"
                                value={config.timer.technical_minutes}
                                onChange={(e) =>
                                  setConfig((prev) => ({
                                    ...prev,
                                    timer: {
                                      ...prev.timer,
                                      technical_minutes: parseInt(e.target.value),
                                    },
                                  }))
                                }
                                className="w-full h-2 bg-bg-quaternary rounded-lg appearance-none cursor-pointer slider"
                                style={{
                                  background: `linear-gradient(to right, #AF52DE 0%, #AF52DE calc(${(config.timer.technical_minutes / 15) * 100}% - 10px), var(--bg-quaternary) calc(${(config.timer.technical_minutes / 15) * 100}% - 10px), var(--bg-quaternary) 100%)`
                                }}
                              />
                              <div className="flex justify-between mt-3 text-xs text-text-tertiary relative">
                                <span>1</span>
                                <span className="absolute left-1/2 transform -translate-x-1/2">8</span>
                                <span>15</span>
                              </div>
                            </div>
                          </div>
                          
                          {/* Live Coding Timer */}
                          <div>
                            <div className="flex items-center justify-between mb-4">
                              <label className="text-sm text-text-tertiary">{t.liveCodingTimer}</label>
                              <div className="flex items-center gap-3">
                                <button
                                  onClick={() => {
                                    if (config.timer.liveCoding_minutes > 1) {
                                      setConfig((prev) => ({
                                        ...prev,
                                        timer: {
                                          ...prev.timer,
                                          liveCoding_minutes: prev.timer.liveCoding_minutes - 1,
                                        },
                                      }))
                                    }
                                  }}
                                  disabled={config.timer.liveCoding_minutes <= 1}
                                  className="w-8 h-8 rounded-lg border-2 border-border-color bg-bg-tertiary text-text-primary hover:border-[#AF52DE] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M20 12H4" />
                                  </svg>
                                </button>
                                <div className="min-w-[60px] text-center">
                                  <span className="text-2xl font-bold text-text-primary">
                                    {config.timer.liveCoding_minutes}
                                  </span>
                                  <span className="text-sm text-text-tertiary ml-1">мин</span>
                                </div>
                                <button
                                  onClick={() => {
                                    if (config.timer.liveCoding_minutes < 60) {
                                      setConfig((prev) => ({
                                        ...prev,
                                        timer: {
                                          ...prev.timer,
                                          liveCoding_minutes: prev.timer.liveCoding_minutes + 1,
                                        },
                                      }))
                                    }
                                  }}
                                  disabled={config.timer.liveCoding_minutes >= 60}
                                  className="w-8 h-8 rounded-lg border-2 border-border-color bg-bg-tertiary text-text-primary hover:border-[#AF52DE] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                            <div className="relative">
                              <input
                                type="range"
                                min="1"
                                max="60"
                                step="1"
                                value={config.timer.liveCoding_minutes}
                                onChange={(e) =>
                                  setConfig((prev) => ({
                                    ...prev,
                                    timer: {
                                      ...prev.timer,
                                      liveCoding_minutes: parseInt(e.target.value),
                                    },
                                  }))
                                }
                                className="w-full h-2 bg-bg-quaternary rounded-lg appearance-none cursor-pointer slider"
                                style={{
                                  background: `linear-gradient(to right, #AF52DE 0%, #AF52DE calc(${(config.timer.liveCoding_minutes / 60) * 100}% - 10px), var(--bg-quaternary) calc(${(config.timer.liveCoding_minutes / 60) * 100}% - 10px), var(--bg-quaternary) 100%)`
                                }}
                              />
                              <div className="flex justify-between mt-3 text-xs text-text-tertiary relative">
                                <span>1</span>
                                <span className="absolute left-1/2 transform -translate-x-1/2">30</span>
                                <span>60</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Access Code */}
                    <div className="bg-bg-secondary rounded-xl border border-border-color p-6">
                      <h3 className="text-lg font-semibold text-text-primary mb-2">
                        {t.accessCode} <span className="text-red-500">*</span>
                      </h3>
                      <p className="text-sm text-text-tertiary mb-4">{t.accessCodeDesc}</p>
                      <div className="flex gap-3">
                        <input
                          type="text"
                          value={config.accessCode}
                          onChange={(e) =>
                            setConfig((prev) => ({ ...prev, accessCode: e.target.value.toUpperCase() }))
                          }
                          placeholder="Введите код доступа или сгенерируйте автоматически"
                          maxLength={10}
                          className={`flex-1 bg-bg-tertiary border ${
                            !config.accessCode || config.accessCode.trim() === ''
                              ? 'border-red-500/50 focus:border-red-500'
                              : 'border-border-color focus:border-[#AF52DE]'
                          } text-text-primary px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#AF52DE] font-mono`}
                        />
                        <button
                          onClick={generateAccessCode}
                          className="px-4 py-2.5 bg-[#AF52DE]/20 hover:bg-[#AF52DE]/30 text-text-primary border border-[#AF52DE] rounded-lg transition-all font-medium"
                        >
                          {t.generateCode}
                        </button>
                      </div>
                      {!selectedCandidateId && (!config.accessCode || config.accessCode.trim() === '') && (
                        <p className="text-sm text-red-500 mt-2">Код доступа обязателен, если не выбрано приглашение кандидату</p>
                      )}
                      {selectedCandidateId && (
                        <p className="text-sm text-text-tertiary mt-2">Код доступа не требуется при отправке приглашения</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Preview Sidebar */}
              <div className="lg:col-span-1">
                <div className="sticky top-8 bg-bg-secondary rounded-xl border border-border-color p-6">
                  <h3 className="text-lg font-semibold text-text-primary mb-6">{t.preview}</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <div className="text-sm text-text-tertiary mb-1">{t.position}</div>
                      <div className="text-text-primary font-medium">
                        {positions.find((p) => p.value === config.position)?.label}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-tertiary mb-1">{t.level}</div>
                      <div className="text-text-primary font-medium">
                        {levels.find((l) => l.value === config.level)?.label}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-tertiary mb-1">{t.difficulty}</div>
                      <div className="text-text-primary font-medium">
                        {difficulties.find((d) => d.value === config.difficulty)?.label}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-tertiary mb-1">{t.questionCount}</div>
                      <div className="text-text-primary font-medium text-xl">{getTotalQuestions()}</div>
                    </div>

                    <div>
                      <div className="text-sm text-text-tertiary mb-1">{t.duration}</div>
                      <div className="text-text-primary font-medium">
                        {calculateEstimatedDuration()} {t.minutes}
                        {config.timer.enabled && (
                          <span className="text-xs text-text-tertiary block mt-1">
                            {language === 'ru' ? '(с учетом таймеров)' : '(with timers)'}
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-tertiary mb-1">{t.accessCode}</div>
                      <div className="text-text-primary font-medium font-mono text-lg">{config.accessCode || 'Не задан'}</div>
                    </div>

                    {config.timer.enabled && (
                      <div>
                        <div className="text-sm text-text-tertiary mb-1">{t.timer}</div>
                        <div className="space-y-1">
                          <div className="text-text-primary text-sm">
                            Технические: {config.timer.technical_minutes} мин
                          </div>
                          <div className="text-text-primary text-sm">
                            Лайвкодинг: {config.timer.liveCoding_minutes} мин
                          </div>
                        </div>
                      </div>
                    )}

                    <div>
                      <div className="text-sm text-text-tertiary mb-2">{t.programmingLanguages}</div>
                      <div className="flex flex-wrap gap-2">
                        {config.programmingLanguages.map((lang) => (
                          <span
                            key={lang}
                            className="px-2 py-1 bg-[#AF52DE]/20 text-text-primary text-xs rounded border border-[#AF52DE]"
                          >
                            {programmingLanguages.find((l) => l.value === lang)?.label}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-tertiary mb-2">{t.topics}</div>
                      <div className="flex flex-wrap gap-2">
                        {config.topics.slice(0, 5).map((topic) => (
                          <span
                            key={topic}
                            className="px-2 py-1 bg-bg-tertiary text-text-tertiary text-xs rounded border border-border-color"
                          >
                            {topic}
                          </span>
                        ))}
                        {config.topics.length > 5 && (
                          <span className="px-2 py-1 text-text-tertiary text-xs">+{config.topics.length - 5}</span>
                        )}
                      </div>
                    </div>

                    <div className="pt-4 border-t border-border-color">
                      <div className="text-sm text-text-tertiary mb-2">Активные этапы</div>
                      <div className="space-y-1">
                        {Object.entries(config.stages).map(([stage, enabled]) => {
                          if (!enabled) return null
                          const stageLabels: Record<string, string> = {
                            introduction: t.introduction,
                            softSkills: t.softSkills,
                            technical: t.technical,
                            liveCoding: t.liveCoding,
                          }
                          const questionCount = (stage === 'introduction' || stage === 'softSkills')
                            ? (Array.isArray(config.questionsPerStage[stage as keyof typeof config.questionsPerStage])
                                ? (config.questionsPerStage[stage as keyof typeof config.questionsPerStage] as string[]).length
                                : 0)
                            : (config.questionsPerStage[stage as keyof typeof config.questionsPerStage] as number)
                          return (
                            <div key={stage} className="flex justify-between text-sm">
                              <span className="text-text-primary">{stageLabels[stage]}</span>
                              <span className="text-text-tertiary">
                                {questionCount} {questionCount === 1 ? 'вопрос' : questionCount < 5 ? 'вопроса' : 'вопросов'}
                              </span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Create Button */}
                  <div className="mt-6 pt-6 border-t border-border-color">
                    <button
                      onClick={handleCreate}
                      disabled={validateConfig().length > 0}
                      className="w-full px-6 py-3 bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] text-white hover:from-[#8E44AD] hover:to-[#AF52DE] disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all font-semibold shadow-md"
                    >
                      {t.create}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
