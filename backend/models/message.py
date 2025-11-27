"""Модели для сообщений и чата"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.models import Base


class MessageStatus(str, enum.Enum):
    """Статусы сообщений"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


class Message(Base):
    """Модель сообщения в чате"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.SENT, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    # Связи
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])


class InterviewInvitation(Base):
    """Модель приглашения на собеседование"""
    __tablename__ = "interview_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hr_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=True)  # Персональное сообщение от HR
    status = Column(String, default="pending", nullable=False, index=True)  # pending, accepted, declined, expired
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    responded_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Срок действия приглашения
    
    # Связи
    interview = relationship("Interview", backref="invitations")
    candidate = relationship("User", foreign_keys=[candidate_id])
    hr = relationship("User", foreign_keys=[hr_id])






