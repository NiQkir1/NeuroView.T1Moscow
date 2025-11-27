'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import dynamicImport from 'next/dynamic'
import Image from 'next/image'

export const dynamic = 'force-dynamic'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../components/Sidebar'
import LoadingSpinner from '../components/LoadingSpinner'
import { useActivityMonitor } from './hooks/useActivityMonitor'
import { useKeystrokeDynamics } from './hooks/useKeystrokeDynamics'
import { generateDeviceFingerprint } from '@/lib/fingerprint'
import { useNotifications } from '../hooks/useNotifications'
import { useTheme } from '../hooks/useTheme'

// Динамический импорт Monaco Editor
const MonacoEditor = dynamicImport(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-full text-gray-500">Loading editor...</div>,
}) as any

interface TestCase {
  id: number
  input: string
  expectedOutput: string
  actualOutput?: string
  status?: 'passed' | 'failed' | 'running' | 'pending'
  error?: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'judge'
  content: string
  timestamp: Date
}

interface InterviewConfig {
  position?: string
  difficulty?: string
  level?: string
  topics?: string[]
  programmingLanguages?: string[]
  duration_minutes?: number
  hrPrompt?: string
  stages?: {
    introduction?: boolean
    technical?: boolean
    liveCoding?: boolean
  }
  questions_per_stage?: Record<string, number>
  questionsPerStage?: Record<string, number>
  template_questions?: Record<string, any[]>
  timer?: {
    enabled: boolean
    technical_minutes: number
    liveCoding_minutes: number
  }
}

interface Interview {
  id: number
  title: string
  access_code?: string
  position?: string
  difficulty?: string
  level?: string
  topics?: string[]
  programming_languages?: string[]
  interview_config?: {
    position?: string
    level?: string
    programming_languages?: string[]
    programmingLanguages?: string[]  // Поддержка обоих вариантов написания
    required_skills?: string[]
    question_count?: number
    questions_per_stage?: Record<string, any>
    template_questions?: Record<string, any[]>
    timer?: {
      enabled: boolean
      technical_minutes: number
      liveCoding_minutes: number
    }
  }
  duration_minutes?: number
  hr_prompt?: string
  stages?: Record<string, any>
  timer?: {
    enabled: boolean
    technical_minutes: number
    liveCoding_minutes: number
  }
}

interface VerifyCodeResponse {
  valid: boolean
  message?: string
  session_id?: number
}

interface Session {
  id: number
  questions?: Array<{
    id: number
    question_text: string
    order: number
    topic?: string
    answers?: Array<any>
  }>
}

interface CodeExecuteResult {
  success: boolean
  output?: string
  error?: string
}

interface ChatMessageResponse {
  response: string
  language?: string
}

interface AnswerResponse {
  id: number
  evaluation?: {
    score?: number
    feedback?: string
  }
}

const translations = {
  ru: {
    run: 'Запуск',
    running: 'Запуск...',
    submit: 'Отправить',
    submitting: 'Отправка...',
    testCases: 'Тесты',
    chat: 'Чат',
    passed: 'Пройдено',
    failed: 'Не пройдено',
    running_test: 'Выполняется...',
    pending: 'Ожидание',
    input: 'Входные данные',
    expected: 'Ожидаемый результат',
    actual: 'Фактический результат',
    error: 'Ошибка',
    chatPlaceholder: 'Напишите сообщение интервьюеру...',
    send: 'Отправить',
    loading: 'Загрузка...',
    noTests: 'Запустите код, чтобы увидеть результаты тестов',
    testResults: 'Результаты тестов',
    chatWithInterviewer: 'Чат с интервьюером',
    language: 'Язык',
    timeRemaining: 'Осталось времени',
    waitingForQuestion: 'Ожидание вопроса от интервьюера...',
    taskDescription: 'Описание задачи',
    finishInterview: 'Завершить интервью',
    finishConfirm: 'Вы уверены, что хотите завершить интервью? Это действие нельзя отменить.',
    interviewFinished: 'Интервью завершено',
  },
  en: {
    run: 'Run',
    running: 'Running...',
    submit: 'Submit',
    submitting: 'Submitting...',
    testCases: 'Tests',
    chat: 'Chat',
    passed: 'Passed',
    failed: 'Failed',
    running_test: 'Running...',
    pending: 'Pending',
    input: 'Input',
    expected: 'Expected',
    actual: 'Actual',
    error: 'Error',
    chatPlaceholder: 'Type a message to the interviewer...',
    send: 'Send',
    loading: 'Loading...',
    noTests: 'Run code to see test results',
    testResults: 'Test Results',
    chatWithInterviewer: 'Chat with Interviewer',
    language: 'Language',
    timeRemaining: 'Time Remaining',
    waitingForQuestion: 'Waiting for question from interviewer...',
    taskDescription: 'Task Description',
    finishInterview: 'Finish Interview',
    finishConfirm: 'Are you sure you want to finish the interview? This action cannot be undone.',
    interviewFinished: 'Interview finished',
  },
}

