"""
Communication Automation Service - автоматизация коммуникаций
Mercor AI v2.0.0: Автоматизация коммуникаций
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session


class CommunicationAutomation:
    """Сервис для автоматизации коммуникаций с кандидатами"""
    
    async def send_interview_scheduled_notification(
        self,
        candidate_email: str,
        interview_date: datetime,
        interview_title: str,
        access_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправка уведомления о запланированном интервью
        TODO: Интеграция с email/SMS сервисами
        """
        message = f"""
Уважаемый кандидат,

Ваше интервью "{interview_title}" запланировано на {interview_date.strftime("%d.%m.%Y %H:%M")}.

{f'Код доступа: {access_code}' if access_code else ''}

Пожалуйста, будьте готовы к началу интервью.
"""
        
        # TODO: Реальная отправка через email/SMS API
        return {
            "status": "sent",
            "method": "email",
            "recipient": candidate_email,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def send_interview_reminder(
        self,
        candidate_email: str,
        interview_date: datetime,
        hours_before: int = 24
    ) -> Dict[str, Any]:
        """Отправка напоминания об интервью"""
        message = f"""
Напоминание: Ваше интервью состоится через {hours_before} часов ({interview_date.strftime("%d.%m.%Y %H:%M")}).

Пожалуйста, убедитесь, что вы готовы.
"""
        
        # TODO: Реальная отправка
        return {
            "status": "sent",
            "method": "email",
            "recipient": candidate_email,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def send_interview_completed_notification(
        self,
        candidate_email: str,
        interview_title: str,
        score: Optional[float] = None
    ) -> Dict[str, Any]:
        """Отправка уведомления о завершении интервью"""
        if score is not None:
            message = f"""
Спасибо за участие в интервью "{interview_title}".

Ваша оценка: {score:.1f}/100

Результаты будут обработаны, и мы свяжемся с вами в ближайшее время.
"""
        else:
            message = f"""
Спасибо за участие в интервью "{interview_title}".

Результаты будут обработаны, и мы свяжемся с вами в ближайшее время.
"""
        
        # TODO: Реальная отправка
        return {
            "status": "sent",
            "method": "email",
            "recipient": candidate_email,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def generate_follow_up_message(
        self,
        session_id: int,
        db: Session
    ) -> str:
        """Генерация персонализированного follow-up сообщения"""
        from backend.models.interview import InterviewSession
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            return "Спасибо за участие в интервью."
        
        score = session.total_score
        interview_title = session.interview.title
        
        if score is None:
            return f"Спасибо за участие в интервью '{interview_title}'. Результаты будут обработаны."
        
        if score >= 80:
            return f"""
Отличная работа на интервью '{interview_title}'! 
Ваша оценка: {score:.1f}/100. Мы впечатлены вашими знаниями и навыками.
"""
        elif score >= 60:
            return f"""
Спасибо за участие в интервью '{interview_title}'.
Ваша оценка: {score:.1f}/100. Вы показали хорошие результаты.
"""
        else:
            return f"""
Спасибо за участие в интервью '{interview_title}'.
Ваша оценка: {score:.1f}/100. Рекомендуем дополнительную подготовку.
"""
    
    async def schedule_follow_up(
        self,
        candidate_email: str,
        days_after: int = 7
    ) -> Dict[str, Any]:
        """Планирование follow-up сообщения"""
        follow_up_date = datetime.utcnow() + timedelta(days=days_after)
        
        # TODO: Интеграция с системой планирования задач
        return {
            "scheduled": True,
            "follow_up_date": follow_up_date.isoformat(),
            "recipient": candidate_email
        }
    
    # v3.0.0: Новые функции автоматизации
    
    async def notify_status_change(
        self,
        candidate_email: str,
        candidate_name: str,
        old_status: str,
        new_status: str,
        interview_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Уведомление об изменении статуса заявки"""
        status_messages = {
            "test_task": "Вам отправлено тестовое задание. Пожалуйста, выполните его в указанные сроки.",
            "finalist": "Поздравляем! Вы прошли в финальный отбор. Мы свяжемся с вами в ближайшее время.",
            "offer": "Поздравляем! Вам направлено предложение о работе. Пожалуйста, ознакомьтесь с деталями.",
            "rejected": "К сожалению, на данном этапе мы не можем предложить вам позицию. Спасибо за интерес к нашей компании."
        }
        
        message = f"""
Уважаемый(ая) {candidate_name},

Статус вашей заявки на позицию "{interview_title or 'разработчик'}" изменен.

Новый статус: {new_status}
{status_messages.get(new_status, '')}

С уважением,
Команда NeuroView
"""
        
        # TODO: Реальная отправка
        return {
            "status": "sent",
            "method": "email",
            "recipient": candidate_email,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def send_test_task_notification(
        self,
        candidate_email: str,
        candidate_name: str,
        task_title: str,
        deadline: datetime,
        interview_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Уведомление о получении тестового задания"""
        message = f"""
Уважаемый(ая) {candidate_name},

Вам отправлено тестовое задание для позиции "{interview_title or 'разработчик'}".

Название задания: {task_title}
Дедлайн: {deadline.strftime("%d.%m.%Y %H:%M")}

Пожалуйста, выполните задание до указанного срока.

С уважением,
Команда NeuroView
"""
        
        # TODO: Реальная отправка
        return {
            "status": "sent",
            "method": "email",
            "recipient": candidate_email,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def send_test_task_reminder(
        self,
        candidate_email: str,
        candidate_name: str,
        task_title: str,
        deadline: datetime
    ) -> Dict[str, Any]:
        """Напоминание о приближающемся дедлайне тестового задания"""
        hours_left = (deadline - datetime.utcnow()).total_seconds() / 3600
        
        message = f"""
Уважаемый(ая) {candidate_name},

Напоминаем, что дедлайн выполнения тестового задания "{task_title}" истекает через {int(hours_left)} часов.

Дедлайн: {deadline.strftime("%d.%m.%Y %H:%M")}

Пожалуйста, убедитесь, что вы отправили решение вовремя.

С уважением,
Команда NeuroView
"""
        
        # TODO: Реальная отправка
        return {
            "status": "sent",
            "method": "email",
            "recipient": candidate_email,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }


# Глобальный экземпляр
communication_automation = CommunicationAutomation()


