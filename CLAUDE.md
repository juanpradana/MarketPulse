# CLAUDE.md - MarketPulse Architecture & Development Guide

> **IMPORTANT**: This document serves as the canonical reference for understanding MarketPulse's frontend-backend architecture. Preserve this knowledge for all future development work.

---

## 1. Project Overview

**MarketPulse** is a full-stack investment intelligence platform for Indonesian equity analysis. It combines news sentiment analysis, NeoBDM fund flow data, broker tracking, price-volume analytics, and workflow-driven screening (Alpha Hunter).

### Core Philosophy
- **Data-Driven Decisions**: Every feature is backed by quantitative analysis
- **Modular Architecture**: Domain-driven design enables independent feature development
- **Type Safety**: Full TypeScript frontend with strongly-typed API contracts
- **Real-time Intelligence**: Live scraping, analysis, and visualization pipeline

---

## 2. System Architecture

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MARKETPULSE SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐         HTTP/REST          ┌──────────────────┐      │
│  │   Next.js 16     │ ◄────────────────────────► │   FastAPI        │      │
│  │   (Frontend)     │    CORS-enabled API        │   (Backend)      │      │
│  │                  │    GZip compression        │                  │      │
│  │  localhost:3000  │                          │  localhost:8000  │      │
│  └──────────────────┘                            └────────┬─────────┘      │
│           ▲                                               │                │
│           │                                               ▼                │
│           │                                     ┌──────────────────┐      │
│           │                                     │   Domain Routers │      │
│           │                                     │  - Dashboard     │      │
│           │                                     │  - NeoBDM        │      │
│           │                                     │  - Done Detail   │      │
│           │                                     │  - Alpha Hunter  │      │
│           │                                     │  - Bandarmology  │      │
│           │                                     └────────┬─────────┘      │
│           │                                              │                │
│           │                                     ┌────────▼─────────┐      │
│           │                                     │   Data Layer     │      │
│           │                                     │  - SQLite DB     │      │
│           │                                     │  - ChromaDB      │      │
│           │                                     │  - File Storage  │      │
│           │                                     └──────────────────┘      │
│           │                                                                │
│           │                                     ┌──────────────────┐      │
│           └──────────────────────────────────── │   Ollama LLM       │      │
│                                                 │  (AI Analysis)     │      │
│                                                 └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16 + TypeScript | React framework with App Router |
| **Styling** | Tailwind CSS v4 | Utility-first styling |
| **Charts** | Recharts | Data visualization |
| **Backend** | FastAPI + Python 3.10+ | High-performance API framework |
| **Database** | SQLite | Primary relational storage |
| **Vector DB** | ChromaDB | RAG embeddings storage |
| **AI/ML** | Ollama (LLaMA 3.2) | Local LLM inference |
| **Scraping** | Playwright | Browser automation |

---

## 3. Frontend Architecture

### 3.1 Directory Structure

```
frontend/src/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx               # Root layout with providers
│   ├── page.tsx                 # Home (redirects to /dashboard)
│   ├── dashboard/               # Market Intelligence Dashboard
│   ├── alpha-hunter/            # Multi-stage screening workflow
│   ├── bandarmology/            # Broker behavior analysis
│   ├── broker-summary/          # Broker activity summary
│   ├── done-detail/             # Trade data analysis
│   ├── neobdm-summary/          # Fund flow summary
│   ├── neobdm-tracker/          # Historical flow visualization
│   ├── news-library/            # News aggregation
│   ├── price-volume/            # Price-volume analytics
│   ├── rag-chat/                # AI chat with disclosures
│   └── ...
│
├── components/
│   ├── alpha-hunter/            # Alpha Hunter feature components
│   ├── bandarmology/            # Bandarmology components
│   ├── charts/                  # Reusable chart components
│   ├── dashboard/               # Dashboard-specific components
│   ├── done-detail-components/  # Done Detail analysis UI
│   ├── layout/                  # Layout components (sidebar, etc.)
│   ├── news-library/            # News feed components
│   ├── rag-chat/                # Chat interface
│   ├── shared/                  # Shared UI components
│   └── ui/                      # shadcn/ui base components
│
├── context/
│   └── filter-context.tsx       # Global filter state (ticker, date range)
│
├── hooks/
│   ├── useApi.ts               # Generic API hook with loading/error states
│   ├── useDashboard.ts         # Dashboard-specific queries
│   ├── useNeoBDM.ts            # NeoBDM data fetching
│   └── ...
│
├── lib/
│   ├── utils.ts                # Utility functions (cn, etc.)
│   └── string-utils.ts         # String manipulation helpers
│
├── services/
│   └── api/
│       ├── base.ts             # API base URL & utilities
│       ├── index.ts            # Centralized API exports
│       ├── dashboard.ts        # Dashboard API client
│       ├── neobdm.ts           # NeoBDM API client
│       ├── doneDetail.ts       # Done Detail API client
│       ├── bandarmology.ts     # Bandarmology API client
│       └── ...                 # Other domain APIs
│
└── types/
    └── market.ts               # Core TypeScript interfaces
```

