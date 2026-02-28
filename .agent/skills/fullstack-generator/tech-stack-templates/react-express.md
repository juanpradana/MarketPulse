# React + Express Stack Template

## Project Structure
```
project/
├── frontend/          # React + Vite
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── pages/
│   │   └── types/
│   └── package.json
├── backend/           # Express + Prisma
│   ├── src/
│   │   ├── routes/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── prisma/
│   └── package.json
└── docker-compose.yml
```

## Frontend Setup

### Dependencies
```bash
npm install @tanstack/react-query axios zod react-hook-form @hookform/resolvers
npm install -D @types/node typescript tailwindcss postcss autoprefixer
```

### Key Files
- `src/lib/api.ts` - Axios instance with interceptors
- `src/hooks/useApi.ts` - React Query hooks
- `src/types/api.ts` - Generated from OpenAPI

## Backend Setup

### Dependencies
```bash
npm install express cors helmet morgan dotenv bcryptjs jsonwebtoken zod
npm install -D @types/express @types/cors @types/bcryptjs @types/jsonwebtoken typescript ts-node nodemon prisma
```

### Key Files
- `src/prisma/schema.prisma` - Database schema
- `src/routes/` - API route definitions
- `src/middleware/` - Auth, validation, error handling

## Database (Prisma)
```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(uuid())
  email     String   @unique
  name      String
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

## Integration
1. Backend generates OpenAPI spec
2. Frontend uses `openapi-typescript` to generate types
3. React Query hooks use generated types