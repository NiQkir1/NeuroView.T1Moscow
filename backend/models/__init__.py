"""Модели данных"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .interview import (
    Interview, InterviewSession, Question, Answer, TestTask,
    InterviewStatus, QuestionType, ApplicationStatus
)
from .user import User, Role, RoleType, ExperienceLevel
from .message import Message, MessageStatus, InterviewInvitation

__all__ = [
    "Base",
    "Interview",
    "InterviewSession",
    "Question",
    "Answer",
    "TestTask",
    "InterviewStatus",
    "QuestionType",
    "ApplicationStatus",
    "User",
    "Role",
    "RoleType",
    "ExperienceLevel",
    "Message",
    "MessageStatus",
    "InterviewInvitation",
]

