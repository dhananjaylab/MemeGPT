# Template Image Loading - Testing Guide

## Quick Start Testing

### 1. Start the Backend
```bash
cd backend
uvicorn main:app --reload
```

**Expected Output:**
```
✅ Mounted /frames → a:/MemeGPT/public/frames
✅ Mounted /fonts → a:/MemeGPT/public/fonts
✅ Mounted /static → a:/MemeGPT/public
✅ Found 11 existing templates in database
```

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```

**Expected Output:**
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:3000/
```

### 3. Test Local Template Images

#### Test 1: Direct Image Access
Open in browser:
- `http://localhost:8000/frames/Drake-Hotline-Bling.jpg`
- `http://localhost:8000/frames/Distracted-Boyfriend.jpg`

**Expected:** Images should load directly

#### Test 2: Template API
Open in browser:
- `http://localhost:8000/api/memes/templates`

**Expected JSON Response:**
```json
[
  {
    "id": 0,
    "name": "Drake Hotline Bling Meme",
    "image_url": "/frames/Drake-Hotline-Bling.jpg",
    "preview_image_url": "/frames/Drake-Hotline-Bling.jpg",
    "text_field_count": 2,
    "source": "local",
    ...
  }
]
```

#### Test 3: Template Selector UI
1. Open `http://localhost:3000`
2. Navigate to meme generator
3. Check template selector

**Expected:**
- All 11 templates visible
- Images load instantly
- No CORS errors in console
- Hover effects work smoothly

#### Test 4: Meme Preview
1. Select a template (e.g., Drake)
2. Check preview panel

**Expected:**
- Template image loads in canvas
- No "Failed to load template image" error
- Text overlays render correctly
- Drag-to-reposition works

### 4. Test Error Handling

#### Test 5: Simulate Image Load Failure
1. Stop the backend server
2. Refresh frontend
3. Try to select a template

**Expected:**
- Loading spinner appears
- Error message shows: "⚠️ Image failed to load"
- Fallback placeholder displays with template name
- Retry button appears in preview

#### Test 6: Test Retry Functionality
1. Start backend server again
2. Click "Retry" button in preview

**Expected:**
- Image loads successfully
- Error state clears
- Canvas displays template correctly

### 5. Test Proxy Endpoint

#### Test 7: External Image Proxy
Open in browser:
- `http://localhost:8000/api/memes/proxy-image?url=https://i.imgflip.com/30b1gx.jpg`

**Expected:**
- Image loads through proxy
- No CORS errors
- Response headers include:
  - `Access-Control-Allow-Origin: *`
  - `Cache-Control: public, max-age=86400, immutable`

#### Test 8: Invalid URL Handling
Open in browser:
- `http://localhost:8000/api/memes/proxy-image?url=ftp://invalid.com/image.jpg`

**Expected:**
- HTTP 400 error
- Error message: "Invalid URL scheme"

### 6. Test Database Seeding

#### Test 9: Manual Template Seeding
```bash
curl -X POST http://localhost:8000/api/memes/seed-templates
```

**Expected Response:**
```json
{
  "message": "Templates seeded successfully",
  "added": 0,
  "updated": 11,
  "total": 11
}
```

#### Test 10: Check Seeded Templates
```bash
curl http://localhost:8000/api/memes/templates | jq '.[0]'
```

**Expected:**
- All templates have `image_url` starting with `/frames/`
- All templates have `source: "local"`
- All templates have correct `text_field_count`

### 7. Performance Testing

#### Test 11: Network Performance
1. Open browser DevTools (F12)
2. Go to Network tab
3. Refresh meme generator page
4. Check template image requests

**Expected:**
- Local images load in < 50ms
- No external API calls for local templates
- Images cached on subsequent loads
- Total page load time improved

#### Test 12: Lazy Loading
1. Open template selector
2. Scroll through templates
3. Watch Network tab

