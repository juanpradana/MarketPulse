---
name: universal-context
description: Exhaustive contextual analysis and blast radius mapping
glob: "**/*"
alwaysApply: true
trigger: always_on
---

# Universal Context Protocol v2.0: The ICEBERG Method

## Core Philosophy
Abandon "narrow" scoping. Adopt **wild, explorative, creative, exhaustive** analysis.
**The request is just the tip. 90% is hidden beneath.**

## The ICEBERG Phases

### I - Investigation (Deep Dive)
**Get As Much Context As You Want** - never limit curiosity.

- **Global Search**: Broad regex, find usages in unexpected places (strings, comments, dynamic imports)
- **Follow Threads**: Import → Utility → All 50 files using that utility
- **Creative Patterns**: Look for "cousin" code (UserTable → ProductTable → generic Table)
- **Aggressive Reading**: If unsure, read the file. If still unsure, read the directory.

### C - Context Mapping (Blast Radius)
Before writing code, map the entire ecosystem:

#### A. Ancestry & Descendants (Full Call Graph)
- Who calls this? Who does this call?
- Use `find_referencing_symbols` recursively
- Map data flow: Database → API → UI → Back

#### B. Implicit Dependencies (Invisible Links)
- **CI/CD**: `.github/`, `scripts/`, `Makefile` - Will build break?
- **Docker/Env**: `Dockerfile`, `.env.example` - Env vars changed?
- **Documentation**: `README.md`, `/docs`, `*.stories.js` - Docs outdated?
- **Config**: `package.json`, `tsconfig.json` - Build rules affected?

#### C. System Symmetry (No Code Left Behind)
- If refactoring a pattern, refactor it **everywhere**
- **Total Consistency** - no legacy patterns alongside new ones
- Identify all occurrences before changing one

### E - Evaluation (Risk Assessment)
- **Impact Level**: Low (isolated) / Medium (component) / High (system-wide)
- **Rollback Complexity**: Easy revert / Migration needed / Breaking changes
- **Test Coverage**: Unit / Integration / E2E requirements

### B - Boundary Setting (Scope Definition)
- **In Scope**: Explicit deliverables
- **Out of Scope**: Explicit exclusions
- **Dependencies**: Required before/after this task

### E - Execution Preparation
- **Tool Selection**: Which MCP tools, which rules, which skills
- **Checkpoint Planning**: Validation gates between steps
- **Contingency**: Fallback plans for discovered complexity

### R - Review & Refinement
- **Code Review**: Self-review against standards
- **Pattern Check**: Symmetry maintained?
- **Documentation**: Updates required?

### G - Guard & Grow (Quality Assurance)
- **Testing**: All levels covered
- **Monitoring**: Error tracking, performance metrics
- **Knowledge Capture**: Update memories, document decisions

## Mandatory Actions

### For ANY request, you MUST:

1. **Search Globally**:
   ```bash
   # Find all occurrences
   grep -r "pattern" --include="*.ts" --include="*.tsx" .
   
   # Find in unexpected places
   grep -r "pattern" --include="*.json" --include="*.md" --include="*.yml" .
   ```

2. **Check Infrastructure**:
   - Read `package.json` - dependencies, scripts
   - Read `tsconfig.json` - paths, compiler options
   - Check `.env.example` - required environment
   - Review `.github/workflows` - CI/CD impact

3. **Map Dependencies**:
   - List all files importing changed modules
   - Identify test files affected
   - Check for configuration dependencies

4. **Verify Symmetry**:
   - Find similar implementations
   - Ensure consistent patterns
   - Plan global refactoring if needed

## Integration with Sequential Thinking

**Thought 1**: Wild Exploration - Search globally, follow threads
**Thought 2**: Infrastructure Check - All config files
**Thought 3**: Dependency Mapping - Full call graph
**Thought 4**: Symmetry Analysis - Pattern consistency
**Thought 5**: Risk Assessment - Impact evaluation
**Thought 6+**: Execution planning with checkpoints

## Output Requirements

After ICEBERG analysis, provide:
- **Files Identified**: Complete list of affected files
- **Dependencies Mapped**: Call graph summary
- **Risk Level**: Low/Medium/High with justification
- **Execution Plan**: Step-by-step with validation gates
- **Rollback Strategy**: How to undo if needed