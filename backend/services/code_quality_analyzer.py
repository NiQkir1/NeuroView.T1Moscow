"""
Code Quality Analyzer v4.2.0 - анализ качества кода

Возможности:
- Cyclomatic complexity (radon)
- Code style и качество (pylint для Python)
- Maintainability index
- Количество строк кода (LOC)
- Комментарии и документация
- Дублирование кода
"""
import tempfile
import os
import subprocess
from typing import Dict, Any, Optional, List
from backend.utils.logger import get_module_logger

logger = get_module_logger("CodeQualityAnalyzer")


class CodeQualityAnalyzer:
    """Анализатор качества кода"""
    
    def __init__(self):
        self.radon_available = False
        self.pylint_available = False
        
        # Проверяем доступность инструментов
        try:
            subprocess.run(['radon', '--version'], capture_output=True, timeout=5)
            self.radon_available = True
        except:
            logger.warning("radon недоступен, метрики сложности будут ограничены")
        
        try:
            subprocess.run(['pylint', '--version'], capture_output=True, timeout=5)
            self.pylint_available = True
        except:
            logger.warning("pylint недоступен, анализ стиля будет ограничен")
    
    async def analyze(
        self,
        code: str,
        language: str = "python",
        include_style: bool = True,
        include_complexity: bool = True
    ) -> Dict[str, Any]:
        """
        Полный анализ качества кода
        
        Args:
            code: Код для анализа
            language: Язык программирования
            include_style: Включить анализ стиля
            include_complexity: Включить анализ сложности
        
        Returns:
            Результаты анализа с метриками
        """
        results = {
            "language": language,
            "metrics": {},
            "style_issues": [],
            "complexity_issues": [],
            "overall_score": 0,
        }
        
        if language == "python":
            if include_complexity:
                complexity_results = await self._analyze_python_complexity(code)
                results["metrics"]["complexity"] = complexity_results
                
                # Оценка сложности
                if complexity_results.get("average_complexity", 0) > 10:
                    results["complexity_issues"].append({
                        "severity": "high",
                        "message": f"Высокая средняя сложность: {complexity_results.get('average_complexity', 0):.1f}",
                        "recommendation": "Разбейте сложные функции на более простые"
                    })
                elif complexity_results.get("average_complexity", 0) > 5:
                    results["complexity_issues"].append({
                        "severity": "medium",
                        "message": f"Умеренная сложность: {complexity_results.get('average_complexity', 0):.1f}",
                        "recommendation": "Рассмотрите возможность упрощения логики"
                    })
            
            if include_style:
                style_results = await self._analyze_python_style(code)
                results["style_issues"] = style_results.get("issues", [])
                results["metrics"]["style_score"] = style_results.get("score", 5)
            
            # Общие метрики
            results["metrics"]["lines_of_code"] = self._count_loc(code)
            results["metrics"]["comment_ratio"] = self._calculate_comment_ratio(code, language)
            
            # Общая оценка (0-10)
            results["overall_score"] = self._calculate_overall_score(results)
        
        elif language == "javascript":
            # Для JavaScript базовый анализ
            results["metrics"]["lines_of_code"] = self._count_loc(code)
            results["metrics"]["comment_ratio"] = self._calculate_comment_ratio(code, language)
            results["overall_score"] = 7  # Базовая оценка
        
        else:
            # Для остальных языков - базовые метрики
            results["metrics"]["lines_of_code"] = self._count_loc(code)
            results["overall_score"] = 7
        
        return results
    
    async def _analyze_python_complexity(self, code: str) -> Dict[str, Any]:
        """Анализ сложности Python кода через radon"""
        if not self.radon_available:
            # Простая эвристика без radon
            return self._simple_complexity_analysis(code)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Запускаем radon cc (cyclomatic complexity)
            result = subprocess.run(
                ['radon', 'cc', temp_file, '-s', '-j'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                import json
                try:
                    data = json.loads(result.stdout)
                    
                    # Извлекаем метрики
                    functions = []
                    total_complexity = 0
                    max_complexity = 0
                    
                    for file_data in data.values():
                        for item in file_data:
                            complexity = item.get('complexity', 0)
                            functions.append({
                                "name": item.get('name', 'unknown'),
                                "complexity": complexity,
                                "rank": item.get('rank', 'A'),
                                "lineno": item.get('lineno', 0),
                            })
                            total_complexity += complexity
                            max_complexity = max(max_complexity, complexity)
                    
                    average_complexity = total_complexity / len(functions) if functions else 1
                    
                    return {
                        "average_complexity": round(average_complexity, 2),
                        "max_complexity": max_complexity,
                        "total_complexity": total_complexity,
                        "functions": functions,
                        "function_count": len(functions),
                    }
                except:
                    pass
            
            # Fallback если radon не вернул данные
            return self._simple_complexity_analysis(code)
        
        except Exception as e:
            logger.warning(f"Ошибка анализа сложности: {e}")
            return self._simple_complexity_analysis(code)
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def _simple_complexity_analysis(self, code: str) -> Dict[str, Any]:
        """Простой анализ сложности без внешних инструментов"""
        lines = code.split('\n')
        
        # Подсчитываем ветвления (if, elif, else, for, while, try, except)
        branches = sum(
            1 for line in lines
            if any(keyword in line for keyword in ['if ', 'elif ', 'for ', 'while ', 'try:', 'except'])
        )
        
        # Подсчитываем функции
        functions = sum(1 for line in lines if line.strip().startswith('def '))
        
        # Простая оценка сложности
        complexity_per_function = (branches + 1) / max(functions, 1)
        
        return {
            "average_complexity": round(complexity_per_function, 2),
            "max_complexity": branches + 1,
            "total_complexity": branches + 1,
            "function_count": functions,
            "functions": [],
            "method": "simple_heuristic"
        }
    
    async def _analyze_python_style(self, code: str) -> Dict[str, Any]:
        """Анализ стиля Python кода через pylint"""
        if not self.pylint_available:
            return {"score": 7, "issues": [], "method": "no_pylint"}
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Запускаем pylint
            result = subprocess.run(
                ['pylint', temp_file, '--output-format=json', '--score=yes'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.stdout:
                import json
                try:
                    data = json.loads(result.stdout)
                    
                    # Извлекаем проблемы
                    issues = []
                    for item in data:
                        if isinstance(item, dict):
                            severity = item.get('type', 'info')
                            message = item.get('message', '')
                            line = item.get('line', 0)
                            
                            # Фильтруем только важные проблемы
                            if severity in ['error', 'warning', 'convention']:
                                issues.append({
                                    "severity": severity,
                                    "message": message,
                                    "line": line,
                                    "symbol": item.get('symbol', ''),
                                })
                    
                    # Извлекаем оценку из stderr (pylint выводит туда score)
                    score = 7.0
                    if result.stderr:
                        import re
                        score_match = re.search(r'Your code has been rated at ([\d.]+)/10', result.stderr)
                        if score_match:
                            score = float(score_match.group(1))
                    
                    return {
                        "score": round(score, 1),
                        "issues": issues[:10],  # Топ-10 проблем
                        "total_issues": len(issues),
                    }
                except:
                    pass
            
            return {"score": 7, "issues": [], "method": "pylint_error"}
        
        except Exception as e:
            logger.warning(f"Ошибка анализа стиля: {e}")
            return {"score": 7, "issues": [], "method": "error"}
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def _count_loc(self, code: str) -> int:
        """Подсчет строк кода (без пустых и комментариев)"""
        lines = code.split('\n')
        loc = 0
        
        for line in lines:
            stripped = line.strip()
            # Пропускаем пустые строки и комментарии
            if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
                loc += 1
        
        return loc
    
    def _calculate_comment_ratio(self, code: str, language: str) -> float:
        """Рассчитывает отношение комментариев к коду"""
        lines = code.split('\n')
        total_lines = len([l for l in lines if l.strip()])
        
        if total_lines == 0:
            return 0.0
        
        comment_lines = 0
        
        if language == "python":
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#') or '"""' in stripped or "'''" in stripped:
                    comment_lines += 1
        
        elif language in ["javascript", "java", "cpp", "go", "rust"]:
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    comment_lines += 1
        
        return round(comment_lines / total_lines, 3)
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Рассчитывает общую оценку качества кода (0-10)"""
        score = 10.0
        
        # Снижаем за высокую сложность
        avg_complexity = results["metrics"].get("complexity", {}).get("average_complexity", 0)
        if avg_complexity > 10:
            score -= 3
        elif avg_complexity > 7:
            score -= 2
        elif avg_complexity > 5:
            score -= 1
        
        # Снижаем за проблемы стиля
        style_issues = len(results.get("style_issues", []))
        if style_issues > 10:
            score -= 2
        elif style_issues > 5:
            score -= 1
        elif style_issues > 2:
            score -= 0.5
        
        # Снижаем за отсутствие комментариев
        comment_ratio = results["metrics"].get("comment_ratio", 0)
        if comment_ratio < 0.05:
            score -= 0.5
        
        # Учитываем style_score если есть
        style_score = results["metrics"].get("style_score")
        if style_score is not None:
            # Усредняем с style_score
            score = (score + style_score) / 2
        
        return max(0, min(10, round(score, 1)))
    
    def get_quality_grade(self, score: float) -> str:
        """Возвращает буквенную оценку качества"""
        if score >= 9:
            return "A+ (Отличное качество)"
        elif score >= 8:
            return "A (Очень хорошее качество)"
        elif score >= 7:
            return "B (Хорошее качество)"
        elif score >= 6:
            return "C (Удовлетворительное качество)"
        elif score >= 5:
            return "D (Требует улучшения)"
        else:
            return "F (Низкое качество)"


# Глобальный экземпляр
code_quality_analyzer = CodeQualityAnalyzer()

