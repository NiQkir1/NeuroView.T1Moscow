/**
 * Interview Progress Bar v4.2.0
 * 
 * Визуализация прогресса интервью для кандидата
 */
'use client';

import { useEffect, useState } from 'react';

interface Stage {
  id: string;
  name: string;
  icon: string;
  completed: boolean;
  current: boolean;
  questionsAsked: number;
  questionsRequired: number;
}

interface InterviewProgressBarProps {
  currentStage: string;
  stageProgress: Record<string, any>;
  stages: string[];
  currentQuestion?: number;
  totalQuestions?: number;
  timeRemaining?: number; // в секундах
  totalTime?: number; // в секундах
  showTimer?: boolean;
}

const STAGE_NAMES: Record<string, string> = {
  'ready_check': 'Проверка готовности',
  'introduction': 'Знакомство',
  'softSkills': 'Soft Skills',
  'technical': 'Технические вопросы',
  'liveCoding': 'Live Coding',
};

const STAGE_ICONS: Record<string, string> = {
  'ready_check': '✅',
  'introduction': '👋',
  'softSkills': '💡',
  'technical': '🔧',
  'liveCoding': '💻',
};

export default function InterviewProgressBar({
  currentStage,
  stageProgress,
  stages,
  currentQuestion,
  totalQuestions,
  timeRemaining,
  totalTime,
  showTimer = true,
}: InterviewProgressBarProps) {
  const [progress, setProgress] = useState(0);
  const [formattedTime, setFormattedTime] = useState('');
  
  // Рассчитываем общий прогресс
  useEffect(() => {
    if (!stageProgress || !stages || stages.length === 0) {
      setProgress(0);
      return;
    }
    
    let completedStages = 0;
    let totalStagesCount = stages.filter(s => s !== 'ready_check').length;
    
    for (const stage of stages) {
      if (stage === 'ready_check') continue; // Не учитываем ready_check
      
      const stageInfo = stageProgress[stage];
      if (stageInfo?.completed) {
        completedStages += 1;
      } else if (stage === currentStage) {
        // Частичный прогресс текущей стадии
        const questionsAsked = stageInfo?.questions_asked || 0;
        const questionsRequired = stageInfo?.questions_required || 1;
        const stageProgress = Math.min(questionsAsked / questionsRequired, 1);
        completedStages += stageProgress;
      }
    }
    
    const overallProgress = (completedStages / totalStagesCount) * 100;
    setProgress(Math.round(overallProgress));
  }, [currentStage, stageProgress, stages]);
  
  // Форматируем оставшееся время
  useEffect(() => {
    if (timeRemaining !== undefined) {
      const minutes = Math.floor(timeRemaining / 60);
      const seconds = timeRemaining % 60;
      setFormattedTime(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    }
  }, [timeRemaining]);
  
  // Преобразуем stages в Stage объекты
  const stageObjects: Stage[] = stages
    .filter(s => s !== 'ready_check')
    .map((stageId) => {
      const stageInfo = stageProgress[stageId] || {};
      return {
        id: stageId,
        name: STAGE_NAMES[stageId] || stageId,
        icon: STAGE_ICONS[stageId] || '📋',
        completed: stageInfo.completed || false,
        current: stageId === currentStage,
        questionsAsked: stageInfo.questions_asked || 0,
        questionsRequired: stageInfo.questions_required || 0,
      };
    });
  
  return (
    <div className="w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-6">
      {/* Общий прогресс-бар */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Общий прогресс
            </span>
            {currentQuestion !== undefined && totalQuestions !== undefined && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Вопрос {currentQuestion} из {totalQuestions}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
              {progress}%
            </span>
            {showTimer && timeRemaining !== undefined && (
              <div className="flex items-center gap-1 text-sm">
                <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className={`font-mono font-semibold ${
                  timeRemaining < 300 ? 'text-red-600 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'
                }`}>
                  {formattedTime}
                </span>
              </div>
            )}
          </div>
        </div>
        
        {/* Прогресс-бар */}
        <div className="relative h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
          </div>
        </div>
      </div>
      
      {/* Этапы интервью */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Этапы интервью
        </h4>
        <div className="flex items-center justify-between gap-2">
          {stageObjects.map((stage, index) => (
            <div key={stage.id} className="flex items-center flex-1">
              {/* Этап */}
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all duration-300 ${
                    stage.completed
                      ? 'bg-green-500 text-white shadow-lg scale-110'
                      : stage.current
                      ? 'bg-blue-500 text-white shadow-lg scale-110 animate-pulse'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-400'
                  }`}
                >
                  {stage.completed ? '✓' : stage.icon}
                </div>
                <span
                  className={`mt-2 text-xs text-center transition-all ${
                    stage.completed || stage.current
                      ? 'font-semibold text-gray-900 dark:text-white'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {stage.name}
                </span>
                {stage.questionsRequired > 0 && (
                  <span className="text-[10px] text-gray-400 mt-1">
                    {stage.questionsAsked}/{stage.questionsRequired}
                  </span>
                )}
              </div>
              
              {/* Линия между этапами */}
              {index < stageObjects.length - 1 && (
                <div
                  className={`h-0.5 flex-1 transition-all duration-300 ${
                    stage.completed
                      ? 'bg-green-500'
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>
      
      {/* Дополнительная информация */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>💡 Совет: Отвечайте развернуто и приводите примеры</span>
          <span>Удачи! 🍀</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Компактный прогресс-бар (для верхней панели)
 */
export function CompactProgressBar({
  progress,
  currentStage,
  timeRemaining,
}: {
  progress: number;
  currentStage: string;
  timeRemaining?: number;
}) {
  const [formattedTime, setFormattedTime] = useState('');
  
  useEffect(() => {
    if (timeRemaining !== undefined) {
      const minutes = Math.floor(timeRemaining / 60);
      const seconds = timeRemaining % 60;
      setFormattedTime(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    }
  }, [timeRemaining]);
  
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
          {STAGE_NAMES[currentStage] || currentStage}
        </span>
        <span className="text-xs text-gray-500">{progress}%</span>
      </div>
      
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      
      {timeRemaining !== undefined && (
        <div className="flex items-center gap-1 text-xs font-mono">
          <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className={timeRemaining < 300 ? 'text-red-600 font-semibold' : 'text-gray-700 dark:text-gray-300'}>
            {formattedTime}
          </span>
        </div>
      )}
    </div>
  );
}

