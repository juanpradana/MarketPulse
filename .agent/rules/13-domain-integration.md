---
name: domain-integration
description: System integration patterns for connecting services
glob: "integrations/**/*.{ts,js,py}"
alwaysApply: false
trigger: always_on
---

# Integration Domain Standards

## Integration Patterns

### 1. API Gateway Pattern
Single entry point for multiple services.
- **Routing**: Path-based to microservices
- **Aggregation**: Combine multiple backend calls
- **Transformation**: Protocol translation (REST ↔ GraphQL)
- **Rate limiting**: Global and per-service limits

### 2. Event-Driven Architecture
Async communication via message broker.
- **Broker**: RabbitMQ, Kafka, AWS SNS/SQS, Redis Pub/Sub
- **Events**: UserCreated, OrderPlaced, PaymentReceived
- **Consumers**: Idempotent, retry with backoff
- **Dead letter queues**: For failed processing

### 3. Data Synchronization
Bi-directional data consistency.
- **Master-slave**: One source of truth
- **Multi-master**: Conflict resolution required
- **Event sourcing**: Audit trail of all changes
- **CQRS**: Separate read/write models

### 4. Adapter Pattern
Normalize external service interfaces.
- **Wrapper**: Hide external API complexity
- **Transform**: Convert data formats
- **Circuit breaker**: Fail fast on service outage
- **Fallback**: Degraded functionality

## Connection Management

### Resilience Patterns
- **Retry**: Exponential backoff, max 3 attempts
- **Circuit breaker**: Open after 5 failures, half-open after 30s
- **Timeout**: 5s for critical, 30s for background
- **Bulkhead**: Isolate connection pools per service

### Authentication Strategies
- **OAuth 2.0**: Standard for user-delegated access
- **API Keys**: For service-to-service (rotate quarterly)
- **mTLS**: For high-security environments
- **JWT**: Short-lived access tokens + refresh tokens

## Data Transformation

### Mapping Layer
```typescript
// adapters/salesforce.ts
interface SalesforceAccount {
  Id: string;
  Name: string;
  Industry: string;
}

interface InternalAccount {
  id: string;
  name: string;
  sector: string;
  source: 'salesforce';
}

function mapSalesforceToInternal(sf: SalesforceAccount): InternalAccount {
  return {
    id: sf.Id,
    name: sf.Name,
    sector: mapIndustry(sf.Industry),
    source: 'salesforce'
  };
}
```

### Schema Versioning
- **Backward compatibility**: New fields optional
- **Version headers**: `Accept: application/vnd.api.v2+json`
- **Migration scripts**: Data transformation on version change
- **Deprecation warnings**: 6 months notice before removal

## Monitoring & Observability

### Metrics
- **Latency**: p50, p95, p99 response times
- **Throughput**: Requests per second
- **Error rate**: 4xx and 5xx percentages
- **Saturation**: Connection pool utilization

### Distributed Tracing
- **Correlation ID**: Propagate through all services
- **Span context**: Track request lifecycle
- **Baggage**: Pass metadata without changing payload

### Alerting
- **Latency**: Alert if p95 > 500ms for 5 minutes
- **Errors**: Alert if error rate > 1% for 2 minutes
- **Saturation**: Alert if > 80% capacity

## Testing Strategy

### Contract Testing
- **Pact**: Consumer-driven contracts
- **Provider verification**: Validate against consumers
- **Breaking changes**: Detect before deployment

### Integration Testing
- **Test containers**: Real databases and services
- **WireMock**: Stub external services
- **Chaos testing**: Simulate service failures

## Security

### Data Protection
- **Encryption in transit**: TLS 1.3 minimum
- **Encryption at rest**: AES-256 for sensitive data
- **PII handling**: Mask in logs, encrypt in databases
- **Data residency**: Respect geographic restrictions

### Access Control
- **Least privilege**: Minimum required permissions
- **Audit logging**: All data access logged
- **Regular review**: Quarterly access audits