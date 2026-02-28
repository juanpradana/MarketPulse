---
name: execution-standards
description: Mandatory execution standards and quality gates
glob: "**/*"
alwaysApply: true
trigger: always_on
---

# Execution Standards v2.0: The VAULT Method

**V**erify before action, **A**utomate testing, **U**se best practices, **L**everage tools, **T**rack changes

## Mandatory Pre-Execution

### 1. Project Reconnaissance (ALWAYS)
```bash
# Before any changes:
find . -type f -name "*.py" -o -name "*.ts" -o -name "*.js" | head -20
ls -la
cat package.json 2>/dev/null || cat requirements.txt 2>/dev/null || cat Cargo.toml 2>/dev/null
```

**Requirement**: Understand project structure, tech stack, and existing patterns before modifying anything.

### 2. Virtual Environment (ALWAYS)
- **Python**: `python -m venv venv` → `source venv/bin/activate`
- **Node**: Check for `.nvmrc` or use default LTS
- **Rust**: Check `rust-toolchain.toml`
- **Go**: Check `go.mod` for version

**Rule**: Never install packages globally. Always use isolated environments.

### 3. Dependency Audit (BEFORE installing)
- Check `package.json` / `requirements.txt` for existing packages
- Verify version compatibility
- Check for security vulnerabilities
- Prefer existing packages over new additions

## Quality Gates

### Gate 1: Code Quality
- **Type Safety**: TypeScript strict mode, Python type hints, Rust strict compiler
- **Linting**: ESLint, Prettier, Black, Clippy - zero warnings
- **Formatting**: Consistent style across all files
- **Comments**: Strategic - complex logic only, no noise

### Gate 2: Testing (PLAYWRIGHT MANDATORY)
**ALWAYS** end with Playwright testing:
1. Unit tests for business logic
2. Integration tests for APIs
3. **E2E tests with Playwright MCP** for critical user flows

**Test Requirements**:
- Minimum 80% coverage for business logic
- All happy paths covered
- Critical error paths covered
- Visual regression for UI changes

### Gate 3: Git Hygiene
**ALWAYS** commit with meaningful messages:
```
type(scope): description

[optional body]

[optional footer]
```

**Types**: feat, fix, docs, style, refactor, test, chore, perf, ci
**Scope**: domain (frontend, backend, api, integration, etc.)

**Commit Checklist**:
- [ ] All tests passing
- [ ] No console errors
- [ ] No debug code left
- [ ] Documentation updated
- [ ] CHANGELOG.md updated if breaking change

### Gate 4: Security
- **NEVER** commit: API keys, passwords, tokens, `.env` files
- **ALWAYS** use: `.env.example` with dummy values
- **VALIDATE**: All inputs sanitized
- **CHECK**: No SQL injection, XSS, or CSRF vulnerabilities

### Gate 5: Performance
- **Lazy loading** for routes/components >100KB
- **Image optimization**: WebP/AVIF, responsive sizes
- **Bundle analysis**: Check for bloat
- **Database**: Indexed queries, N+1 prevention

## Tool Integration Matrix

| Task | Primary Tool | Secondary Tool | Verification |
|------|--------------|----------------|--------------|
| Complex logic | Sequential Thinking | Context7 (if libs) | Unit tests |
| UI changes | Playwright MCP | Snapshot testing | Visual regression |
| API work | Context7 | Sequential Thinking | Integration tests |
| Integration | Sequential Thinking | Custom MCPs | E2E tests |
| Refactoring | Universal Context | Sequential Thinking | Full test suite |
| Reverse engineering | Playwright MCP | Network analysis | Replay validation |

## Execution Flow

1. **Analyze**: Sequential thinking + Universal context
2. **Plan**: Tool selection, checkpoint definition
3. **Implement**: Code with symmetry and patterns
4. **Test**: Unit → Integration → Playwright E2E
5. **Verify**: Security, performance, accessibility
6. **Document**: Update README, CHANGELOG, inline docs
7. **Commit**: Meaningful message, all checks passing

## Prohibited Actions

- **NEVER**: Skip testing to save time
- **NEVER**: Commit directly to main without review
- **NEVER**: Use `any` type in TypeScript without justification
- **NEVER**: Leave `console.log` in production code
- **NEVER**: Ignore linting errors
- **NEVER**: Break existing tests without fixing