"""
Analytics API Routes v4.2.0
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta

from backend.database import get_db
from backend.utils.auth import get_current_user
from backend.models.user import User
from backend.models.interview import InterviewSession, Question, Answer, InterviewStatus

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def get_analytics_summary(
    range: str = Query("week", regex="^(week|month|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Общая статистика по интервью"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Определяем временной диапазон
    now = datetime.utcnow()
    if range == "week":
        start_date = now - timedelta(days=7)
    elif range == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = datetime.min
    
    # Общее количество интервью
    total_interviews = db.query(InterviewSession).filter(
        InterviewSession.created_at >= start_date
    ).count()
    
    # Завершенные интервью
    completed_interviews = db.query(InterviewSession).filter(
        InterviewSession.created_at >= start_date,
        InterviewSession.status == InterviewStatus.COMPLETED
    ).count()
    
    # Активные интервью
    active_interviews = db.query(InterviewSession).filter(
        InterviewSession.status == InterviewStatus.IN_PROGRESS
    ).count()
    
    # Средний балл
    avg_score = db.query(func.avg(InterviewSession.total_score)).filter(
        InterviewSession.created_at >= start_date,
        InterviewSession.status == InterviewStatus.COMPLETED,
        InterviewSession.total_score.isnot(None)
    ).scalar() or 0
    
    # Процент прохождения (балл >= 60)
    passed_count = db.query(InterviewSession).filter(
        InterviewSession.created_at >= start_date,
        InterviewSession.status == InterviewStatus.COMPLETED,
        InterviewSession.total_score >= 60
    ).count()
    
    pass_rate = (passed_count / completed_interviews * 100) if completed_interviews > 0 else 0
    
    # Средняя длительность (в минутах)
    sessions = db.query(InterviewSession).filter(
        InterviewSession.created_at >= start_date,
        InterviewSession.status == InterviewStatus.COMPLETED,
        InterviewSession.started_at.isnot(None),
        InterviewSession.completed_at.isnot(None)
    ).all()
    
    if sessions:
        total_duration = sum(
            (s.completed_at - s.started_at).total_seconds() / 60
            for s in sessions
        )
        average_duration = total_duration / len(sessions)
    else:
        average_duration = 0
    
    return {
        "totalInterviews": total_interviews,
        "completedInterviews": completed_interviews,
        "activeInterviews": active_interviews,
        "averageScore": round(avg_score, 1),
        "passRate": round(pass_rate, 1),
        "averageDuration": round(average_duration, 1),
    }


@router.get("/topics")
async def get_topic_statistics(
    range: str = Query("week", regex="^(week|month|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Статистика по темам вопросов"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Определяем временной диапазон
    now = datetime.utcnow()
    if range == "week":
        start_date = now - timedelta(days=7)
    elif range == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = datetime.min
    
    # Получаем статистику по темам
    topic_stats = db.query(
        Question.topic,
        func.count(Question.id).label('count'),
        func.avg(Answer.score).label('avg_score')
    ).join(Answer, Question.id == Answer.question_id).join(
        InterviewSession, Question.session_id == InterviewSession.id
    ).filter(
        InterviewSession.created_at >= start_date,
        Question.topic != 'ready_check',
        Answer.score.isnot(None)
    ).group_by(Question.topic).all()
    
    topics = []
    for topic, count, avg_score in topic_stats:
        if topic:
            topics.append({
                "topic": topic,
                "count": count,
                "averageScore": round(avg_score or 0, 1),
                "passRate": 0,  # TODO: рассчитать процент прохождения
            })
    
    # Сортируем по количеству
    topics.sort(key=lambda x: x['count'], reverse=True)
    
    return {"topics": topics[:10]}  # Топ-10 тем


@router.get("/top-candidates")
async def get_top_candidates(
    range: str = Query("week", regex="^(week|month|all)$"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Топ кандидаты по результатам"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Определяем временной диапазон
    now = datetime.utcnow()
    if range == "week":
        start_date = now - timedelta(days=7)
    elif range == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = datetime.min
    
    # Получаем топ кандидатов
    sessions = db.query(InterviewSession).join(
        User, InterviewSession.candidate_id == User.id
    ).filter(
        InterviewSession.created_at >= start_date,
        InterviewSession.status == InterviewStatus.COMPLETED,
        InterviewSession.total_score.isnot(None)
    ).order_by(desc(InterviewSession.total_score)).limit(limit).all()
    
    candidates = []
    for session in sessions:
        candidate = session.candidate
        candidates.append({
            "id": candidate.id,
            "name": candidate.username,
            "email": candidate.email,
            "score": round(session.total_score, 1),
            "completedAt": session.completed_at.isoformat() if session.completed_at else None,
            "position": session.interview.position if session.interview else None,
        })
    
    return {"candidates": candidates}


@router.get("/trends")
async def get_trends(
    metric: str = Query("score", regex="^(score|duration|count)$"),
    period: str = Query("week", regex="^(week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Тренды метрик по дням"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # TODO: Реализовать агрегацию по дням
    # Это требует более сложных SQL запросов с GROUP BY дате
    
    return {"trends": [], "message": "В разработке"}

