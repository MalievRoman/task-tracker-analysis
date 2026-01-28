"""
Переиспользуемые функции для создания визуализаций
Содержит функции сохранения графиков в PNG/PDF
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Tuple, Optional
from datetime import datetime


# ========== РАЗДЕЛ 1: УТИЛИТЫ СОХРАНЕНИЯ ==========

def save_figure(fig, filename: str, output_dir: str = 'outputs/visualizations', 
                formats: list = ['png', 'pdf'], dpi: int = 300, verbose: bool = True) -> list:
    """
    Сохраняет фигуру в разных форматах
    
    Args:
        fig: matplotlib figure object
        filename (str): имя файла без расширения (напр. 'sla_chart')
        output_dir (str): директория для сохранения
        formats (list): список форматов ('png', 'pdf', 'jpg')
        dpi (int): разрешение в точках на дюйм
        verbose (bool): выводить ли сообщения
        
    Returns:
        list: список сохранённых путей
        
    Example:
        >>> fig, ax = plt.subplots()
        >>> ax.hist([1, 2, 3])
        >>> paths = save_figure(fig, 'my_histogram', formats=['png', 'pdf'])
    """
    os.makedirs(output_dir, exist_ok=True)
    saved_paths = []
    
    for fmt in formats:
        filepath = os.path.join(output_dir, f"{filename}.{fmt}")
        fig.savefig(filepath, dpi=dpi, bbox_inches='tight', format=fmt)
        saved_paths.append(filepath)
        
        if verbose:
            print(f"Сохранено: {filepath}")
    
    return saved_paths


def close_and_save(fig, filename: str, output_dir: str = 'outputs/visualizations',
                   formats: list = ['png'], dpi: int = 300) -> None:
    """
    Сохраняет фигуру и закрывает её (экономит память)
    
    Args:
        fig: matplotlib figure object
        filename (str): имя файла без расширения
        output_dir (str): директория для сохранения
        formats (list): список форматов
        dpi (int): разрешение
    """
    save_figure(fig, filename, output_dir, formats, dpi, verbose=False)
    plt.close(fig)


# ========== РАЗДЕЛ 2: ГРАФИКИ (С ФУНКЦИЕЙ СОХРАНЕНИЯ) ==========

def plot_sla_chart(df: pd.DataFrame, output_dir: str = 'outputs/visualizations',
                   save: bool = True, figsize: Tuple[int, int] = (14, 7)) -> Tuple:
    """
    Создаёт график SLA анализа по 5 порогам и сохраняет его
    
    Args:
        df (pd.DataFrame): датафрейм с days_to_resolve
        output_dir (str): директория для сохранения
        save (bool): сохранять ли график
        figsize (Tuple): размер фигуры
        
    Returns:
        Tuple: (fig, ax)
    """
    resolved = df[(df['resolved_dt'].notna()) & (df['days_to_resolve'] >= 0)]
    
    thresholds = [1, 3, 7, 14, 30]
    percentages = [
        (resolved['days_to_resolve'] <= t).sum() / len(resolved) * 100
        for t in thresholds
    ]
    counts = [
        (resolved['days_to_resolve'] <= t).sum()
        for t in thresholds
    ]
    
    fig, ax = plt.subplots(figsize=figsize)
    colors = sns.color_palette("RdYlGn", len(thresholds))
    bars = ax.bar(range(len(thresholds)), percentages, color=colors, alpha=0.85, 
                  edgecolor='black', linewidth=1.5)
    
    ax.set_xticks(range(len(thresholds)))
    ax.set_xticklabels([f'{t} дн' for t in thresholds], fontweight='bold', fontsize=11)
    ax.set_ylabel('% решённых задач', fontweight='bold', fontsize=12)
    ax.set_xlabel('Пороги времени разрешения', fontweight='bold', fontsize=12)
    ax.set_title('SLA Анализ: Пороги разрешения задач', fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, 105)
    
    # Добавляем значения
    for bar, pct, count in zip(bars, percentages, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{pct:.1f}%\n({int(count):,})',
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    
    if save:
        save_figure(fig, 'sla_chart', output_dir)
    
    return fig, ax


def plot_category_distribution(df: pd.DataFrame, output_dir: str = 'outputs/visualizations',
                               save: bool = True, figsize: Tuple[int, int] = (16, 6)) -> Tuple:
    """
    Создаёт два графика распределения по категориям (пирог + столбцы)
    
    Args:
        df (pd.DataFrame): датафрейм с категориями
        output_dir (str): директория для сохранения
        save (bool): сохранять ли график
        figsize (Tuple): размер фигуры
        
    Returns:
        Tuple: (fig, axes)
    """
    category_counts = df.groupby('category').size()
    resolution_rates = df.groupby('category')['resolved_dt'].apply(
        lambda x: (x.notna().sum() / len(x) * 100)
    )
    
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    fig.suptitle('Распределение по категориям (пирог + столбцы)', 
                 fontsize=14, fontweight='bold')
    
    colors = sns.color_palette("Set2", len(category_counts))
    
    # Пирог
    axes[0].pie(category_counts, labels=category_counts.index, autopct='%1.1f%%',
                colors=colors, startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
    axes[0].set_title('Процентное распределение', fontsize=12, fontweight='bold')
    
    # Столбцы
    bars = axes[1].bar(range(len(category_counts)), category_counts.values, 
                       color=colors, alpha=0.85, edgecolor='black', linewidth=1.5)
    axes[1].set_xticks(range(len(category_counts)))
    axes[1].set_xticklabels(category_counts.index, fontweight='bold', fontsize=10, rotation=0)
    axes[1].set_ylabel('Количество задач', fontweight='bold', fontsize=11)
    axes[1].set_title('Абсолютное распределение с % разрешения', fontsize=12, fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)
    
    for i, (bar, rate) in enumerate(zip(bars, resolution_rates.values)):
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{rate:.1f}%\n({int(height):,})',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    
    if save:
        save_figure(fig, 'category_distribution', output_dir)
    
    return fig, axes


def plot_resolution_distribution(df: pd.DataFrame, output_dir: str = 'outputs/visualizations',
                                 save: bool = True, figsize: Tuple[int, int] = (14, 7)) -> Tuple:
    """
    Создаёт график распределения времени разрешения (0-15 дней)
    
    Args:
        df (pd.DataFrame): датафрейм с days_to_resolve
        output_dir (str): директория для сохранения
        save (bool): сохранять ли график
        figsize (Tuple): размер фигуры
        
    Returns:
        Tuple: (fig, axes)
    """
    resolved_all = df[(df['resolved_dt'].notna()) & (df['days_to_resolve'] >= 0)]
    resolved_vis = resolved_all[resolved_all['days_to_resolve'] <= 15].copy()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    fig.suptitle('Распределение времени разрешения', fontsize=14, fontweight='bold')
    
    # Гистограмма
    counts, bins, patches = ax1.hist(resolved_vis['days_to_resolve'], bins=50, 
                                      color='#3498db', alpha=0.8, edgecolor='black', linewidth=1)
    cm = plt.cm.Blues
    for i, patch in enumerate(patches):
        patch.set_facecolor(cm(0.4 + 0.5 * (i / len(patches))))
    
    ax1.set_xlabel('Дни разрешения', fontweight='bold', fontsize=11)
    ax1.set_ylabel('Количество задач', fontweight='bold', fontsize=11)
    ax1.set_title('Гистограмма (0-15 дней)', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # Категории
    categories_simple = ['0-2ч\n(быстро)', '2-12ч\n(день)', '1-3д\n(срочно)', 
                       '3-7д\n(обычно)', '7-15д\n(долго)']
    bins_simple = [0, 2/24, 12/24, 3, 7, 15]
    
    resolved_vis_cat = resolved_vis.copy()
    resolved_vis_cat['category_simple'] = pd.cut(resolved_vis_cat['days_to_resolve'],
                                                  bins=bins_simple, 
                                                  labels=categories_simple,
                                                  include_lowest=True)
    
    counts_simple = resolved_vis_cat['category_simple'].value_counts().sort_index()
    colors_simple = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#c0392b']
    bars = ax2.bar(range(len(counts_simple)), counts_simple.values, 
                   color=colors_simple, alpha=0.85, edgecolor='black', linewidth=2)
    
    ax2.set_xticks(range(len(counts_simple)))
    ax2.set_xticklabels(counts_simple.index, fontweight='bold', fontsize=10)
    ax2.set_ylabel('Количество задач', fontweight='bold', fontsize=11)
    ax2.set_title('Категоризация по скорости', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    for bar, count in zip(bars, counts_simple.values):
        height = bar.get_height()
        pct = (count / len(resolved_vis_cat)) * 100
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count):,}\n({pct:.1f}%)',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    
    if save:
        save_figure(fig, 'resolution_distribution', output_dir)
    
    return fig, (ax1, ax2)


# ========== РАЗДЕЛ 3: УТИЛИТА ДЛЯ СОХРАНЕНИЯ ВСЕХ ГРАФИКОВ ==========

def save_all_visualizations(df: pd.DataFrame, output_dir: str = 'outputs/visualizations',
                           formats: list = ['png'], verbose: bool = True) -> dict:
    """
    Создаёт и сохраняет все основные визуализации
    
    Args:
        df (pd.DataFrame): датафрейм с задачами
        output_dir (str): директория для сохранения
        formats (list): форматы сохранения
        verbose (bool): выводить ли сообщения
        
    Returns:
        dict: словарь с путями ко всем сохранённым файлам
        
    Example:
        >>> paths = save_all_visualizations(df, output_dir='my_outputs')
        >>> print(paths.keys())
        dict_keys(['sla_chart', 'category_distribution', 'trend_analysis', 'resolution_distribution'])
    """
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    if verbose:
        print("\n" + "="*70)
        print("СОХРАНЕНИЕ ВСЕХ ВИЗУАЛИЗАЦИЙ")
        print("="*70)
    
    # SLA Chart
    if verbose:
        print("\nSLA Chart...")
    fig, _ = plot_sla_chart(df, output_dir, save=False)
    results['sla_chart'] = save_figure(fig, 'sla_chart', output_dir, formats, verbose=verbose)
    plt.close(fig)
    
    # Category Distribution
    if verbose:
        print("\nCategory Distribution...")
    fig, _ = plot_category_distribution(df, output_dir, save=False)
    results['category_distribution'] = save_figure(fig, 'category_distribution', output_dir, formats, verbose=verbose)
    plt.close(fig)
    
    # Resolution Distribution
    if verbose:
        print("\nResolution Distribution...")
    fig, _ = plot_resolution_distribution(df, output_dir, save=False)
    results['resolution_distribution'] = save_figure(fig, 'resolution_distribution', output_dir, formats, verbose=verbose)
    plt.close(fig)
    
    if verbose:
        print("\n" + "="*70)
        print(f"Все графики сохранены в {output_dir}/")
        print("="*70 + "\n")
    
    return results
