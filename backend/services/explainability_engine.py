"""
Explainability Engine - объяснение решений ИИ
Mercor AI v2.0.0: Explainable AI и прозрачность
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session


class ExplainabilityEngine:
    """Сервис для объяснения решений ИИ"""
    
    def explain_evaluation(
        self,
        question: str,
        answer: str,
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Генерация объяснения оценки ответа
        
        Args:
            question: Текст вопроса
            answer: Ответ кандидата
            evaluation: Результат оценки от ИИ
        
        Returns:
            Объяснение с факторами влияния
        """
        score = evaluation.get("score", 0)
        correctness = evaluation.get("correctness", 0)
        completeness = evaluation.get("completeness", 0)
        quality = evaluation.get("quality", 0)
        
        # Определяем ключевые факторы
        factors = []
        
        if correctness < 5:
            factors.append({
                "factor": "Правильность ответа",
                "impact": "negative",
                "weight": 0.3,
                "explanation": "Ответ содержит неточности или ошибки"
            })
        elif correctness >= 8:
            factors.append({
                "factor": "Правильность ответа",
                "impact": "positive",
                "weight": 0.3,
                "explanation": "Ответ технически корректен"
            })
        
        if completeness < 5:
            factors.append({
                "factor": "Полнота ответа",
                "impact": "negative",
                "weight": 0.25,
                "explanation": "Ответ неполный, отсутствуют важные детали"
            })
        elif completeness >= 8:
            factors.append({
                "factor": "Полнота ответа",
                "impact": "positive",
                "weight": 0.25,
                "explanation": "Ответ охватывает все аспекты вопроса"
            })
        
        if quality < 5:
            factors.append({
                "factor": "Качество изложения",
                "impact": "negative",
                "weight": 0.2,
                "explanation": "Ответ плохо структурирован или неясен"
            })
        elif quality >= 8:
            factors.append({
                "factor": "Качество изложения",
                "impact": "positive",
                "weight": 0.2,
                "explanation": "Ответ хорошо структурирован и понятен"
            })
        
        # Анализ ключевых слов
        expected_keywords = evaluation.get("expected_keywords", [])
        if expected_keywords:
            found_keywords = []
            missing_keywords = []
            
            answer_lower = answer.lower()
            for keyword in expected_keywords:
                if keyword.lower() in answer_lower:
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            if missing_keywords:
                factors.append({
                    "factor": "Ключевые термины",
                    "impact": "negative",
                    "weight": 0.15,
                    "explanation": f"Отсутствуют важные термины: {', '.join(missing_keywords[:3])}"
                })
            
            if found_keywords:
                factors.append({
                    "factor": "Ключевые термины",
                    "impact": "positive",
                    "weight": 0.15,
                    "explanation": f"Использованы правильные термины: {', '.join(found_keywords[:3])}"
                })
        
        # Сильные стороны и улучшения
        strengths = evaluation.get("strengths", [])
        improvements = evaluation.get("improvements", [])
        
        # Общее объяснение
        explanation_text = self._generate_explanation_text(
            score, factors, strengths, improvements
        )
        
        return {
            "score": score,
            "explanation": explanation_text,
            "factors": factors,
            "strengths": strengths,
            "improvements": improvements,
            "feature_importance": self._calculate_feature_importance(factors),
            "transparency_score": self._calculate_transparency_score(factors)
        }
    
    def _generate_explanation_text(
        self,
        score: float,
        factors: List[Dict[str, Any]],
        strengths: List[str],
        improvements: List[str]
    ) -> str:
        """Генерация текстового объяснения"""
        explanation_parts = [f"Общая оценка: {score:.1f}/100"]
        
        if factors:
            explanation_parts.append("\nОсновные факторы оценки:")
            for i, factor in enumerate(factors[:3], 1):
                impact_marker = "+" if factor["impact"] == "positive" else "-"
                explanation_parts.append(
                    f"{i}. [{impact_marker}] {factor['factor']}: {factor['explanation']}"
                )
        
        if strengths:
            explanation_parts.append("\nСильные стороны:")
            for strength in strengths[:3]:
                explanation_parts.append(f"• {strength}")
        
        if improvements:
            explanation_parts.append("\nРекомендации по улучшению:")
            for improvement in improvements[:3]:
                explanation_parts.append(f"• {improvement}")
        
        return "\n".join(explanation_parts)
    
    def _calculate_feature_importance(self, factors: List[Dict[str, Any]]) -> Dict[str, float]:
        """Расчет важности признаков"""
        importance = {}
        for factor in factors:
            factor_name = factor["factor"]
            weight = factor.get("weight", 0)
            if factor_name not in importance:
                importance[factor_name] = 0
            importance[factor_name] += weight
        
        # Нормализация
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}
        
        return importance
    
    def _calculate_transparency_score(self, factors: List[Dict[str, Any]]) -> float:
        """Расчет оценки прозрачности (чем больше факторов объяснено, тем выше)"""
        if not factors:
            return 0.0
        
        # Базовый score зависит от количества объясненных факторов
        base_score = min(len(factors) * 20, 100)
        
        # Бонус за детальность объяснений
        detail_bonus = sum(
            10 for factor in factors
            if "explanation" in factor and len(factor["explanation"]) > 20
        )
        
        return min(base_score + detail_bonus, 100)
    
    def explain_session_score(
        self,
        db: Session,
        session_id: int
    ) -> Dict[str, Any]:
        """Объяснение общей оценки сессии"""
        from backend.models.interview import InterviewSession, Question, Answer
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Сессия не найдена")
        
        questions = db.query(Question).filter(
            Question.session_id == session_id
        ).all()
        
        question_explanations = []
        total_score = 0
        question_count = 0
        
        for question in questions:
            if question.answers:
                answer = question.answers[0]
                if answer.evaluation:
                    explanation = self.explain_evaluation(
                        question.question_text,
                        answer.answer_text or "",
                        answer.evaluation
                    )
                    question_explanations.append({
                        "question_id": question.id,
                        "question_text": question.question_text,
                        "explanation": explanation
                    })
                    
                    if answer.score is not None:
                        total_score += answer.score
                        question_count += 1
        
        avg_score = total_score / question_count if question_count > 0 else 0
        
        return {
            "session_id": session_id,
            "overall_score": avg_score,
            "question_count": question_count,
            "explanations": question_explanations,
            "summary": self._generate_session_summary(question_explanations, avg_score)
        }
    
    def _generate_session_summary(
        self,
        explanations: List[Dict[str, Any]],
        avg_score: float
    ) -> str:
        """Генерация сводки по сессии"""
        if not explanations:
            return "Нет данных для анализа"
        
        # Подсчет положительных и отрицательных факторов
        positive_count = 0
        negative_count = 0
        
        for exp in explanations:
            factors = exp.get("explanation", {}).get("factors", [])
            for factor in factors:
                if factor.get("impact") == "positive":
                    positive_count += 1
                else:
                    negative_count += 1
        
        summary_parts = [
            f"Общая оценка сессии: {avg_score:.1f}/100",
            f"Проанализировано вопросов: {len(explanations)}",
            f"Положительных факторов: {positive_count}",
            f"Областей для улучшения: {negative_count}"
        ]
        
        if avg_score >= 80:
            summary_parts.append("Отличный результат! Кандидат показал высокий уровень знаний.")
        elif avg_score >= 60:
            summary_parts.append("Хороший результат с потенциалом для улучшения.")
        else:
            summary_parts.append("Требуется дополнительная подготовка.")
        
        return "\n".join(summary_parts)


# Глобальный экземпляр
explainability_engine = ExplainabilityEngine()

