export default function InterviewPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const interviewId = searchParams.get('id')
  const { showError, showWarning, showInfo } = useNotifications()
  const { theme: currentTheme } = useTheme()
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const t = translations[language]
  
  const [question, setQuestion] = useState<string>('')
  const [code, setCode] = useState<string>('// Start writing code here\n\ndef solution():\n    pass\n')
  const [isLoading, setIsLoading] = useState(false)
  const [interviewConfig, setInterviewConfig] = useState<InterviewConfig | null>(null)
  const [currentQuestionId, setCurrentQuestionId] = useState<string>('') // ID текущего вопроса для отслеживания смены
  const [sessionId, setSessionId] = useState<number | null>(null) // ID сессии для античита
  const [questionShownAt, setQuestionShownAt] = useState<number | null>(null) // Время показа вопроса
  const [currentAnswerText, setCurrentAnswerText] = useState<string>('') // Текущий текст ответа для отслеживания изменений
  const [warningCount, setWarningCount] = useState<number>(0) // Счетчик предупреждений (максимум 2)
  
  // Восстанавливаем таймер из localStorage или устанавливаем начальное значение
  const getInitialTime = () => {
    if (typeof window !== 'undefined') {
      const savedStartTime = localStorage.getItem('interview_start_time')
      const savedTimeRemaining = localStorage.getItem('interview_time_remaining')
      const savedQuestionId = localStorage.getItem('current_question_id')
      
      // Если есть сохраненные данные таймера, восстанавливаем их
      if (savedStartTime && savedTimeRemaining) {
        const startTime = parseInt(savedStartTime)
        const savedRemaining = parseInt(savedTimeRemaining)
        const elapsed = Math.floor((Date.now() - startTime) / 1000)
        const remaining = Math.max(0, savedRemaining - elapsed)
        return remaining
      }
      
      // Если есть конфигурация интервью, но таймер еще не запущен
      const configStr = sessionStorage.getItem('interview_config')
      if (configStr) {
        try {
          const config = JSON.parse(configStr)
          // Если таймер включен, но еще нет сохраненного времени, возвращаем 0
          // Таймер запустится при получении первого вопроса
          if (config.timer?.enabled) {
            return 0
          }
          // Если таймер выключен, используем общую длительность
          if (config.duration_minutes) {
            return config.duration_minutes * 60
          }
        } catch (e) {
          // Ошибка парсинга конфига
        }
      }
    }
    return 0 // По умолчанию 0, таймер запустится при получении первого вопроса
  }
  
  // Используем useState с функцией-инициализатором, чтобы избежать проблем с SSR
  const [timeRemaining, setTimeRemaining] = useState(() => {
    if (typeof window === 'undefined') {
      return 0 // На сервере всегда 0, чтобы избежать ошибок гидратации
    }
    return getInitialTime()
  })
  const [isClient, setIsClient] = useState(false) // Флаг для проверки, что мы на клиенте
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [testsVisible, setTestsVisible] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [selectedLanguage, setSelectedLanguage] = useState('python')
  const [timeExpired, setTimeExpired] = useState(false)
  const [languageChangedNotification, setLanguageChangedNotification] = useState<string | null>(null)
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
    // Инициализируем на клиенте для избежания ошибок гидратации
    if (typeof window === 'undefined') {
      return []
    }
    return [
      {
        id: 'initial',
        role: 'assistant',
        content: language === 'ru' 
          ? 'Здравствуйте! Я сын Антона и сегодня я провожу ваше собеседование.\n\nГотовы ли вы начать интервью?'
          : 'Hello! I am Anton\'s son and today I will be conducting your interview.\n\nAre you ready to start?',
        timestamp: new Date(),
      }
    ]
  })
  const [chatInput, setChatInput] = useState('')
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<any>(null)
  const isCompletingRef = useRef<boolean>(false) // Флаг для предотвращения повторного завершения
  
  // STT & TTS state
  const [isRecording, setIsRecording] = useState(false)
  const [isSoundEnabled, setIsSoundEnabled] = useState(true)
  const recognitionRef = useRef<any>(null)
  const synthRef = useRef<SpeechSynthesis | null>(null)
  const isRecordingRef = useRef<boolean>(false) // Ref для отслеживания состояния записи
  
  // Добавляем начальное сообщение только на клиенте для избежания ошибок гидратации
  useEffect(() => {
    if (chatMessages.length === 0) {
      setChatMessages([
        {
          id: 'initial',
          role: 'assistant',
          content: language === 'ru' 
            ? 'Здравствуйте! Я сын Антона и сегодня я провожу ваше собеседование.\n\nГотовы ли вы начать интервью?'
            : 'Hello! I am Anton\'s son and today I will be conducting your interview.\n\nAre you ready to start?',
          timestamp: new Date(),
        }
      ])
    }
  }, [])
  
  // Функция автоматического завершения интервью (без подтверждения)
  const autoCompleteInterview = async () => {
    // Проверяем, не завершается ли уже интервью
    if (isCompletingRef.current) {
      return
    }
    
    // Проверяем, не завершено ли уже интервью
    if (typeof window !== 'undefined' && interviewId) {
      const completed = localStorage.getItem(`interview_${interviewId}_completed`)
      if (completed === 'true') {
        return
      }
    }
    
    isCompletingRef.current = true
    
    try {
      if (!interviewId) {
        showError('ID интервью не найден')
        return
      }

      // Завершаем сессию интервью через API
      const data = await apiClient.post(`/api/interviews/${interviewId}/complete`)
      
      // Помечаем интервью как завершенное
      if (typeof window !== 'undefined') {
        if (interviewId) {
          localStorage.setItem(`interview_${interviewId}_completed`, 'true')
          sessionStorage.removeItem(`interview_${interviewId}_verified`)
        }
        
        // Очищаем данные интервью
        localStorage.removeItem('interview_start_time')
        localStorage.removeItem('interview_time_remaining')
        sessionStorage.removeItem('interview_config')
        
        // Очищаем флаги приглашения
        sessionStorage.removeItem(`interview_${interviewId}_invitation`)
        sessionStorage.removeItem(`interview_${interviewId}_verified`)
      }
      
      // Показываем сообщение о завершении из-за нарушения правил
      alert(language === 'ru' 
        ? 'Интервью автоматически завершено из-за переключения на другую вкладку браузера. Это нарушение правил прохождения интервью.' 
        : 'Interview was automatically completed due to switching to another browser tab. This is a violation of interview rules.')
      
      // Перенаправляем на страницу истории интервью
      router.replace('/interviews')
    } catch (error) {
      showError('Ошибка при автоматическом завершении интервью')
      isCompletingRef.current = false
    }
  }
  
  // Античит хуки
  const { activityLog } = useActivityMonitor({
    sessionId,
    enabled: !!sessionId,
    onSuspiciousActivity: (event) => {
      // Система предупреждений при переключении вкладок
      if (event.type === 'visibility_change' && event.details?.hidden === true) {
        setWarningCount((prevCount) => {
          const newCount = prevCount + 1
          
          if (newCount <= 2) {
            // Показываем предупреждение (1-е или 2-е)
            showWarning(language === 'ru' 
              ? `ПРЕДУПРЕЖДЕНИЕ ${newCount}/2: Вы переключились на другую вкладку! При следующем нарушении интервью будет завершено.`
              : `WARNING ${newCount}/2: You switched to another tab! The interview will be terminated on the next violation.`, 8000)
            alert(language === 'ru' 
              ? `ПРЕДУПРЕЖДЕНИЕ ${newCount}/2\n\nВы переключились на другую вкладку или приложение!\n\nЭто нарушение правил прохождения интервью. При следующем нарушении интервью будет автоматически завершено.\n\nПожалуйста, оставайтесь на текущей вкладке до завершения интервью.`
              : `WARNING ${newCount}/2\n\nYou switched to another tab or application!\n\nThis is a violation of the interview rules. The interview will be automatically terminated on the next violation.\n\nPlease stay on the current tab until the interview is complete.`)
          } else {
            // Завершаем интервью на 3-й раз
            showError('Превышено количество предупреждений. Интервью завершено автоматически.')
            autoCompleteInterview()
          }
          
          return newCount
        })
      }
    }
  })
  
  const { analyzeTypingPattern, reset: resetKeystrokes } = useKeystrokeDynamics()

  // Блокировка возврата через кнопку "Назад" после завершения интервью
  useEffect(() => {
    if (typeof window === 'undefined') return

    // Проверяем, завершено ли интервью
    const checkIfCompleted = () => {
      if (interviewId) {
        const completed = localStorage.getItem(`interview_${interviewId}_completed`)
        return completed === 'true'
      }
      return false
    }

    // Добавляем запись в историю, чтобы можно было перехватить возврат
    window.history.pushState(null, '', window.location.href)

    // Обработчик попытки вернуться назад
    const handlePopState = (event: PopStateEvent) => {
      if (checkIfCompleted()) {
        // Если интервью завершено, блокируем возврат
        window.history.pushState(null, '', window.location.href)
        alert(language === 'ru' 
          ? 'Это интервью уже завершено. Вы не можете вернуться к нему.' 
          : 'This interview is already completed. You cannot return to it.')
        router.replace('/interviews')
      } else {
        // Если интервью не завершено, но пользователь пытается уйти - предупреждаем
        const confirmed = window.confirm(
          language === 'ru' 
            ? 'Вы уверены, что хотите покинуть интервью? Прогресс может быть потерян.' 
            : 'Are you sure you want to leave the interview? Progress may be lost.'
        )
        if (!confirmed) {
          // Отменяем навигацию
          window.history.pushState(null, '', window.location.href)
        } else {
          // Разрешаем уход
          router.replace('/interviews')
        }
      }
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [interviewId, router, language])

  // Загрузка конфигурации интервью
  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    
    if (auth.isHR()) {
      router.push('/dashboard')
      return
    }

    // Проверяем, завершено ли интервью
    const checkIfCompleted = () => {
      if (typeof window !== 'undefined' && interviewId) {
        // Проверяем в localStorage, завершено ли интервью
        const completed = localStorage.getItem(`interview_${interviewId}_completed`)
        if (completed === 'true') {
          alert(language === 'ru' 
            ? 'Это интервью уже завершено. Вы не можете вернуться к нему.' 
            : 'This interview is already completed. You cannot return to it.')
          router.replace('/interviews')
          return true
        }
      }
      return false
    }

    // Проверяем, требуется ли код доступа
    const checkAccessCode = async () => {
      // Сначала проверяем, завершено ли интервью
      if (checkIfCompleted()) {
        return
      }

      if (interviewId) {
        // Проверяем, был ли код уже проверен в этой сессии или есть приглашение
        const verified = sessionStorage.getItem(`interview_${interviewId}_verified`)
        const hasInvitation = sessionStorage.getItem(`interview_${interviewId}_invitation`)
        
        if (!verified && !hasInvitation) {
          // Проверяем, требуется ли код для этого интервью
          try {
            const interview = await apiClient.get(`/api/interviews/${interviewId}`, false) as Interview
              if (interview.access_code) {
                // Требуется код, перенаправляем на страницу ввода кода
                router.push(`/interview/enter-code`)
                return
              }
              
              // Загружаем конфигурацию интервью
              // Таймер может быть в interview.timer или в interview.interview_config.timer
              const timerFromConfig = interview.interview_config?.timer || interview.timer
              const config: InterviewConfig = {
                position: interview.interview_config?.position || interview.position || 'frontend',
                difficulty: interview.difficulty || 'medium',
                level: interview.interview_config?.level || interview.level || 'middle',
                topics: interview.topics || [],
                programmingLanguages: interview.interview_config?.programming_languages || interview.programming_languages || interview.interview_config?.programmingLanguages || ['python'],
                duration_minutes: interview.duration_minutes || 60,
                hrPrompt: interview.hr_prompt,
                stages: interview.stages || {},
                questions_per_stage: interview.interview_config?.questions_per_stage,
                questionsPerStage: interview.interview_config?.questions_per_stage,
                template_questions: (interview.interview_config as any)?.template_questions,
                timer: timerFromConfig || {
                  enabled: false,
                  technical_minutes: 15,
                  liveCoding_minutes: 30,
                },
              }
              
              setInterviewConfig(config)
              
              // Сохраняем конфигурацию в sessionStorage
              sessionStorage.setItem('interview_config', JSON.stringify(config))
              
              // Устанавливаем язык программирования из конфига
              if (config.programmingLanguages && config.programmingLanguages.length > 0) {
                setSelectedLanguage(config.programmingLanguages[0])
              }
              
              // Инициализация античита: загружаем или создаем сессию
              try {
                // Пытаемся найти существующую сессию через verify-code endpoint
                // который создает сессию если её нет
                const verifyResponse = await apiClient.post(`/api/interviews/${interview.id}/verify-code`, {
                  code: ''
                }, false) as VerifyCodeResponse
                if (verifyResponse && verifyResponse.session_id) {
                  setSessionId(verifyResponse.session_id)
                  // Регистрируем устройство
                  try {
                    const fingerprint = await generateDeviceFingerprint()
                    await apiClient.post(`/api/sessions/${verifyResponse.session_id}/register-device`, {
                      fingerprint
                    }, false)
                  } catch (fingerprintError) {
                    showWarning('Не удалось зарегистрировать отпечаток устройства')
                    // Продолжаем работу даже если fingerprint не зарегистрирован
                  }
                }
              } catch (error) {
                showWarning('Не удалось инициализировать сессию')
                // Продолжаем работу даже если античит не инициализирован
              }
              
              // Сохраняем конфигурацию таймера для использования при новых вопросах
              if (config.timer?.enabled && typeof window !== 'undefined') {
                localStorage.setItem('interview_timer_config', JSON.stringify(config.timer))
              }
          } catch (error) {
            showError('Ошибка при проверке доступа к интервью')
          }
        } else {
          // Код уже проверен, загружаем конфигурацию из sessionStorage
          const configStr = sessionStorage.getItem('interview_config')
          if (configStr) {
            try {
              const config = JSON.parse(configStr)
              setInterviewConfig(config)
              if (config.programmingLanguages && config.programmingLanguages.length > 0) {
                setSelectedLanguage(config.programmingLanguages[0])
              }
            } catch (e) {
              showError('Ошибка при загрузке конфигурации интервью')
            }
          }
        }
      } else {
        // Загружаем конфигурацию из sessionStorage, если есть
        const configStr = sessionStorage.getItem('interview_config')
        if (configStr) {
          try {
            const config = JSON.parse(configStr)
            setInterviewConfig(config)
            if (config.programmingLanguages && config.programmingLanguages.length > 0) {
              setSelectedLanguage(config.programmingLanguages[0])
            }
          } catch (e) {
            showError('Ошибка при загрузке конфигурации интервью')
          }
        }
      }
    }

    checkAccessCode()
    
    // Восстанавливаем ID текущего вопроса из localStorage
    if (typeof window !== 'undefined') {
      setIsClient(true) // Устанавливаем флаг, что мы на клиенте
      const savedQuestionId = localStorage.getItem('current_question_id')
      if (savedQuestionId) {
        setCurrentQuestionId(savedQuestionId)
      }
      
      // Восстанавливаем таймер из localStorage только если интервью уже начато
      // Таймер запускается только при получении первого вопроса/задачи
      const savedStartTime = localStorage.getItem('interview_start_time')
      const savedTimeRemaining = localStorage.getItem('interview_time_remaining')
      if (savedStartTime && savedTimeRemaining) {
        const startTime = parseInt(savedStartTime)
        const savedRemaining = parseInt(savedTimeRemaining)
        const elapsed = Math.floor((Date.now() - startTime) / 1000)
        const remaining = Math.max(0, savedRemaining - elapsed)
        setTimeRemaining(remaining)
      } else {
        // Если таймер еще не запущен, устанавливаем 0
        setTimeRemaining(0)
      }
    }
  }, [router, interviewId])

  // Обновляем начальное сообщение при смене языка
  useEffect(() => {
    if (chatMessages.length === 1 && chatMessages[0].id === 'initial') {
      setChatMessages([{
        id: 'initial',
        role: 'assistant',
        content: language === 'ru' 
          ? 'Здравствуйте! Я сын Антона и сегодня я провожу ваше собеседование.\n\nГотовы ли вы начать интервью?'
          : 'Hello! I am Anton\'s son and today I will be conducting your interview.\n\nAre you ready to start?',
        timestamp: new Date(),
      }])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language])

  // Таймер с сохранением в localStorage
  useEffect(() => {
    // Убеждаемся, что start_time установлен при первом запуске таймера
    if (timeRemaining > 0 && !timeExpired && typeof window !== 'undefined') {
      const savedStartTime = localStorage.getItem('interview_start_time')
      if (!savedStartTime) {
        // Если start_time не установлен, устанавливаем его сейчас
        localStorage.setItem('interview_start_time', Date.now().toString())
      }
    }
    
    if (timeRemaining > 0 && !timeExpired) {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => {
          const newTime = Math.max(0, prev - 1)
          // Сохраняем время в localStorage
          if (typeof window !== 'undefined') {
            localStorage.setItem('interview_time_remaining', newTime.toString())
            // Обновляем start_time только если его нет
            const startTime = localStorage.getItem('interview_start_time')
            if (!startTime) {
              localStorage.setItem('interview_start_time', Date.now().toString())
            }
          }
          
          // Если время истекло
          if (newTime === 0) {
            setTimeExpired(true)
            // Блокируем все действия
            alert(language === 'ru' 
              ? 'Время истекло! Интервью завершено.' 
              : 'Time expired! Interview is over.')
          }
          
          return newTime
        })
      }, 1000)
      return () => clearInterval(timer)
    }
    // Не устанавливаем timeExpired в true, если таймер просто еще не запущен
    // timeExpired должен быть true только если таймер был запущен и истек
  }, [timeRemaining, timeExpired, language])

  // Автопрокрутка чата при появлении новых сообщений
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Блокировка копирования/вставки в чате
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        if (target.getAttribute('data-chat-input') === 'true') {
          e.preventDefault()
          e.stopPropagation()
          return false
        }
      }
    }

    const handleCopy = (e: ClipboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        if (target.getAttribute('data-chat-input') === 'true') {
          e.preventDefault()
          e.stopPropagation()
          return false
        }
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        if (target.getAttribute('data-chat-input') === 'true') {
          // Блокируем Ctrl+C, Ctrl+V, Ctrl+A
          if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'v' || e.key === 'a' || e.key === 'x')) {
            e.preventDefault()
            e.stopPropagation()
            return false
          }
        }
      }
    }

    const handleContextMenu = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        if (target.getAttribute('data-chat-input') === 'true') {
          e.preventDefault()
          return false
        }
      }
    }

    document.addEventListener('paste', handlePaste, true)
    document.addEventListener('copy', handleCopy, true)
    document.addEventListener('keydown', handleKeyDown, true)
    document.addEventListener('contextmenu', handleContextMenu, true)

    return () => {
      document.removeEventListener('paste', handlePaste, true)
      document.removeEventListener('copy', handleCopy, true)
      document.removeEventListener('keydown', handleKeyDown, true)
      document.removeEventListener('contextmenu', handleContextMenu, true)
    }
  }, [])

  // Initialize Speech Recognition and Synthesis
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Initialize TTS
      synthRef.current = window.speechSynthesis

      // Initialize STT
      // @ts-ignore
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition()
          recognition.continuous = true
          recognition.interimResults = true
          recognition.lang = language === 'ru' ? 'ru-RU' : 'en-US'

          recognition.onresult = (event: any) => {
            let finalTranscript = ''
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript
              }
            }
            if (finalTranscript) {
              setChatInput((prev) => prev + (prev ? ' ' : '') + finalTranscript)
            }
          }

          recognition.onerror = (event: any) => {
            console.error('Speech recognition error', event.error)
            isRecordingRef.current = false
            setIsRecording(false)
            
            // Показываем пользователю ошибку
            if (event.error === 'not-allowed') {
              showError(language === 'ru' 
                ? 'Доступ к микрофону запрещен. Разрешите доступ в настройках браузера.' 
                : 'Microphone access denied. Please allow access in browser settings.')
            } else if (event.error === 'no-speech') {
              // Это нормально, просто нет речи - не показываем ошибку
              console.log('No speech detected')
            } else if (event.error === 'aborted') {
              // Распознавание было прервано - не показываем ошибку
              console.log('Recognition aborted')
            } else {
              showWarning(language === 'ru' 
                ? `Ошибка распознавания речи: ${event.error}` 
                : `Speech recognition error: ${event.error}`)
            }
          }

          recognition.onend = () => {
            // Автоматически перезапускаем, если запись была активна
            if (isRecordingRef.current && recognitionRef.current) {
              try {
                recognitionRef.current.start()
              } catch (e) {
                // Если не удалось перезапустить, останавливаем запись
                console.error('Failed to restart recognition:', e)
                setIsRecording(false)
                isRecordingRef.current = false
              }
            }
          }

          recognition.onstart = () => {
            console.log('Speech recognition started')
          }

          recognitionRef.current = recognition
        } catch (error) {
          console.error('Failed to initialize speech recognition:', error)
          showError(language === 'ru' 
            ? 'Не удалось инициализировать распознавание речи' 
            : 'Failed to initialize speech recognition')
        }
      } else {
        console.warn('Speech Recognition API not available')
        showWarning(language === 'ru' 
          ? 'Распознавание речи недоступно в вашем браузере' 
          : 'Speech recognition not available in your browser')
      }
    }
  }, [language])

  // Text-to-Speech function
  const speakText = (text: string) => {
    if (!isSoundEnabled || !synthRef.current) return

    // Cancel current speech
    synthRef.current.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = language === 'ru' ? 'ru-RU' : 'en-US'
    utterance.rate = 1.0
    utterance.pitch = 1.0
    
    synthRef.current.speak(utterance)
  }

  // Синхронизация isRecordingRef с isRecording
  useEffect(() => {
    isRecordingRef.current = isRecording
  }, [isRecording])

  // Stop speech when sound is disabled
  useEffect(() => {
    if (!isSoundEnabled && synthRef.current) {
      synthRef.current.cancel()
    }
  }, [isSoundEnabled])

  // Auto-speak new assistant messages
  useEffect(() => {
    if (chatMessages.length > 0) {
      const lastMessage = chatMessages[chatMessages.length - 1]
      if (lastMessage.role === 'assistant') {
        speakText(lastMessage.content)
      }
    }
  }, [chatMessages, isSoundEnabled])

  const handleToggleRecording = async () => {
    if (isRecording) {
      try {
        isRecordingRef.current = false
        recognitionRef.current?.stop()
        setIsRecording(false)
      } catch (error) {
        console.error('Error stopping recognition:', error)
        isRecordingRef.current = false
        setIsRecording(false)
      }
    } else {
      // Проверяем доступность API
      // @ts-ignore
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (!SpeechRecognition) {
        showError(language === 'ru' 
          ? 'Распознавание речи недоступно в вашем браузере. Используйте Chrome, Edge или Safari.' 
          : 'Speech recognition not available. Please use Chrome, Edge, or Safari.')
        return
      }

      if (!recognitionRef.current) {
        showError(language === 'ru' 
          ? 'Распознавание речи не инициализировано. Перезагрузите страницу.' 
          : 'Speech recognition not initialized. Please reload the page.')
        return
      }

      try {
        // Запрашиваем разрешение на микрофон
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach(track => track.stop()) // Останавливаем сразу, разрешение получено
        
        isRecordingRef.current = true
        recognitionRef.current.start()
        setIsRecording(true)
      } catch (error: any) {
        console.error('Error starting recognition:', error)
        isRecordingRef.current = false
        setIsRecording(false)
        
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          showError(language === 'ru' 
            ? 'Доступ к микрофону запрещен. Разрешите доступ в настройках браузера и попробуйте снова.' 
            : 'Microphone access denied. Please allow access in browser settings and try again.')
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
          showError(language === 'ru' 
            ? 'Микрофон не найден. Убедитесь, что микрофон подключен.' 
            : 'Microphone not found. Please ensure microphone is connected.')
        } else {
          showError(language === 'ru' 
            ? `Ошибка при запуске распознавания речи: ${error.message || error}` 
            : `Error starting speech recognition: ${error.message || error}`)
        }
      }
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Функция для определения языка программирования из текста
  const detectProgrammingLanguage = (text: string): string | null => {
    const lowerText = text.toLowerCase()
    const availableLanguages = interviewConfig?.programmingLanguages || ['python', 'javascript', 'java', 'cpp', 'sql']
    
    // Маппинг ключевых слов на языки программирования
    const languageKeywords: Record<string, string[]> = {
      python: ['python', 'питон', 'питон', 'def ', 'import ', 'print(', 'lambda'],
      javascript: ['javascript', 'js', 'node', 'nodejs', 'function ', 'const ', 'let ', 'var ', '=>', 'async'],
      java: ['java', 'джава', 'public class', 'public static', 'system.out', 'string[]', 'int[]'],
      cpp: ['c++', 'cpp', 'c plus plus', '#include', 'std::', 'cout', 'cin', 'vector<'],
      sql: ['sql', 'select', 'from', 'where', 'join', 'database', 'база данных', 'запрос'],
    }
    
    // Сначала проверяем явное указание языка в ответе API
    if (text.includes('language:') || text.includes('язык:')) {
      for (const [lang, keywords] of Object.entries(languageKeywords)) {
        if (availableLanguages.includes(lang)) {
          const langPattern = new RegExp(`(language|язык):\\s*${lang}`, 'i')
          if (langPattern.test(text)) {
            return lang
          }
        }
      }
    }
    
    // Проверяем упоминания языков в тексте
    for (const [lang, keywords] of Object.entries(languageKeywords)) {
      if (availableLanguages.includes(lang)) {
        // Проверяем прямое упоминание языка
        const langNamePattern = new RegExp(`\\b${lang}\\b`, 'i')
        if (langNamePattern.test(lowerText)) {
          return lang
        }
        
        // Проверяем ключевые слова языка
        for (const keyword of keywords) {
          if (lowerText.includes(keyword)) {
            return lang
          }
        }
      }
    }
    
    return null
  }

  const getTimeWarning = (seconds: number) => {
    if (seconds === 0) {
      return { color: 'text-red-500', bgColor: 'bg-red-500', pulse: true, warning: true }
    } else if (seconds <= 300) { // 5 минут
      return { color: 'text-red-400', bgColor: 'bg-red-500', pulse: true, warning: true }
    } else if (seconds <= 600) { // 10 минут
      return { color: 'text-yellow-400', bgColor: 'bg-yellow-500', pulse: false, warning: true }
    } else if (seconds <= 900) { // 15 минут
      return { color: 'text-orange-400', bgColor: 'bg-orange-500', pulse: false, warning: false }
    }
    return { color: 'text-red-400', bgColor: 'bg-red-500', pulse: false, warning: false }
  }

  const handleRunCode = async () => {
    if (timeExpired) {
      alert(language === 'ru' ? 'Время истекло! Действия заблокированы.' : 'Time expired! Actions are blocked.')
      return
    }
    setIsRunning(true)
    setTestsVisible(true)
    
    // Выполнение кода через API
    try {
      const result = await apiClient.post('/api/code/execute', {
        code: code,
        language: selectedLanguage,
      }, false) as CodeExecuteResult
      
      // Генерация тестовых случаев на основе вопроса
      const generatedTests: TestCase[] = [
        { id: 1, input: '[]', expectedOutput: 'null', status: 'pending' },
        { id: 2, input: '[1, 2, 3]', expectedOutput: '3', status: 'pending' },
        { id: 3, input: '[5, 10, 2, 8]', expectedOutput: '10', status: 'pending' },
      ]
      
      // Выполнение тестов
      for (let i = 0; i < generatedTests.length; i++) {
        setTestCases((prev) => {
          const updated = [...prev]
          updated[i] = { ...updated[i], status: 'running' }
          return updated
        })
        
        await new Promise((resolve) => setTimeout(resolve, 800))
        
        // Симуляция проверки теста
        const testCase = generatedTests[i]
        let passed = false
        let actualOutput = ''
        let error = ''
        
        if (result.success) {
          // Здесь должна быть реальная проверка результата
          passed = Math.random() > 0.2
          actualOutput = passed ? testCase.expectedOutput : 'Wrong output'
        } else {
          error = result.error || 'Execution error'
          actualOutput = ''
        }
        
        setTestCases((prev) => {
          const updated = [...prev]
          updated[i] = {
            ...updated[i],
            status: passed ? 'passed' : 'failed',
            actualOutput: actualOutput,
            error: error,
          }
          return updated
        })
      }
    } catch (error) {
      showError('Ошибка при выполнении кода')
      // Показываем ошибку в тестах
      setTestCases([{
        id: 1,
        input: '',
        expectedOutput: '',
        status: 'failed',
        error: 'Failed to execute code',
      }])
    } finally {
      setIsRunning(false)
    }
  }

  const handleSubmitAnswer = async () => {
    if (timeExpired) {
      alert(language === 'ru' ? 'Время истекло! Действия заблокированы.' : 'Time expired! Actions are blocked.')
      return
    }
    setIsLoading(true)
    try {
      // Собираем античит данные
      const timeToAnswer = questionShownAt ? (Date.now() - questionShownAt) / 1000 : null
      const typingMetrics = analyzeTypingPattern()
      const activityDuringAnswer = Array.isArray(activityLog) ? activityLog.filter(
        (event) => questionShownAt && event.timestamp >= questionShownAt
      ) : []
      
      // Получаем ID вопроса из сессии (если есть)
      let questionId: number | null = null
      if (sessionId && currentQuestionId) {
        try {
          const session = await apiClient.get(`/api/sessions/${sessionId}`, false) as Session
          if (session && session.questions && Array.isArray(session.questions)) {
            const lastQuestion = session.questions[session.questions.length - 1]
            if (lastQuestion && lastQuestion.id) {
              questionId = lastQuestion.id
            }
          }
        } catch (error) {
          // Продолжаем без questionId, используем fallback API
        }
      }
      
      // Отправляем ответ с античит данными
      if (questionId) {
        await apiClient.post(`/api/questions/${questionId}/answers`, {
          answer_text: code,
          code_solution: code,
          time_to_answer: timeToAnswer,
          typing_metrics: typingMetrics ? {
            typingSpeed: typingMetrics.typingSpeed,
            averageInterval: typingMetrics.averageInterval,
            variance: typingMetrics.variance,
            averageKeyDuration: typingMetrics.averageKeyDuration
          } : null,
          activity_during_answer: activityDuringAnswer.length > 0 ? activityDuringAnswer : null
        }, false) as AnswerResponse
      } else {
        // Fallback на старый API если нет questionId
        // Формируем тестовые случаи из текущих testCases (если есть)
        const testCasesForEval = testCases.map(tc => ({
          input: tc.input,
          expected_output: tc.expectedOutput,
          actual_output: tc.actualOutput,
          passed: tc.status === 'passed',
        }))
        
        const legacyEvaluation = await apiClient.post('/api/ai/evaluate-answer', {
          question: question,
          answer: code,
          code: code,
          language: selectedLanguage,
          test_cases: testCasesForEval.length > 0 ? testCasesForEval : undefined,
          run_tests: true,
        }, false) as { test_results?: any[] }
        
        if (legacyEvaluation?.test_results && Array.isArray(legacyEvaluation.test_results)) {
          const updatedTests: TestCase[] = legacyEvaluation.test_results.map((tr: any, idx: number) => ({
            id: idx + 1,
            input: tr.input || '',
            expectedOutput: tr.expected_output || '',
            actualOutput: tr.actual_output || '',
            status: tr.passed ? 'passed' : 'failed',
            error: tr.error,
          }))
          if (updatedTests.length > 0) {
            setTestCases(updatedTests)
            setTestsVisible(true)
          }
        }
      }
      
      // Добавляем сообщение от судьи в чат
      const judgeMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'judge',
        content: language === 'ru' 
          ? 'Ответ сохранён. Интервьюер уже подбирает следующий вопрос.'
          : 'Answer saved. The interviewer is preparing the next question.',
        timestamp: new Date(),
      }
      setChatMessages((prev) => [...prev, judgeMessage])
      
      // Сбрасываем состояние для следующего вопроса
      setQuestionShownAt(null)
      resetKeystrokes()
    } catch (error: any) {
      console.error('Error submitting answer:', error)
      const errorMessage = error?.message || error?.toString() || 'Unknown error'
      showError(language === 'ru' ? `Ошибка при оценке ответа: ${errorMessage}` : `Error evaluating answer: ${errorMessage}`)
      alert(language === 'ru' ? `Ошибка при оценке ответа: ${errorMessage}` : `Error evaluating answer: ${errorMessage}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFinishInterview = async () => {
    // Проверяем, не завершается ли уже интервью
    if (isCompletingRef.current) {
      return
    }
    
    if (window.confirm(t.finishConfirm)) {
      isCompletingRef.current = true
      
      try {
        if (!interviewId) {
          alert('Ошибка: ID интервью не найден')
          isCompletingRef.current = false
          return
        }

        // Завершаем сессию интервью через API
        const data = await apiClient.post(`/api/interviews/${interviewId}/complete`)
        
        // Помечаем интервью как завершенное
        if (typeof window !== 'undefined') {
          if (interviewId) {
            // Помечаем интервью как завершенное в localStorage
            localStorage.setItem(`interview_${interviewId}_completed`, 'true')
            sessionStorage.removeItem(`interview_${interviewId}_verified`)
          }
          
          // Очищаем данные интервью
          localStorage.removeItem('interview_start_time')
          localStorage.removeItem('interview_time_remaining')
          sessionStorage.removeItem('interview_config')
        }
        
        // Показываем сообщение
        alert(t.interviewFinished)
        
        // Очищаем флаги приглашения
        if (typeof window !== 'undefined' && interviewId) {
          sessionStorage.removeItem(`interview_${interviewId}_invitation`)
          sessionStorage.removeItem(`interview_${interviewId}_verified`)
        }
        
        // Перенаправляем на страницу истории интервью (replace чтобы нельзя было вернуться назад)
        router.replace('/interviews')
      } catch (error) {
        showError('Ошибка при завершении интервью')
        alert('Ошибка при завершении интервью')
        isCompletingRef.current = false
      }
    }
  }

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isSendingMessage) return
    
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: chatInput,
      timestamp: new Date(),
    }
    
    setChatMessages((prev) => [...prev, userMessage])
    const messageText = chatInput
    setChatInput('')
    setIsSendingMessage(true)
    
    try {
      // Получаем конфигурацию из state или sessionStorage
      let currentConfig = interviewConfig
      if (!currentConfig && typeof window !== 'undefined') {
        const configStr = sessionStorage.getItem('interview_config')
        if (configStr) {
          try {
            currentConfig = JSON.parse(configStr)
            setInterviewConfig(currentConfig)
          } catch (e) {
            console.error('Error parsing interview config:', e)
          }
        }
      }
      
      // Формируем историю разговора для API
      const conversationHistory = chatMessages.map((msg) => ({
        role: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
      }))
      
      // Проверяем, это ответ на вопрос готовности?
      const isReadyAnswer = messageText.toLowerCase().includes('готов') || 
                            messageText.toLowerCase().includes('ready') ||
                            messageText.toLowerCase().includes('да') ||
                            messageText.toLowerCase().includes('yes')
      
      // Если это ответ на вопрос готовности И у нас есть sessionId, отправляем через submit_answer
      if (isReadyAnswer && sessionId) {
        try {
          const session = await apiClient.get(`/api/sessions/${sessionId}`, false) as Session
          if (session && session.questions && Array.isArray(session.questions)) {
            const readyQuestion = session.questions.find((q: any) => q.topic === 'ready_check' || q.order === 0)
            if (readyQuestion && !readyQuestion.answers?.length) {
              // Отправляем ответ на вопрос готовности
              await apiClient.post(`/api/questions/${readyQuestion.id}/answers`, {
                answer_text: messageText,
                time_to_answer: 5.0
              }, false)
              
              // Добавляем сообщение в чат от системы
              const systemMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: language === 'ru' 
                  ? 'Отлично! Начинаем интервью.\n\nПожалуй, начнем с алгоритма. Попробуйте решить следующую задачу:'
                  : 'Great! Let\'s start the interview.\n\nLet\'s begin with an algorithm. Try to solve the following task:',
                timestamp: new Date(),
              }
              
              setChatMessages((prev) => [...prev, systemMessage])
              setIsSendingMessage(false)
              return
            }
          }
        } catch (error) {
          console.error('Error submitting ready answer:', error)
          // Продолжаем с обычным chat API если не получилось
        }
      }
      
      // Отправка сообщения в API для получения ответа от AI-интервьюера
      const data = await apiClient.post('/api/chat/message', {
        message: messageText,
        conversation_history: conversationHistory,
        question_context: question,
        interview_config: currentConfig, // Передаем конфигурацию интервью
      }) as ChatMessageResponse
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || (language === 'ru' ? 'Спасибо за ваш ответ. Продолжайте.' : 'Thank you for your answer. Please continue.'),
        timestamp: new Date(),
      }
      
      setChatMessages((prev) => [...prev, assistantMessage])
      
      // Проверяем, содержит ли сообщение задачу
      const responseText = data.response || ''
      const lowerText = responseText.toLowerCase()
      
      // Автоматически определяем и меняем язык программирования, если он указан
      const detectedLanguage = detectProgrammingLanguage(responseText)
      if (detectedLanguage && currentConfig?.programmingLanguages?.includes(detectedLanguage)) {
        if (detectedLanguage !== selectedLanguage) {
          setSelectedLanguage(detectedLanguage)
          const langName = detectedLanguage === 'python' ? 'Python' : 
                          detectedLanguage === 'javascript' ? 'JavaScript' :
                          detectedLanguage === 'java' ? 'Java' :
                          detectedLanguage === 'cpp' ? 'C++' : 'SQL'
          setLanguageChangedNotification(langName)
          setTimeout(() => setLanguageChangedNotification(null), 3000)
          showInfo(`Язык программирования автоматически изменен на ${langName}`)
        }
      }
      
      // Также проверяем поле language в ответе API (если агент явно указал язык)
      if (data.language && currentConfig?.programmingLanguages?.includes(data.language)) {
        if (data.language !== selectedLanguage) {
          setSelectedLanguage(data.language)
          const langName = data.language === 'python' ? 'Python' : 
                          data.language === 'javascript' ? 'JavaScript' :
                          data.language === 'java' ? 'Java' :
                          data.language === 'cpp' ? 'C++' : 'SQL'
          setLanguageChangedNotification(langName)
          setTimeout(() => setLanguageChangedNotification(null), 3000)
          showInfo(`Язык программирования установлен на ${langName}`)
        }
      }
      
      // Ключевые слова, указывающие на задачу
      const taskKeywords = language === 'ru' 
        ? ['задача', 'реализуйте', 'напишите', 'создайте', 'разработайте', 'функция', 'алгоритм', 'требования']
        : ['task', 'implement', 'write', 'create', 'develop', 'function', 'algorithm', 'requirements']
      
      // Если сообщение содержит ключевые слова задачи или длинное описание с техническими деталями
      const hasTaskKeywords = taskKeywords.some(keyword => lowerText.includes(keyword))
      const isLongTechnical = responseText.length > 150 && (
        lowerText.includes('code') || 
        lowerText.includes('код') ||
        lowerText.includes('function') ||
        lowerText.includes('функция') ||
        lowerText.includes('array') ||
        lowerText.includes('массив')
      )
      
      if (hasTaskKeywords || isLongTechnical) {
        // Извлекаем только текст вопроса (после "**Вопрос" или "**Следующий вопрос:")
        const extractQuestion = (text: string): string => {
          // Ищем паттерн "**Вопрос X:**" или "**Следующий вопрос:**" с последующим текстом
          const questionPatterns = [
            /\*\*.*?[Вопрос|Question].*?\*\*\s*\n\s*(.+?)(?:\n\n|$)/is,
            /\*\*.*?[Вопрос|Question].*?\*\*\s*\n\s*(.+)/is,
          ]
          
          for (const pattern of questionPatterns) {
            const match = text.match(pattern)
            if (match && match[1]) {
              return match[1].trim()
            }
          }
          
          // Если паттерн не найден, но есть "**Вопрос" в тексте, берем все после него
          const questionIndex = text.indexOf('**Вопрос') !== -1 
            ? text.indexOf('**Вопрос')
            : text.indexOf('**Следующий вопрос')
          
          if (questionIndex !== -1) {
            const afterQuestion = text.substring(questionIndex)
            // Находим перенос строки после "**Вопрос X:**"
            const colonIndex = afterQuestion.indexOf(':')
            if (colonIndex !== -1) {
              const afterColon = afterQuestion.substring(colonIndex + 1)
              const newlineIndex = afterColon.indexOf('\n')
              if (newlineIndex !== -1) {
                return afterColon.substring(newlineIndex + 1).trim()
              }
              return afterColon.trim()
            }
          }
          
          // Если ничего не найдено, возвращаем весь текст
          return text
        }
        
        const questionText = extractQuestion(responseText)
        const newQuestionId = Date.now().toString()
        const prevQuestion = question
        const isNewQuestion = prevQuestion !== questionText
        
        setQuestion(questionText)
        setCurrentQuestionId(newQuestionId)
        setQuestionShownAt(Date.now()) // Записываем время показа вопроса
        resetKeystrokes() // Сбрасываем метрики печати для нового вопроса
        
        // Перезапускаем таймер для нового вопроса/задачи
        if (isNewQuestion && interviewConfig?.timer?.enabled && typeof window !== 'undefined') {
          // Определяем тип вопроса: лайвкодинг (есть код) или технический
          const isLiveCoding = isLongTechnical || lowerText.includes('код') || lowerText.includes('code') || 
                               lowerText.includes('реализуйте') || lowerText.includes('implement') ||
                               lowerText.includes('напишите') || lowerText.includes('write') ||
                               lowerText.includes('создайте') || lowerText.includes('create')
          
          const timerMinutes = isLiveCoding 
            ? (interviewConfig.timer.liveCoding_minutes || 30)
            : (interviewConfig.timer.technical_minutes || 10)
          
          const durationSeconds = timerMinutes * 60
          setTimeRemaining(durationSeconds)
          setTimeExpired(false)
          localStorage.setItem('interview_time_remaining', durationSeconds.toString())
          localStorage.setItem('interview_start_time', Date.now().toString())
          localStorage.setItem('current_question_id', newQuestionId)
        }
      }
    } catch (error: any) {
      showError(language === 'ru' ? 'Ошибка при отправке сообщения' : 'Error sending message')
      let errorMessage = language === 'ru' ? 'Произошла ошибка. Попробуйте еще раз.' : 'An error occurred. Please try again.'
      
      if (error.name === 'AbortError') {
        errorMessage = language === 'ru' 
          ? 'Превышено время ожидания ответа. Сервер не отвечает. Проверьте, запущен ли бэкенд.'
          : 'Request timeout. Server is not responding. Please check if backend is running.'
      } else if (error.message) {
        errorMessage = error.message
      }
      
      const errorChatMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: errorMessage,
        timestamp: new Date(),
      }
      setChatMessages((prev) => [...prev, errorChatMessage])
    } finally {
      setIsSendingMessage(false)
    }
  }

  return (
    <div className="h-screen bg-bg-primary flex overflow-hidden">
      <Sidebar language={language} />
      <div className="flex-1 flex flex-col overflow-hidden bg-bg-primary text-text-primary h-full">
        {/* Верхняя панель управления */}
        <div className="bg-bg-secondary border-b border-border-color flex items-center justify-between px-4 py-2 h-12 flex-shrink-0">
          <div className="flex items-center gap-4">
            {/* Таймер - показываем только если включен в конфигурации и мы на клиенте */}
            {isClient && interviewConfig?.timer?.enabled && (
              <div className="flex items-center gap-2">
                {(() => {
                  const timeWarning = getTimeWarning(timeRemaining)
                  return (
                    <>
                      <div 
                        className={`w-3 h-3 ${timeWarning.bgColor} rounded-full ${
                          timeWarning.pulse ? 'animate-pulse' : ''
                        }`}
                      ></div>
                      <span className={`text-sm font-mono font-bold ${timeWarning.color} ${
                        timeWarning.pulse ? 'animate-pulse' : ''
                      }`}>
                        {timeRemaining === 0 
                          ? (language === 'ru' ? '00:00 ВРЕМЯ ИСТЕКЛО' : '00:00 TIME EXPIRED')
                          : formatTime(timeRemaining)
                        }
                      </span>
                      {timeWarning.warning && timeRemaining > 0 && (
                        <span className="text-xs text-red-400 font-semibold">
                          {timeRemaining <= 300 
                            ? (language === 'ru' ? 'КРИТИЧНО!' : 'CRITICAL!')
                            : (language === 'ru' ? 'МАЛО ВРЕМЕНИ' : 'LOW TIME')
                          }
                        </span>
                      )}
                    </>
                  )
                })()}
              </div>
            )}
            
            {/* Кнопки управления */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleRunCode}
                disabled={isRunning || !code || timeExpired}
                className="px-3 py-1.5 bg-text-primary text-bg-primary hover:bg-[#f0f0f0] disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium rounded transition-all duration-200 flex items-center gap-2"
              >
                <Image src="/pic/play.circle.fill.png" alt="" width={16} height={16} className="w-4 h-4" />
                {isRunning ? t.running : t.run}
              </button>
              <button
                onClick={handleSubmitAnswer}
                disabled={isLoading || !code || timeExpired}
                className="px-3 py-1.5 bg-text-primary text-bg-primary hover:bg-[#f0f0f0] disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium rounded transition-all duration-200"
              >
                {isLoading ? t.submitting : t.submit}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Выбор языка интерфейса */}
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as 'ru' | 'en')}
              className="bg-bg-tertiary border border-border-color text-text-primary text-sm px-3 py-1.5 rounded focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
            >
              <option value="ru">RU</option>
              <option value="en">EN</option>
            </select>

            {/* Выбор языка программирования */}
            <div className="relative">
              <select
                value={selectedLanguage}
                onChange={(e) => {
                  setSelectedLanguage(e.target.value)
                  setLanguageChangedNotification(null)
                }}
                disabled={!interviewConfig?.programmingLanguages || interviewConfig.programmingLanguages.length <= 1}
                className="bg-bg-tertiary border border-border-color text-text-primary text-sm px-3 py-1.5 rounded focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all disabled:opacity-50"
              >
              {interviewConfig?.programmingLanguages && interviewConfig.programmingLanguages.length > 0 ? (
                interviewConfig.programmingLanguages.map((lang) => (
                  <option key={lang} value={lang}>{lang}</option>
                ))
              ) : (
                <>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                  <option value="sql">SQL</option>
                </>
              )}
              </select>
              {languageChangedNotification && (
                <div className="absolute -top-8 left-0 bg-text-primary text-bg-primary text-xs px-2 py-1 rounded shadow-lg animate-pulse whitespace-nowrap">
                  {language === 'ru' 
                    ? `Язык автоматически изменен на ${languageChangedNotification}`
                    : `Language automatically changed to ${languageChangedNotification}`
                  }
                </div>
              )}
            </div>

            {/* Sound Toggle */}
            <button
              onClick={() => setIsSoundEnabled(!isSoundEnabled)}
              className={`p-2 rounded transition-all duration-200 ${
                isSoundEnabled ? 'text-text-primary hover:bg-bg-hover' : 'text-text-tertiary hover:bg-bg-hover'
              }`}
              title={language === 'ru' ? 'Включить/выключить звук' : 'Toggle sound'}
            >
              <Image 
                src={isSoundEnabled ? "/pic/speaker.wave.3.fill.png" : "/pic/speaker.slash.fill.png"} 
                alt="Sound" 
                width={20} 
                height={20} 
                className="w-5 h-5"
              />
            </button>

            {/* Кнопка завершения интервью */}
            <button
              onClick={handleFinishInterview}
              className="px-4 py-1.5 bg-[#ff4444] hover:bg-[#ff6666] text-text-primary text-sm font-medium rounded transition-all duration-200"
            >
              {t.finishInterview}
            </button>
          </div>
        </div>

        {/* Основной контент - три панели */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Левая панель - Чат */}
          <div className="w-96 bg-bg-secondary border-r border-border-color flex flex-col overflow-hidden min-h-0">
            {/* Заголовок чата */}
            <div className="p-3 border-b border-border-color">
              <h3 className="text-sm font-semibold text-text-primary tracking-tight">{t.chat}</h3>
            </div>

            {/* Сообщения чата */}
            <div 
              className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
              style={{ 
                scrollBehavior: 'auto',
                overflowAnchor: 'none',
                overscrollBehavior: 'contain',
                height: '100%',
                maxHeight: '100%'
              } as React.CSSProperties}
              onCopy={(e) => e.preventDefault()}
              onPaste={(e) => e.preventDefault()}
              onCut={(e) => e.preventDefault()}
              onContextMenu={(e) => e.preventDefault()}
            >
              {chatMessages.length === 0 && (
                <div className="text-center text-text-tertiary py-8">
                  <p className="text-sm">{t.chatWithInterviewer}</p>
                </div>
              )}
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  onCopy={(e) => e.preventDefault()}
                  onPaste={(e) => e.preventDefault()}
                  onCut={(e) => e.preventDefault()}
                  onContextMenu={(e) => e.preventDefault()}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 select-none border ${
                      message.role === 'user'
                        ? 'bg-text-primary text-bg-primary'
                        : message.role === 'judge'
                        ? 'bg-[#1a1a1a] text-[#AF52DE] border-[#2a2a2a]'
                        : 'bg-bg-tertiary text-text-primary border-border-color'
                    }`}
                    style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
                    onCopy={(e) => e.preventDefault()}
                    onPaste={(e) => e.preventDefault()}
                    onCut={(e) => e.preventDefault()}
                    onContextMenu={(e) => e.preventDefault()}
                    onMouseDown={(e) => {
                      // Блокируем выделение при клике
                      if (e.detail > 1) {
                        e.preventDefault()
                      }
                    }}
                  >
                    <div className="text-xs text-text-tertiary mb-1" style={{ userSelect: 'none' }}>
                      {message.role === 'user' ? 'You' : message.role === 'judge' ? 'Judge' : 'Interviewer'}
                    </div>
                    <div className="text-sm whitespace-pre-wrap" style={{ userSelect: 'none' }}>{message.content}</div>
                  </div>
                </div>
              ))}
              {isSendingMessage && (
                <div className="flex justify-start">
                  <div className="bg-bg-tertiary rounded-lg p-3 border border-border-color">
                    <div className="text-sm text-text-tertiary">{t.loading}</div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Поле ввода */}
            <div className="border-t border-border-color p-3">
              <div className="flex gap-2 items-center">
                <div className="relative flex-1">
                  <input
                    type="text"
                    data-chat-input="true"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    disabled={false}
                    onPaste={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      return false
                    }}
                    onCopy={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      return false
                    }}
                    onCut={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      return false
                    }}
                    onContextMenu={(e) => {
                      e.preventDefault()
                      return false
                    }}
                    placeholder={t.chatPlaceholder}
                    className="w-full bg-bg-tertiary border border-border-color text-text-primary text-sm px-3 pr-8 py-2 rounded focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                  />
                  {chatInput && (
                    <button
                      onClick={() => setChatInput('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-[#666] hover:text-text-primary transition-colors"
                      title={language === 'ru' ? 'Очистить' : 'Clear'}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  )}
                </div>
                <button
                  onClick={handleToggleRecording}
                  className={`w-[38px] h-[38px] flex items-center justify-center rounded transition-all duration-200 ${
                    isRecording ? 'bg-red-500/20 text-red-500 animate-pulse' : 'bg-bg-tertiary text-text-primary hover:bg-bg-hover border border-border-color'
                  }`}
                  title={language === 'ru' ? 'Голосовой ввод' : 'Voice input'}
                >
                  <Image 
                    src="/pic/microphone.circle.fill.png" 
                    alt="Mic" 
                    width={20} 
                    height={20} 
                    className="w-5 h-5"
                  />
                </button>
                <button
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim() || isSendingMessage}
                  className="px-3 py-2 h-[38px] bg-text-primary text-bg-primary hover:bg-[#f0f0f0] disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium rounded transition-all duration-200 flex items-center"
                >
                  {t.send}
                </button>
              </div>
            </div>
          </div>

          {/* Средняя панель - Редактор кода */}
          <div className="flex-1 flex flex-col bg-bg-primary overflow-hidden">
            {/* Вкладки файлов */}
            <div className="bg-bg-secondary border-b border-border-color flex items-center px-2 h-8">
              <div className="flex items-center gap-1">
                <div className="px-3 py-1 bg-bg-primary text-text-primary text-sm border-t border-text-primary border-t-2">
                  solution.{selectedLanguage === 'python' ? 'py' : selectedLanguage === 'javascript' ? 'js' : selectedLanguage === 'java' ? 'java' : selectedLanguage === 'cpp' ? 'cpp' : 'sql'}
                </div>
              </div>
            </div>

            {/* Редактор */}
            <div className="flex-1 relative">
              <MonacoEditor
                height="100%"
                defaultLanguage={selectedLanguage}
                language={selectedLanguage}
                value={code}
                onChange={(value: string | undefined) => setCode(value || '')}
                theme={currentTheme === 'light' ? 'light' : 'vs-dark'}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: 'SF Mono, Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
                  lineNumbers: 'on',
                  roundedSelection: false,
                  scrollBeyondLastLine: false,
                  readOnly: false,
                  cursorStyle: 'line',
                  automaticLayout: true,
                  tabSize: 4,
                  wordWrap: 'on',
                  // Блокировка копирования/вставки
                  readOnlyMessage: { value: '' },
                  contextmenu: false,
                  copyWithSyntaxHighlighting: false,
                }}
                onMount={(editor: any, monaco: any) => {
                  editorRef.current = editor
                  // Блокируем копирование/вставку через клавиатуру
                  if (monaco) {
                    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyC, () => {})
                    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyV, () => {})
                    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyX, () => {})
                    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyA, () => {})
                  }
                  
                  // Блокируем контекстное меню
                  editor.onContextMenu(() => {
                    return false
                  })
                  
                  // Блокируем вставку через события
                  const preventPaste = (e: ClipboardEvent) => {
                    e.preventDefault()
                    e.stopPropagation()
                    return false
                  }
                  
                  const editorElement = editor.getContainerDomNode()
                  if (editorElement) {
                    editorElement.addEventListener('paste', preventPaste, true)
                    editorElement.addEventListener('copy', (e: ClipboardEvent) => {
                      e.preventDefault()
                      e.stopPropagation()
                      return false
                    }, true)
                  }
                }}
              />
            </div>
          </div>

          {/* Правая панель - Описание задачи */}
          <div className="w-80 bg-bg-secondary border-l border-border-color flex flex-col overflow-hidden">
            <div className="p-3 border-b border-border-color">
              <h3 className="text-sm font-semibold text-text-primary">{t.taskDescription}</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
              {question ? (
                <div className="prose prose-invert max-w-none">
                  <div className="text-text-primary whitespace-pre-wrap text-sm leading-relaxed">
                    {question}
                  </div>
                </div>
              ) : (
                <div className="p-4">
                  <div className="mb-4 p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                    <p className="text-sm text-blue-300 font-semibold mb-2">
                      {language === 'ru' ? 'Как начать:' : 'How to Start:'}
                    </p>
                    <ol className="text-xs text-blue-200 space-y-2 list-decimal list-inside">
                      <li>{language === 'ru' ? 'Ответьте "Да, готов" в чате слева ←' : 'Answer "Yes, ready" in chat on the left ←'}</li>
                      <li>{language === 'ru' ? 'Получите задачу от AI-интервьюера' : 'Receive task from AI interviewer'}</li>
                      <li>{language === 'ru' ? 'Напишите код в центральном редакторе' : 'Write code in center editor'}</li>
                      <li>{language === 'ru' ? 'Нажмите "Запуск" для теста' : 'Click "Run" to test'}</li>
                      <li>{language === 'ru' ? 'Нажмите "Отправить", чтобы сохранить ответ' : 'Click "Submit" to save your answer'}</li>
                    </ol>
                  </div>
                  <div className="flex items-center justify-center text-text-tertiary">
                    <p className="text-sm text-center">{t.waitingForQuestion}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
