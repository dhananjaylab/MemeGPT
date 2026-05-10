-- Remove templates with broken proxy-image URLs
-- These templates are causing 404 errors because the imgflip URLs are no longer valid

-- First, let's see what we're about to delete
SELECT id, name, image_url 
FROM meme_templates 
WHERE image_url LIKE '%proxy-image%';

-- Delete the broken templates
DELETE FROM meme_templates 
WHERE image_url LIKE '%proxy-image%';

-- Verify deletion
SELECT COUNT(*) as remaining_templates FROM meme_templates;

-- Made with Bob
