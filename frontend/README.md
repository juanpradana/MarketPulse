# Frontend - MarketPulse

Frontend aplikasi MarketPulse dibangun dengan Next.js (App Router), TypeScript, Tailwind CSS, dan modular API client di `src/services/api`.

## Menjalankan Frontend

```bash
npm install
npm run dev
```

Default URL:
- http://localhost:3000

Pastikan backend sudah berjalan di `http://localhost:8000`.

## Environment Variable

Buat file `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Struktur Penting

- `src/app/*`: halaman utama (dashboard, news-library, rag-chat, neobdm-summary, watchlist, dll).
- `src/components/*`: komponen UI reusable.
- `src/context/*`: global state seperti filter context.
- `src/services/api/*`: API client per domain (news, neobdm, watchlist, brokerStalker, scheduler, dst).

## Halaman Utama

- `/dashboard`
- `/news-library`
- `/story-finder`
- `/rag-chat`
- `/neobdm-summary`
- `/neobdm-tracker`
- `/broker-summary`
- `/price-volume`
- `/alpha-hunter`
- `/bandarmology`
- `/adimology`
- `/watchlist`
- `/broker-stalker`
- `/done-detail`

## Build Production

```bash
npm run build
npm run start
```
