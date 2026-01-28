import sys
import os
import matplotlib

matplotlib.use('Agg')

# Добавляем папку scripts в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from analysis import (
    load_data,
    calculate_metrics,
    get_metrics_by_category,
    print_metrics_report,
    print_category_report,
    ensure_output_dir,
    log_message,
)

from visualizations import (
    plot_sla_chart,
    plot_category_distribution,
    plot_resolution_distribution,
    save_all_visualizations,
)

import pandas as pd
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')


def main():
    """
    Главная функция анализа
    Загружает данные, вычисляет метрики, создаёт и сохраняет графики
    """
    
    print("\n" + "="*80)
    print("🚀 ЗАПУСК ПОЛНОГО АНАЛИЗА СИСТЕМЫ УПРАВЛЕНИЯ ЗАДАЧАМИ")
    print("="*80 + "\n")
    
    # ========== ШАГ 1: ПОДГОТОВКА ПАПОК ==========
    print("📁 Шаг 1: Подготовка директорий...")
    output_dir = ensure_output_dir('outputs/visualizations')
    print(f"   ✓ Папка для графиков: {output_dir}\n")
    
    # ========== ШАГ 2: ЗАГРУЗКА ДАННЫХ ==========
    print("📂 Шаг 2: Загрузка и очистка данных...")
    try:
        df = load_data('data/issues.csv', 'data/resolutions.csv')
    except FileNotFoundError as e:
        print(f"\n❌ ОШИБКА: Файл не найден!")
        print(f"   Убедитесь что файлы находятся в папке data/:")
        print(f"   - data/issues.csv")
        print(f"   - data/resolutions.csv")
        return False
    
    # ========== ШАГ 3: РАСЧЁТ МЕТРИК ==========
    print("\n📊 Шаг 3: Расчёт метрик...")
    metrics = calculate_metrics(df)
    print_metrics_report(metrics)
    
    # ========== ШАГ 4: АНАЛИЗ ПО КАТЕГОРИЯМ ==========
    print("📋 Шаг 4: Анализ по категориям...")
    df_categories = get_metrics_by_category(df)
    print_category_report(df_categories)
    
    # ========== ШАГ 5: СОЗДАНИЕ ГРАФИКОВ ==========
    print("\n🎨 Шаг 5: Создание и сохранение визуализаций...")
    
    try:
        # Используем одну функцию которая сохраняет ВСЕ графики
        results = save_all_visualizations(
            df,
            output_dir=output_dir,
            formats=['png'],  # Используем PNG, можно добавить 'pdf'
            verbose=True
        )
        
        # Сохраняем также в PDF если нужно
        print("\n💾 Дополнительно сохраняем в PDF...")
        results_pdf = save_all_visualizations(
            df,
            output_dir=output_dir,
            formats=['pdf'],
            verbose=False
        )
        
        print("   ✓ PDF версии сохранены\n")
        
    except Exception as e:
        print(f"\n❌ Ошибка при создании графиков: {e}")
        return False
    
    # ========== ШАГ 6: ИТОГОВЫЙ ОТЧЁТ ==========
    print("="*80)
    print("✅ АНАЛИЗ УСПЕШНО ЗАВЕРШЁН!")
    print("="*80)
    
    print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"   Всего задач:           {metrics['total']:>10,.0f}")
    print(f"   Решено:                {metrics['resolved']:>10,.0f} ({metrics['resolution_rate']:>5.2f}%)")
    print(f"   Открыто:               {metrics['open']:>10,.0f}")
    print(f"   Среднее время:         {metrics['avg_days']:>10.2f} дней")
    print(f"   Медиана времени:       {metrics['median_days']:>10.4f} дней")
    print(f"   P95 время:             {metrics['p95_days']:>10.2f} дней")
    print(f"   SLA 30 дней:           {metrics['sla_30day']:>10.2f}%")
    
    print(f"\n📁 СОХРАНЁННЫЕ ФАЙЛЫ:")
    print(f"   Папка: {output_dir}/")
    print(f"   └─ sla_chart.png")
    print(f"   └─ sla_chart.pdf")
    print(f"   └─ category_distribution.png")
    print(f"   └─ category_distribution.pdf")
    print(f"   └─ resolution_distribution.png")
    print(f"   └─ resolution_distribution.pdf")
    
    print(f"\n📈 КАТЕГОРИИ:")
    for _, row in df_categories.iterrows():
        print(f"   {row['category']:20} → {row['total']:>6,.0f} задач ({row['resolution_rate']:>5.1f}% решено)")
    
    print("\n" + "="*80)
    print("📍 Откройте графики в папке outputs/visualizations/")
    print("="*80 + "\n")
    
    return True


def analyze_single_category(category_name: str, output_dir: str = 'outputs/visualizations'):
    """
    Анализ отдельной категории
    
    Args:
        category_name (str): имя категории для анализа
        output_dir (str): папка для сохранения
    """
    print(f"\n📊 Анализ категории: {category_name}")
    print("="*80)
    
    df = load_data('data/issues.csv', 'data/resolutions.csv')
    df_cat = df[df['category'] == category_name]
    
    if len(df_cat) == 0:
        print(f"❌ Категория '{category_name}' не найдена!")
        return
    
    metrics = calculate_metrics(df_cat)
    print_metrics_report(metrics, title=f"📊 МЕТРИКИ: {category_name}")
    
    # Создаём графики только для этой категории
    print(f"\n🎨 Создание графиков для '{category_name}'...")
    
    fig, ax = plot_sla_chart(df_cat, output_dir=output_dir, save=False)
    fig.suptitle(f'SLA Анализ: {category_name}', fontsize=14, fontweight='bold')
    from visualizations import save_figure
    save_figure(fig, f'sla_chart_{category_name.lower()}', output_dir)
    
    print(f"   ✓ Готово!\n")


if __name__ == '__main__':
    # Запуск полного анализа
    success = main()
    
    # Если нужно анализировать конкретную категорию, раскомментируйте:
    # analyze_single_category('Bug', 'outputs/visualizations')
    # analyze_single_category('Feature', 'outputs/visualizations')
    # analyze_single_category('Task', 'outputs/visualizations')
    
    sys.exit(0 if success else 1)
