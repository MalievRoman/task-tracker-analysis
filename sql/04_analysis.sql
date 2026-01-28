/* ---------------------------------------------------------
   1. Быстрые sanity-checks витрины
--------------------------------------------------------- */

-- Пример данных (проверка структуры)
SELECT * FROM issues_clean LIMIT 10;

-- Общие объёмы и диапазон дат
SELECT
    COUNT(*) AS total_tickets,
    COUNT(CASE WHEN resolved_dt IS NOT NULL THEN 1 END) AS resolved,
    COUNT(CASE WHEN resolved_dt IS NULL THEN 1 END) AS unresolved,
    ROUND(COUNT(CASE WHEN resolved_dt IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS resolution_rate,
    MIN(created_dt) AS first_ticket,
    MAX(created_dt) AS last_ticket,
    COUNT(DISTINCT category) AS unique_categories
FROM issues_clean;

-- Распределение по категориям
SELECT
    category,
    COUNT(*) AS ticket_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM issues_clean), 2) AS pct_of_all
FROM issues_clean
GROUP BY category
ORDER BY ticket_count DESC;


/* ---------------------------------------------------------
   2. Базовые метрики задания
--------------------------------------------------------- */

-- Доля решённых в тот же месяц (общая)
SELECT
    COUNT(CASE
        WHEN DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt) THEN 1
    END) AS same_month_resolved,
    COUNT(*) AS total_resolved,
    ROUND(
        COUNT(CASE
            WHEN DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt) THEN 1
        END) * 100.0 / COUNT(*),
        2
    ) AS pct_same_month
FROM issues_clean
WHERE resolved_dt IS NOT NULL;

-- Доля решённых в тот же месяц (по категориям)
SELECT
    category,
    COUNT(*) AS total_resolved,
    COUNT(CASE
        WHEN DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt) THEN 1
    END) AS same_month_count,
    ROUND(
        COUNT(CASE
            WHEN DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt) THEN 1
        END) * 100.0 / COUNT(*),
        2
    ) AS pct_same_month
FROM issues_clean
WHERE resolved_dt IS NOT NULL
GROUP BY category
ORDER BY pct_same_month DESC;

-- Количество решённых тикетов по резолюциям (по названиям)
SELECT
    r.key AS resolution_name,
    COUNT(*) AS ticket_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM issues_clean WHERE resolved_dt IS NOT NULL), 2) AS pct_of_resolved
FROM issues_clean i
JOIN resolutions r ON i.resolution = r.id
WHERE i.resolved_dt IS NOT NULL
GROUP BY r.key
ORDER BY ticket_count DESC;


/* ---------------------------------------------------------
   3. Скорость решения (SLA-пороги) по категориям
   Идея: “в тот же месяц” часто слишком грубо; добавим 1/3/7/14/30 дней
--------------------------------------------------------- */

SELECT
    category,
    COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL) AS resolved_cnt,

    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 1)
          / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0), 2) AS pct_resolved_le_1d,

    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 3)
          / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0), 2) AS pct_resolved_le_3d,

    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 7)
          / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0), 2) AS pct_resolved_le_7d,

    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 14)
          / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0), 2) AS pct_resolved_le_14d,

    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 30)
          / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0), 2) AS pct_resolved_le_30d

FROM issues_clean
GROUP BY category
ORDER BY resolved_cnt DESC;


/* ---------------------------------------------------------
   4. Распределение времени решения (квантили)
   Почему: среднее “ломается” об хвосты; квантили дают честную картину
--------------------------------------------------------- */

-- Квантили по категориям (ограничим <= 365 дней как в вашем анализе)
SELECT
    category,
    COUNT(*) AS resolved_cnt,
    ROUND(AVG(days_to_resolve)::numeric, 2) AS avg_days,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) AS p50_days,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) AS p75_days,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) AS p90_days,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) AS p95_days,
    ROUND(MAX(days_to_resolve)::numeric, 2) AS max_days
FROM issues_clean
WHERE resolved_dt IS NOT NULL
  AND days_to_resolve <= 365
GROUP BY category
ORDER BY p90_days DESC;

-- Квантили по резолюциям (<= 365 дней)
SELECT
    r.key AS resolution_name,
    COUNT(*) AS resolved_cnt,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY i.days_to_resolve)::numeric, 2) AS p50_days,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY i.days_to_resolve)::numeric, 2) AS p90_days,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY i.days_to_resolve)::numeric, 2) AS p95_days