### 3.2 API Service Layer Pattern

**CRITICAL**: All API communication flows through the `services/api/` layer. This abstraction is essential for:
- Type safety across frontend-backend boundary
- Consistent error handling
- Easy mocking for testing
- Centralized URL management

#### Base Configuration (`services/api/base.ts`)

```typescript
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

// URL parameter builder with null/undefined filtering
export function buildParams(params: Record<string, any>): URLSearchParams

// Date sanitization for API calls
export function sanitizeDate(date?: string): string | undefined

// Consistent response error handling
export async function handleResponse<T>(response: Response, fallback?: T): Promise<T>
```

#### Domain API Client Pattern (`services/api/neobdm.ts`)

```typescript
export const neobdmApi = {
    // Each method is fully typed
    getNeoBDMSummary: async (method: string, period: string): Promise<NeoBDMData> => {
        const params = buildParams({ method, period });
        const response = await fetch(`${API_BASE_URL}/api/neobdm-summary?${params}`);
        return await response.json();
    },
    // ... more methods
};
```

#### Centralized API Export (`services/api/index.ts`)

```typescript
const api = {
    ...dashboardApi,
    ...newsApi,
    ...neobdmApi,
    // ... all domain APIs merged
};

export { dashboardApi, newsApi, neobdmApi, api };
```

### 3.3 State Management Pattern

#### Global Filter Context (`context/filter-context.tsx`)

**CRITICAL**: The FilterContext provides global state for:
- **Current Ticker**: Selected stock symbol (defaults to 'All')
- **Date Range**: 30-day default range (start/end dates)

```typescript
interface FilterContextType {
    ticker: string;
    setTicker: (ticker: string) => void;
    dateRange: { start: string; end: string };
    setDateRange: (range: DateRange) => void;
}
```

**Usage Pattern**:
```typescript
const { ticker, dateRange } = useFilter();

// All components use these as primary filters
const stats = await api.getDashboardStats(ticker, dateRange.start, dateRange.end);
```

#### Custom Hooks Pattern (`hooks/useApi.ts`)

The `useApi` hook provides standardized loading/error handling:

```typescript
const { data, loading, error, execute, reset } = useApi(apiFunction, {
    initialData: defaultValue,
    onSuccess: (data) => console.log('Success:', data),
    onError: (err) => console.error('Error:', err)
});
```

### 3.4 Component Architecture

#### Page Structure Pattern

Each page follows a consistent structure:
1. **'use client'** directive for interactivity
2. **Context Provider** wrapper (if needed)
3. **Filter Integration** via `useFilter()` hook
4. **API Data Fetching** via custom hooks or direct API calls
5. **Responsive Layout** with Tailwind breakpoints

#### Example Page (`app/dashboard/page.tsx`):

```typescript
'use client';

export default function DashboardPage() {
    const { ticker: globalTicker, dateRange } = useFilter();
    const ticker = globalTicker === 'All' ? '^JKSE' : globalTicker;

    const [metrics, setMetrics] = useState({...});

    // Fetch data when filters change
    useEffect(() => {
        fetchMetrics();
    }, [ticker, dateRange.start, dateRange.end]);

    // Component JSX...
}
```

---

## 4. Backend Architecture

### 4.1 Directory Structure

