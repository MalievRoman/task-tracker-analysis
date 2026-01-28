-- Чистый слой для аналитики: даты + длительность + отсев явных аномалий.

DROP VIEW IF EXISTS issues_clean;

CREATE VIEW issues_clean AS
SELECT
    key,
    TO_TIMESTAMP(created / 1000.0) AS created_dt,
    TO_TIMESTAMP(resolved / 1000.0) AS resolved_dt,
    created AS created_raw,
    resolved AS resolved_raw,
    resolution,
    category,
    CASE
        WHEN resolved IS NOT NULL
        THEN (resolved - created) / 1000.0 / 60 / 60 / 24
        ELSE NULL
    END AS days_to_resolve
FROM issues
WHERE created > 1000000000000;  -- исключаем epoch-аномалии

-- Быстрая проверка витрины
SELECT
    COUNT(*) AS total_tickets,
    COUNT(CASE WHEN resolved_dt IS NOT NULL THEN 1 END) AS resolved,
    COUNT(CASE WHEN resolved_dt IS NULL THEN 1 END) AS unresolved
FROM issues_clean;