FROM issues_clean i
JOIN resolutions r ON r.id = i.resolution
WHERE i.resolved_dt IS NOT NULL
  AND i.days_to_resolve <= 365
GROUP BY r.key
ORDER BY resolved_cnt DESC;


/* ---------------------------------------------------------
   5. "Хвост" долгих тикетов
   Цель: объяснить, из чего состоит хвост (категории/резолюции)
--------------------------------------------------------- */

-- Самые долгие решённые тикеты (топ-20)
SELECT
    key,
    category,
    r.key AS resolution_name,
    created_dt,
    resolved_dt,
    ROUND(days_to_resolve::numeric, 2) AS days_to_resolve
FROM issues_clean i
LEFT JOIN resolutions r ON r.id = i.resolution
WHERE i.resolved_dt IS NOT NULL
ORDER BY days_to_resolve DESC NULLS LAST
LIMIT 20;

-- Доля “долгих” тикетов по категориям
SELECT
    category,
    COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL) AS resolved_cnt,
    COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve > 30)  AS gt_30d,
    COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve > 90)  AS gt_90d,
    COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve > 180) AS gt_180d,
    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve > 30)
          / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0), 2) AS pct_gt_30d
FROM issues_clean
GROUP BY category
ORDER BY pct_gt_30d DESC;


/* ---------------------------------------------------------
   6. Резолюции и категории: структура исходов
   (помогает формализовать “закономерности категорий” через outcomes)
--------------------------------------------------------- */

-- Категории внутри каждой резолюции (процент внутри резолюции)
SELECT
    r.key AS resolution_name,
    i.category,
    COUNT(*) AS ticket_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY r.key), 2) AS pct_within_resolution
FROM issues_clean i
JOIN resolutions r ON i.resolution = r.id
WHERE i.resolved_dt IS NOT NULL
GROUP BY r.key, i.category
ORDER BY r.key, ticket_count DESC;

-- Резолюции внутри категории (процент внутри категории)
SELECT
    i.category,
    r.key AS resolution_name,
    COUNT(*) AS ticket_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY i.category), 2) AS pct_within_category
FROM issues_clean i
JOIN resolutions r ON i.resolution = r.id
WHERE i.resolved_dt IS NOT NULL
GROUP BY i.category, r.key
ORDER BY i.category, ticket_count DESC;

-- TOP-3 резолюции внутри каждой категории
WITH ranked AS (
    SELECT
        i.category,
        r.key AS resolution_name,
        COUNT(*) AS ticket_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY i.category), 2) AS pct_in_category,
        ROW_NUMBER() OVER (PARTITION BY i.category ORDER BY COUNT(*) DESC) AS rn
    FROM issues_clean i
    JOIN resolutions r ON i.resolution = r.id
    WHERE i.resolved_dt IS NOT NULL
    GROUP BY i.category, r.key
)
SELECT
    category,
    resolution_name,
    ticket_count,
    pct_in_category
FROM ranked
WHERE rn <= 3
ORDER BY category, rn;


/* ---------------------------------------------------------
   7. Объём входящих и эффективность по когортам
   Идея: “в среднем хорошо” может скрывать просадки в отдельные месяцы
--------------------------------------------------------- */

-- Объём созданных тикетов по месяцам и категориям (как у вас)
SELECT
    TO_CHAR(created_dt, 'YYYY-MM') AS month,
    category,
    COUNT(*) AS created_cnt
FROM issues_clean
GROUP BY TO_CHAR(created_dt, 'YYYY-MM'), category
ORDER BY month, category;

-- Когортный анализ по месяцу создания: размер когорты, доля решённых, same-month%, p50/p90 дней
WITH base AS (
    SELECT
        DATE_TRUNC('month', created_dt) AS created_month,
        category,
        days_to_resolve,
        created_dt,
        resolved_dt
    FROM issues_clean
)
SELECT
    created_month,
    category,
    COUNT(*) AS created_cnt,
    COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL) AS resolved_cnt,
    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL) / NULLIF(COUNT(*), 0), 2) AS resolution_rate,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE resolved_dt IS NOT NULL
              AND DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt)
        ) / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0),
        2
    ) AS same_month_pct,

    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) FILTER (WHERE days_to_resolve IS NOT NULL) AS p50_days,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) FILTER (WHERE days_to_resolve IS NOT NULL) AS p90_days

FROM base
GROUP BY created_month, category
ORDER BY created_month, category;


/* ---------------------------------------------------------
   8. Временные паттерны: дни недели (создание)
--------------------------------------------------------- */

