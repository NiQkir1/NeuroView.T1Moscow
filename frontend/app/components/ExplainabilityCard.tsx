'use client'

interface ExplanationFactor {
  factor: string
  impact: 'positive' | 'negative'
  weight: number
  explanation: string
}

interface Explanation {
  score: number
  explanation: string
  factors: ExplanationFactor[]
  strengths: string[]
  improvements: string[]
  feature_importance: { [key: string]: number }
  transparency_score: number
}

interface ExplainabilityCardProps {
  explanation: Explanation
  loading?: boolean
}

export default function ExplainabilityCard({ explanation, loading }: ExplainabilityCardProps) {
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
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-red-400'
  }

  return (
    <div className="bg-bg-secondary rounded-lg border border-border-color p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-text-primary tracking-tight">
          Объяснение оценки
        </h3>
        <div className="text-xs text-text-tertiary">
          Прозрачность: {explanation.transparency_score != null ? explanation.transparency_score.toFixed(0) : 'N/A'}%
        </div>
      </div>

      {/* Score */}
      <div className="mb-6 p-4 bg-bg-tertiary rounded-lg border border-border-color">
        <div className="flex items-center justify-between">
          <span className="text-text-tertiary text-sm">Общая оценка</span>
          <div className="flex items-center gap-3">
            <span className={`text-3xl font-semibold ${getScoreColor(explanation.score || 0)}`}>
              {explanation.score != null ? explanation.score.toFixed(1) : 'N/A'}
            </span>
            <span className="text-text-tertiary">/ 100</span>
          </div>
        </div>
      </div>

      {/* Factors */}
      {explanation.factors && explanation.factors.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text-primary mb-3">Факторы оценки</h4>
          <div className="space-y-3">
            {explanation.factors.map((factor, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  factor.impact === 'positive'
                    ? 'bg-green-500/10 border-green-500/30'
                    : 'bg-red-500/10 border-red-500/30'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {factor.impact === 'positive' ? (
                      <span className="text-green-400 text-lg">✅</span>
                    ) : (
                      <span className="text-red-400 text-lg">⚠️</span>
                    )}
                    <span className="text-text-primary font-medium text-sm">{factor.factor}</span>
                  </div>
                  <span className="text-text-tertiary text-xs">
                    Влияние: {factor.weight != null ? (factor.weight * 100).toFixed(0) : 'N/A'}%
                  </span>
                </div>
                <p className="text-text-tertiary text-sm mt-2">{factor.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feature Importance */}
      {explanation.feature_importance && Object.keys(explanation.feature_importance).length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text-primary mb-3">Важность признаков</h4>
          <div className="space-y-2">
            {Object.entries(explanation.feature_importance || {})
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .map(([feature, importance]) => (
                <div key={feature} className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-primary text-sm">{feature}</span>
                      <span className="text-text-tertiary text-xs">
                        {importance != null ? ((importance as number) * 100).toFixed(1) : 'N/A'}%
                      </span>
                    </div>
                    <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-apple transition-all"
                        style={{ width: `${importance * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Strengths */}
      {explanation.strengths && explanation.strengths.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-green-400 mb-3">Сильные стороны</h4>
          <ul className="space-y-2">
            {explanation.strengths.map((strength, index) => (
              <li key={index} className="text-sm text-text-tertiary flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>{strength}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Improvements */}
      {explanation.improvements && explanation.improvements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-orange-400 mb-3">Рекомендации по улучшению</h4>
          <ul className="space-y-2">
            {explanation.improvements.map((improvement, index) => (
              <li key={index} className="text-sm text-text-tertiary flex items-start gap-2">
                <span className="text-orange-400 mt-1">•</span>
                <span>{improvement}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}







