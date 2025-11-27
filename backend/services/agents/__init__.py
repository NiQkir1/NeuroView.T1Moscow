"""
Модуль агентов LangChain для интервью
"""
from backend.services.agents.base_agent import BaseAgent
from backend.services.agents.general_agent import GeneralQuestionAgent
from backend.services.agents.technical_agent import TechnicalQuestionAgent
from backend.services.agents.coding_agent import CodingAgent
from backend.services.agents.emotion_agent import EmotionAgent
from backend.services.agents.report_agent import ReportAgent, report_agent

__all__ = [
    "BaseAgent",
    "GeneralQuestionAgent",
    "TechnicalQuestionAgent",
    "CodingAgent",
    "EmotionAgent",
    "ReportAgent",
    "report_agent",
]

# Глобальные экземпляры агентов
# Модели для разных типов задач:
# - qwen3-32b-awq: общие вопросы, знакомство, soft skills
# - qwen3-coder-30b-a3b-instruct-fp8: технические вопросы и лайфкодинг
general_agent = GeneralQuestionAgent(model_override="qwen3-32b-awq")
technical_agent = TechnicalQuestionAgent(model_override="qwen3-coder-30b-a3b-instruct-fp8")
coding_agent = CodingAgent(model_override="qwen3-coder-30b-a3b-instruct-fp8")
emotion_agent = EmotionAgent(model_override="qwen3-32b-awq")














