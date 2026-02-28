---
name: domain-backend
description: Backend-specific standards for Node.js/Python/Go
glob: "backend/**/*.{ts,js,py,go}"
alwaysApply: false
trigger: always_on
---

# Backend Domain Standards

## Tech Stack Detection
Auto-detect runtime and framework:
- **Node.js**: Express, Fastify, NestJS, Koa
- **Python**: FastAPI, Flask, Django, Tornado
- **Go**: Gin, Echo, Fiber, standard library
- **Database**: PostgreSQL, MySQL, MongoDB, Redis

## API Design Principles

### RESTful Standards
- **Versioning**: `/api/v1/resource`
- **Naming**: Plural nouns (`/users`, `/orders`)
- **Methods**: GET (read), POST (create), PUT (update), DELETE (remove)
- **Status codes**: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found, 500 Error

### Response Format
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 100
  },
  "error": null
}
```

## Security Standards

### Authentication & Authorization
- **JWT**: Access token (15min) + Refresh token (7 days)
- **Passwords**: bcrypt with 12+ rounds
- **CORS**: Whitelist specific origins
- **Helmet**: Security headers for Express/Fastify

### Input Validation
- **Node.js**: Zod or Joi
- **Python**: Pydantic or Marshmallow
- **Go**: go-playground/validator
- **Sanitization**: Prevent XSS, SQL injection

### Rate Limiting
- **Public APIs**: 100 requests/minute
- **Authenticated**: 1000 requests/minute
- **Burst**: Allow short bursts with exponential backoff

## Database Patterns

### ORM/Query Builder
- **Node.js**: Prisma (preferred) or TypeORM
- **Python**: SQLAlchemy 2.0 or Django ORM
- **Go**: GORM or Ent

### Migration Strategy
- **Version control**: All migrations in `/migrations`
- **Rollback plan**: Every up migration has down migration
- **Data integrity**: Foreign keys, constraints, indexes
- **Seeding**: Development data in `/seeds`

## Error Handling

### Structured Logging
```typescript
// Winston (Node.js) or structlog (Python)
{
  "timestamp": "2026-02-25T10:00:00Z",
  "level": "error",
  "message": "User creation failed",
  "context": {
    "userId": "123",
    "error": "Duplicate email",
    "stack": "..."
  },
  "requestId": "uuid-v4"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email already exists",
    "details": [{ "field": "email", "issue": "unique" }]
  }
}
```