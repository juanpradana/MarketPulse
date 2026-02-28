# Breakpoint Strategy Guide

## Standard Breakpoints (Tailwind CSS)

```css
/* Mobile first - default is mobile */
/* sm */ @media (min-width: 640px) { /* Large phones */ }
/* md */ @media (min-width: 768px) { /* Tablets */ }
/* lg */ @media (min-width: 1024px) { /* Small laptops */ }
/* xl */ @media (min-width: 1280px) { /* Desktops */ }
/* 2xl */ @media (min-width: 1536px) { /* Large screens */ }
```

## Custom Breakpoints

### When to Add Custom
- Content breaks at non-standard widths
- Specific device targeting (iPad, etc.)
- Component-specific needs

### Configuration
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    screens: {
      'xs': '475px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
      'tall': { 'raw': '(min-height: 800px)' },
      'landscape': { 'raw': '(orientation: landscape)' },
    }
  }
}
```

## Component Breakpoints

### Card Grid
```css
/* Mobile: 1 column */
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

/* Tablet: 2 columns */
@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop: 4 columns */
@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
```

### Navigation
```css
/* Mobile: Hamburger */
.nav-mobile { display: block; }
.nav-desktop { display: none; }

/* Desktop: Horizontal */
@media (min-width: 1024px) {
  .nav-mobile { display: none; }
  .nav-desktop { display: flex; }
}
```

## Container Queries (Modern Approach)

```css
/* Component-level responsive */
.card-container {
  container-type: inline-size;
  container-name: card;
}

@container card (min-width: 400px) {
  .card {
    display: flex;
    flex-direction: row;
  }
}

@container card (min-width: 600px) {
  .card {
    display: grid;
    grid-template-columns: 1fr 2fr;
  }
}
```

## Breakpoint Selection Guide

| Content Type | Mobile | Tablet | Desktop |
|--------------|--------|--------|---------|
| Text | Single column | 2 columns | 3 columns max |
| Images | Full width | 50% width | 33% width |
| Navigation | Hamburger | Collapsible sidebar | Horizontal |
| Tables | Card view | Horizontal scroll | Full table |
| Forms | Stacked | 2 columns | Multi-column |

## Testing Checklist

- [ ] iPhone SE (375px)
- [ ] iPhone 14 (390px)
- [ ] iPad Mini (768px)
- [ ] iPad Pro (1024px)
- [ ] Desktop (1440px)
- [ ] Large Desktop (1920px)
- [ ] Landscape mobile
- [ ] Portrait tablet