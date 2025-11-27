"""
Генератор PDF отчетов из JSON данных интервью
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Опциональный импорт reportlab
try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    # Проверяем, что colors действительно доступен и имеет нужные атрибуты
    if not hasattr(colors, 'HexColor') or not hasattr(colors, 'Color'):
        raise ImportError("reportlab.lib.colors не имеет необходимых атрибутов")
    REPORTLAB_AVAILABLE = True
except (ImportError, AttributeError) as e:
    REPORTLAB_AVAILABLE = False
    # Создаем заглушки для типизации
    colors = None
    A4 = None
    letter = None
    getSampleStyleSheet = None
    ParagraphStyle = None
    inch = None
    SimpleDocTemplate = None
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    PageBreak = None
    Preformatted = None
    pdfmetrics = None
    TTFont = None


class ReportGenerator:
    """Генератор PDF отчетов для интервью"""
    
    def __init__(self, output_dir: str = "reports"):
        """
        Инициализация генератора отчетов
        
        Args:
            output_dir: Директория для сохранения отчетов
            
        Raises:
            ImportError: Если reportlab не установлен
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab не установлен. Установите его командой: pip install reportlab>=4.0.0"
            )
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Настройка шрифтов для поддержки кириллицы
        self._setup_fonts()
        
        # Настройка стилей
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_fonts(self):
        """Настройка шрифтов с поддержкой кириллицы"""
        if not REPORTLAB_AVAILABLE:
            return
        
        font_registered = False
        self.font_name = 'Helvetica'
        self.font_bold = 'Helvetica-Bold'
        
        # Пути к системным шрифтам Windows с поддержкой кириллицы
        if sys.platform == 'win32':
            fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            
            # Список шрифтов для проверки (в порядке приоритета)
            font_candidates = [
                ('arial.ttf', 'arialbd.ttf'),  # Arial
                ('times.ttf', 'timesbd.ttf'),  # Times New Roman
                ('calibri.ttf', 'calibrib.ttf'),  # Calibri
                ('tahoma.ttf', 'tahomabd.ttf'),  # Tahoma
            ]
            
            for regular_font, bold_font in font_candidates:
                regular_path = os.path.join(fonts_dir, regular_font)
                bold_path = os.path.join(fonts_dir, bold_font)
                
                if os.path.exists(regular_path):
                    try:
                        # Регистрируем обычный шрифт
                        pdfmetrics.registerFont(TTFont('CyrillicFont', regular_path))
                        
                        # Регистрируем жирный шрифт
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('CyrillicFontBold', bold_path))
                        else:
                            # Если жирного нет, используем обычный
                            pdfmetrics.registerFont(TTFont('CyrillicFontBold', regular_path))
                        
                        self.font_name = 'CyrillicFont'
                        self.font_bold = 'CyrillicFontBold'
                        font_registered = True
                        break
                    except Exception as e:
                        # Продолжаем поиск, если не удалось зарегистрировать
                        continue
        
        # Если не нашли системные шрифты, пробуем другие варианты
        if not font_registered:
            # Пытаемся найти шрифты в других стандартных местах
            alternative_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                '/System/Library/Fonts/Helvetica.ttc',  # macOS
            ]
            
            for font_path in alternative_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                        pdfmetrics.registerFont(TTFont('CyrillicFontBold', font_path))
                        self.font_name = 'CyrillicFont'
                        self.font_bold = 'CyrillicFontBold'
                        font_registered = True
                        break
                    except Exception:
                        continue
        
        # Если ничего не найдено, используем стандартные шрифты
        # (могут не поддерживать кириллицу полностью, но лучше чем ничего)
        if not font_registered:
            import warnings
            warnings.warn(
                "Не найдены шрифты с поддержкой кириллицы. Используются стандартные шрифты. "
                "Кириллические символы могут отображаться некорректно.",
                UserWarning
            )
    
    def _safe_encode(self, text: str) -> str:
        """Безопасная обработка текста для reportlab (удаление проблемных символов)"""
        if not text:
            return ""
        # Сначала пытаемся правильно обработать как UTF-8
        try:
            text = str(text).encode('utf-8', errors='ignore').decode('utf-8')
        except:
            pass
        # Удаляем символы, которые могут вызвать проблемы с latin-1
        # Оставляем только печатаемые символы
        result = []
        for char in text:
            try:
                # Проверяем, можно ли закодировать в latin-1
                char.encode('latin-1')
                result.append(char)
            except UnicodeEncodeError:
                # Если не можем, заменяем на безопасный символ
                if ord(char) < 256:
                    result.append(char)
                else:
                    result.append('?')
        return ''.join(result)
    
    def _transliterate(self, text: str) -> str:
        """Транслитерация кириллицы в латиницу для имени файла"""
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        result = []
        for char in text:
            if char in translit_map:
                result.append(translit_map[char])
            elif char.isalnum() or char in ('_', '-'):
                result.append(char)
            else:
                result.append('_')
        return ''.join(result)
    
    def _setup_custom_styles(self):
        """Настройка пользовательских стилей в соответствии с дизайн-принципами Apple"""
        if not REPORTLAB_AVAILABLE:
            return
        
        # Apple Design: минимализм, нейтральные цвета, чистая типографика
        # Цветовая палитра Apple: черный (#000000), темно-серый (#1d1d1f), средне-серый (#6e6e73), светло-серый (#f5f5f7)
        
        # Заголовок отчета
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontName=self.font_bold,
            fontSize=32,
            textColor=colors.HexColor('#1d1d1f'),
            spaceAfter=48,
            spaceBefore=0,
            alignment=0,  # Выравнивание по левому краю (Apple style)
            leading=38
        ))
        
        # Подзаголовок
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Heading2'],
            fontName=self.font_bold,
            fontSize=20,
            textColor=colors.HexColor('#1d1d1f'),
            spaceAfter=24,
            spaceBefore=32,
            leading=26
        ))
        
        # Заголовок вопроса
        self.styles.add(ParagraphStyle(
            name='QuestionTitle',
            parent=self.styles['Heading3'],
            fontName=self.font_bold,
            fontSize=17,
            textColor=colors.HexColor('#1d1d1f'),
            spaceAfter=12,
            spaceBefore=32,
            leading=22
        ))
        
        # Текст ответа
        self.styles.add(ParagraphStyle(
            name='AnswerText',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=13,
            textColor=colors.HexColor('#1d1d1f'),
            spaceAfter=16,
            leftIndent=0,
            leading=21
        ))
        
        # Код - Apple использует SF Mono, но для совместимости оставляем Courier
        self.styles.add(ParagraphStyle(
            name='CodeText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1d1d1f'),
            fontName='Courier',
            spaceAfter=16,
            leftIndent=0,
            backColor=colors.HexColor('#f5f5f7'),
            borderPadding=12,
            leading=16
        ))
        
        # Оценка
        self.styles.add(ParagraphStyle(
            name='ScoreText',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=13,
            textColor=colors.HexColor('#1d1d1f'),
            spaceAfter=8,
            leading=21
        ))
        
        # Обновляем стандартные стили для использования кириллического шрифта
        self.styles['Normal'].fontName = self.font_name
        self.styles['Heading1'].fontName = self.font_bold
        self.styles['Heading2'].fontName = self.font_bold
        self.styles['Heading3'].fontName = self.font_bold
    
    def parse_json(self, json_path: str) -> Dict[str, Any]:
        """
        Парсинг JSON файла с данными интервью
        
        Args:
            json_path: Путь к JSON файлу
            
        Returns:
            Словарь с данными интервью
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    
    def _format_score_color(self, score: float):
        """Определение цвета оценки в соответствии с дизайном Apple"""
        if not REPORTLAB_AVAILABLE or colors is None:
            return None
        
        try:
            # Apple использует нейтральные оттенки вместо ярких цветов
            # Все оценки отображаются в одном цвете для минимализма
            return colors.HexColor('#1d1d1f')  # Темно-серый Apple
        except (AttributeError, TypeError):
            return None
    
    def _create_header(self, data: Dict[str, Any]) -> List:
        if not REPORTLAB_AVAILABLE:
            return []
        """Создание заголовка отчета"""
        elements = []
        
        # Заголовок
        title = Paragraph("Отчет о собеседовании", self.styles['ReportTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Информация о кандидате
        is_early_completion = data.get('is_early_completion', False)
        total_questions = data.get('total_questions', 0)
        answered_questions = data.get('answered_questions', 0)
        
        candidate_info = [
            ['Кандидат:', data.get('candidate_name', 'Не указано')],
            ['Email:', data.get('candidate_email', 'Не указано')],
            ['Интервью:', data.get('interview_title', 'Не указано')],
            ['Дата:', data.get('interview_date', datetime.now().strftime('%Y-%m-%d %H:%M'))],
        ]
        
        # Добавляем информацию о досрочном завершении, если применимо
        if is_early_completion:
            candidate_info.append(['Статус:', 'Завершено досрочно'])
            candidate_info.append(['Вопросов задано:', f"{total_questions}"])
            candidate_info.append(['Вопросов отвечено:', f"{answered_questions}"])
        
        candidate_info.append(['Общая оценка:', f"{data.get('total_score', 0):.1f}%"])
        
        # Определение цвета общей оценки
        total_score = data.get('total_score', 0)
        score_color = self._format_score_color(total_score)
        
        table_data = []
        for row in candidate_info:
            # Убеждаемся, что все строки в Unicode
            label_text = str(row[0]).encode('utf-8', errors='ignore').decode('utf-8')
            value_text = str(row[1]).encode('utf-8', errors='ignore').decode('utf-8')
            
            label = Paragraph(f"<b>{label_text}</b>", self.styles['Normal'])
            if row[0] == 'Общая оценка:' and score_color is not None:
                value = Paragraph(
                    f"<font color='{score_color.hexval()}'><b>{value_text}</b></font>",
                    self.styles['Normal']
                )
            else:
                value = Paragraph(value_text, self.styles['Normal'])
            table_data.append([label, value])
        
        table = Table(table_data, colWidths=[2*inch, 4*inch])
        # Apple Design: тонкие линии, минимальные границы, много белого пространства
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1d1d1f')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.font_bold),
            ('FONTNAME', (1, 0), (1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 13),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#d2d2d7')),
            ('LINEBELOW', (0, -1), (-1, -1), 0.25, colors.HexColor('#d2d2d7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_question_answer_section(self, qa: Dict[str, Any], index: int) -> List:
        """Создание секции вопроса и ответа"""
        if not REPORTLAB_AVAILABLE:
            return []
        
        elements = []
        
        # Заголовок вопроса
        question_type = qa.get('question_type', 'unknown').upper()
        question_title = f"Вопрос {index + 1} ({question_type})"
        elements.append(Paragraph(question_title, self.styles['QuestionTitle']))
        
        # Текст вопроса - убеждаемся, что строка правильно обработана
        question_text = str(qa.get('question_text', 'Вопрос не указан')).encode('utf-8', errors='ignore').decode('utf-8')
        elements.append(Paragraph(f"<b>Вопрос:</b> {question_text}", self.styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Ответ
        answer_text = qa.get('answer_text')
        code_solution = qa.get('code_solution')
        evaluation = qa.get('evaluation', {}) or {}
        structured_answer = evaluation.get('structured_answer', {})
        
        # Обработка None и пустых строк
        if code_solution and str(code_solution).strip():
            elements.append(Paragraph("<b>Решение (код):</b>", self.styles['Normal']))
            # Форматирование кода - убеждаемся в правильной кодировке
            code_text = str(code_solution).encode('utf-8', errors='ignore').decode('utf-8')
            code_para = Preformatted(code_text, self.styles['CodeText'], maxLineLength=80)
            elements.append(code_para)
        elif answer_text and str(answer_text).strip():
            # Проверяем, есть ли структурированный ответ для удобства чтения
            if structured_answer and isinstance(structured_answer, dict):
                elements.append(Paragraph("<b>Ответ (структурированный):</b>", self.styles['Normal']))
                
                # Выводим краткое резюме
                summary = structured_answer.get('summary', '')
                if summary:
                    elements.append(Paragraph(f"<i>{summary}</i>", self.styles['AnswerText']))
                    elements.append(Spacer(1, 0.05*inch))
                
                # Выводим ключевые пункты
                key_points = structured_answer.get('key_points', [])
                if key_points:
                    elements.append(Paragraph("<b>Ключевые пункты:</b>", self.styles['Normal']))
                    for point in key_points[:5]:  # Максимум 5 пунктов
                        point_clean = str(point).encode('utf-8', errors='ignore').decode('utf-8')
                        elements.append(Paragraph(f"• {point_clean}", self.styles['AnswerText']))
                    elements.append(Spacer(1, 0.05*inch))
                
                # Выводим детали (опыт, навыки, проекты)
                details = structured_answer.get('details', {})
                if details and isinstance(details, dict):
                    has_details = False
                    for detail_key, detail_value in details.items():
                        if detail_value:
                            if not has_details:
                                elements.append(Paragraph("<b>Детали:</b>", self.styles['Normal']))
                                has_details = True
                            detail_key_ru = detail_key.replace('experience', 'Опыт').replace('skills', 'Навыки').replace('projects', 'Проекты').replace('achievements', 'Достижения')
                            detail_str = str(detail_value).encode('utf-8', errors='ignore').decode('utf-8')
                            elements.append(Paragraph(f"<i>{detail_key_ru}:</i> {detail_str}", self.styles['AnswerText']))
                    if has_details:
                        elements.append(Spacer(1, 0.05*inch))
                
                # Оригинальный ответ (свернутый)
                elements.append(Paragraph("<b>Полный ответ:</b>", self.styles['Normal']))
                answer_text_clean = str(answer_text).encode('utf-8', errors='ignore').decode('utf-8')
                # Сокращаем длинные ответы
                if len(answer_text_clean) > 500:
                    answer_text_clean = answer_text_clean[:497] + "..."
                elements.append(Paragraph(f"<font size='9'>{answer_text_clean}</font>", self.styles['AnswerText']))
            else:
                # Обычный вывод без структурирования
                elements.append(Paragraph("<b>Ответ:</b>", self.styles['Normal']))
                answer_text_clean = str(answer_text).encode('utf-8', errors='ignore').decode('utf-8')
                elements.append(Paragraph(answer_text_clean, self.styles['AnswerText']))
        else:
            elements.append(Paragraph("<i>Ответ не предоставлен</i>", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Оценка (evaluation уже получена выше)
        score = float(qa.get('score', 0) or 0)
        
        if evaluation:
            # Детальная оценка
            score_color = self._format_score_color(score)
            
            eval_data = [
                ['Оценка:', f"{score:.1f}%"],
                ['Правильность:', f"{evaluation.get('correctness', 0):.1f}/10"],
                ['Полнота:', f"{evaluation.get('completeness', 0):.1f}/10"],
                ['Качество:', f"{evaluation.get('quality', 0):.1f}/10"],
            ]
            
            if 'optimality' in evaluation:
                eval_data.append(['Оптимальность:', f"{evaluation.get('optimality', 0):.1f}/10"])
            
            table_data = []
            for row in eval_data:
                label = Paragraph(f"<b>{row[0]}</b>", self.styles['Normal'])
                if row[0] == 'Оценка:' and score_color is not None:
                    value = Paragraph(
                        f"<font color='{score_color.hexval()}'><b>{row[1]}</b></font>",
                        self.styles['Normal']
                    )
                else:
                    value = Paragraph(str(row[1]), self.styles['Normal'])
                table_data.append([label, value])
            
            eval_table = Table(table_data, colWidths=[2*inch, 2*inch])
            # Apple Design: минималистичные таблицы с тонкими разделителями
            eval_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1d1d1f')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), self.font_bold),
                ('FONTNAME', (1, 0), (1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 13),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#d2d2d7')),
                ('LINEBELOW', (0, -1), (-1, -1), 0.25, colors.HexColor('#d2d2d7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(eval_table)
            elements.append(Spacer(1, 0.1*inch))
            
            # Обратная связь
            feedback = evaluation.get('feedback', '')
            if feedback:
                feedback_clean = str(feedback).encode('utf-8', errors='ignore').decode('utf-8')
                elements.append(Paragraph("<b>Обратная связь:</b>", self.styles['Normal']))
                elements.append(Paragraph(feedback_clean, self.styles['AnswerText']))
                elements.append(Spacer(1, 0.1*inch))
            
            # Сильные стороны
            strengths = evaluation.get('strengths', [])
            if strengths:
                strengths_clean = [str(s).encode('utf-8', errors='ignore').decode('utf-8') for s in strengths]
                strengths_text = "<b>Сильные стороны:</b><br/>" + "<br/>".join([f"• {s}" for s in strengths_clean])
                elements.append(Paragraph(strengths_text, self.styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
            
            # Области для улучшения
            improvements = evaluation.get('improvements', [])
            if improvements:
                improvements_clean = [str(i).encode('utf-8', errors='ignore').decode('utf-8') for i in improvements]
                improvements_text = "<b>Области для улучшения:</b><br/>" + "<br/>".join([f"• {i}" for i in improvements_clean])
                elements.append(Paragraph(improvements_text, self.styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
            
            # Анализ эмоций (если есть)
            emotion_analysis = evaluation.get('emotion_analysis', {})
            if emotion_analysis:
                elements.append(Paragraph("<b>Анализ эмоций:</b>", self.styles['Normal']))
                emotion_text = str(emotion_analysis.get('summary', 'Данные не доступны')).encode('utf-8', errors='ignore').decode('utf-8')
                elements.append(Paragraph(emotion_text, self.styles['AnswerText']))
                elements.append(Spacer(1, 0.1*inch))
        else:
            # Простая оценка
            score_color = self._format_score_color(score)
            if score_color is not None:
                score_para = Paragraph(
                    f"<b>Оценка:</b> <font color='{score_color.hexval()}'>{score:.1f}%</font>",
                    self.styles['ScoreText']
                )
            else:
                score_para = Paragraph(
                    f"<b>Оценка:</b> {score:.1f}%",
                    self.styles['ScoreText']
                )
            elements.append(score_para)
        
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_summary(self, data: Dict[str, Any]) -> List:
        """Создание итоговой секции"""
        if not REPORTLAB_AVAILABLE:
            return []
        
        elements = []
        
        elements.append(PageBreak())
        elements.append(Paragraph("Итоговая статистика", self.styles['ReportSubtitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        questions = data.get('questions_answers', [])
        total_questions = len(questions)
        answered_questions = sum(1 for qa in questions if (qa.get('answer_text') and str(qa.get('answer_text')).strip()) or (qa.get('code_solution') and str(qa.get('code_solution')).strip()))
        total_score = float(data.get('total_score', 0) or 0)
        scores = [float(qa.get('score', 0) or 0) for qa in questions]
        avg_score = sum(scores) / total_questions if total_questions > 0 else 0
        
        # Статистика по типам вопросов
        type_stats = {}
        for qa in questions:
            q_type = qa.get('question_type', 'unknown')
            if q_type not in type_stats:
                type_stats[q_type] = {'count': 0, 'total_score': 0}
            type_stats[q_type]['count'] += 1
            type_stats[q_type]['total_score'] += qa.get('score', 0)
        
        summary_data = [
            ['Всего вопросов:', str(total_questions)],
            ['Отвечено:', str(answered_questions)],
            ['Общая оценка:', f"{total_score:.1f}%"],
            ['Средняя оценка:', f"{avg_score:.1f}%"],
        ]
        
        table_data = []
        for row in summary_data:
            label = Paragraph(f"<b>{row[0]}</b>", self.styles['Normal'])
            value = Paragraph(str(row[1]), self.styles['Normal'])
            table_data.append([label, value])
        
        summary_table = Table(table_data, colWidths=[3*inch, 3*inch])
        # Apple Design: чистый белый фон, тонкие разделители, нейтральные цвета
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1d1d1f')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.font_bold),
            ('FONTNAME', (1, 0), (1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#d2d2d7')),
            ('LINEBELOW', (0, -1), (-1, -1), 0.25, colors.HexColor('#d2d2d7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Статистика по типам
        if type_stats:
            elements.append(Paragraph("Статистика по типам вопросов", self.styles['Heading3']))
            elements.append(Spacer(1, 0.1*inch))
            
            type_data = [['Тип вопроса', 'Количество', 'Средняя оценка']]
            for q_type, stats in type_stats.items():
                avg = float(stats['total_score']) / stats['count'] if stats['count'] > 0 else 0.0
                type_data.append([
                    str(q_type).upper(),
                    str(stats['count']),
                    f"{avg:.1f}%"
                ])
            
            type_table = Table(type_data, colWidths=[2*inch, 2*inch, 2*inch])
            # Apple Design: минималистичный заголовок, тонкие линии, без чередующихся фонов
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1d1d1f')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
                ('FONTNAME', (0, 1), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 13),
                ('FONTSIZE', (0, 1), (-1, -1), 13),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
                ('TOPPADDING', (0, 0), (-1, -1), 14),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#1d1d1f')),
                ('LINEBELOW', (0, 1), (-1, -2), 0.25, colors.HexColor('#d2d2d7')),
                ('LINEBELOW', (0, -1), (-1, -1), 0.25, colors.HexColor('#d2d2d7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(type_table)
        
        return elements
    
    def _create_ai_evaluation_section(self, data: Dict[str, Any]) -> List:
        """Создание секции с AI оценкой"""
        if not REPORTLAB_AVAILABLE:
            return []
            
        evaluation = data.get('evaluation')
        if not evaluation:
            return []
            
        elements = []
        elements.append(PageBreak())
        elements.append(Paragraph("Финальная оценка AI", self.styles['ReportSubtitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Вердикт и Рекомендация
        verdict = evaluation.get('verdict', 'UNKNOWN')
        verdict_color = colors.HexColor('#1d1d1f')
        if verdict == 'RECOMMENDED':
            verdict_color = colors.HexColor('#28a745')
            verdict_ru = "РЕКОМЕНДОВАН"
        elif verdict == 'CONDITIONAL':
            verdict_color = colors.HexColor('#ffc107')
            verdict_ru = "УСЛОВНО РЕКОМЕНДОВАН"
        else:
            verdict_color = colors.HexColor('#dc3545')
            verdict_ru = "НЕ РЕКОМЕНДОВАН"
            
        elements.append(Paragraph(f"Вердикт: <font color='{verdict_color.hexval()}'><b>{verdict_ru}</b></font>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.1*inch))
        
        recommendation = evaluation.get('recommendation', '')
        if recommendation:
            elements.append(Paragraph(str(recommendation), self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Оценки по навыкам
        tech_score = evaluation.get('technical_skills_score', 0)
        soft_score = evaluation.get('soft_skills_score', 0)
        exp_score = evaluation.get('experience_score', 0)
        code_score = evaluation.get('coding_score', 0)
        
        skills_data = [
            ['Технические навыки', f"{tech_score}/10"],
            ['Soft Skills', f"{soft_score}/10"],
            ['Опыт работы', f"{exp_score}/10"],
            ['Качество кода', f"{code_score}/10"],
        ]
        
        table_data = []
        for row in skills_data:
            label = Paragraph(f"<b>{row[0]}</b>", self.styles['Normal'])
            value = Paragraph(str(row[1]), self.styles['Normal'])
            table_data.append([label, value])
            
        skills_table = Table(table_data, colWidths=[3*inch, 3*inch])
        skills_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1d1d1f')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.font_bold),
            ('FONTNAME', (1, 0), (1, -1), self.font_name),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#d2d2d7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(skills_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Сильные и слабые стороны
        strengths = evaluation.get('strengths', [])
        weaknesses = evaluation.get('weaknesses', [])
        
        if strengths:
            elements.append(Paragraph("Сильные стороны:", self.styles['Heading3']))
            for s in strengths:
                elements.append(Paragraph(f"• {s}", self.styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            
        if weaknesses:
            elements.append(Paragraph("Области для развития:", self.styles['Heading3']))
            for w in weaknesses:
                elements.append(Paragraph(f"• {w}", self.styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            
        # Детальный анализ
        detailed = evaluation.get('detailed_analysis', {})
        if detailed:
            elements.append(Spacer(1, 0.1*inch))
            if 'technical_analysis' in detailed:
                elements.append(Paragraph("Технический анализ:", self.styles['Heading3']))
                elements.append(Paragraph(str(detailed['technical_analysis']), self.styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
            
            if 'introduction_analysis' in detailed: # Soft skills usually here
                elements.append(Paragraph("Анализ Soft Skills:", self.styles['Heading3']))
                elements.append(Paragraph(str(detailed['introduction_analysis']), self.styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))

        return elements

    def _create_anticheat_section(self, data: Dict[str, Any]) -> List:
        """Создание секции античита"""
        if not REPORTLAB_AVAILABLE:
            return []
        
        elements = []
        suspicion_score = float(data.get('suspicion_score', 0))
        typing_metrics = data.get('typing_metrics')
        
        # Если уровень подозрительности низкий и нет метрик, пропускаем секцию
        if suspicion_score < 0.1 and not typing_metrics:
            return []
            
        elements.append(PageBreak())
        elements.append(Paragraph("Анализ честности прохождения", self.styles['ReportSubtitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Уровень риска
        risk_level = "Низкий"
        risk_color = colors.HexColor('#28a745') # Зеленый
        
        if suspicion_score > 0.7:
            risk_level = "Высокий"
            risk_color = colors.HexColor('#dc3545') # Красный
        elif suspicion_score > 0.3:
            risk_level = "Средний"
            risk_color = colors.HexColor('#ffc107') # Желтый
            
        risk_text = f"Уровень риска: <font color='{risk_color.hexval()}'><b>{risk_level}</b></font> ({suspicion_score:.2f})"
        elements.append(Paragraph(risk_text, self.styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
        
        anticheat_data = []
        
        # Метрики печати
        if typing_metrics:
            avg_speed = typing_metrics.get('average_speed', 0)
            anticheat_data.append(['Скорость печати:', f"{avg_speed:.0f} зн/мин"])
            
            variance = typing_metrics.get('variance', 0)
            if variance < 100:
                anticheat_data.append(['Вариативность:', 'Подозрительно низкая (возможен макрос)'])
            else:
                anticheat_data.append(['Вариативность:', 'В норме'])
        
        # AI детекция
        ai_results = data.get('ai_detection_results')
        if ai_results:
            prob = ai_results.get('ai_probability', 0) * 100
            anticheat_data.append(['Вероятность использования AI:', f"{prob:.1f}%"])
            
        if anticheat_data:
            table_data = []
            for row in anticheat_data:
                label = Paragraph(f"<b>{row[0]}</b>", self.styles['Normal'])
                value = Paragraph(str(row[1]), self.styles['Normal'])
                table_data.append([label, value])
            
            ac_table = Table(table_data, colWidths=[3*inch, 3*inch])
            ac_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1d1d1f')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), self.font_bold),
                ('FONTNAME', (1, 0), (1, -1), self.font_name),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#d2d2d7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(ac_table)
            
        elements.append(Spacer(1, 0.3*inch))
        return elements

    def generate_pdf(self, json_path: str, output_filename: Optional[str] = None) -> str:
        """
        Генерация PDF отчета из JSON файла
        
        Args:
            json_path: Путь к JSON файлу с данными
            output_filename: Имя выходного файла (опционально)
            
        Returns:
            Путь к созданному PDF файлу
        """
        # Парсинг JSON
        data = self.parse_json(json_path)
        
        # Определение имени выходного файла
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            candidate_name = data.get('candidate_name', 'unknown')
            # Очищаем имя от кириллицы и специальных символов для имени файла
            import re
            safe_name = re.sub(r'[^\w\s-]', '', candidate_name)
            safe_name = re.sub(r'[-\s]+', '_', safe_name)
            # Транслитерация кириллицы в латиницу для имени файла
            safe_name = self._transliterate(safe_name)
            output_filename = f"report_{safe_name}_{timestamp}.pdf"
        
        output_path = self.output_dir / output_filename
        
        # Создание PDF документа
        # Используем абсолютный путь для избежания проблем с кодировкой
        output_path_str = str(output_path.absolute())
        
        # SimpleDocTemplate не поддерживает параметр encoding напрямую
        # Но мы убеждаемся, что все строки правильно обработаны
        doc = SimpleDocTemplate(
            output_path_str,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Устанавливаем метаданные PDF с правильной обработкой кириллицы
        # reportlab использует latin-1 для метаданных, поэтому нужно транслитерировать
        candidate_name = data.get('candidate_name', 'Unknown')
        interview_title = data.get('interview_title', 'Interview Report')
        
        # Транслитерируем для метаданных (reportlab требует latin-1)
        # Также убеждаемся, что все символы в ASCII диапазоне
        safe_candidate = self._transliterate(str(candidate_name))[:50]  # Ограничиваем длину
        safe_title = self._transliterate(str(interview_title))[:50]
        
        # Устанавливаем метаданные через атрибуты документа
        # Используем только ASCII символы для избежания ошибок кодировки
        try:
            doc.title = self._safe_encode(f"Interview Report: {safe_candidate}")
            doc.author = "NeuroView AI Interview System"
            doc.subject = self._safe_encode(f"Interview Report for {safe_candidate} - {safe_title}")
            doc.creator = "NeuroView Backend"
        except (UnicodeEncodeError, UnicodeDecodeError, Exception):
            # Если все еще ошибка, используем минимальные метаданные
            doc.title = "Interview Report"
            doc.author = "NeuroView"
            doc.subject = "Interview Report"
            doc.creator = "NeuroView"
        
        # Сборка элементов документа
        elements = []
        
        # Заголовок
        elements.extend(self._create_header(data))
        
        # Вопросы и ответы
        elements.append(Paragraph("Вопросы и ответы", self.styles['ReportSubtitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        questions_answers = data.get('questions_answers', [])
        for i, qa in enumerate(questions_answers):
            elements.extend(self._create_question_answer_section(qa, i))
            if i < len(questions_answers) - 1:
                elements.append(Spacer(1, 0.1*inch))
        
        # Итоговая статистика
        elements.extend(self._create_summary(data))
        
        # AI Оценка (новая секция)
        elements.extend(self._create_ai_evaluation_section(data))
        
        # Секция античита
        elements.extend(self._create_anticheat_section(data))
        
        # Генерация PDF с обработкой ошибок кодировки
        try:
            doc.build(elements)
        except UnicodeEncodeError as e:
            # Если ошибка в метаданных, пробуем без них
            import warnings
            warnings.warn(f"Ошибка кодировки при установке метаданных: {e}. Продолжаем без метаданных.")
            # Сбрасываем метаданные на безопасные значения
            doc.title = "Interview Report"
            doc.author = "NeuroView"
            doc.subject = "Interview Report"
            doc.creator = "NeuroView"
            # Пробуем снова
            doc.build(elements)
        
        return str(output_path)


def main():
    """Основная функция для тестирования"""
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python report_generator.py <json_file> [output_file]")
        print("Пример: python report_generator.py test_interview.json")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    generator = ReportGenerator()
    
    try:
        output_path = generator.generate_pdf(json_path, output_file)
        print(f"Отчет успешно создан: {output_path}")
    except Exception as e:
        print(f"Ошибка при создании отчета: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

