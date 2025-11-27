"""
Утилита управления тест-кейсами для coding задач.

Файл был удалён вместе с тестами, но на него ссылается CodingAgent.
Ниже реализован облегчённый вариант менеджера, достаточный для
генерации и фильтрации тестов в рантайме.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import itertools
import uuid


@dataclass
class TestCase:
    """Единичный тест-кейс."""

    input: Any
    expected_output: Any
    description: str = ""
    visible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "input": self.input,
            "expected_output": self.expected_output,
            "description": self.description,
            "visible": self.visible,
        }


class TestCaseManager:
    """
    Мини-менеджер тестов.

    Обязанности:
    - нормализация базовых тестов, предоставленных агентом
    - автогенерация пары скрытых тестов при необходимости
    - выборка видимых тестов для кандидата
    """

    _difficulty_hidden_multiplier = {
        "easy": 0,
        "medium": 1,
        "hard": 2,
    }

    def create_test_suite(
        self,
        task_type: str,
        difficulty: str,
        basic_tests: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        basic_tests = basic_tests or []
        normalized: List[TestCase] = []

        for idx, test in enumerate(basic_tests):
            normalized.append(
                TestCase(
                    input=test.get("input"),
                    expected_output=test.get("expected_output"),
                    description=test.get("description", f"Тест #{idx + 1}"),
                    visible=test.get("visible", True),
                )
            )

        # Добавляем скрытые тесты, чтобы бэкенд мог прогонять более строгую проверку
        hidden_count = self._difficulty_hidden_multiplier.get(difficulty, 1)
        if hidden_count > 0:
            for i in range(hidden_count):
                normalized.append(
                    TestCase(
                        input=f"hidden_case_{i}",
                        expected_output="__auto__",
                        description="Скрытый тест",
                        visible=False,
                    )
                )

        return {
            "task_type": task_type,
            "difficulty": difficulty,
            "tests": [case.as_dict() for case in normalized],
        }

    def filter_visible_tests(self, test_suite: Dict[str, Any]) -> List[Dict[str, Any]]:
        tests = test_suite.get("tests", [])
        return [test for test in tests if test.get("visible", True)]

    def iter_hidden_tests(self, test_suite: Dict[str, Any]):
        tests = test_suite.get("tests", [])
        for test in tests:
            if not test.get("visible", True):
                yield test


# Глобальный экземпляр для импорта
test_case_manager = TestCaseManager()



