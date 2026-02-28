# Architecture Patterns

## Clean Architecture (Recommended)

### Layer Structure
```
src/
├── domain/          # Entities, value objects, domain services
│   ├── entities/
│   ├── value-objects/
│   └── services/
├── application/     # Use cases, DTOs, interfaces
│   ├── ports/
│   └── services/
├── infrastructure/  # External concerns
│   ├── persistence/
│   ├── web/
│   └── external/
└── interface/       # Controllers, presenters, CLI
    ├── http/
    └── cli/
```

### Dependency Rule
Dependencies point inward:
- Domain has no dependencies
- Application depends on Domain
- Infrastructure depends on Application
- Interface depends on Infrastructure

## Domain-Driven Design (DDD)

### Building Blocks
- **Entity**: Has identity (User, Order)
- **Value Object**: No identity (Money, Address)
- **Aggregate**: Cluster of entities with root
- **Repository**: Persistence abstraction
- **Domain Service**: Business logic spanning aggregates
- **Application Service**: Orchestrates use cases

## MVC (Traditional)

### Structure
```
src/
├── models/          # Data layer, business logic
├── views/           # Presentation layer
└── controllers/     # Request handling, coordination
```

### When to Use
- Simple CRUD applications
- Rapid prototyping
- Small teams

## Tech Stack Specific

### Node.js/TypeScript
- **Framework**: Express, Fastify, NestJS
- **ORM**: Prisma, TypeORM
- **Validation**: Zod, class-validator

### Python
- **Framework**: FastAPI, Django, Flask
- **ORM**: SQLAlchemy, Django ORM
- **Validation**: Pydantic, Marshmallow

### Go
- **Framework**: Gin, Echo, Fiber
- **ORM**: GORM, Ent
- **Validation**: go-playground/validator