SELECT
    EXTRACT(DOW FROM created_dt)::int AS day_number,
    TO_CHAR(created_dt, 'Day') AS day_name,
    category,
    COUNT(*) AS ticket_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY category), 2) AS pct_in_category
FROM issues_clean
GROUP BY day_number, day_name, category
ORDER BY day_number, category;


/* ---------------------------------------------------------
   9. Backlog: анализ нерешённых тикетов (aging)
   Важно: у вас есть 2,766 нерешённых тикетов (≈5.33%) — это отдельная история. [file:32]
--------------------------------------------------------- */

-- Возраст открытых тикетов (средний/максимальный)
SELECT
    category,
    COUNT(*) AS unresolved_count,
    ROUND(AVG((EXTRACT(EPOCH FROM NOW()) * 1000 - created_raw) / 1000.0 / 60 / 60 / 24)::numeric, 0) AS avg_days_open,
    ROUND(MAX((EXTRACT(EPOCH FROM NOW()) * 1000 - created_raw) / 1000.0 / 60 / 60 / 24)::numeric, 0) AS max_days_open
FROM issues_clean
WHERE resolved_dt IS NULL
GROUP BY category
ORDER BY avg_days_open DESC;

-- Aging buckets: распределение открытых тикетов по “возрастным корзинам”
WITH open_tickets AS (
    SELECT
        category,
        (EXTRACT(EPOCH FROM NOW()) * 1000 - created_raw) / 1000.0 / 60 / 60 / 24 AS days_open
    FROM issues_clean
    WHERE resolved_dt IS NULL
),
bucketed AS (
    SELECT
        category,
        CASE
            WHEN days_open <= 7 THEN '0-7'
            WHEN days_open <= 30 THEN '8-30'
            WHEN days_open <= 90 THEN '31-90'
            WHEN days_open <= 180 THEN '91-180'
            ELSE '180+'
        END AS age_bucket
    FROM open_tickets
)
SELECT
    category,
    age_bucket,
    COUNT(*) AS tickets_cnt,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY category), 0), 2) AS pct_within_category
FROM bucketed
GROUP BY category, age_bucket
ORDER BY category, age_bucket;


/* ---------------------------------------------------------
   10. Сводная “витрина” по категориям (в одном запросе)
   Это расширенная версия вашего итогового запроса: добавим p50/p90 и SLA-7d/30d
--------------------------------------------------------- */

WITH resolved AS (
    SELECT *
    FROM issues_clean
    WHERE resolved_dt IS NOT NULL
),
agg AS (
    SELECT
        category,

        COUNT(*) AS total_tickets,
        COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL) AS resolved_cnt,
        COUNT(*) FILTER (WHERE resolved_dt IS NULL) AS unresolved_cnt,

        ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL) / NULLIF(COUNT(*), 0), 2) AS resolution_rate,

        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE resolved_dt IS NOT NULL
                AND DATE_TRUNC('month', created_dt) = DATE_TRUNC('month', resolved_dt)
            ) / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0),
            2
        ) AS same_month_pct,

        ROUND(AVG(CASE WHEN resolved_dt IS NOT NULL AND days_to_resolve <= 365 THEN days_to_resolve END)::numeric, 2) AS avg_days_to_resolve,

        ROUND(
            100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 7)
            / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0),
            2
        ) AS pct_resolved_le_7d,

        ROUND(
            100.0 * COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL AND days_to_resolve <= 30)
            / NULLIF(COUNT(*) FILTER (WHERE resolved_dt IS NOT NULL), 0),
            2
        ) AS pct_resolved_le_30d

    FROM issues_clean
    GROUP BY category
),
q AS (
    SELECT
        category,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) AS p50_days,
        ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY days_to_resolve)::numeric, 2) AS p90_days
    FROM resolved
    WHERE days_to_resolve <= 365
    GROUP BY category
)
SELECT
    a.category,
    a.total_tickets,
    ROUND(100.0 * a.total_tickets / NULLIF((SELECT COUNT(*) FROM issues_clean), 0), 2) AS pct_of_all,
    a.resolved_cnt,
    a.unresolved_cnt,
    a.resolution_rate,
    a.same_month_pct,
    a.avg_days_to_resolve,
    q.p50_days,
    q.p90_days,
    a.pct_resolved_le_7d,
    a.pct_resolved_le_30d
FROM agg a
LEFT JOIN q USING (category)
ORDER BY a.total_tickets DESC;
