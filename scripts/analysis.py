import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import os
from datetime import datetime


# ========== РАЗДЕЛ 1: ЗАГРУЗКА И ОЧИСТКА ДАННЫХ ==========

def load_data(issues_csv: str, resolutions_csv: str) -> pd.DataFrame:
    """
    Загружает и очищает данные из CSV файлов
    
    Args:
        issues_csv (str): путь к файлу issues.csv
        resolutions_csv (str): путь к файлу resolutions.csv
        
    Returns:
        pd.DataFrame: очищенный датафрейм с 51,950 записями
        
    Example:
        >>> df = load_data('data/issues.csv', 'data/resolutions.csv')
        >>> print(len(df))
        51950
    """
    print("="*70)
    print("ЗАГРУЗКА И ОЧИСТКА ДАННЫХ")
    print("="*70)
    
    # Загрузка
    issues = pd.read_csv(issues_csv, sep=';')
    resolutions = pd.read_csv(resolutions_csv, sep=';')
    
    print(f"\nЗагружено:")
    print(f"   ├─ Issues: {len(issues):,} записей")
    print(f"   └─ Resolutions: {len(resolutions):,} записей")
    
    # Очистка: исключаем epoch аномалии (значения < 1 триллиона миллисекунд)
    issues_clean = issues[issues['created'] > 1000000000000].copy()
    
    # Конвертируем timestamp (миллисекунды) в datetime
    issues_clean['created_dt'] = pd.to_datetime(issues_clean['created'] / 1000, unit='s')
    issues_clean['resolved_dt'] = pd.to_datetime(issues_clean['resolved'] / 1000, unit='s', errors='coerce')
    
    # Вычисляем время разрешения в днях
    issues_clean['days_to_resolve'] = (issues_clean['resolved'] - issues_clean['created']) / (1000 * 60 * 60 * 24)
    
    # Merge с таблицей resolutions
    issues_clean = issues_clean.merge(
        resolutions.rename(columns={'id': 'resolution'})[['resolution', 'key']],
        on='resolution',
        how='left'
    )
    issues_clean = issues_clean.rename(columns={'key': 'resolution_name'})
    
    resolved_count = issues_clean['resolved_dt'].notna().sum()
    open_count = issues_clean['resolved_dt'].isna().sum()
    
    print(f"\nДанные после очистки:")
    print(f"   ├─ Всего записей: {len(issues_clean):,}")
    print(f"   ├─ Решённых: {resolved_count:,} ({resolved_count/len(issues_clean)*100:.2f}%)")
    print(f"   ├─ Открытых: {open_count:,} ({open_count/len(issues_clean)*100:.2f}%)")
    print(f"   └─ Уникальные категории: {issues_clean['category'].nunique()}")
    print("="*70 + "\n")
    
    return issues_clean


# ========== РАЗДЕЛ 2: ВЫЧИСЛЕНИЕ МЕТРИК ==========

def calculate_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Вычисляет все ключевые метрики разрешения задач
    
    Args:
        df (pd.DataFrame): датафрейм с задачами
        
    Returns:
        Dict[str, float]: словарь с 15+ метриками
    """
    resolved = df[(df['resolved_dt'].notna()) & (df['days_to_resolve'] >= 0)]
    total = len(df)
    
    metrics = {
        # Базовые
        'total': total,
        'resolved': len(resolved),
        'open': total - len(resolved),
        'resolution_rate': len(resolved) / total * 100,
        
        # Время разрешения
        'avg_days': resolved['days_to_resolve'].mean(),
        'median_days': resolved['days_to_resolve'].median(),
        'min_days': resolved['days_to_resolve'].min(),
        'max_days': resolved['days_to_resolve'].max(),
        'std_days': resolved['days_to_resolve'].std(),
        
        # Квартили
        'p25_days': resolved['days_to_resolve'].quantile(0.25),
        'p75_days': resolved['days_to_resolve'].quantile(0.75),
        'p90_days': resolved['days_to_resolve'].quantile(0.90),
        'p95_days': resolved['days_to_resolve'].quantile(0.95),
        
        # SLA метрики
        'sla_1day': (resolved['days_to_resolve'] <= 1).sum() / len(resolved) * 100,
        'sla_3day': (resolved['days_to_resolve'] <= 3).sum() / len(resolved) * 100,
        'sla_7day': (resolved['days_to_resolve'] <= 7).sum() / len(resolved) * 100,
        'sla_14day': (resolved['days_to_resolve'] <= 14).sum() / len(resolved) * 100,
        'sla_30day': (resolved['days_to_resolve'] <= 30).sum() / len(resolved) * 100,
        
        # Долгие задачи
        'long_30pct': (resolved['days_to_resolve'] > 30).sum() / len(resolved) * 100,
        'long_90pct': (resolved['days_to_resolve'] > 90).sum() / len(resolved) * 100,
    }
    
    return metrics


def get_metrics_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Вычисляет метрики по категориям задач
    
    Args:
        df (pd.DataFrame): датафрейм с задачами
        
    Returns:
        pd.DataFrame: таблица с метриками по категориям
    """
    results = []
    
    for category in sorted(df['category'].unique()):
        cat_all = df[df['category'] == category]
        cat_resolved = cat_all[cat_all['resolved_dt'].notna()]
        cat_with_time = cat_resolved[cat_resolved['days_to_resolve'] >= 0]
        
        results.append({
            'category': category,
            'total': len(cat_all),
            'resolved': len(cat_resolved),
            'resolution_rate': len(cat_resolved) / len(cat_all) * 100 if len(cat_all) > 0 else 0,
            'avg_days': cat_with_time['days_to_resolve'].mean() if len(cat_with_time) > 0 else 0,
            'median_days': cat_with_time['days_to_resolve'].median() if len(cat_with_time) > 0 else 0,
            'p95_days': cat_with_time['days_to_resolve'].quantile(0.95) if len(cat_with_time) > 0 else 0,
        })
    
    return pd.DataFrame(results)


