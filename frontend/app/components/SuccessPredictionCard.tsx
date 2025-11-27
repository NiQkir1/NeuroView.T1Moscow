'use client'

interface PredictionData {
  success_probability: number
  confidence: number
  retention_probability: number
  performance_forecast?: {
    expected_level?: string
    months_to_peak_performance?: number
    estimated_score_6months?: number
  }
  factors?: {
    [key: string]: {
      score?: number
      weight?: number
      impact?: string
    }
  }
  recommendations?: string[]
  risk_level?: string
  sessions_analyzed?: number
}

interface SuccessPredictionCardProps {
  data: PredictionData
  loading?: boolean
}

const factorLabels: { [key: string]: string } = {
  technical_skills: 'Технические навыки',
  soft_skills: 'Мягкие навыки',
  consistency: 'Стабильность',
  progress: 'Прогресс',
  job_fit: 'Соответствие вакансии',
}

const riskLabels: { [key: string]: { label: string; color: string } } = {
  low: { label: 'Низкий риск', color: 'text-green-400 bg-green-500/20 border-green-500/50' },
  medium: { label: 'Средний риск', color: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50' },
  high: { label: 'Высокий риск', color: 'text-red-400 bg-red-500/20 border-red-500/50' },
}

const performanceLabels: { [key: string]: string } = {
  excellent: 'Отличная',
  good: 'Хорошая',
  average: 'Средняя',
  below_average: 'Ниже среднего',
}

export default function SuccessPredictionCard({ data, loading }: SuccessPredictionCardProps) {
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

  const getProbabilityColor = (prob: number) => {
    if (prob >= 0.7) return 'text-green-400'
    if (prob >= 0.5) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="bg-bg-secondary rounded-lg border border-border-color p-6">
      <h3 className="text-xl font-semibold text-text-primary mb-6 tracking-tight">
        Прогноз успешности
      </h3>

      {/* Main Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
          <div className="text-text-tertiary text-xs mb-2">Вероятность успеха</div>
          <div className={`text-3xl font-semibold ${getProbabilityColor(data.success_probability || 0)}`}>
            {data.success_probability != null ? (data.success_probability * 100).toFixed(0) : 'N/A'}%
          </div>
          <div className="text-text-tertiary text-xs mt-1">
            Уверенность: {data.confidence != null ? (data.confidence * 100).toFixed(0) : 'N/A'}%
          </div>
        </div>

        <div className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
          <div className="text-text-tertiary text-xs mb-2">Удержание</div>
          <div className={`text-3xl font-semibold ${getProbabilityColor(data.retention_probability || 0)}`}>
            {data.retention_probability != null ? (data.retention_probability * 100).toFixed(0) : 'N/A'}%
          </div>
          <div className="text-text-tertiary text-xs mt-1">Вероятность</div>
        </div>

        <div className="p-4 bg-bg-tertiary rounded-lg border border-border-color">
          <div className="text-text-tertiary text-xs mb-2">Уровень риска</div>
          <div className={`text-lg font-semibold px-3 py-1 rounded inline-block border ${
            data.risk_level && riskLabels[data.risk_level]?.color || riskLabels.medium.color
          }`}>
            {data.risk_level ? (riskLabels[data.risk_level]?.label || data.risk_level) : 'Не указан'}
          </div>
        </div>
      </div>

      {/* Performance Forecast */}
      {data.performance_forecast && (
        <div className="mb-6 p-4 bg-bg-tertiary rounded-lg border border-border-color">
          <h4 className="text-sm font-semibold text-text-primary mb-3">Прогноз производительности</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-text-tertiary text-xs">Ожидаемый уровень:</span>
              <div className="text-text-primary font-medium mt-1">
                {data.performance_forecast.expected_level
                  ? (performanceLabels[data.performance_forecast.expected_level] || data.performance_forecast.expected_level)
                  : 'Не указан'}
              </div>
            </div>
            <div>
              <span className="text-text-tertiary text-xs">До пика производительности:</span>
              <div className="text-text-primary font-medium mt-1">
                {data.performance_forecast.months_to_peak_performance !== undefined
                  ? `${data.performance_forecast.months_to_peak_performance} месяцев`
                  : 'Не указано'}
              </div>
            </div>
            <div>
              <span className="text-text-tertiary text-xs">Оценка через 6 месяцев:</span>
              <div className="text-text-primary font-medium mt-1">
                {data.performance_forecast.estimated_score_6months !== undefined
                  ? `${data.performance_forecast.estimated_score_6months.toFixed(1)}/10`
                  : 'Не указано'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Factors */}
      {data.factors && Object.keys(data.factors).length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text-primary mb-3">Факторы влияния</h4>
          <div className="space-y-2">
            {Object.entries(data.factors).map(([key, factor]) => (
            <div key={key} className="flex items-center justify-between p-3 bg-bg-tertiary rounded border border-border-color">
              <div className="flex-1">
                <div className="text-text-primary text-sm font-medium mb-1">
                  {factorLabels[key] || key}
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-bg-quaternary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-apple transition-all"
                      style={{ width: `${((factor.score || 0) / 10) * 100}%` }}
                    />
                  </div>
                  <span className="text-text-tertiary text-xs w-12 text-right">
                    {factor.score !== undefined ? `${factor.score.toFixed(1)}/10` : 'N/A'}
                  </span>
                </div>
              </div>
              <div className="ml-4 text-xs text-text-tertiary">
                Вес: {factor.weight !== undefined ? `${(factor.weight * 100).toFixed(0)}%` : 'N/A'}
              </div>
            </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations && data.recommendations.length > 0 && (
        <div className="pt-6 border-t border-border-color">
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

      {data.sessions_analyzed !== undefined && (
        <div className="mt-4 text-xs text-text-tertiary text-center">
          На основе анализа {data.sessions_analyzed} сессий
        </div>
      )}
    </div>
  )
}


