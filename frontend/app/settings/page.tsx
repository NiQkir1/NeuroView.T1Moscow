'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import Sidebar from '../components/Sidebar'
import MenuButton from '../components/MenuButton'
import Logo from '../components/Logo'
import { useTheme } from '../hooks/useTheme'

export default function SettingsPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState<'ru' | 'en'>('ru')
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [pushNotifications, setPushNotifications] = useState(true)
  const { theme, toggleTheme, mounted } = useTheme()

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }
    setIsLoading(false)
  }, [router])

  const translations = {
    ru: {
      title: 'Настройки',
      general: 'Общие',
      language: 'Язык интерфейса',
      theme: 'Тема',
      notifications: 'Уведомления',
      emailNotifications: 'Email уведомления',
      pushNotifications: 'Push уведомления',
      security: 'Безопасность',
      changePassword: 'Изменить пароль',
      twoFactor: 'Двухфакторная аутентификация',
      save: 'Сохранить',
      saved: 'Настройки сохранены',
    },
    en: {
      title: 'Settings',
      general: 'General',
      language: 'Interface Language',
      theme: 'Theme',
      notifications: 'Notifications',
      emailNotifications: 'Email Notifications',
      pushNotifications: 'Push Notifications',
      security: 'Security',
      changePassword: 'Change Password',
      twoFactor: 'Two-Factor Authentication',
      save: 'Save',
      saved: 'Settings saved',
    },
  }

  const t = translations[language]

  // TODO: Реализовать логику обработки уведомлений
  // - При включении email уведомлений: отправлять настройки на сервер
  // - При включении push уведомлений: запрашивать разрешение на браузерные уведомления
  // - Сохранять настройки в localStorage и на сервере
  // - Обрабатывать ошибки при сохранении
  const handleNotificationChange = (type: 'email' | 'push', enabled: boolean) => {
    if (type === 'email') {
      setEmailNotifications(enabled)
      // TODO: Отправить настройку email уведомлений на сервер
    } else if (type === 'push') {
      setPushNotifications(enabled)
      // TODO: Запросить разрешение на браузерные уведомления, если enabled === true
      // TODO: Отправить настройку push уведомлений на сервер
    }
  }

  const handleSave = () => {
    // Сохранение настроек
    if (typeof window !== 'undefined') {
      localStorage.setItem('app_language', language)
      localStorage.setItem('app_email_notifications', emailNotifications.toString())
      localStorage.setItem('app_push_notifications', pushNotifications.toString())
    }
    alert(t.saved)
  }

  const handleThemeChange = (newTheme: 'dark' | 'light') => {
    toggleTheme(newTheme)
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
          <div className="max-w-7xl mx-auto space-y-8">
            {/* General Settings */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.general}</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">{t.language}</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as 'ru' | 'en')}
                    className="w-full bg-bg-tertiary border border-border-color text-text-primary px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                  >
                    <option value="ru">Русский</option>
                    <option value="en">English</option>
                  </select>
                </div>

                <div>
                  <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">{t.theme}</label>
                  <select
                    value={mounted ? theme : 'dark'}
                    onChange={(e) => handleThemeChange(e.target.value as 'dark' | 'light')}
                    className="w-full bg-bg-tertiary border border-border-color text-text-primary px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                  >
                    <option value="dark">Темная</option>
                    <option value="light">Светлая</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.notifications}</h2>
              
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-text-primary font-medium mb-1">{t.emailNotifications}</div>
                    <div className="text-text-tertiary text-sm">Получать уведомления на email</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={emailNotifications}
                      onChange={(e) => handleNotificationChange('email', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-bg-hover peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[#AF52DE]/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-[#AF52DE] peer-checked:to-[#8E44AD]"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-text-primary font-medium mb-1">{t.pushNotifications}</div>
                    <div className="text-text-tertiary text-sm">Получать push уведомления</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={pushNotifications}
                      onChange={(e) => handleNotificationChange('push', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-bg-hover peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[#AF52DE]/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-[#AF52DE] peer-checked:to-[#8E44AD]"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* Security */}
            <div className="bg-bg-secondary rounded-lg border border-border-color p-8">
              <h2 className="text-xl font-semibold text-text-primary mb-8 tracking-tight">{t.security}</h2>
              
              <div className="space-y-3">
                <button className="w-full px-6 py-2.5 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg transition-all duration-200 text-left font-medium">
                  {t.changePassword}
                </button>
                <button className="w-full px-6 py-2.5 bg-bg-tertiary hover:bg-bg-quaternary text-text-primary border border-border-color rounded-lg transition-all duration-200 text-left font-medium">
                  {t.twoFactor}
                </button>
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                className="px-8 py-3 bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] text-white rounded-lg transition-all duration-200 font-semibold hover:from-[#8E44AD] hover:to-[#AF52DE] shadow-md"
              >
                {t.save}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

