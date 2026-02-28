# Next.js + Prisma Full Stack Template

## Project Structure
```
project/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── api/            # API Routes
│   │   ├── (routes)/       # Page routes
│   │   └── layout.tsx
│   ├── components/         # React components
│   ├── lib/                # Utilities, Prisma client
│   ├── server/             # Server-only code
│   │   ├── actions/        # Server Actions
│   │   └── queries/        # Database queries
│   └── types/              # TypeScript types
├── prisma/
│   └── schema.prisma
└── package.json
```

## Setup

### Dependencies
```bash
npm install next@latest react@latest react-dom@latest
npm install @prisma/client zod react-hook-form @hookform/resolvers
npm install -D prisma typescript @types/node @types/react tailwindcss postcss autoprefixer
```

## Database (Prisma)
```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  author    User     @relation(fields: [authorId], references: [id])
  authorId  String
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model User {
  id    String @id @default(cuid())
  email String @unique
  name  String?
  posts Post[]
}
```

## Server Actions (Next.js 14+)
```typescript
// src/server/actions/post.ts
'use server'

import { prisma } from '@/lib/prisma'
import { revalidatePath } from 'next/cache'
import { z } from 'zod'

const createPostSchema = z.object({
  title: z.string().min(1),
  content: z.string().optional(),
})

export async function createPost(input: unknown) {
  const data = createPostSchema.parse(input)
  
  const post = await prisma.post.create({
    data: {
      ...data,
      authorId: 'user_id', // Get from session
    }
  })
  
  revalidatePath('/posts')
  return post
}
```

## Client Components
```typescript
// src/components/post-form.tsx
'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { createPost } from '@/server/actions/post'

export function PostForm() {
  const form = useForm({
    resolver: zodResolver(createPostSchema)
  })
  
  return (
    <form action={createPost}>
      {/* Form fields */}
    </form>
  )
}
```

## Benefits
- Single codebase for frontend/backend
- Type-safe database queries
- Server Actions for mutations
- Automatic caching and revalidation