'use client'

import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { auth } from '@/lib/auth'
import { useTheme } from '../../hooks/useTheme'
import { useSidebar } from '../../components/SidebarContext'

interface AdminSidebarProps {
  currentPage: 'users' | 'reports'
}

export default function AdminSidebar({ currentPage }: AdminSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const user = auth.getUser()
  const { toggle } = useTheme()
  const { isOpen, closeSidebar } = useSidebar()

  const handleLogout = () => {
    auth.logout()
    router.push('/login')
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
        <Link
          href="/admin"
          onClick={closeSidebar}
          className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border border-transparent transition-colors duration-200 ${
            currentPage === 'users'
              ? 'text-[#AF52DE] font-medium'
              : 'text-text-tertiary hover:text-[#AF52DE] hover:bg-bg-tertiary hover:border-[#AF52DE]/30'
          }`}
        >
          <Image src="/pic/profile.png" alt="Users" width={16} height={16} className="w-4 h-4" />
          <span className="text-sm tracking-tight">Пользователи</span>
        </Link>

        <Link
          href="/admin/reports"
          onClick={closeSidebar}
          className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border border-transparent transition-colors duration-200 ${
            currentPage === 'reports'
              ? 'text-[#AF52DE] font-medium'
              : 'text-text-tertiary hover:text-[#AF52DE] hover:bg-bg-tertiary hover:border-[#AF52DE]/30'
          }`}
        >
          <Image src="/pic/report.png" alt="Reports" width={16} height={16} className="w-4 h-4" />
          <span className="text-sm tracking-tight">Отчеты</span>
        </Link>
      </nav>

      {/* Theme Toggle & Logout */}
      <div className="p-6 border-t border-border-color space-y-2">
        <button
          onClick={toggle}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-all duration-200"
        >
          <Image src="/pic/lightbulb.circle.fill.png" alt="Theme" width={16} height={16} className="w-4 h-4" />
          <span className="text-sm tracking-tight">Тема</span>
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-all duration-200"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
          </svg>
          <span className="text-sm tracking-tight">Выйти</span>
        </button>
      </div>
    </div>
    </>
  )
}

