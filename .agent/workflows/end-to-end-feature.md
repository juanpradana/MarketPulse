name: "End-to-End Feature Development"
description: "Complete feature development from database to responsive UI with full testing"
trigger: ["buat fitur", "add feature", "implement", "fullstack"]

phases:
  1_analysis:
    name: "Requirements & Architecture"
    steps:
      - "Activate sequential thinking for complexity analysis"
      - "Detect tech stack from package files"
      - "Query Context7 for unfamiliar libraries"
      - "Map blast radius with universal context"
      - "Define API contracts between frontend/backend"
    checkpoint: "Architecture approved, tech stack confirmed"

  2_backend:
    name: "Backend Implementation"
    steps:
      - "Design database schema with migrations"
      - "Implement RESTful API with validation"
      - "Add authentication/authorization"
      - "Write unit and integration tests"
      - "Generate OpenAPI documentation"
    checkpoint: "All API tests passing, docs generated"
    handoff: "OpenAPI spec to frontend team"

  3_frontend:
    name: "Frontend Implementation"
    steps:
      - "Generate TypeScript types from OpenAPI"
      - "Create React Query/Vue Query hooks"
      - "Build UI components with validation"
      - "Implement responsive layouts"
      - "Add error and loading states"
    checkpoint: "Components built, typesafe integration"
    handoff: "Component library to responsive phase"

  4_responsive:
    name: "Responsive Optimization"
    steps:
      - "Audit current layouts across breakpoints"
      - "Implement mobile-first adaptations"
      - "Optimize touch targets and navigation"
      - "Performance optimization (images, fonts)"
      - "Cross-device Playwright testing"
    checkpoint: "Lighthouse scores >90, all breakpoints tested"
    handoff: "Optimized UI to testing phase"

  5_testing:
    name: "End-to-End Verification"
    steps:
      - "Unit test coverage >80%"
      - "Integration tests for API flows"
      - "Playwright E2E for critical paths"
      - "Security audit (dependencies, inputs)"
      - "Performance budget verification"
    checkpoint: "All tests green, security passed"

  6_deployment:
    name: "Documentation & Commit"
    steps:
      - "Update README with feature docs"
      - "Update CHANGELOG.md"
      - "Write git commit with conventional format"
      - "Create PR description with test evidence"
      - "Archive workflow state"
    checkpoint: "Feature complete and documented"

error_recovery:
  backend_failure:
    action: "rollback_migration"
    retry: 2
    escalate_after: 3
    
  frontend_failure:
    action: "revert_to_last_checkpoint"
    retry: 2
    
  test_failure:
    action: "debug_and_fix"
    manual_intervention: true