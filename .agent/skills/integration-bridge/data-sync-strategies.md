# Data Synchronization Strategies

## 1. Master-Slave Replication

### Pattern
One primary source of truth, read replicas for scale.

### Implementation
```typescript
// Write to master
await masterDB.users.create(data);

// Replicate to slaves
replicationStream.on('change', async (change) => {
  await slaveDB.apply(change);
});

// Read from slave
const user = await slaveDB.users.findById(id);
```

### When to Use
- Read-heavy workloads
- Geographic distribution
- High availability requirements

## 2. Bi-Directional Sync

### Pattern
Both systems can modify data, conflicts resolved.

### Implementation
```typescript
interface SyncRecord {
  id: string;
  data: any;
  version: number;
  timestamp: Date;
  source: string;
}

async function syncBidirectional(
  local: SyncRecord[],
  remote: SyncRecord[]
): Promise<SyncResult> {
  const conflicts: Conflict[] = [];
  const merged: SyncRecord[] = [];
  
  for (const record of [...local, ...remote]) {
    const existing = merged.find(r => r.id === record.id);
    
    if (!existing) {
      merged.push(record);
    } else if (existing.version < record.version) {
      merged[merged.indexOf(existing)] = record;
    } else if (existing.version === record.version) {
      conflicts.push({ local: existing, remote: record });
    }
  }
  
  return { merged, conflicts };
}

// Conflict resolution strategies
function resolveConflict(local: SyncRecord, remote: SyncRecord): SyncRecord {
  // Strategy: Last write wins
  return local.timestamp > remote.timestamp ? local : remote;
  
  // Strategy: Source priority
  // return local.source === 'master' ? local : remote;
  
  // Strategy: Manual resolution
  // throw new ConflictError(local, remote);
}
```

## 3. Event Sourcing

### Pattern
Store all changes as events, reconstruct state from event log.

### Implementation
```typescript
interface Event {
  id: string;
  type: string;
  aggregateId: string;
  payload: any;
  timestamp: Date;
  version: number;
}

class EventStore {
  async append(event: Event): Promise<void> {
    await this.db.events.insert(event);
    await this.project(event);
  }
  
  async getEvents(aggregateId: string): Promise<Event[]> {
    return this.db.events.find({ aggregateId })
      .sort({ version: 1 });
  }
  
  private async project(event: Event): Promise<void> {
    // Update read models
    const projector = this.projectors.get(event.type);
    if (projector) {
      await projector.handle(event);
    }
  }
}

// Reconstruct aggregate
async function reconstructAggregate(
  eventStore: EventStore,
  aggregateId: string
): Promise<Aggregate> {
  const events = await eventStore.getEvents(aggregateId);
  return events.reduce((aggregate, event) => {
    return aggregate.apply(event);
  }, new Aggregate(aggregateId));
}
```

## 4. CQRS (Command Query Responsibility Segregation)

### Pattern
Separate models for reads and writes.

### Implementation
```typescript
// Command side (writes)
class UserCommandHandler {
  async createUser(command: CreateUserCommand): Promise<void> {
    const user = User.create(command);
    await this.userRepo.save(user);
    await this.eventBus.publish(new UserCreatedEvent(user));
  }
}

// Query side (reads)
class UserQueryHandler {
  async getUserById(id: string): Promise<UserDTO> {
    return this.readDB.users.findById(id);
  }
  
  async searchUsers(criteria: SearchCriteria): Promise<UserDTO[]> {
    return this.readDB.users.search(criteria);
  }
}

// Sync via events
eventBus.on(UserCreatedEvent, async (event) => {
  await readDB.users.insert({
    id: event.userId,
    name: event.name,
    // Denormalized for query efficiency
  });
});
```

## Comparison

| Strategy | Consistency | Complexity | Use Case |
|----------|-------------|------------|----------|
| Master-Slave | Eventual | Low | Read scaling |
| Bi-Directional | Eventual | Medium | Distributed systems |
| Event Sourcing | Strong | High | Audit trails, complex domains |
| CQRS | Eventual | High | High read/write ratio |