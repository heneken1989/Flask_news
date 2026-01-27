-- Check for duplicate articles in samfund section

-- Count total articles by language
SELECT 
    language,
    COUNT(*) as total_articles
FROM articles
WHERE section = 'samfund'
GROUP BY language
ORDER BY language;

-- Check for duplicate DA articles by published_url
SELECT 
    published_url,
    COUNT(*) as count,
    STRING_AGG(CAST(id AS TEXT), ', ') as article_ids
FROM articles
WHERE section = 'samfund'
    AND language = 'da'
    AND published_url IS NOT NULL
    AND published_url != ''
GROUP BY published_url
HAVING COUNT(*) > 1
ORDER BY count DESC, published_url;

-- Check for duplicate EN articles by published_url
SELECT 
    published_url,
    COUNT(*) as count,
    STRING_AGG(CAST(id AS TEXT), ', ') as article_ids
FROM articles
WHERE section = 'samfund'
    AND language = 'en'
    AND published_url IS NOT NULL
    AND published_url != ''
GROUP BY published_url
HAVING COUNT(*) > 1
ORDER BY count DESC, published_url;

-- Show details of duplicate DA articles
SELECT 
    a.id,
    a.published_url,
    a.title,
    a.language,
    a.is_home,
    a.created_at
FROM articles a
WHERE a.section = 'samfund'
    AND a.language = 'da'
    AND a.published_url IN (
        SELECT published_url
        FROM articles
        WHERE section = 'samfund'
            AND language = 'da'
            AND published_url IS NOT NULL
            AND published_url != ''
        GROUP BY published_url
        HAVING COUNT(*) > 1
    )
ORDER BY a.published_url, a.id;

