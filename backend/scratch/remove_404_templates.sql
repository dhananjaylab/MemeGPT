-- Remove templates with broken image URLs (404 errors)
-- These URLs were identified from server logs as returning 404

-- First, let's see which templates will be affected
SELECT id, name, image_url, source
FROM meme_templates
WHERE image_url LIKE '%https://i.imgflip.com/1jgig.jpg%'
   OR image_url LIKE '%https://i.imgflip.com/3bb4c7.jpg%'
   OR image_url LIKE '%https://i.imgflip.com/6gg7y9.jpg%';

-- Uncomment the following lines to actually delete the templates:
-- DELETE FROM meme_templates
-- WHERE image_url LIKE '%https://i.imgflip.com/1jgig.jpg%'
--    OR image_url LIKE '%https://i.imgflip.com/3bb4c7.jpg%'
--    OR image_url LIKE '%https://i.imgflip.com/6gg7y9.jpg%';

-- Made with Bob
