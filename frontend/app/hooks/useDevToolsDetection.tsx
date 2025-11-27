/**
 * DevTools Detection Hook v4.2.0
 * 
 * Детектирует:
 * - Открытие DevTools
 * - Браузерные расширения (ChatGPT, Copilot, и др.)
 * - Подозрительные глобальные переменные
 * - Изменения в console API
 */
'use client';

import { useEffect, useRef, useState } from 'react';

interface DevToolsDetectionConfig {
  onDevToolsOpen?: () => void;
  onExtensionDetected?: (extensionName: string) => void;
  onSuspiciousActivity?: (type: string, details: any) => void;
  enabled?: boolean;
}

export function useDevToolsDetection(config: DevToolsDetectionConfig = {}) {
  const [devToolsOpen, setDevToolsOpen] = useState(false);
  const [detectedExtensions, setDetectedExtensions] = useState<string[]>([]);
  const detectionInterval = useRef<NodeJS.Timeout>();
  
  useEffect(() => {
    if (!config.enabled) return;
    
    // 1. Детектирование DevTools по размеру окна
    const detectDevToolsBySize = () => {
      const threshold = 160;
      const widthThreshold = window.outerWidth - window.innerWidth > threshold;
      const heightThreshold = window.outerHeight - window.innerHeight > threshold;
      
      const isOpen = widthThreshold || heightThreshold;
      
      if (isOpen && !devToolsOpen) {
        setDevToolsOpen(true);
        config.onDevToolsOpen?.();
        config.onSuspiciousActivity?.('devtools_opened', {
          outerWidth: window.outerWidth,
          innerWidth: window.innerWidth,
          outerHeight: window.outerHeight,
          innerHeight: window.innerHeight,
        });
      } else if (!isOpen && devToolsOpen) {
        setDevToolsOpen(false);
      }
    };
    
    // 2. Детектирование через console.log timing
    const detectDevToolsByConsole = () => {
      const startTime = performance.now();
      const div = document.createElement('div');
      
      Object.defineProperty(div, 'id', {
        get: function() {
          // DevTools открыты если это свойство вычисляется
          const endTime = performance.now();
          if (endTime - startTime > 100) {
            if (!devToolsOpen) {
              setDevToolsOpen(true);
              config.onDevToolsOpen?.();
              config.onSuspiciousActivity?.('devtools_console_timing', {
                timing: endTime - startTime
              });
            }
          }
          return 'detect';
        }
      });
      
      // Вызываем console с объектом
      console.dir(div);
      console.clear(); // Очищаем чтобы не мешать
    };
    
    // 3. Детектирование популярных расширений
    const detectExtensions = () => {
      const extensionsToCheck = [
        // ChatGPT расширения
        {
          name: 'ChatGPT Chrome Extension',
          check: () => {
            return document.querySelector('[data-chatgpt-extension]') !== null ||
                   (window as any).chatGPTExtension !== undefined;
          }
        },
        // GitHub Copilot
        {
          name: 'GitHub Copilot',
          check: () => {
            return (window as any).copilot !== undefined ||
                   document.querySelector('[data-copilot]') !== null;
          }
        },
        // Grammarly
        {
          name: 'Grammarly',
          check: () => {
            return document.querySelector('grammarly-extension') !== null ||
                   (window as any).grammarly !== undefined;
          }
        },
        // Другие AI ассистенты
        {
          name: 'AI Assistant',
          check: () => {
            return (window as any).aiAssistant !== undefined ||
                   (window as any).assistant !== undefined;
          }
        }
      ];
      
      const detected: string[] = [];
      
      for (const ext of extensionsToCheck) {
        try {
          if (ext.check()) {
            detected.push(ext.name);
            
            if (!detectedExtensions.includes(ext.name)) {
              config.onExtensionDetected?.(ext.name);
              config.onSuspiciousActivity?.('extension_detected', {
                extension: ext.name
              });
            }
          }
        } catch (e) {
          // Игнорируем ошибки проверки
        }
      }
      
      if (detected.length > 0) {
        setDetectedExtensions(detected);
      }
    };
    
    // 4. Детектирование изменений в console API
    const originalConsole = {
      log: console.log,
      warn: console.warn,
      error: console.error,
      info: console.info,
    };
    
    // Проверяем, не был ли console переопределен
    const detectConsoleOverride = () => {
      if (console.log !== originalConsole.log ||
          console.warn !== originalConsole.warn ||
          console.error !== originalConsole.error) {
        config.onSuspiciousActivity?.('console_override', {
          message: 'Console API был изменен'
        });
      }
    };
    
    // 5. Детектирование debugger statement
    const detectDebugger = () => {
      const before = Date.now();
      // debugger; // Раскомментировать для активации
      const after = Date.now();
      
      if (after - before > 100) {
        config.onSuspiciousActivity?.('debugger_detected', {
          timing: after - before
        });
      }
    };
    
    // Запускаем все проверки
    const runAllDetections = () => {
      detectDevToolsBySize();
      detectDevToolsByConsole();
      detectExtensions();
      detectConsoleOverride();
      // detectDebugger(); // Можно включить при необходимости
    };
    
    // Начальная проверка
    runAllDetections();
    
    // Периодические проверки каждые 2 секунды
    detectionInterval.current = setInterval(runAllDetections, 2000);
    
    // Слушаем изменение размера окна
    window.addEventListener('resize', detectDevToolsBySize);
    
    return () => {
      if (detectionInterval.current) {
        clearInterval(detectionInterval.current);
      }
      window.removeEventListener('resize', detectDevToolsBySize);
    };
  }, [config.enabled, devToolsOpen, detectedExtensions]);
  
  return {
    devToolsOpen,
    detectedExtensions,
    isClean: !devToolsOpen && detectedExtensions.length === 0,
  };
}

/**
 * Компонент предупреждения о DevTools
 */
export function DevToolsWarning({ onClose }: { onClose?: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-6 border-2 border-red-500">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-red-600 dark:text-red-400">
              ⚠️ Обнаружено нарушение
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Предупреждение системы безопасности
            </p>
          </div>
        </div>
        
        <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
          <p>
            <strong>Обнаружено использование инструментов разработчика (DevTools).</strong>
          </p>
          <p>
            Во время собеседования запрещено:
          </p>
          <ul className="list-disc list-inside space-y-1 pl-2">
            <li>Открывать консоль разработчика</li>
            <li>Использовать браузерные расширения (ChatGPT, Copilot и т.д.)</li>
            <li>Использовать внешние инструменты для помощи</li>
          </ul>
          <p className="text-red-600 dark:text-red-400 font-semibold">
            Закройте DevTools и продолжите собеседование честно.
          </p>
          <p className="text-xs text-gray-500">
            Все нарушения фиксируются и влияют на итоговую оценку.
          </p>
        </div>
        
        {onClose && (
          <button
            onClick={onClose}
            className="mt-4 w-full px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium transition-colors"
          >
            Я понимаю
          </button>
        )}
      </div>
    </div>
  );
}

