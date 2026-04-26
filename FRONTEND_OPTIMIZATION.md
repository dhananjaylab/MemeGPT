# Frontend Performance Optimization Guide

## Bundle Size Optimization

### Current Vite Configuration
The frontend uses Vite for fast development and optimized production builds.

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    target: 'es2020',
    minify: 'terser',
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'ui-vendor': ['framer-motion', '@radix-ui/react-dialog'],
          'api': ['./src/lib/api.ts'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom'],
  },
});
```

### Code Splitting Strategy

1. **Vendor Splitting**
   - React core
   - UI libraries
   - API utilities

2. **Route-based Splitting**
   - Dashboard (lazy)
   - Gallery (lazy)
   - Admin (lazy)

3. **Async Components**
   - Use React.lazy() for route components
   - Suspense boundaries for loading states

### Bundle Analysis

Run bundle analysis:
```bash
npm run build
npm run analyze  # If configured
```

Monitor metrics:
- Main bundle: < 200KB
- Vendor bundle: < 300KB
- CSS: < 50KB

### Optimization Techniques

#### 1. Tree Shaking
```typescript
// ✅ Good - specific imports
import { Button } from '@radix-ui/react-button';

// ❌ Bad - entire package
import * as UI from '@radix-ui/react-dialog';
```

#### 2. Dynamic Imports
```typescript
// Route-based code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Gallery = lazy(() => import('./pages/Gallery'));

// Suspense wrapper
<Suspense fallback={<Loading />}>
  <Dashboard />
</Suspense>
```

#### 3. Image Optimization
```typescript
// Use responsive images
<img
  src={imageUrl}
  srcSet={`${smallUrl} 480w, ${largeUrl} 1200w`}
  sizes="(max-width: 768px) 100vw, 50vw"
  loading="lazy"
/>

// Or use webp with fallback
<picture>
  <source srcSet={imageUrl + '.webp'} type="image/webp" />
  <img src={imageUrl + '.jpg'} />
</picture>
```

#### 4. CSS-in-JS Optimization
```typescript
// Styled-components/Emotion
import { css } from '@emotion/react';

// Only include necessary styles
const buttonStyles = css`
  padding: 8px 16px;
  border-radius: 4px;
`;
```

#### 5. Dependencies Review
```bash
# Check for large packages
npm list --depth=0

# Audit unused dependencies
npm audit
npm outdated
```

### Performance Metrics

Monitor with Lighthouse or Web Vitals:

```typescript
// web-vitals integration
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

getCLS(console.log);
getFID(console.log);
getFCP(console.log);
getLCP(console.log);
getTTFB(console.log);
```

### Caching Strategy

```typescript
// Service worker caching
- Cache assets: 30 days
- Cache API responses: 5 minutes
- Stale-while-revalidate for images
```

### Recommended Dependencies to Remove

Check for duplicates and unused packages:
- Audit all node_modules
- Review package-lock.json
- Use npm audit to find vulnerabilities

## Loading Performance

### Critical Path Optimization

1. **Preload critical resources**
```html
<link rel="preload" as="script" href="/main.js" />
<link rel="preload" as="style" href="/main.css" />
```

2. **DNS prefetch**
```html
<link rel="dns-prefetch" href="//cdn.memegpt.com" />
```

3. **Prefetch non-critical resources**
```html
<link rel="prefetch" href="/gallery.js" />
```

### Lazy Load Non-Critical Content
- Off-screen images
- Below-fold components
- Modal content

## Mobile Optimization

### Responsive Design Checks
- Test on various screen sizes (320px, 768px, 1024px)
- Touch targets minimum 48px
- Viewport meta tag configured
- Responsive images

### Mobile Performance
- Minimize CSS/JS for mobile
- Optimize images for mobile
- Efficient event handling
- Reduce repaints/reflows

## Build Output

### Recommended Bundle Sizes

| Bundle | Size | Target |
|--------|------|--------|
| Main JS | < 150KB | 100-150KB |
| Vendor JS | < 200KB | 150-200KB |
| CSS | < 30KB | 20-30KB |
| Images (total) | Variable | Optimize via CDN |

### Build Command
```bash
npm run build  # Optimized production build
```

Output structure:
```
dist/
  index.html
  assets/
    index-[hash].js (main)
    vendor-[hash].js (vendor)
    index-[hash].css
    [image files]
```

## Frontend SEO Optimization

### Meta Tags
```typescript
// In component or layout
<Helmet>
  <title>MemeGPT - AI Meme Generator</title>
  <meta name="description" content="..." />
  <meta name="keywords" content="..." />
  <link rel="canonical" href={url} />
</Helmet>
```

### Structured Data
```typescript
import { HelmetData } from 'react-helmet-async';

const schema = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "MemeGPT",
  "url": "https://memegpt.com",
};

<script type="application/ld+json">
  {JSON.stringify(schema)}
</script>
```

### Open Graph Tags
```typescript
// Implemented via social_sharing service
// See backend/services/social_sharing.py
```

## Performance Monitoring

### Google PageSpeed Insights Integration
```typescript
// Monitor Core Web Vitals
const reportWebVitals = (metric) => {
  // Send to analytics
  if (metric.name === 'LCP') {
    // Largest Contentful Paint < 2.5s
  }
  if (metric.name === 'FID') {
    // First Input Delay < 100ms
  }
  if (metric.name === 'CLS') {
    // Cumulative Layout Shift < 0.1
  }
};
```

### Real User Monitoring
- Google Analytics
- Sentry for error tracking
- Custom performance metrics

## Optimization Checklist

- [ ] Tree shake unused code
- [ ] Code split routes
- [ ] Lazy load images
- [ ] Minimize CSS/JS
- [ ] Use production builds
- [ ] Enable gzip compression
- [ ] Optimize fonts (subset/preload)
- [ ] Remove unused dependencies
- [ ] Test with Lighthouse
- [ ] Monitor Core Web Vitals
- [ ] Set up error tracking
- [ ] Configure caching headers
- [ ] Implement service worker
- [ ] Test on mobile
- [ ] Monitor real user metrics
