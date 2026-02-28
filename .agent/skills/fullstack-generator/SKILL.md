---
name: fullstack-generator
description: End-to-end feature development from database to responsive UI. Use for building complete features across all layers.
---

## Fullstack Generator Skill

### When to Activate
- User requests: "buat fitur", "add feature", "implement fullstack"
- Scope spans: Database + API + Frontend + Testing
- Keywords: "end-to-end", "fullstack", "complete feature"

### Resources
- @architecture-patterns.md - Clean architecture, DDD, MVC
- @tech-stack-templates/ - Boilerplate for detected stack

### Execution Protocol

#### Phase 1: Requirements Engineering
1. **Parse request**: Identify entities, operations, constraints
2. **Stack detection**: Read package.json, requirements.txt
3. **Pattern matching**: Find similar existing features
4. **Constraint analysis**: Security, performance, compliance

#### Phase 2: Backend Implementation
1. **Database**:
   - Design schema (Prisma/SQLAlchemy/migrations)
   - Add indexes for query performance
   - Seed data for development

2. **API Development**:
   - RESTful endpoints with validation
   - Authentication/authorization checks
   - Error handling and logging
   - OpenAPI documentation

3. **Testing**:
   - Unit tests for business logic
   - Integration tests for API endpoints

#### Phase 3: Frontend Implementation
1. **Type Generation**:
   - Generate TypeScript types from OpenAPI
   - Create React Query/Vue Query hooks

2. **Component Development**:
   - Build UI components (mobile-first)
   - Implement form validation (Zod/Yup)
   - Add loading and error states

3. **Integration**:
   - Connect to backend APIs
   - Handle authentication flows
   - Optimistic updates where appropriate

#### Phase 4: Responsive Optimization
1. **Mobile adaptation**: Touch targets, simplified navigation
2. **Desktop enhancement**: Data tables, side-by-side layouts
3. **Testing**: Playwright across breakpoints

#### Phase 5: Verification
1. **E2E Testing**: Playwright MCP critical user flows
2. **Integration Testing**: Cross-service validation
3. **Performance**: Lighthouse CI, bundle analysis
4. **Security**: Dependency audit, vulnerability scan

### Coordination Points
- **Backend → Frontend**: OpenAPI spec handoff
- **Frontend → Responsive**: Component review checkpoint
- **All → Testing**: Feature freeze before E2E

### Output Artifacts
- Database migrations
- API endpoints with tests
- Frontend components with types
- Playwright E2E tests
- Documentation updates

### Quality Gates
- [ ] All tests passing
- [ ] Type safety 100%
- [ ] Responsive on all breakpoints
- [ ] No console errors
- [ ] Performance budget met