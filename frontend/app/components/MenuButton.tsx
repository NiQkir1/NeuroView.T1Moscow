'use client'

import Image from 'next/image'
import { useSidebar } from './SidebarContext'

export default function MenuButton() {
  const { toggleSidebar, isOpen } = useSidebar()

  return (
    <button
      onClick={toggleSidebar}
      className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors relative z-[60]"
      aria-label="Toggle menu"
    >
      {isOpen ? (
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
      ) : (
        <Image src="/pic/menu.png" alt="Menu" width={24} height={24} className="w-6 h-6" />
      )}
    </button>
  )
}