**Expected:**
- Images load as they come into view
- Not all images load at once
- Smooth scrolling experience

### 8. Integration Testing

#### Test 13: End-to-End Meme Generation
1. Open meme generator
2. Select "Drake Hotline Bling" template
3. Enter text in both fields
4. Preview updates in real-time
5. Generate meme

**Expected:**
- Template loads instantly
- Preview shows text overlays
- Meme generates successfully
- Final meme uses correct template

#### Test 14: Manual Mode
1. Switch to Manual mode
2. Select template
3. Adjust text positions
4. Generate meme

**Expected:**
- Template loads in preview
- Text fields are draggable
- Position updates reflect in preview
- Generated meme matches preview

### 9. Browser Compatibility

#### Test 15: Cross-Browser Testing
Test in:
- Chrome/Edge (Chromium)
- Firefox
- Safari (if available)

**Expected:**
- Images load in all browsers
- No CORS errors
- Consistent behavior

### 10. Error Recovery

#### Test 16: Network Interruption
1. Load meme generator
2. Disconnect network
3. Try to load template
4. Reconnect network
5. Click retry

**Expected:**
- Error state shows during disconnection
- Retry works after reconnection
- No page refresh needed

## Automated Testing Commands

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### E2E Tests (if configured)
```bash
npm run test:e2e
```

## Common Issues & Solutions

### Issue: Images not loading
**Check:**
1. Backend is running on port 8000
2. Frontend proxy is configured correctly
3. `public/frames/` directory exists
4. Template files are in `public/frames/`

**Solution:**
```bash
# Verify files exist
ls public/frames/

# Check backend logs for mount messages
# Should see: "✅ Mounted /frames"
```

### Issue: CORS errors
**Check:**
1. Using correct URL format
2. Proxy endpoint is working
3. CORS headers are present

**Solution:**
```bash
# Test proxy directly
curl -I http://localhost:8000/api/memes/proxy-image?url=https://i.imgflip.com/30b1gx.jpg

# Should see:
# Access-Control-Allow-Origin: *
```

### Issue: Templates not seeding
**Check:**
1. Database connection is working
2. `public/meme_data.json` exists
3. Check backend logs

**Solution:**
```bash
# Manual seed
curl -X POST http://localhost:8000/api/memes/seed-templates

# Check database
# Should have 11 templates with source="local"
```

## Success Criteria Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] All 11 templates visible in selector
- [ ] Template images load instantly
- [ ] No CORS errors in console
- [ ] Preview component displays templates
- [ ] Text overlays render correctly
- [ ] Error states show helpful messages
- [ ] Retry button works
- [ ] Fallback placeholders display
- [ ] Proxy endpoint works for external URLs
- [ ] Manual seeding works
- [ ] End-to-end meme generation works
- [ ] Performance is improved
- [ ] All browsers work correctly

## Performance Benchmarks

### Before Implementation
- Template load time: 500-1000ms (external API)
- CORS errors: Frequent
- Failed loads: Common
- User experience: Poor

### After Implementation
- Template load time: < 50ms (local files)
- CORS errors: None for local templates
- Failed loads: Rare (with retry)
- User experience: Excellent

## Next Steps After Testing

1. **If all tests pass:**
   - Mark implementation as complete
   - Deploy to staging environment
   - Monitor for issues
   - Deploy to production

2. **If tests fail:**
   - Check error messages
   - Review implementation
   - Fix issues
   - Re-test

3. **Optimization opportunities:**
   - Add image preloading
   - Implement service worker caching
   - Add progressive image loading
   - Optimize image sizes further

## Support

If you encounter issues:
1. Check backend logs
2. Check browser console
3. Review network tab
4. Check file permissions
5. Verify environment variables

For detailed implementation info, see:
- `TEMPLATE_IMAGE_LOADING_PLAN.md`
- `TEMPLATE_IMAGE_LOADING_IMPLEMENTATION.md`