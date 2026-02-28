---
name: responsive-optimizer
description: Optimize applications for mobile and desktop with performance-focused responsive design. Use for UI adaptation, breakpoint strategy, and cross-device testing.
---

## Responsive Optimizer Skill

### When to Activate
- User requests: "responsive", "mobile view", "breakpoint", "optimize UI"
- Task involves: Layout changes, mobile adaptation, performance
- Keywords: "mobile-first", "desktop", "tablet", "viewport"

### Resources
- @mobile-first-checklist.md - Design principles and constraints
- @breakpoint-strategy.md - Tailwind/custom breakpoint configuration

### Execution Protocol

#### Phase 1: Current State Audit
1. **Screenshot analysis**: Playwright across viewports (320, 768, 1024, 1440)
2. **Performance audit**: Lighthouse scores mobile vs desktop
3. **Component inventory**: Identify non-responsive components
4. **Touch target analysis**: Verify 44px minimum sizes

#### Phase 2: Strategy Definition
1. **Content priority**: What matters most on mobile?
2. **Navigation pattern**: Hamburger, tab bar, or drawer?
3. **Image strategy**: Art direction, srcset, lazy loading
4. **Typography**: Fluid type scale or breakpoint-based

#### Phase 3: Implementation
1. **Layout refactoring**:
   - CSS Grid/Flexbox adjustments
   - Container queries where appropriate
   - Hide/show content strategically

2. **Component adaptation**:
   - Table → Card view on mobile
   - Multi-column → Single column
   - Modal → Full screen on mobile

3. **Touch optimization**:
   - Button sizing
   - Gesture support
   - Input types (tel, email, number)

4. **Performance**:
   - Code splitting by route
   - Image optimization (WebP/AVIF)
   - Font subsetting
   - Critical CSS

#### Phase 4: Testing
1. **Device emulation**: Playwright with device presets
2. **Real device testing**: iPhone, Android, iPad if available
3. **Accessibility**: Screen reader, keyboard navigation
4. **Performance**: Core Web Vitals verification

#### Phase 5: Documentation
1. **Breakpoint guide**: Document chosen breakpoints
2. **Component patterns**: Responsive variations
3. **Testing matrix**: Supported devices/browsers
4. **Performance budget**: Document limits

### Output Artifacts
- Updated component files
- `/docs/design/responsive-strategy.md`
- `/tests/e2e/responsive.spec.ts` (Playwright)
- Performance budget documentation

### Quality Gates
- [ ] Mobile score >90 Lighthouse
- [ ] Desktop score >90 Lighthouse
- [ ] No layout shift (CLS <0.1)
- [ ] Touch targets all >44px
- [ ] Accessible navigation