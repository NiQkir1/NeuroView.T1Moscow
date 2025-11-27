'use client'

import { useEffect, useRef } from 'react'

interface KeystrokeEvent {
  key: string
  timestamp: number
  keydown: number
  keyup: number
  duration: number
}

interface TypingMetrics {
  averageInterval: number
  variance: number
  typingSpeed: number // символов в минуту
  averageKeyDuration: number
  totalKeystrokes: number
}

export function useKeystrokeDynamics() {
  const keystrokes = useRef<KeystrokeEvent[]>([])
  const keydownTimes = useRef<Map<string, number>>(new Map())
  const lastKeystrokeTime = useRef<number>(0)
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Игнорируем служебные клавиши
      if (e.key === 'Tab' || e.key === 'Escape' || e.key === 'F1' || e.key.startsWith('F')) {
        return
      }
      
      const now = Date.now()
      keydownTimes.current.set(e.key, now)
    }
    
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'Tab' || e.key === 'Escape' || e.key === 'F1' || e.key.startsWith('F')) {
        return
      }
      
      const keydownTime = keydownTimes.current.get(e.key)
      if (keydownTime) {
        const now = Date.now()
        const duration = now - keydownTime
        
        keystrokes.current.push({
          key: e.key,
          timestamp: now,
          keydown: keydownTime,
          keyup: now,
          duration: duration
        })
        
        lastKeystrokeTime.current = now
        keydownTimes.current.delete(e.key)
      }
    }
    
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('keyup', handleKeyUp)
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('keyup', handleKeyUp)
    }
  }, [])
  
  const analyzeTypingPattern = (): TypingMetrics | null => {
    if (keystrokes.current.length < 10) {
      return null
    }
    
    // Вычисляем интервалы между нажатиями
    const intervals: number[] = []
    for (let i = 1; i < keystrokes.current.length; i++) {
      const interval = keystrokes.current[i].timestamp - keystrokes.current[i - 1].timestamp
      if (interval < 5000) { // Игнорируем очень большие интервалы (паузы)
        intervals.push(interval)
      }
    }
    
    if (intervals.length === 0) {
      return null
    }
    
    const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length
    
    // Вычисляем дисперсию
    const variance = intervals.reduce((sum, interval) => {
      return sum + Math.pow(interval - avgInterval, 2)
    }, 0) / intervals.length
    
    // Вычисляем скорость печати (символов в минуту)
    const timeSpan = keystrokes.current[keystrokes.current.length - 1].timestamp - 
                     keystrokes.current[0].timestamp
    const typingSpeed = timeSpan > 0 
      ? (keystrokes.current.length / (timeSpan / 1000)) * 60 
      : 0
    
    // Средняя длительность нажатия клавиши
    const avgKeyDuration = keystrokes.current.reduce((sum, k) => sum + k.duration, 0) / keystrokes.current.length
    
    return {
      averageInterval: avgInterval,
      variance: variance,
      typingSpeed: typingSpeed,
      averageKeyDuration: avgKeyDuration,
      totalKeystrokes: keystrokes.current.length
    }
  }
  
  const reset = () => {
    keystrokes.current = []
    keydownTimes.current.clear()
    lastKeystrokeTime.current = 0
  }
  
  return {
    keystrokes: keystrokes.current,
    analyzeTypingPattern,
    reset,
    getKeystrokeCount: () => keystrokes.current.length
  }
}




