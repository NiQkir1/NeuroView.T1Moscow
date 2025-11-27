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

export default function EnterInterviewCodePage() {
  const router = useRouter()
  const { showError } = useNotifications()
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    if (auth.isHR()) {
      router.push('/dashboard')
      return
    }
  }, [router])

  const translations = {
    ru: {
      title: 'Пройти собеседование',
      enterCode: 'Введите код доступа к собеседованию',
      codePlaceholder: 'Код доступа',
      submit: 'Начать собеседование',
      invalidCode: 'Неверный код доступа',
      loading: 'Проверка...',
      codeUsed: 'Этот код уже был использован',
    },
    en: {
      title: 'Take Interview',
      enterCode: 'Enter interview access code',
      codePlaceholder: 'Access code',
      submit: 'Start Interview',
      invalidCode: 'Invalid access code',
      loading: 'Verifying...',
      codeUsed: 'This code has already been used',
    },
  }

  const t = translations[language]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (!code.trim()) {
      setError(t.invalidCode)
      return
    }

    setIsLoading(true)

    try {
      // Ищем интервью по коду
      const interview = await apiClient.get(
        `/api/interviews/by-code/${encodeURIComponent(code.trim())}`,
        false
      ) as any

      // Проверяем код
      const verifyData = await apiClient.post(
        `/api/interviews/${interview.id}/verify-code`,
        { code: code.trim() },
        false
      ) as any

      if (verifyData.valid) {
        // Удаляем код доступа (делаем одноразовым)
        await apiClient.post(`/api/interviews/${interview.id}/use-code`, {}, false)

        // Сохраняем информацию о том, что код проверен
        if (typeof window !== 'undefined') {
          sessionStorage.setItem(`interview_${interview.id}_verified`, 'true')
        }
        router.push(`/interview?id=${interview.id}`)
      } else {
        setError(t.invalidCode)
      }
    } catch (error) {
      showError('Ошибка при проверке кода')
      setError('Ошибка при проверке кода')
    } finally {
      setIsLoading(false)
    }
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
        <main className="flex-1 flex items-center justify-center p-12">
          <div className="w-full max-w-md">
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-semibold text-text-primary mb-2 tracking-tight">{t.enterCode}</h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => {
                      setCode(e.target.value.toUpperCase())
                      setError('')
                    }}
                    placeholder={t.codePlaceholder}
                    maxLength={10}
                    className="w-full bg-bg-tertiary border border-border-color text-text-primary px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#AF52DE] focus:border-transparent font-mono text-xl tracking-widest text-center transition-all"
                    autoFocus
                    disabled={isLoading}
                  />
                  {error && (
                    <p className="mt-2 text-sm text-red-500 text-center">{error}</p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !code.trim()}
                  className="w-full px-6 py-3 bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] text-white hover:from-[#8E44AD] hover:to-[#AF52DE] disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all duration-200 font-semibold shadow-md"
                >
                  {isLoading ? t.loading : t.submit}
                </button>
              </form>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