# ========== РАЗДЕЛ 3: ПЕЧАТЬ ОТЧЁТОВ ==========

def print_metrics_report(metrics: Dict[str, float], title: str = "📊 КЛЮЧЕВЫЕ МЕТРИКИ") -> None:
    """
    Красиво печатает метрики в консоль
    
    Args:
        metrics (Dict): словарь метрик
        title (str): заголовок отчёта
    """
    print("="*80)
    print(title)
    print("="*80)
    
    print(f"\nОБЩИЕ СТАТИСТИКИ:")
    print(f"  Всего задач:              {metrics['total']:>10,.0f}")
    print(f"  Решено:                   {metrics['resolved']:>10,.0f} ({metrics['resolution_rate']:>5.2f}%)")
    print(f"  Открыто:                  {metrics['open']:>10,.0f}")
    
    print(f"\nВРЕМЯ РАЗРЕШЕНИЯ (дни):")
    print(f"  Минимум:                  {metrics['min_days']:>10.4f}")
    print(f"  Среднее:                  {metrics['avg_days']:>10.2f}")
    print(f"  Медиана (P50):            {metrics['median_days']:>10.4f}")
    print(f"  75-й квартиль (P75):      {metrics['p75_days']:>10.2f}")
    print(f"  90-й квартиль (P90):      {metrics['p90_days']:>10.2f}")
    print(f"  95-й квартиль (P95):      {metrics['p95_days']:>10.2f}")
    print(f"  Максимум:                 {metrics['max_days']:>10.2f}")
    
    print(f"\nSLA МЕТРИКИ (% задач решено в срок):")
    print(f"  За 1 день:                {metrics['sla_1day']:>10.2f}%")
    print(f"  За 3 дня:                 {metrics['sla_3day']:>10.2f}%")
    print(f"  За 7 дней:                {metrics['sla_7day']:>10.2f}%")
    print(f"  За 14 дней:               {metrics['sla_14day']:>10.2f}%")
    print(f"  За 30 дней:               {metrics['sla_30day']:>10.2f}%")
    
    print(f"\nДОЛГИЕ ЗАДАЧИ:")
    print(f"  Дольше 30 дней:           {metrics['long_30pct']:>10.2f}%")
    print(f"  Дольше 90 дней:           {metrics['long_90pct']:>10.2f}%")
    
    print("="*80 + "\n")


def print_category_report(df_categories: pd.DataFrame) -> None:
    """Печатает отчёт по категориям"""
    print("="*80)
    print("РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ")
    print("="*80)
    print(f"{'Категория':20} | {'Кол-во':>10} | {'% всех':>8} | {'Решено %':>8} | {'Avg дн':>8} | {'P95 дн':>8}")
    print("-"*80)
    
    total = df_categories['total'].sum()
    for _, row in df_categories.iterrows():
        print(f"{row['category']:20} | {row['total']:>10,.0f} | {row['total']/total*100:>7.1f}% | {row['resolution_rate']:>7.1f}% | {row['avg_days']:>7.2f} | {row['p95_days']:>7.2f}")
    
    print("="*80 + "\n")


# ========== РАЗДЕЛ 4: УТИЛИТЫ ==========

def ensure_output_dir(output_dir: str = 'outputs') -> str:
    """
    Создаёт директорию для сохранения графиков если её нет
    
    Args:
        output_dir (str): путь к директории
        
    Returns:
        str: путь к директории
    """
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_timestamp() -> str:
    """Возвращает текущее время в формате YYYY-MM-DD_HH-MM-SS"""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def log_message(message: str, level: str = "INFO") -> None:
    """
    Логирует сообщение с временной меткой
    
    Args:
        message (str): сообщение для логирования
        level (str): уровень логирования (INFO, WARNING, ERROR)
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] {level}:"
    print(f"{prefix} {message}")
