# Vue + FastAPI Stack Template

## Project Structure
```
project/
├── frontend/          # Vue 3 + Vite
│   ├── src/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── stores/
│   │   ├── views/
│   │   └── types/
│   └── package.json
├── backend/           # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── schemas/
│   └── requirements.txt
└── docker-compose.yml
```

## Frontend Setup

### Dependencies
```bash
npm install vue@next vue-router@4 pinia @vueuse/core axios zod
npm install -D @vitejs/plugin-vue typescript tailwindcss postcss autoprefixer
```

### Key Files
- `src/composables/useApi.ts` - API composables
- `src/stores/` - Pinia stores
- `src/types/api.ts` - Generated from OpenAPI

## Backend Setup

### Dependencies
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

### Key Files
- `app/core/config.py` - Settings management
- `app/models/` - SQLAlchemy models
- `app/schemas/` - Pydantic schemas
- `app/api/deps.py` - Dependencies (auth, DB)

## Database (SQLAlchemy + Alembic)
```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## Integration
1. FastAPI auto-generates OpenAPI at `/openapi.json`
2. Use `openapi-typescript` to generate types
3. Vue composables use generated types