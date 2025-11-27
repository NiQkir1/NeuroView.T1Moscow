'use client'

import { useMemo } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { auth } from '@/lib/auth'
import { useTheme } from '../hooks/useTheme'
import { useSidebar } from './SidebarContext'

interface SidebarProps {
  language?: 'ru' | 'en'
}

export default function Sidebar({ language = 'ru' }: SidebarProps) {
  const { isOpen, closeSidebar } = useSidebar()
  const pathname = usePathname()
  const router = useRouter()
  const isHR = auth.isHR()
  const isAdmin = auth.isAdmin()
  const { toggle } = useTheme()

  const translations = {
    ru: {
      profile: 'Профиль',
      myInterviews: 'Мои интервью',
      interviews: 'Проведенные интервью',
      searchCandidates: 'Поиск кандидатов',
      settings: 'Настройки',
      logout: 'Выйти',
      dashboard: 'Главная',
      admin: 'Админ-панель',
    },
    en: {
      profile: 'Profile',
      myInterviews: 'My Interviews',
      interviews: 'Conducted Interviews',
      searchCandidates: 'Search Candidates',
      settings: 'Settings',
      logout: 'Logout',
      dashboard: 'Dashboard',
      admin: 'Admin Panel',
    },
  }

  const t = translations[language]

  // Разные меню для админа, HR и обычных пользователей
  // Мемоизируем menuItems для оптимизации производительности
  const menuItems = useMemo(() => {
    if (isAdmin) {
      return [
        { href: '/admin', label: t.admin, icon: 'admin' },
        { href: '/profile', label: t.profile, icon: 'user' },
        { href: '/settings', label: t.settings, icon: 'settings' },
      ]
    }
    if (isHR) {
      return [
        { href: '/dashboard', label: t.dashboard, icon: 'home' },
        { href: '/profile', label: t.profile, icon: 'user' },
        { href: '/hr/candidates', label: t.searchCandidates, icon: 'search' },
        { href: '/hr/interviews', label: t.interviews, icon: 'briefcase' },
        { href: '/hr/test-tasks', label: 'Тестовые задания', icon: 'briefcase' }, // v3.0.0
        { href: '/settings', label: t.settings, icon: 'settings' },
      ]
    }
    return [
      { href: '/dashboard', label: t.dashboard, icon: 'home' },
      { href: '/profile', label: t.profile, icon: 'user' },
      { href: '/interviews/invitations', label: 'Мои собеседования', icon: 'briefcase' },
      { href: '/interviews', label: 'Отчеты по интервью', icon: 'briefcase' },
      { href: '/test-tasks', label: 'Тестовые задания', icon: 'briefcase' }, // v3.0.0
      { href: '/settings', label: t.settings, icon: 'settings' },
    ]
  }, [isAdmin, isHR, t])

  const handleLogout = () => {
    auth.logout()
    router.push('/login')
  }

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard' || pathname === '/'
    }
    // Точное совпадение или путь начинается с href + '/', но не с более длинного пути
    if (pathname === href) {
      return true
    }
    // Для путей, которые могут конфликтовать (например, /interviews и /interviews/invitations),
    // проверяем более точно
    if (href === '/interviews') {
      // /interviews активен только если это точно /interviews, а не /interviews/invitations
      return pathname === '/interviews'
    }
    if (href === '/interviews/invitations') {
      return pathname === '/interviews/invitations' || pathname?.startsWith('/interviews/invitations/')
    }
    // Для остальных путей используем стандартную проверку
    return pathname?.startsWith(href + '/')
  }

  return (
    <>
      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-screen w-72 bg-bg-secondary border-r border-border-color flex flex-col backdrop-blur-xl z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
      {/* Close Button */}
      <div className="p-8 border-b border-border-color">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
            NeuroView
          </h1>
          <button
            onClick={closeSidebar}
            className="lg:hidden p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
            aria-label="Close menu"
          >
            <svg
              className="w-6 h-6 text-text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-6 space-y-1">
        {menuItems.map((item) => {
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={closeSidebar}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border border-transparent transition-colors duration-200 ${
                active
                  ? 'text-[#AF52DE] font-medium'
                  : 'text-text-tertiary hover:text-[#AF52DE] hover:bg-bg-tertiary hover:border-[#AF52DE]/30'
              }`}
              aria-current={active ? 'page' : undefined}
            >
              {item.icon === 'home' && (
                <Image src="/pic/house.circle.fill.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
              )}
              {item.icon === 'user' && (
                <Image src="/pic/profile.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
              )}
              {item.icon === 'briefcase' && (
                <>
                  {(item.href === '/hr/test-tasks' || item.href === '/test-tasks') ? (
                    <Image src="/pic/square.and.pencil.circle.fill.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
                  ) : (
                    <Image src="/pic/report.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
                  )}
                </>
              )}
              {item.icon === 'book' && (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
              )}
              {item.icon === 'settings' && (
                <Image src="/pic/settings.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
              )}
              {item.icon === 'admin' && (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              )}
              {item.icon === 'search' && (
                <Image src="/pic/magnifyingglass.circle.fill.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
              )}
              <span className="text-sm tracking-tight">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Theme Toggle & Logout */}
      <div className="p-6 border-t border-border-color space-y-2">
        <button
          onClick={toggle}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-all duration-200"
          aria-label="Переключить тему"
        >
          <Image src="/pic/lightbulb.circle.fill.png" alt="" width={16} height={16} className="w-4 h-4" aria-hidden="true" />
          <span className="text-sm tracking-tight">Тема</span>
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-all duration-200"
          aria-label="Выйти из системы"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
          </svg>
          <span className="text-sm tracking-tight">{t.logout}</span>
        </button>
      </div>
    </div>
    </>
  )
}

