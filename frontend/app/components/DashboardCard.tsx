'use client'

import Link from 'next/link'
import { ReactNode } from 'react'

interface DashboardCardProps {
  href: string
  title: string
  description: string
  actionText: string
  icon: ReactNode
  variant?: 'hr' | 'candidate'
}

export default function DashboardCard({
  href,
  title,
  description,
  actionText,
  icon,
  variant = 'candidate',
}: DashboardCardProps) {
  const iconContainerClass =
    variant === 'hr'
      ? 'w-16 h-16 bg-gradient-to-br from-[#AF52DE] to-[#8E44AD] rounded-lg flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-200 shadow-sm'
      : 'w-16 h-16 bg-white rounded-lg flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-200'

  const iconClass = variant === 'hr' ? 'w-8 h-8 text-white' : 'w-8 h-8 text-black'

  return (
    <Link
      href={href}
      className="group relative bg-bg-secondary rounded-lg p-8 border border-border-color hover:border-[#AF52DE] transition-all duration-200"
      aria-label={`${title}: ${description}`}
    >
      <div className="relative z-10">
        <div className={iconContainerClass}>
          <div className={iconClass}>{icon}</div>
        </div>
        <h3 className="text-xl font-semibold text-text-primary mb-3 tracking-tight">{title}</h3>
        <p className="text-text-tertiary text-sm leading-relaxed mb-6">{description}</p>
        <div className="flex items-center text-text-primary font-medium group-hover:text-text-primary transition-colors">
          {actionText}
          <svg
            className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </div>
      </div>
    </Link>
  )
}













