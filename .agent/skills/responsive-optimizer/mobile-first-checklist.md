# Mobile-First Design Checklist

## Layout Principles

### 1. Content Priority
- [ ] Identify core content for mobile
- [ ] Remove or defer secondary content
- [ ] Progressive enhancement for desktop
- [ ] Touch-friendly navigation

### 2. Touch Targets
- [ ] Minimum 44x44px for buttons
- [ ] Minimum 32px spacing between targets
- [ ] Avoid hover-only interactions
- [ ] Gesture support (swipe, pinch)

### 3. Typography
- [ ] Base font size 16px minimum
- [ ] Line height 1.5 for readability
- [ ] Contrast ratio 4.5:1 minimum
- [ ] Maximum 35-40 characters per line

### 4. Navigation Patterns

#### Mobile
- Hamburger menu (top left or right)
- Bottom tab bar (max 5 items)
- Swipe gestures for navigation
- Back button in header

#### Tablet
- Persistent sidebar (collapsible)
- Split view for lists/detail
- Larger touch targets

#### Desktop
- Horizontal navigation bar
- Mega menus for complex hierarchies
- Hover dropdowns (with click fallback)

## Performance Checklist

### Images
- [ ] Responsive images with srcset
- [ ] WebP/AVIF format with fallbacks
- [ ] Lazy loading below fold
- [ ] Preload critical images

### CSS
- [ ] Critical CSS inlined
- [ ] Unused CSS eliminated (PurgeCSS)
- [ ] CSS containment for isolation
- [ ] Avoid layout shifts

### JavaScript
- [ ] Code splitting by route
- [ ] Dynamic imports for heavy components
- [ ] Intersection Observer for lazy loading
- [ ] Passive event listeners

## Accessibility

### Screen Readers
- [ ] Semantic HTML elements
- [ ] ARIA labels where needed
- [ ] Skip navigation link
- [ ] Focus management

### Keyboard Navigation
- [ ] Tab order logical
- [ ] Focus indicators visible
- [ ] Escape key closes modals
- [ ] Enter/Space activates buttons

### Motion
- [ ] Respect prefers-reduced-motion
- [ ] No auto-playing content
- [ ] Parallax effects optional