# Описание структуры базы данных

Полная документация архитектуры данных, таблиц, представлений и обработки аномалий в проекте Task Tracker Analysis.

## Обзор модели данных

Система состоит из двух основных таблиц-источников: issues (основные данные о тикетах) и resolutions (справочник типов разрешений), а также производного представления issues_clean для аналитики.

```
┌────────────────────────────┐
│      issues                │
├────────────────────────────┤
│ PK: key (TEXT)             │
│ created (BIGINT)           │
│ resolved (BIGINT, NULL)    │
│ resolution (TEXT)          │
│ category (TEXT)            │
│ Размер: 51,955 строк       │
└────────────────────────────┘
         │
         ├──→ [issues_clean] VIEW
         │    (with transformations)
         │
         └──→ resolution (FK)
              
┌────────────────────────────┐
│    resolutions             │
├────────────────────────────┤
│ PK: id (INTEGER)           │
│ key (TEXT)                 │
│ Размер: 176 строк          │
│ Используется: 5 только     │
└────────────────────────────┘
```

## Спецификация таблиц

### Таблица: issues

Основная таблица содержит все записи о тикетах системы Task Tracker.

| Поле | Тип | Ограничения | Описание |
|------|-----|------------|---------|
| key | TEXT | PRIMARY KEY | Уникальный идентификатор тикета |
| created | BIGINT | NOT NULL | Время создания в миллисекундах (Unix epoch) |
| resolved | BIGINT | NULLABLE | Время разрешения в миллисекундах (NULL если открыт) |
| resolution | TEXT | NOT NULL | Тип разрешения (Fixed, Wont Fix, Duplicate и т.д.) |
| category | TEXT | NOT NULL | Категория: Local, Remote, New User, Software License |

**Размер таблицы**: 51,955 строк  
**Размер на диске**: ~4.2 МБ  
**Статус**: Исторические данные, без обновлений

**Распределение по категориям:**
- Local: 26,366 (50.75%)
- Remote: 18,167 (34.97%)
- New User: 6,144 (11.83%)
- Software License: 1,273 (2.45%)

### Таблица: resolutions

Справочная таблица типов разрешений для классификации.

| Поле | Тип | Ограничения | Описание |
|------|-----|------------|---------|
| id | INTEGER | PRIMARY KEY | Внутренний идентификатор |
| key | TEXT | UNIQUE | Ключ типа разрешения |

**Размер таблицы**: 176 строк  
**Активно используется**: 5 резолюций
- Fixed (46,808 тикетов, 95.17%)
- Wont Fix (1,251 тикетов, 2.54%)
- resolvedByUser (791 тикетов, 1.61%)
- Duplicate (294 тикетов, 0.6%)
- escalated (39 тикетов, 0.08%)

**Неиспользуемые**: 171 резолюция (97.16% справочника)

## Представления (Views)

### Представление: issues_clean

Производное представление с очищенными и трансформированными данными.

```sql
CREATE VIEW issues_clean AS
SELECT 
    key,
    created,
    created::text as created_raw,
    TO_TIMESTAMP(created / 1000) as created_dt,
    resolved,
    resolved::text as resolved_raw,
    TO_TIMESTAMP(resolved / 1000) as resolved_dt,
    CASE 
        WHEN resolved IS NOT NULL 
        THEN (resolved - created) / 1000 / 60 / 60 / 24 
        ELSE NULL 
    END as days_to_resolve,
    resolution,
    category
FROM issues
WHERE created > 1000000000000; -- Исключаем эпохи до 2001
```

**Размер**: 51,950 строк (исключены 5 аномалий эпохи)

**Добавленные столбцы:**
- created_dt: преобразованная дата создания
- resolved_dt: преобразованная дата разрешения
- days_to_resolve: число дней до разрешения (NULL если открыт)

**Использование**: основной источник для всех аналитических запросов.

## Обработка аномалий

### Классификация выявленных проблем

**1. NULL значения**

| Проблема | Количество | Процент | Решение |
|----------|-----------|---------|---------|
| NULL в created | 3 | 0.006% | Исключены из анализа |
| NULL в resolved | 2,766 | 5.32% | Рассматриваются как открытые |
| Другие NULL | 0 | 0% | Отсутствуют |

**2. Временные аномалии**

| Проблема | Количество | Описание |
|----------|-----------|---------|
| created < 1000000000000 (до 2001) | 5 | Ошибки эпохи, исключены |
| resolved < created | 0 | Логических ошибок не обнаружено |
| Обработка > 365 дней | 3 | Долгоживущие тикеты |
| Корректные решённые (≤365д) | 44,889 | Нормальный диапазон |

**3. Проблемы связности (foreign keys)**

