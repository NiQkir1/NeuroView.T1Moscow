'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { auth, User } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import AdminSidebar from './components/AdminSidebar'
import MenuButton from '../components/MenuButton'
import Logo from '../components/Logo'
import { useSidebar } from '../components/SidebarContext'
import LoadingSpinner from '../components/LoadingSpinner'
import { useNotifications } from '../hooks/useNotifications'

interface UserWithRole extends User {
  role: 'candidate' | 'hr' | 'admin' | 'moderator'
}

export default function AdminPage() {
  const router = useRouter()
  const { closeSidebar } = useSidebar()
  const { showError } = useNotifications()
  const [users, setUsers] = useState<UserWithRole[]>([])
  const [filteredUsers, setFilteredUsers] = useState<UserWithRole[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  
  // Фильтры
  const [showAdmin, setShowAdmin] = useState(true)
  const [showHR, setShowHR] = useState(true)
  const [showCandidate, setShowCandidate] = useState(true)
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  
  // ОПТИМИЗАЦИЯ: Пагинация
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(50)
  const [totalUsers, setTotalUsers] = useState(0)

  // Закрываем сайдбар при загрузке страницы
  useEffect(() => {
    closeSidebar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    // Проверка прав доступа
    if (!auth.isAuthenticated()) {
      router.push('/login')
      return
    }

    const user = auth.getUser()
    if (!user || user.role !== 'admin') {
      router.push('/dashboard')
      return
    }

    loadUsers()
  }, [router])

  useEffect(() => {
    // Применяем фильтры и поиск
    let filtered = users.filter(user => {
      if (user.role === 'admin' && !showAdmin) return false
      if (user.role === 'hr' && !showHR) return false
      if (user.role === 'candidate' && !showCandidate) return false
      if (user.role === 'moderator') return showCandidate // Модераторы показываются как кандидаты
      return true
    })

    // Поиск по имени пользователя
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim()
      filtered = filtered.filter(user => 
        user.username.toLowerCase().includes(query) ||
        (user.full_name && user.full_name.toLowerCase().includes(query)) ||
        (user.email && user.email.toLowerCase().includes(query))
      )
    }

    setFilteredUsers(filtered)
  }, [users, showAdmin, showHR, showCandidate, searchQuery])

  const loadUsers = async () => {
    try {
      // ОПТИМИЗАЦИЯ: Загружаем с пагинацией
      const skip = (currentPage - 1) * itemsPerPage
      const data = await apiClient.get(`/api/admin/users?skip=${skip}&limit=${itemsPerPage}`) as UserWithRole[]
      setUsers(data)
      // В реальном случае бэкенд должен возвращать total count
      // Для простоты считаем, что если получили полный набор, есть еще страницы
      setTotalUsers(data.length === itemsPerPage ? (currentPage * itemsPerPage) + 1 : (currentPage - 1) * itemsPerPage + data.length)
    } catch (err) {
      setError('Не удалось загрузить список пользователей')
      showError('Не удалось загрузить список пользователей')
    } finally {
      setLoading(false)
    }
  }

  const toggleHRRole = async (userId: number, currentRole: string) => {
    try {
      const newRole = currentRole === 'hr' ? 'candidate' : 'hr'
      await apiClient.patch(`/api/admin/users/${userId}/role`, { role: newRole })
      // Обновляем список пользователей
      await loadUsers()
    } catch (err) {
      setError('Не удалось обновить роль пользователя')
      showError('Не удалось обновить роль пользователя')
    }
  }

  const handleUserClick = (userId: number) => {
    router.push(`/admin/users/${userId}`)
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-500/20 text-red-400 border-red-500/50'
      case 'hr':
        return 'bg-purple-apple/20 text-purple-apple border-purple-apple/50'
      case 'moderator':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50'
    }
  }

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'admin':
        return 'Администратор'
      case 'hr':
        return 'HR'
      case 'moderator':
        return 'Модератор'
      default:
        return 'Кандидат'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-text-primary text-xl">Загрузка...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary flex">
      <AdminSidebar currentPage="users" />
      
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="sticky top-0 bg-bg-secondary border-b border-border-color px-12 py-6 flex items-center justify-between relative z-[55] backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <MenuButton />
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
              Пользователи
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Logo size={48} />
            <h2 className="text-2xl font-semibold text-text-primary tracking-tight">NeuroView</h2>
          </div>
        </header>
        
        <div className="flex-1 p-12 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {/* Description */}
            <div className="mb-12">
              <p className="text-text-tertiary text-sm font-normal tracking-wide">Управление пользователями и ролями</p>
            </div>

          {error && (
            <div className="mb-8 bg-bg-quaternary border border-border-hover rounded-lg p-4 text-red-500 text-sm">
              {error}
            </div>
          )}

          {/* Search and Filter Controls */}
          <div className="mb-8 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            {/* Search */}
            <div className="flex-1 max-w-md">
              <label className="text-text-muted text-xs uppercase tracking-wider mb-2 block">Поиск по имени пользователя</label>
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Введите имя пользователя..."
                  className="w-full px-4 py-2.5 pl-10 bg-bg-tertiary border border-border-color text-text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-text-primary focus:border-transparent transition-all placeholder-text-muted"
                />
                <svg
                  className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-muted"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
              </div>
            </div>

            {/* Filter Button */}
            <div className="relative">
            <button
              onClick={() => setShowFilterMenu(!showFilterMenu)}
                        className="flex items-center gap-2.5 px-5 py-2.5 bg-bg-tertiary text-text-primary border border-border-hover rounded-lg hover:bg-bg-quaternary hover:border-border-hover transition-all duration-200 text-sm font-medium tracking-tight"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
              </svg>
              Фильтры
              {(!showAdmin || !showHR || !showCandidate) && (
                <span className="ml-1 px-2 py-0.5 bg-text-primary text-bg-primary text-xs rounded-full font-medium">
                  {[showAdmin, showHR, showCandidate].filter(Boolean).length}
                </span>
              )}
            </button>

            {/* Filter Menu */}
            {showFilterMenu && (
              <>
                {/* Overlay to close menu on click outside */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowFilterMenu(false)}
                />
                <div className="absolute right-0 top-full mt-2 bg-bg-secondary rounded-lg p-6 border border-border-color shadow-2xl z-20 min-w-[300px] backdrop-blur-xl">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-base font-semibold text-text-primary tracking-tight">Фильтры по ролям</h3>
                    <button
                      onClick={() => setShowFilterMenu(false)}
                      className="text-text-muted hover:text-text-primary transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  
                  <div className="space-y-2.5">
                    <label className="flex items-center gap-3 cursor-pointer group py-2">
                      <input
                        type="checkbox"
                        checked={showAdmin}
                        onChange={(e) => setShowAdmin(e.target.checked)}
                        className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-text-primary focus:ring-offset-0 focus:ring-offset-transparent"
                      />
                      <div className="flex items-center gap-2.5">
                        <span className={`inline-block w-2 h-2 rounded-full ${showAdmin ? 'bg-text-primary' : 'bg-bg-hover'}`}></span>
                        <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">Администраторы</span>
                      </div>
                    </label>
                    
                    <label className="flex items-center gap-3 cursor-pointer group py-2">
                      <input
                        type="checkbox"
                        checked={showHR}
                        onChange={(e) => setShowHR(e.target.checked)}
                        className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-text-primary focus:ring-offset-0 focus:ring-offset-transparent"
                      />
                      <div className="flex items-center gap-2.5">
                        <span className={`inline-block w-2 h-2 rounded-full ${showHR ? 'bg-text-primary' : 'bg-bg-hover'}`}></span>
                        <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">HR</span>
                      </div>
                    </label>
                    
                    <label className="flex items-center gap-3 cursor-pointer group py-2">
                      <input
                        type="checkbox"
                        checked={showCandidate}
                        onChange={(e) => setShowCandidate(e.target.checked)}
                        className="w-4 h-4 rounded border-border-hover bg-bg-tertiary text-text-primary focus:ring-1 focus:ring-text-primary focus:ring-offset-0 focus:ring-offset-transparent"
                      />
                      <div className="flex items-center gap-2.5">
                        <span className={`inline-block w-2 h-2 rounded-full ${showCandidate ? 'bg-text-primary' : 'bg-bg-hover'}`}></span>
                        <span className="text-sm text-text-tertiary group-hover:text-text-primary transition-colors tracking-tight">Кандидаты</span>
                      </div>
                    </label>
                  </div>

                  <div className="mt-6 pt-4 border-t border-border-color">
                    <button
                      onClick={() => {
                        setShowAdmin(true)
                        setShowHR(true)
                        setShowCandidate(true)
                      }}
                      className="w-full px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors tracking-tight"
                    >
                      Сбросить фильтры
                    </button>
                  </div>
                </div>
              </>
            )}
            </div>
          </div>

          {/* Users Table */}
          <div className="bg-bg-secondary rounded-lg border border-border-color overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-color">
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">ID</th>
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">Имя пользователя</th>
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">Email</th>
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">Полное имя</th>
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">Роль</th>
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">Дата регистрации</th>
                    <th className="text-left py-4 px-6 text-text-muted text-xs font-medium uppercase tracking-wider">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr
                      key={user.id}
                      className="border-b border-border-color hover:bg-bg-tertiary hover:border-[#AF52DE]/30 cursor-pointer transition-all duration-150"
                      onClick={() => handleUserClick(user.id)}
                    >
                      <td className="py-4 px-6 text-text-tertiary text-sm">{user.id}</td>
                      <td className="py-4 px-6 text-text-primary text-sm font-medium">{user.username}</td>
                      <td className="py-4 px-6 text-text-tertiary text-sm">{user.email || '-'}</td>
                      <td className="py-4 px-6 text-text-tertiary text-sm">{user.full_name || '-'}</td>
                      <td className="py-4 px-6">
                        <span
                          className={`inline-block px-2.5 py-1 rounded text-xs font-medium tracking-tight ${
                            user.role === 'admin'
                              ? 'bg-text-primary text-bg-primary'
                              : user.role === 'hr'
                              ? 'bg-text-primary text-bg-primary'
                              : 'bg-bg-quaternary text-text-tertiary border border-border-hover'
                          }`}
                        >
                          {getRoleLabel(user.role)}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-text-tertiary text-sm">
                        {new Date(user.created_at).toLocaleDateString('ru-RU')}
                      </td>
                      <td className="py-4 px-6">
                        {user.role !== 'admin' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleHRRole(user.id, user.role)
                            }}
                            className={`px-4 py-1.5 rounded text-xs font-medium transition-all duration-200 tracking-tight ${
                              user.role === 'hr'
                                ? 'bg-bg-quaternary text-red-500 border border-border-hover hover:bg-bg-hover'
                                : 'bg-text-primary text-bg-primary hover:opacity-90'
                            }`}
                          >
                            {user.role === 'hr' ? 'Убрать HR' : 'Назначить HR'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filteredUsers.length === 0 && (
              <div className="text-center py-16 text-text-muted text-sm">
                {users.length === 0 ? 'Пользователи не найдены' : 'Нет пользователей с выбранными ролями'}
              </div>
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}
