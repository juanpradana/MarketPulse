---
name: context7-docs
description: Zero-hallucination documentation retrieval for all libraries
glob: "**/*"
alwaysApply: true
trigger: always_on
---

# Context7 Documentation Protocol v2.0

## The Golden Rule
**NEVER** generate code for public libraries without Context7 verification.
APIs change, versions update, internal knowledge becomes stale.

## Phase 1: Environment Detection (Automatic)

Scan for dependency files immediately:
- **Node/TS**: package.json, yarn.lock, pnpm-lock.yaml
- **Python**: requirements.txt, pyproject.toml, Pipfile
- **Go**: go.mod, go.sum
- **Rust**: Cargo.toml
- **Java**: pom.xml, build.gradle
- **PHP**: composer.json
- **Ruby**: Gemfile
- **CDN**: HTML script tags

## Phase 2: The Detect → Resolve → Fetch Workflow

### Path A: Standard Flow (Unknown Library ID)

**Step 1: RESOLVE**
```javascript
// Tool: resolve-library-id
{
  "libraryName": "detected-package-name",
  "query": "user's specific task context"
}
```

**Step 2: FETCH**
```javascript
// Tool: query-docs
{
  "libraryId": "returned-from-step-1",
  "query": "specific component or API question"
}
```

### Path B: Direct ID (User provides /owner/repo format)
Skip resolve, directly call `query-docs` with provided ID.

## Critical Implementation Rules

### BEFORE generating any code:
1. **CHECK** if library is in package.json or equivalent
2. **RESOLVE** library ID through Context7
3. **QUERY** specific API documentation
4. **VERIFY** version compatibility with lock files

### When Context7 returns "No documentation found":
- **STOP** and inform user clearly
- **DO NOT** hallucinate API signatures
- **ALTERNATIVE**: Ask user for specific version or docs link

### Version-Aware Coding
- Compare installed version with latest docs
- Note deprecated APIs in comments
- Provide migration warnings if version mismatch detected

## Integration Points

- **With Sequential Thinking**: Use during Phase 2 (Analysis) when unfamiliar libs detected
- **With Playwright**: Verify UI library behavior in real browser after implementation
- **With Domain Rules**: Cross-reference framework-specific patterns

## Documentation Standards

After Context7 retrieval:
```markdown
### Context7 Verification Log
- **Library**: [name]@[version]
- **Docs Retrieved**: [timestamp]
- **APIs Used**: [list with links]
- **Version Notes**: [deprecations, changes]
```

## Citation Requirement
When providing solutions, explicitly state:
> "Retrieved from Context7: [library] - [specific section]"