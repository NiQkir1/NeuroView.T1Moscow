'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import Image from 'next/image'
import { auth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import Sidebar from '../components/Sidebar'
import LoadingSpinner from '../components/LoadingSpinner'
import { useNotifications } from '../hooks/useNotifications'
import { useTheme } from '../hooks/useTheme'

// Динамический импорт Monaco Editor
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
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

interface CodeExecutionResult {
  success: boolean
  error?: string
  output?: string
}

interface EvaluationResult {
  score: number
  feedback?: string
}

interface ChatResponse {
  response: string
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
    finishTraining: 'Завершить тренировку',
    finishConfirm: 'Вы уверены, что хотите завершить тренировку?',
    trainingFinished: 'Тренировка завершена',
    back: 'Назад',
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
    finishTraining: 'Finish Training',
    finishConfirm: 'Are you sure you want to finish the training?',
    trainingFinished: 'Training finished',
    back: 'Back',
  },
}

export default function TrainingPage() {
  const router = useRouter()
  const { showError, showWarning, showInfo } = useNotifications()
  const { theme: currentTheme } = useTheme()
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const t = translations[language]
  const [isTrainingFinished, setIsTrainingFinished] = useState(false)
  
  const [question, setQuestion] = useState<string>('')
  const [currentQuestionId, setCurrentQuestionId] = useState<string>('') // ID текущего вопроса для отслеживания смены
  const [code, setCode] = useState<string>('// Start writing code here\n\ndef solution():\n    pass\n')
  const [isLoading, setIsLoading] = useState(false)
  const [evaluation, setEvaluation] = useState<any>(null)
  
  // Восстанавливаем таймер из localStorage или устанавливаем начальное значение
  const getInitialTime = () => {
    if (typeof window !== 'undefined') {
      const savedStartTime = localStorage.getItem('training_start_time')
      const savedTimeRemaining = localStorage.getItem('training_time_remaining')

      if (savedStartTime && savedTimeRemaining) {
        const startTime = parseInt(savedStartTime)
        const savedRemaining = parseInt(savedTimeRemaining)
        const elapsed = Math.floor((Date.now() - startTime) / 1000)
        const remaining = Math.max(0, savedRemaining - elapsed)
        return remaining
      }
      
      // Если таймер еще не запущен, проверяем конфигурацию
      const configStr = sessionStorage.getItem('training_config')
      if (configStr) {
        try {
          const config = JSON.parse(configStr)
          if (config.timer?.enabled) {
            // Используем таймер для технических вопросов по умолчанию
            const minutes = config.timer?.technical_minutes || config.timer?.minutes || 10
            return minutes * 60
          }
        } catch (e) {
          // Ошибка парсинга конфига
        }
      }
    }
    return 600 // 10 минут по умолчанию
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
  
  // Chat state - инициализируем пустым массивом для избежания ошибок гидратации
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<any>(null)
  
  // STT & TTS state
  const [isRecording, setIsRecording] = useState(false)
  const [isSoundEnabled, setIsSoundEnabled] = useState(true)
  const recognitionRef = useRef<any>(null)
  const synthRef = useRef<SpeechSynthesis | null>(null)
  
  // Устанавливаем флаг isClient и добавляем начальное сообщение только на клиенте
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    setIsClient(true)
    // Добавляем начальное сообщение только один раз на клиенте
    if (chatMessages.length === 0) {
      setChatMessages([
        {
          id: 'initial',
          role: 'assistant',
          content: language === 'ru' 
            ? 'Здравствуйте! Я ваш интервьюер для тренировки. Готовы ли вы начать собеседование?'
            : 'Hello! I am your training interviewer. Are you ready to start the interview?',
          timestamp: new Date(),
        }
      ])
    }
  }, [])

  // Блокировка возврата через кнопку "Назад" после завершения тренировки
  useEffect(() => {
    if (typeof window === 'undefined') return

    // Добавляем запись в историю, чтобы можно было перехватить возврат
    window.history.pushState(null, '', window.location.href)

    // Обработчик попытки вернуться назад
    const handlePopState = (event: PopStateEvent) => {
      if (isTrainingFinished) {
        // Если тренировка завершена, блокируем возврат
        window.history.pushState(null, '', window.location.href)
        alert(language === 'ru' 
          ? 'Тренировка уже завершена. Вы не можете вернуться к ней.' 
          : 'Training is already finished. You cannot return to it.')
        router.replace('/dashboard')
      } else {
        // Если тренировка не завершена, но пользователь пытается уйти - предупреждаем
        const confirmed = window.confirm(
          language === 'ru' 
            ? 'Вы уверены, что хотите покинуть тренировку? Прогресс может быть потерян.' 
            : 'Are you sure you want to leave the training? Progress may be lost.'
        )
        if (!confirmed) {
          // Отменяем навигацию
          window.history.pushState(null, '', window.location.href)
        } else {
          // Разрешаем уход
          router.replace('/dashboard')
        }
      }
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [isTrainingFinished, router, language])

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    
    if (auth.isHR()) {
      router.push('/dashboard')
      return
    }

    // Проверяем, завершена ли тренировка
    if (typeof window !== 'undefined') {
      const trainingFinished = localStorage.getItem('training_finished')
      if (trainingFinished === 'true') {
        // Если тренировка завершена, сразу редиректим на главную
        router.replace('/dashboard')
        return
      }
    }

    // Устанавливаем флаг, что мы на клиенте
    setIsClient(true)
    
    // Загружаем конфигурацию и устанавливаем язык программирования
    if (typeof window !== 'undefined') {
      const configStr = sessionStorage.getItem('training_config')
      if (configStr) {
        try {
          const config = JSON.parse(configStr)
          // Устанавливаем первый выбранный язык программирования
          if (config.programmingLanguages && config.programmingLanguages.length > 0) {
            setSelectedLanguage(config.programmingLanguages[0])
          }
        } catch (e) {
          showError('Ошибка при загрузке конфигурации тренировки')
        }
      }
    }
    
    // Восстанавливаем таймер из localStorage только если тренировка уже начата
    // Таймер запускается только при получении первого вопроса/задачи
    if (typeof window !== 'undefined') {
      const savedStartTime = localStorage.getItem('training_start_time')
      const savedTimeRemaining = localStorage.getItem('training_time_remaining')
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
  }, [router])

  // Обновляем начальное сообщение при смене языка
  useEffect(() => {
    if (isClient && chatMessages.length === 1 && chatMessages[0].id === 'initial') {
      setChatMessages([{
        id: 'initial',
        role: 'assistant',
        content: language === 'ru' 
          ? 'Здравствуйте! Я ваш интервьюер для тренировки. Готовы ли вы начать собеседование?'
          : 'Hello! I am your training interviewer. Are you ready to start the interview?',
        timestamp: new Date(),
      }])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, isClient])

  // Таймер с сохранением в localStorage
  useEffect(() => {
    // Убеждаемся, что start_time установлен при первом запуске таймера
    if (timeRemaining > 0 && !timeExpired && typeof window !== 'undefined') {
      const savedStartTime = localStorage.getItem('training_start_time')
      if (!savedStartTime) {
        // Если start_time не установлен, устанавливаем его сейчас
        localStorage.setItem('training_start_time', Date.now().toString())
      }
    }
    
    if (timeRemaining > 0 && !timeExpired) {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => {
          const newTime = Math.max(0, prev - 1)
          // Сохраняем время в localStorage
          if (typeof window !== 'undefined') {
            localStorage.setItem('training_time_remaining', newTime.toString())
            // Обновляем start_time только если его нет
            const startTime = localStorage.getItem('training_start_time')
            if (!startTime) {
              localStorage.setItem('training_start_time', Date.now().toString())
            }
          }
          
          // Если время истекло
          if (newTime === 0) {
            setTimeExpired(true)
          }
          
          return newTime
        })
      }, 1000)
      return () => clearInterval(timer)
    } else if (timeRemaining === 0 && !timeExpired) {
      setTimeExpired(true)
    }
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
          setIsRecording(false)
        }

        recognition.onend = () => {
          // Don't auto-restart if manually stopped
        }

        recognitionRef.current = recognition
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

  const handleToggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
    } else {
      recognitionRef.current?.start()
      setIsRecording(true)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const getTimeWarning = (seconds: number) => {
    if (seconds === 0) {
      return { color: 'text-red-500', bgColor: 'bg-red-500', pulse: true, warning: true }
    } else if (seconds <= 300) {
      return { color: 'text-red-400', bgColor: 'bg-red-500', pulse: true, warning: true }
    } else if (seconds <= 600) {
      return { color: 'text-yellow-400', bgColor: 'bg-yellow-500', pulse: false, warning: true }
    } else if (seconds <= 900) {
      return { color: 'text-orange-400', bgColor: 'bg-orange-500', pulse: false, warning: false }
    }
    return { color: 'text-gray-400', bgColor: 'bg-gray-500', pulse: false, warning: false }
  }

  const handleRunCode = async () => {
    setIsRunning(true)
    setTestsVisible(true)
    
    try {
      const result = await apiClient.post('/api/code/execute', {
        code: code,
        language: selectedLanguage,
      }, false) as CodeExecutionResult
      
      // Генерация тестовых случаев
      const generatedTests: TestCase[] = [
        { id: 1, input: '[]', expectedOutput: 'null', status: 'pending' },
        { id: 2, input: '[1, 2, 3]', expectedOutput: '3', status: 'pending' },
        { id: 3, input: '[5, 10, 2, 8]', expectedOutput: '10', status: 'pending' },
      ]
      
      setTestCases(generatedTests)
      
      // Выполнение тестов
      for (let i = 0; i < generatedTests.length; i++) {
        setTestCases((prev) => {
          const updated = [...prev]
          updated[i] = { ...updated[i], status: 'running' }
          return updated
        })
        
        await new Promise((resolve) => setTimeout(resolve, 800))
        
        const testCase = generatedTests[i]
        let passed = false
        let actualOutput = ''
        let error = ''
        
        if (result.success) {
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
    setIsLoading(true)
    try {
      // Сначала попробуем запустить код и проверить тесты
      let testResults: TestCase[] = []
      let codeExecutionError: string | null = null
      
      // Запускаем код если он не пустой
      if (code.trim() && code.trim().length > 20) {
        try {
          const execResult = await apiClient.post('/api/code/execute', {
            code: code,
            language: selectedLanguage,
          }, false) as CodeExecutionResult
          
          if (!execResult.success && execResult.error) {
            codeExecutionError = execResult.error
          }
        } catch (execError: any) {
          codeExecutionError = execError?.message || 'Ошибка выполнения кода'
        }
      }
      
      // Формируем тестовые случаи из текущих testCases (если есть)
      const testCasesForEval = testCases.map(tc => ({
        input: tc.input,
        expected_output: tc.expectedOutput,
        actual_output: tc.actualOutput,
        passed: tc.status === 'passed',
      }))
      
      // Отправляем код на оценку с дополнительной информацией
      const data = await apiClient.post('/api/ai/evaluate-answer', {
        question: question,
        answer: code,
        code: code,
        language: selectedLanguage,
        test_cases: testCasesForEval.length > 0 ? testCasesForEval : undefined,
        run_tests: true,
      }, false) as EvaluationResult & {
        test_results?: any[]
        tests_passed?: number
        tests_total?: number
      }
      
      setEvaluation(data)
      
      // Формируем сообщение с деталями оценки
      let feedbackMessage = ''
      if (data.score !== undefined) {
        feedbackMessage = language === 'ru' 
          ? `Оценка: ${data.score}/100`
          : `Score: ${data.score}/100`
        
        // Добавляем информацию о тестах если есть
        if (data.tests_passed !== undefined && data.tests_total !== undefined && data.tests_total > 0) {
          feedbackMessage += language === 'ru'
            ? `. Пройдено тестов: ${data.tests_passed}/${data.tests_total}`
            : `. Tests passed: ${data.tests_passed}/${data.tests_total}`
        }
        
        // Добавляем feedback если есть
        if (data.feedback) {
          feedbackMessage += `. ${data.feedback}`
        }
        
        // Добавляем информацию об ошибке выполнения
        if (codeExecutionError) {
          feedbackMessage += language === 'ru'
            ? ` (Ошибка выполнения: ${codeExecutionError})`
            : ` (Execution error: ${codeExecutionError})`
        }
      }
      
      // Добавляем сообщение от судьи в чат
      const judgeMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'judge',
        content: feedbackMessage || (language === 'ru' ? 'Код оценен.' : 'Code evaluated.'),
        timestamp: new Date(),
      }
      setChatMessages((prev) => [...prev, judgeMessage])
      
      // Обновляем результаты тестов если получены от сервера
      if (data.test_results && Array.isArray(data.test_results)) {
        const updatedTests: TestCase[] = data.test_results.map((tr: any, idx: number) => ({
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
    } catch (error: any) {
      const errorMessage = error?.message || error?.toString() || 'Unknown error'
      showError(language === 'ru' ? `Ошибка при оценке ответа: ${errorMessage}` : `Error evaluating answer: ${errorMessage}`)
      alert(language === 'ru' ? `Ошибка при оценке ответа: ${errorMessage}` : `Error evaluating answer: ${errorMessage}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFinishTraining = () => {
    if (window.confirm(t.finishConfirm)) {
      // Очищаем данные тренировки
      if (typeof window !== 'undefined') {
        localStorage.removeItem('training_start_time')
        localStorage.removeItem('training_time_remaining')
        sessionStorage.removeItem('training_config')
        // Помечаем тренировку как завершенную в localStorage
        localStorage.setItem('training_finished', 'true')
      }
      
      // Помечаем тренировку как завершенную
      setIsTrainingFinished(true)
      
      // Показываем сообщение перед редиректом
      alert(t.trainingFinished)
      
      // Сразу делаем replace чтобы нельзя было вернуться назад
      // Используем window.location для гарантированного редиректа
      if (typeof window !== 'undefined') {
        window.location.href = '/dashboard'
      } else {
        router.replace('/dashboard')
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
    setChatInput('')
    setIsSendingMessage(true)
    
    try {
      const conversationHistory = chatMessages.map((msg) => ({
        role: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
      }))
      
      // Получаем конфигурацию из sessionStorage
      let trainingConfig = null
      if (typeof window !== 'undefined') {
        const configStr = sessionStorage.getItem('training_config')
        if (configStr) {
          try {
            trainingConfig = JSON.parse(configStr)
          } catch (e) {
            showError('Ошибка при загрузке конфигурации тренировки')
          }
        }
      }
      
      const data = await apiClient.post('/api/chat/message', {
        message: chatInput,
        conversation_history: conversationHistory,
        question_context: question,
        interview_config: trainingConfig,
      }, false) as ChatResponse
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || (language === 'ru' ? 'Спасибо за ваш ответ. Продолжайте.' : 'Thank you for your answer. Please continue.'),
        timestamp: new Date(),
      }
      
      setChatMessages((prev) => [...prev, assistantMessage])
      
      // Извлекаем вопрос из ответа, если он содержит маркеры вопросов
      const responseText = data.response || ''
      const lowerText = responseText.toLowerCase()
      
      // Функция для извлечения вопроса из ответа
      const extractQuestion = (text: string): string | null => {
        // Проверяем наличие маркеров вопросов
        if (text.includes('**Первый вопрос:**') || text.includes('**Следующий вопрос:**')) {
          // Извлекаем текст после маркера
          const marker = text.includes('**Первый вопрос:**') ? '**Первый вопрос:**' : '**Следующий вопрос:**'
          const parts = text.split(marker)
          if (parts.length > 1) {
            const questionText = parts[1].trim()
            // Убираем лишние символы в начале/конце
            return questionText.split('\n\n')[0].trim()
          }
        }
        return null
      }
      
      // Извлекаем вопрос из ответа
      const extractedQuestion = extractQuestion(responseText)
      
      // Проверяем, содержит ли сообщение задачу или вопрос
      const taskKeywords = language === 'ru' 
        ? ['задача', 'реализуйте', 'напишите', 'создайте', 'разработайте', 'функция', 'алгоритм', 'требования']
        : ['task', 'implement', 'write', 'create', 'develop', 'function', 'algorithm', 'requirements']
      
      const hasTaskKeywords = taskKeywords.some(keyword => lowerText.includes(keyword))
      const isLongTechnical = responseText.length > 150 && (
        lowerText.includes('code') || 
        lowerText.includes('код') ||
        lowerText.includes('function') ||
        lowerText.includes('функция') ||
        lowerText.includes('array') ||
        lowerText.includes('массив')
      )
      
      // Устанавливаем вопрос, если:
      // 1. Извлечен вопрос из ответа (есть маркеры)
      // 2. ИЛИ есть ключевые слова задачи
      // 3. ИЛИ это длинный технический текст
      if (extractedQuestion || hasTaskKeywords || isLongTechnical) {
        const newQuestionId = Date.now().toString()
        const prevQuestion = question
        // Используем извлеченный вопрос, если он есть, иначе весь ответ
        const questionToSet = extractedQuestion || responseText
        const isNewQuestion = prevQuestion !== questionToSet
        
        setQuestion(questionToSet)
        setCurrentQuestionId(newQuestionId)
        
        // Запускаем/перезапускаем таймер для нового вопроса/задачи
        if (isNewQuestion && typeof window !== 'undefined') {
          const configStr = sessionStorage.getItem('training_config')
          if (configStr) {
            try {
              const config = JSON.parse(configStr)
              if (config.timer?.enabled) {
                // Определяем, это технический вопрос или лайвкодинг
                // По умолчанию используем technical_minutes
                let minutes = config.timer?.technical_minutes || 10
                
                // Если в тексте есть упоминание кода/реализации, используем liveCoding_minutes
                if (lowerText.includes('реализ') || lowerText.includes('напиш') || 
                    lowerText.includes('implement') || lowerText.includes('write') ||
                    lowerText.includes('код') || lowerText.includes('code')) {
                  minutes = config.timer?.liveCoding_minutes || 30
                }
                
                const durationSeconds = minutes * 60
                setTimeRemaining(durationSeconds)
                setTimeExpired(false)
                // Запускаем таймер - устанавливаем start_time только сейчас
                localStorage.setItem('training_time_remaining', durationSeconds.toString())
                localStorage.setItem('training_start_time', Date.now().toString())
                localStorage.setItem('current_question_id', newQuestionId)
              }
            } catch (e) {
              showError('Ошибка при загрузке конфигурации тренировки')
            }
          }
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
            {isClient && (() => {
              const configStr = typeof window !== 'undefined' ? sessionStorage.getItem('training_config') : null
              let timerEnabled = true
              if (configStr) {
                try {
                  const config = JSON.parse(configStr)
                  timerEnabled = config.timer?.enabled !== false
                } catch (e) {
                  // Используем значение по умолчанию
                }
              }
              return timerEnabled ? (
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
                              ? (language === 'ru' ? '⚠ КРИТИЧНО!' : '⚠ CRITICAL!')
                              : (language === 'ru' ? '⚠ МАЛО ВРЕМЕНИ' : '⚠ LOW TIME')
                            }
                          </span>
                        )}
                      </>
                    )
                  })()}
                </div>
              ) : null
            })()}
            
            {/* Кнопки управления */}
            <div className="flex items-center gap-2">
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
              
              <button
                onClick={handleRunCode}
                disabled={isRunning || !code}
                className="px-3 py-1.5 bg-text-primary text-bg-primary hover:bg-[#f0f0f0] disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium rounded transition-all duration-200"
              >
                {isRunning ? t.running : t.run}
              </button>
              <button
                onClick={handleSubmitAnswer}
                disabled={isLoading || !code}
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
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="bg-bg-tertiary border border-border-color text-text-primary text-sm px-3 py-1.5 rounded focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
              <option value="sql">SQL</option>
            </select>

            {/* Кнопка завершения тренировки */}
            <button
              onClick={handleFinishTraining}
              className="px-4 py-1.5 bg-[#ff4444] hover:bg-[#ff6666] text-text-primary text-sm font-medium rounded transition-all duration-200"
            >
              {t.finishTraining}
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
            {isClient && chatMessages.length === 0 && (
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
                  className={`max-w-[80%] rounded-lg p-3 select-none ${
                    message.role === 'user'
                      ? 'bg-text-primary text-bg-primary'
                      : message.role === 'judge'
                      ? 'bg-[#1a1a1a] text-[#AF52DE] border border-[#2a2a2a]'
                      : 'bg-bg-tertiary text-text-primary border border-border-color'
                  }`}
                  style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
                  onCopy={(e) => e.preventDefault()}
                  onPaste={(e) => e.preventDefault()}
                  onCut={(e) => e.preventDefault()}
                  onContextMenu={(e) => e.preventDefault()}
                  onMouseDown={(e) => {
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
              <div className="px-3 py-1 bg-bg-tertiary text-text-primary text-sm border-t border-text-primary border-t-2">
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
                contextmenu: false,
                copyWithSyntaxHighlighting: false,
              }}
              onMount={(editor: any, monaco: any) => {
                editorRef.current = editor
                if (monaco) {
                  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyC, () => {})
                  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyV, () => {})
                  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyX, () => {})
                  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyA, () => {})
                }
                
                editor.onContextMenu(() => {
                  return false
                })
                
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
            <h3 className="text-sm font-semibold text-text-primary tracking-tight">{t.taskDescription}</h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            {question ? (
              <div className="prose prose-invert max-w-none">
                <div className="text-text-primary whitespace-pre-wrap text-sm leading-relaxed">
                  {question}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-text-tertiary">
                <p className="text-sm text-center">{t.waitingForQuestion}</p>
              </div>
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}
