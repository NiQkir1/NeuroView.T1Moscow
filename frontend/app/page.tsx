'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { auth } from '@/lib/auth'
import LoadingSpinner from './components/LoadingSpinner'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Перенаправление на логин или dashboard в зависимости от авторизации
    if (auth.isAuthenticated()) {
      router.push('/dashboard')
    } else {
      router.push('/login')
    }
  }, [router])

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center">
      <LoadingSpinner size="lg" />
    </div>
  )
}

