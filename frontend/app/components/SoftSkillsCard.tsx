'use client'

interface SoftSkillsData {
  overall_score: number
  skills: {
    [key: string]: {
      score: number
      level: string
      answers_analyzed: number
    }
  }
  recommendations?: string[]
}

interface SoftSkillsCardProps {
  data: SoftSkillsData
  loading?: boolean
}

const skillLabels: { [key: string]: string } = {
  communication: 'Коммуникация',
  teamwork: 'Работа в команде',
  leadership: 'Лидерство',
  problem_solving: 'Решение проблем',
  adaptability: 'Адаптивность',
  emotional_intelligence: 'Эмоциональный интеллект',
  time_management: 'Тайм-менеджмент',
  critical_thinking: 'Критическое мышление',
}

const levelLabels: { [key: string]: string } = {
  excellent: 'Отлично',
  good: 'Хорошо',
  average: 'Средне',
  needs_improvement: 'Требует улучшения',
  no_data: 'Нет данных',
}

export default function SoftSkillsCard({ data, loading }: SoftSkillsCardProps) {
  if (loading) {
    return (
      <div className="bg-bg-secondary rounded-lg border border-border-color p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-bg-tertiary rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-4 bg-bg-tertiary rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-400'
    if (score >= 6) return 'text-yellow-400'
    if (score >= 4) return 'text-orange-400'
    return 'text-red-400'
  }

  const getScoreBgColor = (score: number) => {
    if (score >= 8) return 'bg-green-500/20 border-green-500/50'
    if (score >= 6) return 'bg-yellow-500/20 border-yellow-500/50'
    if (score >= 4) return 'bg-orange-500/20 border-orange-500/50'
    return 'bg-red-500/20 border-red-500/50'
  }

  return (
    <div className="bg-bg-secondary rounded-lg border border-border-color p-6">
      <h3 className="text-xl font-semibold text-text-primary mb-6 tracking-tight">
        Soft Skills Анализ
      </h3>

      {/* Overall Score */}
      <div className="mb-6 p-4 bg-bg-tertiary rounded-lg border border-border-color">
        <div className="flex items-center justify-between">
          <span className="text-text-tertiary text-sm">Общая оценка</span>
          <div className="flex items-center gap-3">
            <span className={`text-3xl font-semibold ${getScoreColor(data.overall_score || 0)}`}>
              {data.overall_score != null ? data.overall_score.toFixed(1) : 'N/A'}
            </span>
            <span className="text-text-tertiary">/ 10</span>
          </div>
        </div>
      </div>

      {/* Skills Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {Object.entries(data.skills).map(([key, skill]) => (
          <div
            key={key}
            className={`p-4 rounded-lg border ${getScoreBgColor(skill.score)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-text-primary font-medium text-sm">
                {skillLabels[key] || key}
              </span>
              <span className={`text-lg font-semibold ${getScoreColor(skill.score || 0)}`}>
                {skill.score != null ? skill.score.toFixed(1) : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className={`px-2 py-1 rounded ${getScoreBgColor(skill.score)} text-text-primary`}>
                {levelLabels[skill.level] || skill.level}
              </span>
              <span className="text-text-tertiary">
                {skill.answers_analyzed} ответов
              </span>
            </div>
            {/* Progress Bar */}
            <div className="mt-2 h-2 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  skill.score >= 8
                    ? 'bg-green-500'
                    : skill.score >= 6
                    ? 'bg-yellow-500'
                    : skill.score >= 4
                    ? 'bg-orange-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${(skill.score / 10) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {data.recommendations && data.recommendations.length > 0 && (
        <div className="mt-6 pt-6 border-t border-border-color">
          <h4 className="text-sm font-semibold text-text-primary mb-3">Рекомендации</h4>
          <ul className="space-y-2">
            {data.recommendations.map((rec, index) => (
              <li key={index} className="text-sm text-text-tertiary flex items-start gap-2">
                <span className="text-purple-apple mt-1">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}







