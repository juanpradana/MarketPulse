---
name: integration-bridge
description: Connect disparate systems, synchronize data, and maintain consistency across services. Use for API integrations, data sync, and service orchestration.
---

## Integration Bridge Skill

### When to Activate
- User requests: "hubungkan", "integrate", "sync", "bridge services"
- Task involves: Multiple APIs, data synchronization, service mesh
- Keywords: "webhook", "event", "queue", "adapter"

### Resources
- @service-adapter-pattern.md - Wrapper and transformation patterns
- @data-sync-strategies.md - Bi-directional sync, conflict resolution

### Execution Protocol

#### Phase 1: Service Mapping
1. **Identify services**: External APIs, databases, message queues
2. **Map data flow**: Direction, frequency, volume
3. **Analyze contracts**: Existing APIs, data formats
4. **Check constraints**: Rate limits, auth methods, SLAs

#### Phase 2: Architecture Design
1. **Select pattern**:
   - **Sync**: Direct API call with circuit breaker
   - **Async**: Message queue with retry
   - **Batch**: Scheduled ETL jobs
   - **Stream**: Real-time event streaming

2. **Design adapter**:
   - Interface normalization
   - Error translation
   - Retry logic
   - Monitoring hooks

#### Phase 3: Implementation
1. **Authentication**:
   - OAuth flow implementation
   - Token refresh automation
   - Credential secure storage

2. **Data Transformation**:
   - Schema mapping
   - Type conversion
   - Validation rules
   - Sanitization

3. **Resilience**:
   - Circuit breaker configuration
   - Exponential backoff
   - Dead letter queue
   - Fallback strategies

#### Phase 4: Testing
1. **Contract testing**: Pact or similar
2. **Integration testing**: TestContainers for real services
3. **Chaos testing**: Simulate service failures
4. **Load testing**: Verify rate limit handling

#### Phase 5: Monitoring
1. **Metrics**: Latency, throughput, error rates
2. **Alerting**: Anomaly detection
3. **Tracing**: Distributed correlation IDs
4. **Dashboards**: Real-time health status

### Output Artifacts
- `/integrations/adapters/[service].ts`
- `/integrations/workflows/[flow].ts`
- `/docs/architecture/integration-[name].md`
- Monitoring dashboards config

### Safety Checkpoints
- [ ] No credential hardcoding
- [ ] Rate limits respected
- [ ] PII handled correctly
- [ ] Rollback plan documented