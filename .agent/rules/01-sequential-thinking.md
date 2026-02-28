---
name: sequential-thinking
description: Structured problem-solving protocol for all complex tasks
glob: "**/*"
alwaysApply: true
trigger: always_on
---

# Sequential Thinking Protocol v2.0

## Activation Trigger
**ALWAYS** activate for:
- Multi-step tasks (>3 actions)
- Cross-domain operations
- Architecture decisions
- Integration tasks
- Any task with "and", "then", "also", "integrate"

## The THINK Method

**T**otal comprehension - Understand the full scope
**H**ierarchical decomposition - Break into ordered steps  
**I**nvestigation - Gather all context and dependencies
**N**avigation - Execute with validation gates
**K**nowledge capture - Document and verify

## Execution Protocol

### Phase 1: EXPLORATION (Thoughts 1-3)
1. **Wild Search**: Broad regex patterns, find "cousin" code, check unexpected places
2. **Infrastructure Scan**: package.json, tsconfig, Dockerfile, CI/CD, env files
3. **Dependency Mapping**: Who calls this? Who does this call? Full call graph

### Phase 2: ANALYSIS (Thoughts 4-6)
4. **Blast Radius**: Map every file potentially affected
5. **Pattern Recognition**: Identify existing patterns to maintain symmetry
6. **Constraint Identification**: Security, performance, compatibility limits

### Phase 3: PLANNING (Thoughts 7-9)
7. **Strategy Selection**: Choose approach based on patterns and constraints
8. **Step Sequencing**: Order operations with dependency awareness
9. **Checkpoint Definition**: Validation gates between steps

### Phase 4: EXECUTION (Thoughts 10+)
10. **Implementation**: Execute step-by-step with verification
11. **Adaptation**: Adjust plan based on discovered complexity
12. **Completion**: Final validation and documentation

## Dynamic Adjustment Rules

### Expanding Scope
```javascript
{
  thought: "Discovered hidden complexity requiring deeper analysis",
  nextThoughtNeeded: true,
  thoughtNumber: 4,
  totalThoughts: 8,
  needsMoreThoughts: true
}
```

### Contracting Scope
```javascript
{
  thought: "Solution complete. Original estimate was 10, completed in 6.",
  nextThoughtNeeded: false,
  thoughtNumber: 6,
  totalThoughts: 6,
  isRevision: true,
  revisesThought: 1
}
```

## Integration with Other Tools

- **After Thought 3**: Invoke Context7 if unfamiliar libraries detected
- **After Thought 6**: Use Playwright for UI impact assessment if needed
- **During Execution**: Cross-reference with domain-specific rules
- **Final Thought**: Trigger git commit workflow if changes made

## Mandatory Checkpoints

Before proceeding to next thought, confirm:
- [ ] Current understanding documented
- [ ] No assumptions made without verification
- [ ] All dependencies identified
- [ ] Rollback plan considered