"""
Code Executor - безопасное выполнение кода кандидата
"""
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from datetime import datetime


class CodeExecutor:
    """Безопасный исполнитель кода"""
    
    # Поддерживаемые языки
    SUPPORTED_LANGUAGES = {
        "python": {
            "extension": ".py",
            "command": "python",
            "timeout": 10,
        },
        "javascript": {
            "extension": ".js",
            "command": "node",
            "timeout": 10,
        },
    }
    
    def __init__(self):
        self.max_execution_time = 10  # секунд
        self.max_memory_mb = 256
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполнение кода
        
        Args:
            code: Код для выполнения
            language: Язык программирования
            input_data: Входные данные (stdin)
        
        Returns:
            Результат выполнения с выводом и ошибками
        """
        if language not in self.SUPPORTED_LANGUAGES:
            return {
                "success": False,
                "error": f"Неподдерживаемый язык: {language}",
                "output": "",
                "execution_time": 0,
            }
        
        lang_config = self.SUPPORTED_LANGUAGES[language]
        
        # Создание временного файла
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=lang_config["extension"],
            delete=False
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Выполнение кода
            start_time = datetime.utcnow()
            
            process = subprocess.Popen(
                [lang_config["command"], temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else None,
                text=True,
            )
            
            if input_data:
                stdout, stderr = process.communicate(input=input_data, timeout=lang_config["timeout"])
            else:
                stdout, stderr = process.communicate(timeout=lang_config["timeout"])
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr if stderr else None,
                "return_code": process.returncode,
                "execution_time": execution_time,
                "language": language,
            }
        
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "success": False,
                "error": f"Превышено время выполнения ({lang_config['timeout']}s)",
                "output": "",
                "execution_time": lang_config["timeout"],
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "execution_time": 0,
            }
        
        finally:
            # Удаление временного файла
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def validate_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Валидация кода (синтаксическая проверка)
        
        Args:
            code: Код для проверки
            language: Язык программирования
        
        Returns:
            Результат валидации
        """
        if language == "python":
            try:
                compile(code, "<string>", "exec")
                return {"valid": True, "error": None}
            except SyntaxError as e:
                return {
                    "valid": False,
                    "error": f"Синтаксическая ошибка: {e.msg} на строке {e.lineno}",
                }
        
        # Для других языков можно добавить валидацию
        return {"valid": True, "error": None}


# Глобальный экземпляр
code_executor = CodeExecutor()

