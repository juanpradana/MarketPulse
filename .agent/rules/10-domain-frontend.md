---
name: domain-frontend
description: Frontend-specific standards for React/TypeScript/Vue
glob: "frontend/**/*.{tsx,vue,css,scss}"
alwaysApply: false
trigger: always_on
---

# Frontend Domain Standards

## Tech Stack Detection
Auto-detect from package.json:
- **Framework**: React, Vue, Angular, Svelte
- **Styling**: Tailwind, styled-components, CSS modules, SCSS
- **State**: Redux, Zustand, Pinia, Context API
- **Routing**: React Router, Vue Router, Next.js pages/app

## Responsive Design Protocol

### Mobile-First Approach
```css
/* Base: Mobile (default) */
.component { padding: 1rem; }

/* Tablet */
@media (min-width: 768px) { .component { padding: 2rem; } }

/* Desktop */
@media (min-width: 1024px) { .component { padding: 3rem; } }
```

### Breakpoint Strategy
- **sm**: 640px - Large phones
- **md**: 768px - Tablets
- **lg**: 1024px - Small laptops
- **xl**: 1280px - Desktops
- **2xl**: 1536px - Large screens

### Touch Targets
- Minimum 44px touch target size
- Adequate spacing between interactive elements
- Hover states for desktop, active states for touch

## Component Architecture

### Directory Structure
```
src/
├── components/
│   ├── ui/           # Button, Input, Card (dumb)
│   ├── layout/       # Header, Sidebar, Footer
│   ├── features/     # Domain-specific
│   └── pages/        # Route-level
├── hooks/            # Custom React/Vue hooks
├── lib/              # Utilities, helpers
├── types/            # TypeScript definitions
└── styles/           # Global styles, themes
```

### Component Patterns
- **Composition over inheritance**
- **Props drilling avoidance** - Use context or state management
- **Error boundaries** - Wrap route-level components
- **Loading states** - Skeleton screens preferred

## Integration Points

### API Consumption
- Use React Query/SWR for server state
- Centralize API clients in `lib/api.ts`
- Type all requests/responses
- Handle error states consistently

### State Management Decision Tree
- **Local UI state**: useState/useReducer
- **Cross-component**: Context API or Zustand
- **Server state**: React Query/SWR
- **Form state**: React Hook Form + Zod

## Performance Rules
- **Code splitting**: Route-based with React.lazy
- **Image optimization**: Next.js Image or equivalent
- **Memoization**: React.memo for expensive renders
- **Bundle size**: Monitor with @next/bundle-analyzer