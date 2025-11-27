"""
Message Service - управление сообщениями и чатом
Chat & Invitations v2.0.0
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.models.message import Message, MessageStatus, InterviewInvitation
from backend.models.user import User


class MessageService:
    """Сервис для управления сообщениями"""
    
    async def send_message(
        self,
        db: Session,
        sender_id: int,
        recipient_id: int,
        message_text: str
    ) -> Message:
        """Отправка сообщения"""
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_text=message_text,
            status=MessageStatus.SENT
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    async def get_conversation(
        self,
        db: Session,
        user1_id: int,
        user2_id: int,
        limit: int = 50
    ) -> List[Message]:
        """Получение истории переписки между двумя пользователями"""
        messages = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user1_id, Message.recipient_id == user2_id),
                and_(Message.sender_id == user2_id, Message.recipient_id == user1_id)
            )
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        return list(reversed(messages))  # Возвращаем в хронологическом порядке
    
    async def mark_as_read(
        self,
        db: Session,
        message_id: int,
        user_id: int
    ) -> Message:
        """Отметка сообщения как прочитанного"""
        message = db.query(Message).filter(
            Message.id == message_id,
            Message.recipient_id == user_id
        ).first()
        
        if message:
            message.status = MessageStatus.READ
            message.read_at = datetime.utcnow()
            db.commit()
            db.refresh(message)
        
        return message
    
    async def get_unread_count(
        self,
        db: Session,
        user_id: int
    ) -> int:
        """Получение количества непрочитанных сообщений"""
        count = db.query(Message).filter(
            Message.recipient_id == user_id,
            Message.status != MessageStatus.READ
        ).count()
        return count
    
    async def get_conversations_list(
        self,
        db: Session,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Получение списка всех переписок пользователя"""
        # Получаем всех собеседников
        sent_messages = db.query(Message.recipient_id).filter(
            Message.sender_id == user_id
        ).distinct().all()
        
        received_messages = db.query(Message.sender_id).filter(
            Message.recipient_id == user_id
        ).distinct().all()
        
        # Объединяем уникальные ID собеседников
        interlocutor_ids = set()
        for msg in sent_messages:
            interlocutor_ids.add(msg[0])
        for msg in received_messages:
            interlocutor_ids.add(msg[0])
        
        # Получаем информацию о собеседниках и последних сообщениях
        conversations = []
        for interlocutor_id in interlocutor_ids:
            user = db.query(User).filter(User.id == interlocutor_id).first()
            if not user:
                continue
            
            # Получаем последнее сообщение
            last_message = db.query(Message).filter(
                or_(
                    and_(Message.sender_id == user_id, Message.recipient_id == interlocutor_id),
                    and_(Message.sender_id == interlocutor_id, Message.recipient_id == user_id)
                )
            ).order_by(Message.created_at.desc()).first()
            
            # Считаем непрочитанные
            unread_count = db.query(Message).filter(
                Message.sender_id == interlocutor_id,
                Message.recipient_id == user_id,
                Message.status != MessageStatus.READ
            ).count()
            
            conversations.append({
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "last_message": {
                    "text": last_message.message_text if last_message else None,
                    "created_at": last_message.created_at.isoformat() if last_message else None,
                    "is_from_me": last_message.sender_id == user_id if last_message else False
                },
                "unread_count": unread_count
            })
        
        # Сортируем по времени последнего сообщения
        conversations.sort(
            key=lambda x: x["last_message"]["created_at"] or "",
            reverse=True
        )
        
        return conversations


class InvitationService:
    """Сервис для управления приглашениями на собеседования"""
    
    async def create_invitation(
        self,
        db: Session,
        interview_id: int,
        candidate_id: int,
        hr_id: int,
        message: Optional[str] = None,
        expires_in_days: int = 7
    ) -> InterviewInvitation:
        """Создание приглашения на собеседование"""
        invitation = InterviewInvitation(
            interview_id=interview_id,
            candidate_id=candidate_id,
            hr_id=hr_id,
            message=message,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation
    
    async def get_candidate_invitations(
        self,
        db: Session,
        candidate_id: int
    ) -> List[InterviewInvitation]:
        """Получение всех приглашений кандидата"""
        invitations = db.query(InterviewInvitation).filter(
            InterviewInvitation.candidate_id == candidate_id
        ).order_by(InterviewInvitation.created_at.desc()).all()
        return invitations
    
    async def accept_invitation(
        self,
        db: Session,
        invitation_id: int,
        candidate_id: int
    ) -> InterviewInvitation:
        """Принятие приглашения"""
        invitation = db.query(InterviewInvitation).filter(
            InterviewInvitation.id == invitation_id,
            InterviewInvitation.candidate_id == candidate_id
        ).first()
        
        if not invitation:
            raise ValueError("Приглашение не найдено")
        
        if invitation.status != "pending":
            raise ValueError("Приглашение уже обработано")
        
        if invitation.expires_at and invitation.expires_at < datetime.utcnow():
            invitation.status = "expired"
            db.commit()
            raise ValueError("Приглашение истекло")
        
        invitation.status = "accepted"
        invitation.responded_at = datetime.utcnow()
        db.commit()
        db.refresh(invitation)
        
        return invitation
    
    async def decline_invitation(
        self,
        db: Session,
        invitation_id: int,
        candidate_id: int
    ) -> InterviewInvitation:
        """Отклонение приглашения"""
        invitation = db.query(InterviewInvitation).filter(
            InterviewInvitation.id == invitation_id,
            InterviewInvitation.candidate_id == candidate_id
        ).first()
        
        if not invitation:
            raise ValueError("Приглашение не найдено")
        
        if invitation.status != "pending":
            raise ValueError("Приглашение уже обработано")
        
        invitation.status = "declined"
        invitation.responded_at = datetime.utcnow()
        db.commit()
        db.refresh(invitation)
        
        return invitation


# Глобальные экземпляры
message_service = MessageService()
invitation_service = InvitationService()