| Проблема | Количество | Процент |
|----------|-----------|---------|
| Резолюции не в справочнике | 1 | 0.002% |
| Резолюции без использования | 171 | 97.16% |

### Статистика очистки данных

Исходные данные: 51,955 записей  
Исключено при очистке: 5 записей (0.009%)  
Используется в анализе: 51,950 записей (99.991%)

```
51,955 (RAW)
    ↓
    - 5 записей (эпоха аномалии)
    ↓
51,950 (CLEAN) ✓
    ├─ 49,184 решённых (94.67%)
    └─ 2,766 открытых (5.33%)
```

## Индексирование и оптимизация

### Созданные индексы

```sql
-- По категориям (для GROUP BY)
CREATE INDEX idx_issues_category ON issues(category);

-- По резолюции (для фильтрации)
CREATE INDEX idx_issues_resolution ON issues(resolution);

-- Комбинированный (для временных диапазонов)
CREATE INDEX idx_issues_created_resolved ON issues(created, resolved);

-- Selective (для открытых тикетов)
CREATE INDEX idx_issues_resolved_null ON issues(resolved) 
WHERE resolved IS NULL;

-- По датам создания
CREATE INDEX idx_issues_created ON issues(created);
```

### Обоснование индексов

1. **idx_issues_category**: большинство запросов группируют по категориям для анализа распределения
2. **idx_issues_resolution**: фильтрация по типам разрешения в аналитических запросах
3. **idx_issues_created_resolved**: временные диапазоны и интервальные запросы
4. **idx_issues_resolved_null**: быстрый поиск открытых тикетов (selective индекс)
5. **idx_issues_created**: сортировка и фильтрация по датам

## Трансформация данных

### Pipeline обработки

```
Raw issues table (51,955 записей)
        ↓
[Validation layer]
  - Проверка эпохи (created > 1000000000000)
  - Проверка NULL в ключевых полях
  - Проверка связности резолюций
        ↓
[Cleaning layer]
  - Исключение 5 аномалий эпохи
  - Создание issues_clean VIEW
  - Трансформация timestamps
        ↓
[Derived columns]
  - created_dt = TO_TIMESTAMP(created / 1000)
  - resolved_dt = TO_TIMESTAMP(resolved / 1000)
  - days_to_resolve = (resolved - created) / 86400000
        ↓
[Analysis layer]
  - Группировка по категориям
  - Анализ по типам разрешения
  - Same-month разрешение
        ↓
[Output reports] ✓
  - Метрики и таблицы
  - Распределения
  - Выводы
```

### Примеры преобразований

**Конвертация Unix epoch в дату:**
```sql
TO_TIMESTAMP(created / 1000)
-- 1640995200000 → 2021-12-31 00:00:00
```

**Расчёт дней разрешения:**
```sql
(resolved - created) / 1000 / 60 / 60 / 24
-- Преобразует миллисекунды в дни
```

**Same-month флаг:**
```sql
DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt)
-- Определяет разрешение в месяц создания
```

## Распределение данных

### По категориям

| Категория | Количество | Процент | Same-month % |
|-----------|-----------|---------|------------|
| Local | 26,366 | 50.75% | 95.16% |
| Remote | 18,167 | 34.97% | 95.35% |
| New User | 6,144 | 11.83% | 96.29% |
| Software License | 1,273 | 2.45% | 100% |

### По типам разрешения

| Тип | Количество | Процент |
|-----|-----------|---------|
| Fixed | 46,808 | 95.17% |
| Wont Fix | 1,251 | 2.54% |
| resolvedByUser | 791 | 1.61% |
| Duplicate | 294 | 0.6% |
| escalated | 39 | 0.08% |

### По статусу разрешения

| Статус | Количество | Процент |
|--------|-----------|---------|
| Решённые | 49,184 | 94.67% |
| Открытые (NULL resolved) | 2,766 | 5.33% |

## Контроль качества данных

### Выполненные проверки

**Проверка целостности:**
```sql
-- NULL значения
SELECT COUNT(*) FROM issues WHERE created IS NULL; -- 3
SELECT COUNT(*) FROM issues WHERE resolved IS NULL; -- 2,766

-- Обратные диапазоны
SELECT COUNT(*) FROM issues WHERE resolved < created; -- 0

-- Резолюции без справочника
SELECT COUNT(*) FROM issues i 
LEFT JOIN resolutions r ON i.resolution = r.id 
WHERE r.id IS NULL; -- 1
```

**Статистическая валидация:**
```sql
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN resolved IS NOT NULL THEN 1 END) as resolved,
    ROUND(100.0 * COUNT(CASE WHEN resolved IS NOT NULL THEN 1 END) 
          / COUNT(*), 2) as resolution_rate
FROM issues_clean;
-- Result: 51,950 total, 49,184 resolved, 94.67%
```