```
backend/
├── main.py                      # FastAPI application entry point
├── server.py                    # Uvicorn server wrapper
├── config.py                    # Configuration settings
├── data_provider.py             # Market data aggregation
├── rag_client.py                # RAG/LLM interface
├── idx_processor.py             # PDF processing for disclosures
│
├── routes/                      # API endpoint routers
│   ├── dashboard.py             # Dashboard endpoints
│   ├── news.py                  # News aggregation endpoints
│   ├── neobdm.py                # NeoBDM data endpoints
│   ├── done_detail.py           # Done Detail endpoints
│   ├── alpha_hunter.py          # Alpha Hunter workflow endpoints
│   ├── bandarmology.py          # Bandarmology endpoints
│   ├── broker_five.py           # Broker watchlist endpoints
│   ├── price_volume.py          # Price-volume endpoints
│   ├── disclosures.py           # IDX disclosure endpoints
│   ├── scrapers.py              # Scraper control endpoints
│   └── broker_stalker.py        # Broker stalker endpoints
│
├── modules/                     # Business logic modules
│   ├── analyzer.py              # Sentiment analysis engine
│   ├── scraper_*.py             # News scrapers (CNBC, Emiten, etc.)
│   ├── scraper_neobdm.py        # NeoBDM data scraper
│   ├── bandarmology_analyzer.py # Bandarmology scoring engine
│   ├── alpha_hunter_*.py        # Alpha Hunter analysis modules
│   ├── neobdm_api_client.py     # NeoBDM API integration
│   ├── broker_stalker_analyzer.py # Broker analysis
│   └── ...
│
└── db/                          # Database layer
    ├── connection.py            # SQLite connection manager
    ├── news_repository.py       # News data access
    ├── neobdm_repository.py     # NeoBDM data access
    ├── done_detail_repository.py # Done Detail data access
    ├── bandarmology_repository.py # Bandarmology data access
    ├── alpha_hunter_repository.py # Alpha Hunter data access
    └── ...
```

### 4.2 Router Registration Pattern

**CRITICAL**: All routers are registered in `main.py`:

```python
from routes.dashboard import router as dashboard_router
from routes.neobdm import router as neobdm_router
# ... other imports

app = FastAPI(title="MarketPulse API", version="2.0.0")

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for large JSON responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register routers
app.include_router(dashboard_router)
app.include_router(neobdm_router)
# ... other routers
```

### 4.3 API Endpoint Patterns

#### Standard Response Format

All endpoints should return consistent response structures:

```python
# List response
{
    "data": [...],
    "count": 100,
    "date": "2025-02-15"
}

# Detail response
{
    "ticker": "BBCA",
    "field": "value",
    # ... additional fields
}

# Error response
{
    "error": "Error message",
    "detail": "Additional details"
}
```

#### Parameter Patterns

- **Query params**: For GET requests with filters
- **Path params**: For resource identifiers
- **Body params**: For POST/PUT with complex data

### 4.4 Database Layer Pattern

#### Repository Pattern

Each domain has a dedicated repository class:

```python
class NeoBDMRepository:
    def __init__(self):
        self.conn = get_db_connection()

    def get_records(self, ticker: str, start_date: str, end_date: str) -> list:
        # Query implementation
        pass
```

#### Connection Management

