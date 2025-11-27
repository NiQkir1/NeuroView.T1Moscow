'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { auth } from '@/lib/auth'
import Sidebar from '../components/Sidebar'
import Logo from '../components/Logo'
import MenuButton from '../components/MenuButton'
import DashboardCard from '../components/DashboardCard'
import LoadingSpinner from '../components/LoadingSpinner'

export default function DashboardPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const isHR = auth.isHR()

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    const currentUser = auth.getUser()
    // Перенаправляем админа на страницу админки
    if (currentUser?.role === 'admin') {
      router.push('/admin')
      return
    }
    setIsLoading(false)
  }, [router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary flex">
      <Sidebar language="ru" />
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="sticky top-0 bg-bg-secondary border-b border-border-color px-12 py-6 flex items-center justify-between relative z-[55] backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <MenuButton />
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">Главная</h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {/* Welcome Section */}
            <div className="text-center mb-16">
              <h2 className="text-5xl font-semibold text-text-primary mb-3 tracking-tight">
                Добро пожаловать в NeuroView
              </h2>
              <p className="text-text-tertiary text-sm font-normal tracking-wide">
                {isHR ? 'Создайте новое интервью или просмотрите проведенные' : 'Выберите режим работы'}
              </p>
            </div>

            {/* Mode Selection Cards */}
            <div className="grid md:grid-cols-2 gap-8">
              {isHR ? (
                <>
                  <DashboardCard
                    href="/hr/create-interview"
                    title="Создать интервью"
                    description="Настройте параметры интервью: позицию, уровень, количество вопросов и темы."
                    actionText="Создать"
                    variant="hr"
                    icon={
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                      </svg>
                    }
                  />
                  <DashboardCard
                    href="/hr/interviews"
                    title="Проведенные интервью"
                    description="Просмотрите отчеты о проведенных интервью с оценками и статистикой."
                    actionText="Просмотреть"
                    variant="hr"
                    icon={
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                        />
                      </svg>
                    }
                  />
                  <DashboardCard
                    href="/hr/candidates"
                    title="Поиск кандидатов"
                    description="Найдите подходящих кандидатов по навыкам, языкам программирования, роли и уровню."
                    actionText="Найти"
                    variant="hr"
                    icon={
                      <Image src="/pic/magnifyingglass.circle.fill.png" alt="" width={32} height={32} className="w-8 h-8" />
                    }
                  />
                </>
              ) : (
                <>
                  <DashboardCard
                    href="/training/config"
                    title="Тренировочное интервью"
                    description="Практикуйтесь в безопасной среде. Настройте параметры и получите обратную связь без ограничений."
                    actionText="Начать тренировку"
                    variant="candidate"
                    icon={
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
                        />
                      </svg>
                    }
                  />
                  <DashboardCard
                    href="/interview/enter-code"
                    title="Пройти собеседование"
                    description="Начните настоящее собеседование с AI-интервьюером. Введите код доступа для начала."
                    actionText="Ввести код"
                    variant="candidate"
                    icon={
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                        />
                      </svg>
                    }
                  />
                </>
              )}
            </div>

            {/* Info Section */}
            <div className="mt-16 bg-bg-secondary rounded-lg p-8 border border-border-color">
              <h3 className="text-xl font-semibold text-text-primary mb-6 tracking-tight">
                О платформе
              </h3>
              <div className="grid md:grid-cols-3 gap-6 text-text-tertiary text-sm">
                <div>
                  <div className="text-text-primary font-medium mb-2">AI-интервьюер</div>
                  <p>Умный собеседующий на базе GPT-4 и Claude</p>
                </div>
                <div>
                  <div className="text-text-primary font-medium mb-2">Безопасность</div>
                  <p>Ваши данные защищены и конфиденциальны</p>
                </div>
                <div>
                  <div className="text-text-primary font-medium mb-2">Обратная связь</div>
                  <p>Детальная оценка и рекомендации по улучшению</p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
