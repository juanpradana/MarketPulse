---
name: workflow-orchestrator
description: Cross-domain coordination and workflow management
glob: "**/*"
alwaysApply: true
trigger: always_on
---

# Workflow Orchestrator: The Conductor

## Purpose
Coordinate complex multi-domain tasks by:
- Selecting appropriate domains
- Sequencing operations
- Managing handoffs
- Ensuring consistency

## Workflow Triggers

### Auto-Detection Keywords
| Keyword | Domain | Skill |
|---------|--------|-------|
| "buat fitur", "add feature", "implement" | Fullstack | @fullstack-generator |
| "cari API", "reverse", "sniff", "analyze app" | Reverse | @api-discovery |
| "hubungkan", "integrate", "sync", "bridge" | Integration | @integration-bridge |
| "responsive", "mobile view", "breakpoint" | Frontend | @responsive-optimizer |

## The ORCHESTRA Method

**O**rient - Understand the full landscape
**R**oute - Direct to appropriate domains/skills
**C**oordinate - Manage parallel/sequential execution
**H**andoff - Transfer context between domains
**E**xecute - Perform with domain expertise
**S**ynchronize - Ensure consistency across domains
**T**est - Validate end-to-end
**R**eview - Check against standards
**A**rchive - Document and commit

## Execution Flow

### Phase 1: ORIENT (Sequential Thinking)
1. **Analyze request**: Identify domains involved
2. **Map dependencies**: Which domain depends on which?
3. **Select tools**: Context7, Playwright, domain rules
4. **Define checkpoints**: Validation gates between domains

### Phase 2: ROUTE
Route to single or multiple domains:
- **Single domain**: Direct to domain rule
- **Multi-domain**: Activate workflow YAML
- **Complex**: Activate skill with resources

### Phase 3: COORDINATE
For multi-domain tasks:
```
Backend API → Frontend Integration → Responsive UI → E2E Test
     ↑              ↓                    ↓            ↓
   Contract    Type Generation    Component     Verification
   Definition     & Hooks          Build        & Commit
```

### Phase 4: HANDOFF
When transferring between domains:
- **Document state**: What was completed, what's next
- **Pass context**: Files modified, decisions made
- **Validate contract**: Ensure interfaces match

## Domain Handoff Protocol

### Backend → Frontend
1. Backend provides OpenAPI spec
2. Frontend generates types from spec
3. Validate type compatibility
4. Frontend implements UI

### Reverse Engineering → Integration
1. Document discovered API
2. Create adapter in integration layer
3. Test adapter with real calls
4. Document integration pattern

### Integration → Fullstack
1. Verify service connectivity
2. Update environment variables
3. Test cross-service flows
4. Monitor error rates

## Checkpoint Gates

### Gate 1: Pre-Domain
- [ ] Context gathered (Sequential Thinking)
- [ ] Dependencies identified (Universal Context)
- [ ] Tools ready (Context7, Playwright)

### Gate 2: Mid-Domain
- [ ] Pattern consistency checked
- [ ] Tests passing
- [ ] Documentation updated

### Gate 3: Post-Domain
- [ ] Handoff documentation complete
- [ ] Next domain briefed
- [ ] No regressions introduced

### Gate 4: Final
- [ ] All domains complete
- [ ] Integration tests passing
- [ ] Playwright E2E successful
- [ ] Git commit with meaningful message

## Error Recovery

### Domain Failure
1. **Pause**: Stop workflow, preserve state
2. **Diagnose**: Root cause analysis
3. **Rollback**: Revert to last checkpoint
4. **Retry**: Attempt with adjusted parameters
5. **Escalate**: Notify user if >3 failures

### Context Loss
1. **Re-scan**: Re-read project structure
2. **Re-map**: Rebuild dependency graph
3. **Resume**: Continue from last known good state

## Integration with Skills

When workflow complexity requires it, invoke:
- `@fullstack-generator` for end-to-end features
- `@api-discovery` for reverse engineering tasks
- `@integration-bridge` for service connections
- `@responsive-optimizer` for UI adaptation

Each skill has its own detailed execution plan in its SKILL.md