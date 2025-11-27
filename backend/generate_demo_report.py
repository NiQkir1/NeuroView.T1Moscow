"""
Скрипт для генерации демо-отчета из тестовых данных
"""
import json
import sys
from pathlib import Path

# Добавляем путь к backend в sys.path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from utils.report_generator import ReportGenerator


def convert_demo_data_to_report_format(demo_data):
    """
    Преобразование демо-данных в формат, ожидаемый генератором отчетов
    """
    # Собираем все вопросы из всех этапов
    questions_answers = []
    
    for stage in demo_data.get('stages', []):
        stage_name = stage.get('stage')
        for question in stage.get('questions', []):
            qa = {
                'question_type': stage_name,
                'question_text': question.get('question_text'),
                'answer_text': question.get('answer_text'),
                'code_solution': question.get('language') == 'python' and question.get('answer_text') or None,
                'score': question.get('score', 0),
                'evaluation': {
                    'feedback': question.get('feedback'),
                    'correctness': question.get('score', 0) / 10,
                    'completeness': question.get('score', 0) / 10,
                    'quality': question.get('score', 0) / 10,
                }
            }
            
            # Для liveCoding добавляем специфические метрики
            if stage_name == 'liveCoding' and 'code_quality' in question:
                code_quality = question.get('code_quality', {})
                qa['evaluation']['optimality'] = code_quality.get('efficiency', 0) / 10
            
            questions_answers.append(qa)
    
    # Формируем summary и recommendations из демо-данных
    summary_data = demo_data.get('summary', {})
    
    # Создаем финальную оценку
    evaluation = {
        'verdict': 'RECOMMENDED' if 'Рекомендуется к найму' in demo_data.get('hr_decision', '') else 'CONDITIONAL',
        'recommendation': demo_data.get('hr_notes', ''),
        'technical_skills_score': demo_data.get('scoring_breakdown', {}).get('technical', {}).get('score', 0) / 10,
        'soft_skills_score': demo_data.get('scoring_breakdown', {}).get('softSkills', {}).get('score', 0) / 10,
        'experience_score': demo_data.get('scoring_breakdown', {}).get('introduction', {}).get('score', 0) / 10,
        'coding_score': demo_data.get('scoring_breakdown', {}).get('liveCoding', {}).get('score', 0) / 10,
        'strengths': summary_data.get('strengths', []),
        'weaknesses': summary_data.get('weaknesses', []),
        'detailed_analysis': {
            'technical_analysis': 'Кандидат демонстрирует хорошие знания JavaScript и баз данных. Понимание асинхронности на высоком уровне.',
            'introduction_analysis': 'Хорошие коммуникативные навыки. Умеет структурированно излагать свои мысли.',
        }
    }
    
    # Формируем итоговый формат
    report_data = {
        'candidate_name': demo_data.get('candidate_name'),
        'candidate_email': demo_data.get('candidate_email'),
        'interview_title': f"Интервью на позицию {demo_data.get('position')} ({demo_data.get('level')})",
        'interview_date': demo_data.get('interview_date'),
        'total_score': demo_data.get('overall_score', 0),
        'questions_answers': questions_answers,
        'total_questions': demo_data.get('metadata', {}).get('total_questions', len(questions_answers)),
        'answered_questions': demo_data.get('metadata', {}).get('total_questions', len(questions_answers)),
        'evaluation': evaluation,
        'suspicion_score': 0.0,  # Низкий уровень подозрительности для демо
        'typing_metrics': {
            'average_speed': 250,  # нормальная скорость
            'variance': 150,  # нормальная вариативность
        },
        'ai_detection_results': {
            'ai_probability': 0.1  # низкая вероятность AI
        }
    }
    
    return report_data


def main():
    """Основная функция"""
    print("=== Генератор демо-отчета NeuroView v5.7.1 ===\n")
    
    # Путь к тестовым данным
    demo_json_path = backend_dir.parent / 'reports' / 'test_interview_report_demo.json'
    
    if not demo_json_path.exists():
        print(f"[ОШИБКА] Файл {demo_json_path} не найден!")
        return 1
    
    print(f"[1/5] Загружаю тестовые данные из: {demo_json_path}")
    
    # Загружаем демо-данные
    with open(demo_json_path, 'r', encoding='utf-8') as f:
        demo_data = json.load(f)
    
    print(f"[OK] Данные загружены: {demo_data.get('candidate_name')}")
    
    # Преобразуем в формат генератора
    print("\n[2/5] Преобразую данные в формат генератора отчетов...")
    report_data = convert_demo_data_to_report_format(demo_data)
    
    # Сохраняем преобразованные данные
    converted_json_path = backend_dir / 'reports' / 'demo_report_converted.json'
    converted_json_path.parent.mkdir(exist_ok=True)
    
    with open(converted_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Преобразованные данные сохранены: {converted_json_path}")
    
    # Инициализируем генератор
    print("\n[3/5] Инициализирую PDF генератор...")
    try:
        generator = ReportGenerator(output_dir=str(backend_dir / 'reports'))
        print("[OK] Генератор инициализирован")
    except ImportError as e:
        print(f"[ОШИБКА] {e}")
        print("\n[СОВЕТ] Установите reportlab: pip install reportlab>=4.0.0")
        return 1
    
    # Генерируем PDF
    print("\n[4/5] Генерирую PDF-отчет...")
    try:
        output_filename = "DEMO_Interview_Report_Ivanov_Aleksey.pdf"
        pdf_path = generator.generate_pdf(str(converted_json_path), output_filename)
        print(f"[OK] PDF-отчет успешно создан!")
        print(f"\n[INFO] Путь к отчету: {pdf_path}")
        print(f"[INFO] Размер файла: {Path(pdf_path).stat().st_size / 1024:.1f} KB")
        
        # Также копируем в корневую папку reports для удобства
        import shutil
        root_reports = backend_dir.parent / 'reports'
        root_reports.mkdir(exist_ok=True)
        target_path = root_reports / output_filename
        shutil.copy(pdf_path, target_path)
        print(f"\n[5/5] Копия отчета также сохранена в: {target_path}")
        
        print("\n" + "="*60)
        print("ГОТОВО! Отчет успешно сгенерирован для демонстрации организаторам!")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\n[ОШИБКА] Ошибка при генерации PDF: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

