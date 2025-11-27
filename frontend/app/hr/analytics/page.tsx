/**
 * HR Analytics Dashboard v4.2.0
 * 
 * Аналитика и статистика для HR:
 * - Общая статистика интервью
 * - Графики и диаграммы
 * - Топ кандидаты
 * - Статистика по темам
 * - Метрики качества
 */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface AnalyticsSummary {
  totalInterviews: number;
  completedInterviews: number;
  activeInterviews: number;
  averageScore: number;
  passRate: number;
  averageDuration: number;
}

interface TopicStats {
  topic: string;
  count: number;
  averageScore: number;
  passRate: number;
}

interface TopCandidate {
  id: number;
  name: string;
  email: string;
  score: number;
  completedAt: string;
  position: string;
}

export default function AnalyticsDashboard() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<AnalyticsSummary>({
    totalInterviews: 0,
    completedInterviews: 0,
    activeInterviews: 0,
    averageScore: 0,
    passRate: 0,
    averageDuration: 0,
  });
  const [topicStats, setTopicStats] = useState<TopicStats[]>([]);
  const [topCandidates, setTopCandidates] = useState<TopCandidate[]>([]);
  const [timeRange, setTimeRange] = useState('week'); // week, month, all
  
  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);
  
  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }
      
      const [summaryRes, topicsRes, candidatesRes] = await Promise.all([
        fetch(`http://localhost:8000/api/analytics/summary?range=${timeRange}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`http://localhost:8000/api/analytics/topics?range=${timeRange}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`http://localhost:8000/api/analytics/top-candidates?range=${timeRange}&limit=10`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);
      
      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }
      
      if (topicsRes.ok) {
        const data = await topicsRes.json();
        setTopicStats(data.topics || []);
      }
      
      if (candidatesRes.ok) {
        const data = await candidatesRes.json();
        setTopCandidates(data.candidates || []);
      }
    } catch (error) {
      console.error('Ошибка загрузки аналитики:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка аналитики...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Заголовок */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            📊 Аналитика и статистика
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Подробная аналитика по проведенным интервью
          </p>
        </div>
        
        {/* Фильтр по времени */}
        <div className="mb-6 flex gap-2">
          {['week', 'month', 'all'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {range === 'week' ? 'Неделя' : range === 'month' ? 'Месяц' : 'Все время'}
            </button>
          ))}
        </div>
        
        {/* Ключевые метрики */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Всего интервью"
            value={summary.totalInterviews}
            icon="📝"
            color="blue"
          />
          <MetricCard
            title="Завершено"
            value={summary.completedInterviews}
            icon="✅"
            color="green"
            subtitle={`${((summary.completedInterviews / summary.totalInterviews) * 100 || 0).toFixed(0)}%`}
          />
          <MetricCard
            title="Средний балл"
            value={summary.averageScore.toFixed(1)}
            icon="🎯"
            color="purple"
            subtitle="из 100"
          />
          <MetricCard
            title="Процент прохождения"
            value={`${summary.passRate.toFixed(0)}%`}
            icon="📈"
            color="orange"
          />
        </div>
        
        {/* Графики и таблицы */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Статистика по темам */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              📚 Статистика по темам
            </h2>
            <div className="space-y-3">
              {topicStats.length > 0 ? (
                topicStats.map((topic) => (
                  <div key={topic.topic} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {topic.topic}
                        </span>
                        <span className="text-xs text-gray-500">
                          {topic.count} интервью
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                            style={{ width: `${topic.averageScore}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                          {topic.averageScore.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center py-8">Нет данных</p>
              )}
            </div>
          </div>
          
          {/* Топ кандидаты */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              🏆 Топ кандидаты
            </h2>
            <div className="space-y-3">
              {topCandidates.length > 0 ? (
                topCandidates.map((candidate, index) => (
                  <div
                    key={candidate.id}
                    className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer"
                    onClick={() => router.push(`/hr/candidates/${candidate.id}`)}
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {candidate.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {candidate.position || 'Позиция не указана'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-blue-600 dark:text-blue-400">
                        {candidate.score.toFixed(0)}
                      </p>
                      <p className="text-xs text-gray-500">баллов</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center py-8">Нет данных</p>
              )}
            </div>
          </div>
        </div>
        
        {/* Дополнительные метрики */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            📊 Дополнительные метрики
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">
                {summary.averageDuration.toFixed(0)}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Средняя длительность (мин)
              </p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="text-3xl font-bold text-green-600 dark:text-green-400 mb-2">
                {summary.activeInterviews}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Активные интервью
              </p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="text-3xl font-bold text-purple-600 dark:text-purple-400 mb-2">
                {summary.completedInterviews > 0
                  ? ((summary.completedInterviews / summary.totalInterviews) * 100).toFixed(0)
                  : 0}%
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Процент завершения
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Компонент карточки метрики
function MetricCard({
  title,
  value,
  icon,
  color,
  subtitle,
}: {
  title: string;
  value: string | number;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'orange';
  subtitle?: string;
}) {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    purple: 'from-purple-500 to-purple-600',
    orange: 'from-orange-500 to-orange-600',
  };
  
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${colorClasses[color]} flex items-center justify-center text-2xl`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
        {value}
      </p>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {title}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
          {subtitle}
        </p>
      )}
    </div>
  );
}

