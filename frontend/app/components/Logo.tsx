import React from 'react'
import Image from 'next/image'

interface LogoProps {
  size?: number
  className?: string
}

export default function Logo({ size = 48, className = '' }: LogoProps) {
  return (
    <div className={`relative inline-block ${className}`} style={{ width: size, height: size }}>
      <Image
        src="/pic/logo.png"
        alt="NeuroView Logo"
        width={size}
        height={size}
        className="object-contain"
        unoptimized
      />
    </div>
  )
}














