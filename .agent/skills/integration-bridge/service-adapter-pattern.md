# Service Adapter Pattern

## Purpose
Normalize different external service interfaces into a consistent internal API.

## Structure
```typescript
// adapters/base.ts
interface ServiceAdapter<T, R> {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  execute(operation: T): Promise<R>;
  healthCheck(): Promise<HealthStatus>;
}

// adapters/salesforce.ts
class SalesforceAdapter implements ServiceAdapter<SFOperation, SFResult> {
  private client: jsforce.Connection;
  private circuitBreaker: CircuitBreaker;
  
  async connect(): Promise<void> {
    this.client = new jsforce.Connection({
      loginUrl: process.env.SF_URL
    });
    await this.client.login(
      process.env.SF_USERNAME,
      process.env.SF_PASSWORD
    );
  }
  
  async execute(operation: SFOperation): Promise<SFResult> {
    return this.circuitBreaker.fire(async () => {
      switch (operation.type) {
        case 'QUERY':
          return this.client.query(operation.soql);
        case 'CREATE':
          return this.client.sobject(operation.object).create(operation.data);
        default:
          throw new Error(`Unknown operation: ${operation.type}`);
      }
    });
  }
  
  async healthCheck(): Promise<HealthStatus> {
    try {
      await this.client.query('SELECT Id FROM User LIMIT 1');
      return { status: 'healthy', latency: 100 };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }
}
```

## Circuit Breaker Integration
```typescript
import CircuitBreaker from 'opossum';

const options = {
  timeout: 3000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000
};

const breaker = new CircuitBreaker(asyncFunction, options);

breaker.on('open', () => console.log('Circuit is open'));
breaker.on('halfOpen', () => console.log('Circuit is half-open'));
breaker.on('close', () => console.log('Circuit is closed'));
```

## Error Translation
```typescript
class AdapterError extends Error {
  constructor(
    public service: string,
    public code: string,
    public originalError: Error
  ) {
    super(`${service} error: ${code}`);
  }
}

function translateError(service: string, error: any): AdapterError {
  if (error.code === 'ECONNREFUSED') {
    return new AdapterError(service, 'SERVICE_UNAVAILABLE', error);
  }
  if (error.statusCode === 429) {
    return new AdapterError(service, 'RATE_LIMITED', error);
  }
  return new AdapterError(service, 'UNKNOWN_ERROR', error);
}
```

## Usage
```typescript
const adapter = new SalesforceAdapter();
await adapter.connect();

try {
  const result = await adapter.execute({
    type: 'QUERY',
    soql: 'SELECT Id, Name FROM Account'
  });
} catch (error) {
  if (error instanceof AdapterError) {
    // Handle standardized error
  }
}
```