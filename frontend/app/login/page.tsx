'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import Logo from '@/app/components/Logo'

export default function LoginPage() {
  const router = useRouter()
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Функция для очистки всех полей
  const clearAllFields = () => {
    setUsername('')
    setPassword('')
    setFirstName('')
    setLastName('')
    setEmail('')
    setError('')
  }

  // Очистка полей при переключении режима
  const handleModeSwitch = (newIsLogin: boolean) => {
    setIsLogin(newIsLogin)
    clearAllFields()
  }

  useEffect(() => {
    // Если уже авторизован, перенаправить на соответствующую страницу
    if (auth.isAuthenticated()) {
      const user = auth.getUser()
      if (user?.role === 'admin') {
        router.push('/admin')
      } else {
        router.push('/dashboard')
      }
    }
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      let result
      if (isLogin) {
        result = await auth.login(username, password)
        if (!result.success) {
          setError(result.error || 'Неверное имя пользователя или пароль')
          setIsLoading(false)
          return
        }
      } else {
        // Формируем полное имя из имени и фамилии
        const fullName = `${firstName} ${lastName}`.trim() || undefined
        result = await auth.register(username, password, email || undefined, fullName)
        if (!result.success) {
          // Улучшенная обработка ошибок
          let errorMessage = 'Ошибка регистрации'
          if (result.error) {
            if (result.error.includes('Email already registered') || result.error.includes('email already')) {
              errorMessage = 'Данная почта уже используется'
            } else if (result.error.includes('Username already registered') || result.error.includes('username already')) {
              errorMessage = 'Имя пользователя уже занято'
            } else {
              errorMessage = result.error
            }
          }
          setError(errorMessage)
          setIsLoading(false)
          return
        }
      }

      // Если успешно, перенаправляем
      const user = auth.getUser()
      if (user?.role === 'admin') {
        router.push('/admin')
      } else {
        router.push('/dashboard')
      }
    } catch (err) {
      setError('Произошла ошибка. Попробуйте позже')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-12">
          <div className="flex justify-center items-center gap-4 mb-4">
            <Logo size={64} />
            <h1 className="text-5xl font-semibold text-text-primary tracking-tight">
              NeuroView
            </h1>
          </div>
          <p className="text-text-tertiary text-sm font-normal tracking-wide">
            AI-платформа для собеседований
          </p>
        </div>

        {/* Auth Card */}
        <div className="bg-bg-secondary rounded-lg p-8 border border-border-color">
          <div className="flex gap-4 mb-6">
            <button
              type="button"
              onClick={() => handleModeSwitch(true)}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
                isLogin
                  ? 'bg-white text-black'
                  : 'bg-bg-tertiary text-text-tertiary hover:text-text-primary hover:bg-bg-quaternary'
              }`}
            >
              Вход
            </button>
            <button
              type="button"
              onClick={() => handleModeSwitch(false)}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
                !isLogin
                  ? 'bg-white text-black'
                  : 'bg-bg-tertiary text-text-tertiary hover:text-text-primary hover:bg-bg-quaternary'
              }`}
            >
              Регистрация
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {!isLogin && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="firstName" className="block text-sm font-medium text-text-tertiary mb-2 tracking-tight">
                      Имя
                    </label>
                    <input
                      id="firstName"
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                      placeholder="Введите имя"
                      required={!isLogin}
                      autoComplete="given-name"
                    />
                  </div>
                  <div>
                    <label htmlFor="lastName" className="block text-sm font-medium text-text-tertiary mb-2 tracking-tight">
                      Фамилия
                    </label>
                    <input
                      id="lastName"
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                      placeholder="Введите фамилию"
                      required={!isLogin}
                      autoComplete="family-name"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-text-tertiary mb-2 tracking-tight">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                    placeholder="Введите email"
                    required={!isLogin}
                    autoComplete="email"
                  />
                </div>
              </>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-text-tertiary mb-2 tracking-tight">
                Имя пользователя
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                placeholder="Введите имя пользователя"
                required
                autoComplete="username"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text-tertiary mb-2 tracking-tight">
                Пароль
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent transition-all"
                placeholder="Введите пароль"
                required
                autoComplete={isLogin ? "current-password" : "new-password"}
              />
            </div>

            {error && (
              <div className="bg-bg-quaternary border border-border-hover rounded-lg p-4 text-red-500 text-sm">
                {error}
              </div>
            )}

                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full bg-gradient-to-r from-[#AF52DE] to-[#8E44AD] text-white py-4 rounded-lg font-semibold text-lg hover:from-[#8E44AD] hover:to-[#AF52DE] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-md"
                    >
                      {isLoading ? 'Загрузка...' : isLogin ? 'Войти' : 'Зарегистрироваться'}
                    </button>
          </form>

          <p className="mt-6 text-center text-sm text-text-muted">
            {isLogin ? 'Нет аккаунта? ' : 'Уже есть аккаунт? '}
            <button
              type="button"
              onClick={() => handleModeSwitch(!isLogin)}
              className="text-text-primary hover:text-text-tertiary font-medium transition-colors"
            >
              {isLogin ? 'Зарегистрироваться' : 'Войти'}
            </button>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-text-muted text-sm mt-8">
          Для входа используйте: admin / admin
        </p>
      </div>
    </div>
  )
}