```python
# db/connection.py
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

---

## 5. Frontend-Backend Integration

### 5.1 API Contract

**CRITICAL**: The frontend and backend communicate through a strict API contract. Any changes to endpoints MUST be reflected in both:

1. **Backend**: Route handler in `routes/*.py`
2. **Frontend**: API client in `services/api/*.ts`
3. **Types**: Interfaces must match the JSON response structure

### 5.2 Type Safety Bridge

Example of maintaining type safety:

**Backend (Python)**:
```python
@router.get("/api/neobdm-summary")
async def get_neobdm_summary(method: str = "m", period: str = "c"):
    return {
        "scraped_at": datetime.now().isoformat(),
        "data": records
    }
```

**Frontend (TypeScript)**:
```typescript
export interface NeoBDMData {
    scraped_at: string | null;
    data: any[];
}

export const neobdmApi = {
    getNeoBDMSummary: async (method: string = 'm', period: string = 'c'): Promise<NeoBDMData> => {
        // Implementation
    }
};
```

### 5.3 Environment Configuration

#### Frontend (.env.local)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Backend (.env)

```
DATABASE_URL=./data/market_sentinel.db
OLLAMA_BASE_URL=http://localhost:11434
CHROMA_DB_PATH=./chroma_db
```

---

## 6. Feature Modules

### 6.1 Dashboard

**Purpose**: Market overview with sentiment-price correlation

**Key Files**:
- Frontend: `app/dashboard/page.tsx`, `components/dashboard/sentiment-chart.tsx`
- Backend: `routes/dashboard.py`, `data_provider.py`

**Endpoints**:
- `GET /api/dashboard-stats`
- `GET /api/market-data`
- `GET /api/sentiment-data`

### 6.2 Alpha Hunter

**Purpose**: 5-stage screening workflow for trade candidate discovery

**Stages**:
1. Signal Scan (flow-based candidate detection)
2. VPA Validation (volume-price analysis)
3. Smart Flow Check (institutional vs retail)
4. Supply Analysis (retail capitulation detection)
5. Final Conclusion (risk/reward calculation)

**Key Files**:
- Frontend: `app/alpha-hunter/page.tsx`, `components/alpha-hunter/*`
- Backend: `routes/alpha_hunter.py`, `modules/alpha_hunter_*.py`

### 6.3 Bandarmology

**Purpose**: Deep broker behavior analysis with scoring system

**Key Files**:
- Frontend: `app/bandarmology/page.tsx`, `services/api/bandarmology.ts`
- Backend: `routes/bandarmology.py`, `modules/bandarmology_analyzer.py`

**Features**:
- Base screening (Pinky, Crossing, Unusual flags)
- Deep analysis with inventory/broker summary cross-reference
- Entry/target price calculation
- Pump tomorrow prediction

### 6.4 Done Detail

**Purpose**: Paste-based trade data analysis for intraday insights

**Key Files**:
- Frontend: `app/done-detail/page.tsx`, `components/done-detail-components/*`
- Backend: `routes/done_detail.py`, `db/done_detail_repository.py`

**Analysis Types**:
- Imposter Detection (retail brokers trading large values)
- Speed Analysis (trading burst patterns)
- Range Analysis (multi-day patterns)
- Broker Profile (individual broker behavior)

### 6.5 NeoBDM Analysis

**Purpose**: Fund flow tracking and market maker analysis

**Key Files**:
- Frontend: `app/neobdm-summary/page.tsx`, `app/neobdm-tracker/page.tsx`
- Backend: `routes/neobdm.py`, `modules/scraper_neobdm.py`

**Endpoints**:
- `GET /api/neobdm-summary`
- `GET /api/neobdm-history`
- `GET /api/neobdm-broker-summary`

---

## 7. Development Guidelines

### 7.1 Adding a New Feature

1. **Backend**:
   - Create router in `routes/{feature}.py`
   - Implement business logic in `modules/{feature}.py`
   - Add data access in `db/{feature}_repository.py`
   - Register router in `main.py`
   - Test endpoints at `http://localhost:8000/docs`

2. **Frontend**:
   - Create API client in `services/api/{feature}.ts`
   - Export from `services/api/index.ts`
   - Create page at `app/{feature}/page.tsx`
   - Add components in `components/{feature}/`
   - Add sidebar navigation in `components/layout/sidebar.tsx`
   - Add route types to navigation groups

### 7.2 API Versioning

When making breaking changes:
1. Create new endpoint with `/v2/` prefix
2. Deprecate old endpoint with warning header
3. Update frontend to use new endpoint
4. Remove old endpoint after migration period

### 7.3 Database Migrations

SQLite schema changes should be:
1. Documented in `backend/db/connection.py`
2. Backwards compatible where possible
3. Tested with existing data

### 7.4 Component Guidelines

- Use `'use client'` only when necessary (interactivity required)
- Prefer server components for static data display
- Use `useFilter()` for consistent ticker/date filtering
- Implement loading states for all async operations
- Use `ErrorDisplay` component for error handling

---

## 8. Critical Architecture Decisions

### 8.1 Why This Architecture?

| Decision | Rationale |
|----------|-----------|
| **Modular API Services** | Domain isolation enables parallel development and testing |
| **Repository Pattern** | Database logic is decoupled from business logic |
| **Filter Context** | Centralized filter state prevents prop drilling and ensures consistency |
| **useApi Hook** | Standardized loading/error handling across all data fetching |
| **TypeScript Interfaces** | Compile-time verification of API contracts |
| **SQLite + ChromaDB** | Simple, file-based storage with no external dependencies |
| **Ollama (Local LLM)** | Privacy, no API costs, works offline |

### 8.2 Importance for Future Development

**NEVER BREAK THESE PATTERNS**:

1. **API Service Layer**: Always use the `services/api/` layer. Never call `fetch` directly from components.

2. **Type Safety**: Always define TypeScript interfaces that match backend responses. Use `any` sparingly.

3. **Filter Context**: All ticker/date filtering must use the global FilterContext. No local filter state for these.

4. **Repository Pattern**: All database access must go through repository classes. No raw SQL in routes.

5. **Error Handling**: Use the standardized error handling patterns (handleResponse, ErrorDisplay component).

6. **Responsive Design**: All UI must work on mobile (use `lg:`, `md:`, `sm:` breakpoints).

### 8.3 Extension Points

**Safe to Extend**:
- Add new API methods to existing domain clients
- Add new components following existing patterns
- Add new routes following the router pattern
- Add new database tables with repository classes

**Requires Care**:
- Modifying existing API response structures (breaks frontend types)
- Changing FilterContext structure (affects all pages)
- Modifying database schema (requires migration strategy)

---

## 9. Testing & Quality

### 9.1 Frontend Testing

```bash
cd frontend
npm run lint      # ESLint check
npm run build     # TypeScript + build check
npm run dev       # Development server
```

### 9.2 Backend Testing

```bash
cd backend
python -m pytest tests/  # Run test suite
python main.py           # Development server with auto-reload
```

### 9.3 API Documentation

Once backend is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 10. Deployment

### 10.1 Development

```bash
# Terminal 1 - Backend
cd backend
venv\Scripts\activate
python server.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 10.2 Production Build

```bash
# Frontend build
cd frontend
npm run build

# Backend (no build step required)
cd backend
python server.py
```

---

## 11. Implementation Status & TODO

### ✅ Completed Features

| Feature | Location | Status |
|---------|----------|--------|
| Alpha Hunter | `app/alpha-hunter/` | ✅ Complete - 5-stage screening workflow |
| Bandarmology | `app/bandarmology/` | ✅ Complete - Deep broker analysis |
| NeoBDM Analysis | `app/neobdm-*` | ✅ Complete - Fund flow tracking |
| Done Detail | `app/done-detail/` | ✅ Complete - Trade data analysis |
| Dashboard | `app/dashboard/` | ✅ Complete - Market overview |
| News Library | `app/news-library/` | ✅ Complete - News aggregation |
| RAG Chat | `app/rag-chat/` | ✅ Complete - Single-document AI chat |
| Broker Summary | `app/broker-summary/` | ✅ Complete - Broker activity summary |
| Batch Scraping | `scripts/batch_scrape_neobdm.py` | ✅ Complete - Manual batch scraper |
| SQL Optimization | `db/repositories` | ✅ Complete - SQL-level filtering |

### 🔴 NOT IMPLEMENTED (High Priority TODO)

Based on `docs/future_development.md` and `docs/optimization.md`, these features are **NOT YET IMPLEMENTED**:

#### Automation & Infrastructure
- [ ] **Scraper Scheduler (APScheduler)** - No automated scheduling exists; all scraping is manual
  - *Location to add*: `backend/modules/scheduler.py`
  - *Dependency*: `APScheduler` library
  - *Note*: Currently users must manually trigger scrapers via Dashboard button

- [ ] **File Clean-up Utility** - No auto-cleanup for `downloads/` folder
  - *Location to add*: `backend/modules/cleanup.py` or as scheduled task
  - *Purpose*: Remove old PDFs after ingestion to ChromaDB

#### User Features
- [ ] **My Watchlist** - No personalized watchlist per user
  - *Evidence*: Not in sidebar.tsx, only global FilterContext exists
  - *Location to add*: New `app/watchlist/` page + `db/watchlist_repository.py`
  - *Features needed*: Add/remove tickers, daily performance summary

- [ ] **Sentiment-Heatmap Ticker Cloud** - WordCloud exists but not sentiment-colored
  - *Current*: `components/dashboard/ticker-cloud.tsx` (basic word cloud)
  - *Needed*: Color mapping based on sentiment scores (green=positive, red=negative)

- [ ] **Multi-Document RAG** - RAG only works on single document currently
  - *Current*: `rag_client.py` queries per document
  - *Needed*: Cross-document querying with ChromaDB metadata filtering

- [ ] **Market Summary Newsletter** - No automated report generation
  - *Location to add*: `backend/modules/newsletter.py`
  - *Features*: Daily/weekly email or dashboard report with top news, predictions

- [ ] **Knowledge Graph** - No visualization of emiten relationships
  - *Location to add*: `app/knowledge-graph/` page
  - *Dependency*: `react-force-graph` or `D3.js`
  - *Features*: Supplier-customer relationships, partnership networks

#### Frontend Optimizations (from optimization.md)
- [ ] **Skeleton Loading** - Still using basic Loading.tsx component
  - *Current*: `components/shared/Loading.tsx` (spinner only)
  - *Needed*: Skeleton placeholders matching content layout

- [ ] **Synced Charts** - Charts operate independently
  - *Current*: Dashboard charts are separate
  - *Needed*: Hover/selection sync between price and sentiment charts

- [ ] **Optimized React Re-renders** - Limited useMemo/useCallback usage
  - *Evidence*: Only 9 files use optimization hooks out of 104 TSX files
  - *Needed*: Profile and optimize heavy re-render components

#### Backend Optimizations
- [ ] **Asynchronous Scraping** - Most scrapers are synchronous
  - *Current*: Only `scraper_neobdm.py` uses async
  - *Others*: `scraper_cnbc.py`, `scraper_emiten.py`, etc. are synchronous
  - *Impact*: Parallel scraping could reduce time by 70%

### 🟡 Partially Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| Broker Stalker | ⚠️ Backend only | API exists but no frontend page |
| API Pagination | ⚠️ Partial | Only on `/api/news`, not all endpoints |
| useMemo/useCallback | ⚠️ Minimal | Only 9/104 files use optimization |

### 📋 Implementation Checklist

Before marking this project as "complete", implement:

**Must Have:**
- [ ] Scraper Scheduler (APScheduler) - Critical for data freshness
- [ ] My Watchlist - Core user personalization feature
- [ ] Skeleton Loading - Better UX

**Nice to Have:**
- [ ] Sentiment-Heatmap Cloud
- [ ] Multi-Document RAG
- [ ] Asynchronous Scraping
- [ ] Market Summary Newsletter
- [ ] Knowledge Graph
- [ ] File Clean-up Utility

See `docs/future_development.md` and `docs/optimization.md` for detailed specifications.

---

## 12. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `CORS error` | Check backend is running and CORS middleware is enabled |
| `TypeError: Cannot read property` | Check TypeScript interface matches API response |
| `Module not found` | Ensure all imports use `@/` path alias |
| `Database locked` | SQLite doesn't support concurrent writes; ensure single process |

---

## 13. Key Contacts & Resources

- **Documentation**: All docs in `/docs` directory
- **API Reference**: Auto-generated at `/docs` endpoint when running
- **Architecture Guide**: This file (CLAUDE.md)

---

*Last Updated: 2026-02-15*
*Version: 2.1.0*

---

## 14. Important Notes for Future Development

### Why This Architecture?

| Decision | Rationale |
|----------|-----------|
| **Modular API Services** | Domain isolation enables parallel development and testing |
| **Repository Pattern** | Database logic is decoupled from business logic |
| **Filter Context** | Centralized filter state prevents prop drilling and ensures consistency |
| **useApi Hook** | Standardized loading/error handling across all data fetching |
| **TypeScript Interfaces** | Compile-time verification of API contracts |
| **SQLite + ChromaDB** | Simple, file-based storage with no external dependencies |
| **Ollama (Local LLM)** | Privacy, no API costs, works offline |

### NEVER BREAK THESE PATTERNS

1. **API Service Layer**: Always use the `services/api/` layer. Never call `fetch` directly from components.

2. **Type Safety**: Always define TypeScript interfaces that match backend responses. Use `any` sparingly.

3. **Filter Context**: All ticker/date filtering must use the global FilterContext. No local filter state for these.

4. **Repository Pattern**: All database access must go through repository classes. No raw SQL in routes.

5. **Error Handling**: Use the standardized error handling patterns (handleResponse, ErrorDisplay component).

6. **Responsive Design**: All UI must work on mobile (use `lg:`, `md:`, `sm:` breakpoints).

---

> **Remember**: This architecture was designed for maintainability, type safety, and developer productivity. Preserve these patterns for all future development.
