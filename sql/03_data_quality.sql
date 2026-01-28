-- EDA + проверки качества данных + связность со справочником.

-- Количество записей в каждой таблице
SELECT 'issues' AS table_name, COUNT(*) AS row_count FROM issues
UNION ALL
SELECT 'resolutions' AS table_name, COUNT(*) AS row_count FROM resolutions;

-- Примеры данных
SELECT * FROM issues LIMIT 10;
SELECT * FROM resolutions LIMIT 10;

-- Уникальные категории
SELECT DISTINCT category FROM issues ORDER BY category;

-- Диапазон дат (raw timestamp)
SELECT
    MIN(created)  AS min_created,
    MAX(created)  AS max_created,
    MIN(resolved) AS min_resolved,
    MAX(resolved) AS max_resolved
FROM issues;

-- Полнота данных (пропуски)
SELECT
    COUNT(*) AS total_rows,
    COUNT(key) AS has_key,
    COUNT(created) AS has_created,
    COUNT(resolved) AS has_resolved,
    COUNT(resolution) AS has_resolution,
    COUNT(category) AS has_category,
    COUNT(*) - COUNT(key) AS missing_key,
    COUNT(*) - COUNT(created) AS missing_created,
    COUNT(*) - COUNT(resolved) AS missing_resolved,
    COUNT(*) - COUNT(resolution) AS missing_resolution,
    COUNT(*) - COUNT(category) AS missing_category
FROM issues;

-- Аномалии: epoch, resolved < created, “долгие” тикеты, корректные решенные
SELECT 'тикеты с created = 1970-01-01 (epoch)' AS issue_type, COUNT(*) AS count
FROM issues
WHERE created < 1000000000000

UNION ALL
SELECT 'тикеты где resolved < created' AS issue_type, COUNT(*) AS count
FROM issues
WHERE resolved IS NOT NULL AND resolved < created

UNION ALL
SELECT 'тикеты с обработкой > 1 года' AS issue_type, COUNT(*) AS count
FROM issues
WHERE resolved IS NOT NULL
  AND resolved > created
  AND (resolved - created) / 1000.0 / 60 / 60 / 24 > 365

UNION ALL
SELECT 'корректные решённые тикеты' AS issue_type, COUNT(*) AS count
FROM issues
WHERE resolved IS NOT NULL
  AND resolved > created
  AND created > 1000000000000
  AND (resolved - created) / 1000.0 / 60 / 60 / 24 <= 365;

-- Резолюции в issues, которых нет в справочнике
SELECT DISTINCT i.resolution
FROM issues i
LEFT JOIN resolutions r ON i.resolution = r.id
WHERE i.resolution IS NOT NULL
  AND r.id IS NULL;

-- Сколько резолюций в справочнике и сколько реально используется
SELECT
    COUNT(DISTINCT r.id) AS total_resolutions_in_dict,
    COUNT(DISTINCT i.resolution) AS used_resolutions
FROM resolutions r
LEFT JOIN issues i ON r.id = i.resolution;

-- Список используемых резолюций
SELECT
    r.key AS resolution_name,
    COUNT(*) AS tickets
FROM issues i
JOIN resolutions r ON r.id = i.resolution
GROUP BY r.key
ORDER BY tickets DESC;
