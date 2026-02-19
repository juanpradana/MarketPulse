# 🚀 MarketPulse - Complete Setup Guide

**Investment Intelligence Platform - Setup dari Awal hingga Berjalan Normal**

---

## 📋 Daftar Isi
1. [Persyaratan Sistem](#persyaratan-sistem)
2. [Instalasi Dependencies](#instalasi-dependencies)
3. [Konfigurasi Environment](#konfigurasi-environment)
4. [Setup Database](#setup-database)
5. [Menjalankan Backend](#menjalankan-backend)
6. [Menjalankan Frontend](#menjalankan-frontend)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## 1. Persyaratan Sistem

### Software yang Dibutuhkan:
- **Python**: 3.9 atau lebih tinggi
- **Node.js**: 18.x atau lebih tinggi
- **npm**: 9.x atau lebih tinggi
- **Ollama**: Latest version (untuk AI features)
- **Git**: Untuk version control

### Akun yang Dibutuhkan:
- **NeoBDM Account**: Email dan password untuk scraping data
  - Daftar di: https://neobdm.tech

### Spesifikasi Minimum:
- RAM: 8GB (16GB recommended)
- Storage: 10GB free space
- OS: Windows 10/11, macOS, atau Linux

---

## 2. Instalasi Dependencies

### A. Clone Repository
```bash
# Clone project
git clone <repository-url>
cd MarketPulse
```

### B. Setup Backend (Python)

#### 1. Buat Virtual Environment
```bash
cd backend

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Install Playwright Browsers
```bash
playwright install chromium
```

### C. Setup Frontend (Next.js)

```bash
cd frontend
npm install
```

### D. Install Ollama

#### Windows:
1. Download dari: https://ollama.ai/download
2. Install executable
3. Buka terminal dan jalankan:
```bash
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest
ollama pull qwen2.5:7b
```

#### macOS/Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest
ollama pull qwen2.5:7b
```

#### Verifikasi Ollama:
```bash
ollama list
# Harus muncul: llama3.2:latest, nomic-embed-text:latest, qwen2.5:7b
```

---

## 3. Konfigurasi Environment

### A. Backend Configuration

#### 1. Copy Environment Template
```bash
cd backend
copy .env.example .env    # Windows
# atau
cp .env.example .env      # macOS/Linux
```

#### 2. Edit `.env` File
Buka `backend/.env` dan isi dengan kredensial Anda:

```env
# NeoBDM Credentials (REQUIRED)
NEOBDM_EMAIL=your_email@example.com
NEOBDM_PASSWORD=your_password

# Ollama Configuration (REQUIRED)
OLLAMA_BASE_URL=http://localhost:11434

# Database
DB_PATH=./data/market_sentinel.db
CHROMA_PATH=./chroma_db

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
```

**⚠️ PENTING**: Ganti `your_email@example.com` dan `your_password` dengan kredensial NeoBDM Anda yang sebenarnya!

### B. Frontend Configuration

#### 1. Create `.env.local`
```bash
cd frontend
```

Buat file `.env.local` dengan isi:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. Setup Database

Database akan otomatis dibuat saat pertama kali menjalankan backend.

### Struktur Database:
- **Location**: `backend/data/market_sentinel.db`
- **Type**: SQLite
- **Tables**: 15+ tables (auto-created)
- **ChromaDB**: `backend/chroma_db/` (untuk RAG)

### Manual Database Initialization (Optional):
```bash
cd backend
python -c "from db import DatabaseConnection; DatabaseConnection()"
```

Jika berhasil, Anda akan melihat file `market_sentinel.db` di folder `backend/data/`.

---

## 5. Menjalankan Backend

### A. Aktivasi Virtual Environment
```bash
cd backend

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### B. Jalankan Server
```bash
python server.py
```

**Output yang Diharapkan:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### C. Verifikasi Backend

Buka browser dan akses:
- **Health Check**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Contoh Response Health Check:**
```json
{
  "status": "online",
  "message": "Financial Sentiment Analysis & Market Intelligence API is running",
  "version": "2.2.0",
  "features": {
    "dashboard": "Market statistics and sentiment correlation",
    "news": "News aggregation with AI insights",
    "disclosures": "IDX disclosures and RAG chat",
    "neobdm": "Market maker and fund flow analysis",
    "bandarmology": "Deep scoring and trade classification",
    "watchlist": "Personal ticker watchlist with integrated analysis",
    "done_detail": "Done detail visualization and broker flow",
    "broker_stalker": "Broker activity tracking and analysis",
    "scrapers": "Automated data collection",
    "scheduler": "Background job scheduler and manual trigger endpoints"
  }
}
```

---

## 6. Menjalankan Frontend

### A. Buka Terminal Baru
Jangan tutup terminal backend! Buka terminal baru.

### B. Jalankan Development Server
```bash
cd frontend
npm run dev
```

**Output yang Diharapkan:**
```
  ▲ Next.js 16.0.10
  - Local:        http://localhost:3000
  - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.5s
```

### C. Akses Aplikasi

Buka browser dan akses: **http://localhost:3000**

**Halaman yang Tersedia:**
1. **Dashboard** - `/dashboard` - Market overview
2. **News Library** - `/news-library` - News feed, filters, AI brief
3. **Story Finder** - `/story-finder` - Corporate action story discovery
4. **RAG Chat** - `/rag-chat` - IDX disclosures + conversational retrieval
5. **Market Summary** - `/neobdm-summary` - NeoBDM data grid
6. **Flow Tracker** - `/neobdm-tracker` - Historical flow chart
7. **Broker Summary** - `/broker-summary` - Broker accumulation/distribution analysis
8. **Price & Volume** - `/price-volume` - Price-volume anomaly tools
9. **Alpha Hunter** - `/alpha-hunter` - Workflow-driven screening
10. **Bandarmology** - `/bandarmology` - Deep score and trade type
11. **Adimology** - `/adimology` - Broker power calculator
12. **My Watchlist** - `/watchlist` - Personal monitoring + deep analyze trigger
13. **Broker Stalker** - `/broker-stalker` - Backend-connected API module, frontend page masih concept/dummy data
14. **Done Detail** - `/done-detail` - Trade flow analysis

---

## 7. Testing

### A. Backend Unit Tests

```bash
cd backend

# Jalankan semua tests
pytest tests/ -v

# Jalankan test spesifik
pytest tests/test_broker_stalker_repository.py -v
pytest tests/test_broker_stalker_api.py -v
```

**Expected Output:**
```
======================== test session starts ========================
collected 35 items

tests/test_broker_stalker_repository.py::TestBrokerStalkerRepository::test_add_broker_to_watchlist PASSED
tests/test_broker_stalker_repository.py::TestBrokerStalkerRepository::test_calculate_streak_buying PASSED
...
======================== 35 passed in 2.45s ========================
```

### B. API Endpoint Testing

#### Manual Testing via Browser:
1. Buka http://localhost:8000/docs
2. Expand endpoint yang ingin di-test
3. Klik "Try it out"
4. Isi parameter
5. Klik "Execute"

#### Testing Broker Stalker Endpoints:

**1. Add Broker to Watchlist:**
```bash
curl -X POST "http://localhost:8000/api/broker-stalker/watchlist" \
  -H "Content-Type: application/json" \
  -d '{"broker_code": "YP", "broker_name": "Yuanta Securities"}'
```

**2. Get Watchlist:**
```bash
curl "http://localhost:8000/api/broker-stalker/watchlist"
```

**3. Get Broker Portfolio:**
```bash
curl "http://localhost:8000/api/broker-stalker/portfolio/YP"
```

### C. Frontend Testing

1. Buka http://localhost:3000
2. Navigate ke setiap halaman
3. Verifikasi tidak ada error di browser console (F12)

---

## 8. Troubleshooting

### ❌ Problem: "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```bash
cd backend
# Pastikan virtual environment aktif
pip install -r requirements.txt
```

---

### ❌ Problem: "playwright._impl._api_types.Error: Executable doesn't exist"

**Solution:**
```bash
playwright install chromium
```

---

### ❌ Problem: "Connection refused" saat akses Ollama

**Solution:**
```bash
# Pastikan Ollama running
ollama serve

# Di terminal lain, test:
curl http://localhost:11434/api/tags
```

---

### ❌ Problem: "NEOBDM login failed"

**Solution:**
1. Verifikasi kredensial di `backend/.env`
2. Login manual ke https://neobdm.tech untuk memastikan akun aktif
3. Pastikan tidak ada typo di email/password

---

### ❌ Problem: Frontend tidak connect ke Backend

**Solution:**
1. Pastikan backend running di http://localhost:8000
2. Verifikasi `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
3. Restart frontend server:
   ```bash
   # Ctrl+C untuk stop
   npm run dev
   ```

---

### ❌ Problem: "Database is locked"

**Solution:**
```bash
# Tutup semua koneksi ke database
# Restart backend server
cd backend
python server.py
```

---

### ❌ Problem: Port 8000 atau 3000 sudah digunakan

**Solution Backend (Port 8000):**
```bash
# Edit backend/server.py atau backend/main.py
# Ganti port 8000 ke 8001
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

# Update frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
```

**Solution Frontend (Port 3000):**
```bash
# Jalankan dengan port berbeda
npm run dev -- -p 3001
```

---

## 🎯 Quick Start Commands

### Terminal 1 - Backend:
```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
python server.py
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### Terminal 3 - Ollama (jika belum running):
```bash
ollama serve
```

---

## ✅ Verification Checklist

Setelah setup, verifikasi semua komponen berjalan:

- [ ] Backend running di http://localhost:8000
- [ ] Frontend running di http://localhost:3000
- [ ] Ollama running di http://localhost:11434
- [ ] Health check mengembalikan status "online"
- [ ] API docs accessible di http://localhost:8000/docs
- [ ] Frontend dapat diakses tanpa error
- [ ] Database file exists di `backend/data/market_sentinel.db`
- [ ] ChromaDB folder exists di `backend/chroma_db/`
- [ ] All tests passing (`pytest tests/ -v`)

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│                    Next.js (Port 3000)                      │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐ │
│  │Dashboard │   News   │NeoBDM    │  Broker Stalker      │ │
│  └──────────┴──────────┴──────────┴──────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP API Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                             │
│                   FastAPI (Port 8000)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Routes (10 modules)                             │  │
│  │  - Dashboard, News, NeoBDM, Broker Stalker, etc.     │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  Business Logic (Analyzers & Modules)                │  │
│  │  - Broker Stalker Analyzer, Scrapers, etc.           │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  Database Layer (Repositories)                        │  │
│  │  - 7 Repositories with SQLite                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                        │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐ │
│  │  Ollama  │ NeoBDM   │   IDX    │   News Sources       │ │
│  │(AI/RAG)  │(Scraping)│(Scraping)│   (Scraping)         │ │
│  └──────────┴──────────┴──────────┴──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Notes

1. **Jangan commit `.env` file** - Sudah ada di `.gitignore`
2. **Gunakan kredensial yang kuat** untuk NeoBDM
3. **Jangan expose API ke public** tanpa authentication
4. **Backup database** secara berkala

---

## 📞 Support

Jika mengalami masalah:
1. Cek [Troubleshooting](#troubleshooting) section
2. Lihat logs di terminal backend/frontend
3. Cek `backend/logs/` untuk detailed logs
4. Review CHANGELOG.md untuk breaking changes

---

## 🎉 Selamat!

Jika semua langkah di atas berhasil, sistem Anda sudah berjalan dengan normal!

**Next Steps:**
1. Mulai scraping data: gunakan endpoint `/api/scrape` atau menu scraper control di frontend.
2. Cek scheduler: lihat status di `/api/scheduler/status` dan jalankan manual jobs bila diperlukan.
3. Explore features: navigasi semua halaman utama dari sidebar.
4. Jalankan analisis bertahap: mulai dari Alpha Hunter / Bandarmology / Watchlist.

**Happy Trading! 📈**
