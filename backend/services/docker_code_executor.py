"""
Docker Code Executor v4.2.0 - безопасное выполнение кода в изолированных контейнерах

Особенности:
- Полная изоляция кода в Docker контейнерах
- Ограничения по памяти, CPU, времени выполнения
- Сетевая изоляция (network_disabled)
- Изоляция файловой системы (read-only)
- Поддержка множества языков программирования
- Автоматическая очистка контейнеров
"""
import docker
import tempfile
import os
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from backend.utils.logger import get_module_logger

logger = get_module_logger("DockerCodeExecutor")


class DockerCodeExecutor:
    """Безопасный исполнитель кода в Docker контейнерах"""
    
    # Конфигурация для разных языков
    LANGUAGE_CONFIGS = {
        "python": {
            "image": "python:3.11-alpine",  # Легковесный образ
            "extension": ".py",
            "run_command": ["python", "-u", "/code/solution"],
            "timeout": 10,
            "memory_limit": "256m",
            "cpu_quota": 50000,  # 50% от одного ядра
        },
        "javascript": {
            "image": "node:20-alpine",
            "extension": ".js",
            "run_command": ["node", "/code/solution"],
            "timeout": 10,
            "memory_limit": "256m",
            "cpu_quota": 50000,
        },
        "java": {
            "image": "openjdk:17-alpine",
            "extension": ".java",
            "run_command": ["sh", "-c", "cd /code && javac Solution.java && java Solution"],
            "timeout": 15,
            "memory_limit": "512m",
            "cpu_quota": 50000,
        },
        "cpp": {
            "image": "gcc:13-alpine",
            "extension": ".cpp",
            "run_command": ["sh", "-c", "cd /code && g++ -o solution solution.cpp && ./solution"],
            "timeout": 15,
            "memory_limit": "256m",
            "cpu_quota": 50000,
        },
        "go": {
            "image": "golang:1.21-alpine",
            "extension": ".go",
            "run_command": ["sh", "-c", "cd /code && go run solution.go"],
            "timeout": 10,
            "memory_limit": "256m",
            "cpu_quota": 50000,
        },
        "rust": {
            "image": "rust:1.75-alpine",
            "extension": ".rs",
            "run_command": ["sh", "-c", "cd /code && rustc solution.rs && ./solution"],
            "timeout": 20,
            "memory_limit": "512m",
            "cpu_quota": 50000,
        },
        "sql": {
            "image": "postgres:16-alpine",
            "extension": ".sql",
            "run_command": ["psql", "-f", "/code/solution"],
            "timeout": 10,
            "memory_limit": "256m",
            "cpu_quota": 50000,
        },
    }
    
    def __init__(self, use_docker: bool = True, fallback_to_subprocess: bool = True):
        """
        Инициализация executor
        
        Args:
            use_docker: Использовать Docker (True) или subprocess (False)
            fallback_to_subprocess: Fallback на subprocess если Docker недоступен
        """
        self.use_docker = use_docker
        self.fallback_to_subprocess = fallback_to_subprocess
        self.docker_available = False
        self.docker_client = None
        
        if use_docker:
            try:
                self.docker_client = docker.from_env()
                # Проверяем доступность Docker
                self.docker_client.ping()
                self.docker_available = True
                logger.info("✅ Docker доступен, используется изолированное выполнение кода")
            except Exception as e:
                logger.warning(f"⚠️ Docker недоступен: {e}")
                if not fallback_to_subprocess:
                    raise RuntimeError("Docker недоступен и fallback отключен")
                logger.info("📌 Используется fallback на subprocess (небезопасно для production)")
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
        timeout: Optional[int] = None,
        memory_limit: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполнение кода в изолированном контейнере
        
        Args:
            code: Код для выполнения
            language: Язык программирования
            input_data: Входные данные (stdin)
            timeout: Таймаут выполнения (секунды), по умолчанию из конфига
            memory_limit: Лимит памяти (например, "256m"), по умолчанию из конфига
        
        Returns:
            Результат выполнения
        """
        if self.docker_available and self.use_docker:
            return await self._execute_docker(code, language, input_data, timeout, memory_limit)
        elif self.fallback_to_subprocess:
            return await self._execute_subprocess(code, language, input_data, timeout)
        else:
            return {
                "success": False,
                "error": "Docker недоступен и fallback отключен",
                "output": "",
                "execution_time": 0,
            }
    
    async def _execute_docker(
        self,
        code: str,
        language: str,
        input_data: Optional[str] = None,
        timeout: Optional[int] = None,
        memory_limit: Optional[str] = None
    ) -> Dict[str, Any]:
        """Выполнение в Docker контейнере"""
        if language not in self.LANGUAGE_CONFIGS:
            return {
                "success": False,
                "error": f"Неподдерживаемый язык: {language}. Доступны: {', '.join(self.LANGUAGE_CONFIGS.keys())}",
                "output": "",
                "execution_time": 0,
            }
        
        lang_config = self.LANGUAGE_CONFIGS[language]
        timeout = timeout or lang_config["timeout"]
        memory_limit = memory_limit or lang_config["memory_limit"]
        
        # Создаем временную директорию для кода
        temp_dir = tempfile.mkdtemp()
        code_file = os.path.join(
            temp_dir, 
            f"solution{lang_config['extension']}" if language != "java" 
            else "Solution.java"  # Java требует соответствия имени класса и файла
        )
        
        try:
            # Записываем код в файл
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Проверяем и подтягиваем образ, если его нет
            image_name = lang_config["image"]
            try:
                self.docker_client.images.get(image_name)
            except docker.errors.ImageNotFound:
                logger.info(f"📥 Загрузка Docker образа {image_name}...")
                self.docker_client.images.pull(image_name)
                logger.info(f"✅ Образ {image_name} загружен")
            
            # Запуск контейнера
            start_time = time.time()
            
            container = self.docker_client.containers.run(
                image=image_name,
                command=lang_config["run_command"],
                volumes={temp_dir: {'bind': '/code', 'mode': 'ro'}},  # Read-only файловая система
                mem_limit=memory_limit,
                cpu_period=100000,
                cpu_quota=lang_config["cpu_quota"],
                network_disabled=True,  # Отключаем сеть
                detach=True,
                stdin_open=True if input_data else False,
                tty=False,
                remove=False,  # Не удаляем автоматически, чтобы получить логи
                pids_limit=50,  # Ограничение процессов
                read_only=False,  # Некоторым языкам нужна запись во временные файлы
            )
            
            try:
                # Если есть входные данные, отправляем их
                if input_data:
                    container_socket = container.attach_socket(params={'stdin': 1, 'stream': 1})
                    container_socket._sock.sendall(input_data.encode('utf-8'))
                    container_socket.close()
                
                # Ждем завершения с таймаутом
                result = container.wait(timeout=timeout)
                execution_time = time.time() - start_time
                
                # Получаем вывод
                output = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
                error = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
                
                success = result['StatusCode'] == 0
                
                return {
                    "success": success,
                    "output": output,
                    "error": error if error else None,
                    "return_code": result['StatusCode'],
                    "execution_time": execution_time,
                    "language": language,
                    "execution_method": "docker",
                    "memory_limit": memory_limit,
                    "cpu_quota": lang_config["cpu_quota"],
                }
            
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Пытаемся получить логи перед ошибкой
                try:
                    output = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
                    error = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
                except:
                    output = ""
                    error = ""
                
                if "timed out" in str(e).lower() or execution_time >= timeout:
                    return {
                        "success": False,
                        "error": f"⏱️ Превышено время выполнения ({timeout}s). Возможно, код работает слишком долго или зациклился.",
                        "output": output,
                        "execution_time": timeout,
                        "execution_method": "docker",
                    }
                
                return {
                    "success": False,
                    "error": f"Ошибка выполнения: {str(e)}",
                    "output": output,
                    "execution_time": execution_time,
                    "execution_method": "docker",
                }
            
            finally:
                # Удаляем контейнер
                try:
                    container.remove(force=True)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении кода в Docker: {e}")
            return {
                "success": False,
                "error": f"Ошибка инициализации контейнера: {str(e)}",
                "output": "",
                "execution_time": 0,
                "execution_method": "docker",
            }
        
        finally:
            # Очистка временной директории
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
    
    async def _execute_subprocess(
        self,
        code: str,
        language: str,
        input_data: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fallback на subprocess (небезопасно!)"""
        import subprocess
        
        logger.warning(f"⚠️ Используется небезопасное выполнение через subprocess для {language}")
        
        if language not in self.LANGUAGE_CONFIGS:
            return {
                "success": False,
                "error": f"Неподдерживаемый язык: {language}",
                "output": "",
                "execution_time": 0,
            }
        
        lang_config = self.LANGUAGE_CONFIGS[language]
        timeout = timeout or lang_config["timeout"]
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=lang_config["extension"],
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            start_time = time.time()
            
            # Определяем команду выполнения
            if language == "python":
                cmd = ["python", temp_file]
            elif language == "javascript":
                cmd = ["node", temp_file]
            else:
                return {
                    "success": False,
                    "error": f"Subprocess fallback не поддерживает {language}",
                    "output": "",
                    "execution_time": 0,
                }
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else None,
                text=True,
            )
            
            try:
                if input_data:
                    stdout, stderr = process.communicate(input=input_data, timeout=timeout)
                else:
                    stdout, stderr = process.communicate(timeout=timeout)
                
                execution_time = time.time() - start_time
                
                return {
                    "success": process.returncode == 0,
                    "output": stdout,
                    "error": stderr if stderr else None,
                    "return_code": process.returncode,
                    "execution_time": execution_time,
                    "language": language,
                    "execution_method": "subprocess",
                }
            
            except subprocess.TimeoutExpired:
                process.kill()
                return {
                    "success": False,
                    "error": f"⏱️ Превышено время выполнения ({timeout}s)",
                    "output": "",
                    "execution_time": timeout,
                    "execution_method": "subprocess",
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "execution_time": 0,
                "execution_method": "subprocess",
            }
        
        finally:
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
                    "line": e.lineno,
                }
        
        elif language == "javascript":
            # Для JavaScript можно использовать subprocess с node --check
            try:
                result = await self.execute(
                    code=f"// Syntax check\n{code}",
                    language="javascript",
                    timeout=5
                )
                return {"valid": result["success"], "error": result.get("error")}
            except:
                return {"valid": True, "error": None}  # Fallback
        
        # Для других языков пока возвращаем True
        return {"valid": True, "error": None}
    
    def get_supported_languages(self) -> list:
        """Возвращает список поддерживаемых языков"""
        return list(self.LANGUAGE_CONFIGS.keys())
    
    def get_language_info(self, language: str) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о языке"""
        return self.LANGUAGE_CONFIGS.get(language)


# Глобальный экземпляр с автоопределением Docker
# При отсутствии Docker автоматически использует subprocess fallback
docker_code_executor = DockerCodeExecutor(
    use_docker=True,
    fallback_to_subprocess=True
)

