-- Kiểm tra article với published_url có text lạ
-- Tìm article có chứa text "Over en årrække" trong published_url

-- 1. Tìm article có text trong URL
SELECT 
    id,
    title,
    section,
    language,
    published_url,
    CASE 
        WHEN excerpt IS NULL OR excerpt = '' THEN '❌ KHÔNG có excerpt'
        ELSE '✅ Có excerpt (' || LENGTH(excerpt) || ' chars)'
    END as excerpt_status,
    CASE 
        WHEN content IS NULL OR content = '' THEN '❌ KHÔNG có content'
        ELSE '✅ Có content (' || LENGTH(content) || ' chars)'
    END as content_status,
    LEFT(excerpt, 200) as excerpt_preview,
    LEFT(content, 200) as content_preview
FROM articles
WHERE published_url LIKE '%Over en årrække%'
   OR published_url LIKE '%nationalbanken-udsigt-til-lavere-vaekst%'
   OR published_url LIKE '%2334183%'
ORDER BY id DESC
LIMIT 5;

-- 2. Kiểm tra xem text có trong excerpt hay content không
SELECT 
    id,
    title,
    CASE 
        WHEN excerpt LIKE '%Over en årrække%' THEN '✅ Text CÓ trong excerpt'
        WHEN content LIKE '%Over en årrække%' THEN '✅ Text CÓ trong content'
        ELSE '❌ Text KHÔNG có trong excerpt/content'
    END as text_location,
    published_url
FROM articles
WHERE published_url LIKE '%2334183%'
   OR published_url LIKE '%nationalbanken%'
LIMIT 5;

-- 3. Tìm article với instance ID 2334183 (có thể đúng hơn)
SELECT 
    id,
    title,
    instance,
    published_url,
    excerpt,
    LEFT(content, 300) as content_preview
FROM articles
WHERE instance = '2334183'
   OR published_url LIKE '%/2334183'
ORDER BY id DESC
LIMIT 5;
