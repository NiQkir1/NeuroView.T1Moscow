'use client'

import React from 'react'
import Image from 'next/image'

export type ApplicationStatus = 
  | 'active' 
  | 'completed' 
  | 'test_task' 
  | 'finalist' 
  | 'offer' 
  | 'rejected'

interface StatusBadgeProps {
  status: ApplicationStatus | string
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const statusConfig: Record<string, {
  label: string
  color: string
  bgColor: string
  borderColor: string
  icon?: string
}> = {
  active: {
    label: 'Активная',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/50',
  },
  completed: {
    label: 'Завершено',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/50',
    icon: 'checkmark.seal.fill.png',
  },
  test_task: {
    label: 'Тестовое задание',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500/50',
  },
  finalist: {
    label: 'Финалист',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/50',
    icon: 'person.fill.checkmark.png',
  },
  offer: {
    label: 'Оффер',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/50',
    icon: 'person.fill.checkmark.png',
  },
  rejected: {
    label: 'Отклонено',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/50',
    icon: 'person.fill.xmark.png',
  },
}

export default function StatusBadge({ status, size = 'md', showLabel = true }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.active
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  }

  const iconSize = size === 'sm' ? 12 : size === 'md' ? 14 : 16
  const iconClass = size === 'sm' ? 'w-3 h-3' : size === 'md' ? 'w-3.5 h-3.5' : 'w-4 h-4'

  return (
    <span
      className={`
        ${sizeClasses[size]}
        ${config.bgColor}
        ${config.color}
        ${config.borderColor}
        border rounded-lg font-medium inline-flex items-center gap-1.5
      `}
    >
      {config.icon ? (
        <Image 
          src={`/pic/${config.icon}`} 
          alt="" 
          width={iconSize} 
          height={iconSize} 
          className={iconClass}
        />
      ) : (
        <span className={`w-2 h-2 rounded-full ${config.bgColor.replace('/20', '')} ${config.borderColor.replace('/50', '')} border`} />
      )}
      {showLabel && <span>{config.label}</span>}
    </span>
  )
}












