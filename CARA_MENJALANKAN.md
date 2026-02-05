# 🎯 CARA MENJALANKAN MARKETPULSE

**Panduan Singkat - Dari Setup hingga Berjalan Normal**

---

## 📌 Ringkasan Cepat

### Persyaratan:
- Python 3.9+
- Node.js 18+
- Ollama (untuk AI features)
- Akun NeoBDM (email & password)

### Waktu Setup: ~15-20 menit

---

## 🚀 LANGKAH CEPAT (Windows)

### 1️⃣ Double-click file ini:
```
quick-start.bat
```

Script akan otomatis:
- ✅ Check Python & Node.js
- ✅ Buat virtual environment
- ✅ Install semua dependencies
- ✅ Setup environment files
- ✅ Start backend & frontend

### 2️⃣ Edit Kredensial (Pertama kali saja):
File akan terbuka otomatis: `backend\.env`

Ganti dengan kredensial Anda:
```env
NEOBDM_EMAIL=email_anda@example.com
NEOBDM_PASSWORD=password_anda
```

### 3️⃣ Akses Aplikasi:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🔧 LANGKAH MANUAL (Jika quick-start.bat gagal)

### Step 1: Setup Backend
```bash
cd backend

# Buat virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Copy dan edit .env
copy .env.example .env
notepad .env
```

### Step 2: Setup Frontend
```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
```

### Step 3: Install Ollama
1. Download: https://ollama.ai/download
2. Install
3. Jalankan:
```bash
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest
```

### Step 4: Jalankan Servers

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate
python server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Ollama (jika belum running):**
```bash
ollama serve
```

---

## ✅ Verifikasi Sistem Berjalan

### 1. Check Backend:
Buka: http://localhost:8000

Harus muncul:
```json
{
  "status": "online",
  "version": "2.0.0",
  "features": {
    "broker_stalker": "Broker activity tracking and analysis",
    ...
  }
}
```

### 2. Check Frontend:
Buka: http://localhost:3000

Harus muncul: Dashboard dengan menu navigasi

### 3. Check API Docs:
Buka: http://localhost:8000/docs

Harus muncul: Swagger UI dengan semua endpoints

### 4. Check Ollama:
```bash
curl http://localhost:11434/api/tags
```

Harus muncul: List models yang terinstall

---

## 🎮 FITUR YANG TERSEDIA

### 1. Dashboard (`/`)
- Market overview
- Sentiment correlation
- Quick statistics

### 2. News (`/news`)
- News aggregation
- Sentiment analysis
- AI summaries

### 3. NeoBDM (`/neobdm`)
- Market maker analysis
- Fund flow tracking
- Hot signals

### 4. Alpha Hunter (`/alpha-hunter`)
- Multi-stage stock screening
- Custom filters
- Watchlist management

### 5. **Broker Stalker (`/broker-stalker`)** ⭐ NEW!
- Track broker activity
- Portfolio analysis
- Power level scoring
- Streak detection

### 6. Done Detail (`/done-detail`)
- Trade flow analysis
- Broker imposter detection
- Speed analysis

### 7. Disclosures (`/disclosures`)
- IDX disclosures
- RAG chat with documents
- AI-powered search

---

## 🧪 TESTING

### Test Backend:
```bash
cd backend
pytest tests/ -v
```

### Test Broker Stalker:
```bash
pytest tests/test_broker_stalker_repository.py -v
pytest tests/test_broker_stalker_api.py -v
```

### Test API Manual:
1. Buka http://localhost:8000/docs
2. Pilih endpoint
3. Click "Try it out"
4. Execute

---

## ❌ TROUBLESHOOTING UMUM

### Problem: "ModuleNotFoundError"
**Solution:**
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### Problem: "Port already in use"
**Solution:**
```bash
# Cari process yang pakai port
netstat -ano | findstr :8000
# Kill process
taskkill /PID <PID> /F
```

### Problem: "Ollama connection refused"
**Solution:**
```bash
# Start Ollama
ollama serve
```

### Problem: "NeoBDM login failed"
**Solution:**
- Verifikasi kredensial di `backend\.env`
- Test login manual di https://neobdm.tech

### Problem: Frontend tidak connect
**Solution:**
- Check backend running: http://localhost:8000
- Check `frontend\.env.local`:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```
- Restart frontend: `npm run dev`

---

## 📚 DOKUMENTASI LENGKAP

### Untuk detail lebih lengkap:
- **Setup Guide**: [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- **Changelog**: [CHANGELOG.md](./CHANGELOG.md)
- **API Docs**: http://localhost:8000/docs (saat server running)

---

## 🎯 QUICK COMMANDS CHEATSHEET

```bash
# Start Backend
cd backend && venv\Scripts\activate && python server.py

# Start Frontend
cd frontend && npm run dev

# Run Tests
cd backend && pytest tests/ -v

# Check Ollama
ollama list

# Install Ollama Models
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest

# Check Backend Health
curl http://localhost:8000

# Check Ollama Health
curl http://localhost:11434/api/tags
```

---

## 📊 STRUKTUR PROJECT

```
MarketPulse/
├── backend/
│   ├── data/                    # SQLite database
│   ├── db/                      # Repository layer
│   │   ├── broker_stalker_repository.py  ⭐ NEW
│   │   └── ...
│   ├── modules/                 # Business logic
│   │   ├── broker_stalker_analyzer.py    ⭐ NEW
│   │   └── ...
│   ├── routes/                  # API endpoints
│   │   ├── broker_stalker.py    ⭐ NEW
│   │   └── ...
│   ├── tests/                   # Unit & integration tests
│   │   ├── test_broker_stalker_repository.py  ⭐ NEW
│   │   ├── test_broker_stalker_api.py         ⭐ NEW
│   │   └── ...
│   ├── .env.example            # Environment template
│   ├── requirements.txt        # Python dependencies
│   └── server.py               # Main entry point
│
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages
│   │   │   ├── broker-stalker/ # Broker Stalker page
│   │   │   └── ...
│   │   └── services/
│   │       └── api/
│   │           ├── brokerStalker.ts  ⭐ NEW
│   │           └── ...
│   ├── .env.local              # Frontend environment
│   └── package.json            # Node dependencies
│
├── quick-start.bat             # Quick start script ⭐ NEW
├── SETUP_GUIDE.md              # Complete setup guide ⭐ NEW
├── CARA_MENJALANKAN.md         # This file ⭐ NEW
├── CHANGELOG.md                # Version history
└── README.md                   # Project overview
```

---

## 🎉 SELESAI!

Jika semua langkah berhasil, Anda sekarang memiliki:
- ✅ Backend running di port 8000
- ✅ Frontend running di port 3000
- ✅ Ollama running untuk AI features
- ✅ Database siap digunakan
- ✅ Semua 11 features available
- ✅ **Broker Stalker feature** fully functional

**Happy Trading! 📈**

---

## 📞 Support

Jika masih ada masalah:
1. Baca [SETUP_GUIDE.md](./SETUP_GUIDE.md) untuk troubleshooting detail
2. Check logs di terminal backend/frontend
3. Review error messages di browser console (F12)

**Version**: 2.1.0  
**Last Updated**: February 5, 2026
