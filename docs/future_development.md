# Future Development Roadmap: MarketPulse

Dokumen ini menguraikan rencana pengembangan fitur masa depan untuk meningkatkan kapabilitas intelijen bisnis, efisiensi operasional, dan pengalaman pengguna di platform `MarketPulse`.

---

## 🚀 Fitur Utama & Target

### 1. Multi-Document RAG (Global Search)
*   **Deskripsi**: Mengalihkan kapabilitas RAG dari pencarian per dokumen tunggal menjadi pencarian lintas kumpulan dokumen (Keterbukaan Informasi).
*   **Goal**: Memungkinkan pengguna melakukan pertanyaan analitis tingkat tinggi yang membutuhkan data dari berbagai sumber.
*   **Contoh Query**: *"Ringkas semua sentimen mengenai ekspansi sektor energi dari emiten BBCA, PGAS, dan ADRO dalam semester terakhir."*
*   **Teknis**: Optimasi ChromaDB dengan metadata filtering yang lebih luas dan teknik *Reranking* untuk meningkatkan relevansi konteks.

### 2. Knowledge Graph (Koneksi Emiten)
*   **Deskripsi**: Membangun graf hubungan antar emiten berdasarkan entitas yang muncul bersamaan dalam berita atau laporan keterbukaan informasi.
*   **Goal**: Memvisualisasikan ekosistem pasar saham dan ketergantungan antar perusahaan (misal: supplier-customer, kemitraan strategis, atau kompetisi).
*   **Visualisasi**: Graf interaktif menggunakan `react-force-graph` atau `D3.js` yang menunjukkan simpul (emiten) dan garis (tipe hubungan).

### 3. Automatic Market Summary (Newsletter)
*   **Deskripsi**: Sistem AI yang secara periodik (harian/mingguan) merangkum kejadian pasar paling signifikan.
*   **Goal**: Memberikan *insights* instan tanpa harus membaca ratusan berita satu per satu.
*   **Output**: Dashboard ringkasan khusus atau pengiriman otomatis via email/API yang berisi:
    *   Top 3 berita dengan dampak sentimen terbesar.
    *   Ringkasan keterbukaan informasi paling krusial.
    *   Prediksi narasi pasar untuk sesi berikutnya.

### 4. Sentiment-Heatmap Ticker Cloud
*   **Deskripsi**: Evolusi dari WordCloud saat ini, di mana warna setiap ticker merepresentasikan skor sentimen rata-rata.
*   **Goal**: Memberikan gambaran visual cepat mengenai emiten mana yang sedang "panas" secara positif atau negatif.
*   **Skema Warna**:
    *   🟢 **Bright Green**: Sentimen Bullish Kuat
    *   ⚪ **Grey/White**: Sentimen Netral
    *   🔴 **Bright Red**: Sentimen Bearish Kuat

### 5. Automated Market Narrative (Newsletter)
*   **Deskripsi**: Evolusi dari automatic market summary menjadi format narasi siap distribusi (dashboard snapshot + narasi AI).
*   **Goal**: Menyediakan ringkasan harian/mingguan yang bisa dipakai langsung oleh analis/internal users.
*   **Output**: Ringkasan terstruktur + highlights sentimen + top movers berbasis data internal.

---

## ✅ Sudah Diimplementasikan (Dipindah dari Roadmap Lama)

### 1. Scraper Scheduler
*   **Status**: Implemented.
*   **Catatan**: Scheduler API tersedia untuk status/start/stop/manual triggers.

### 2. My Watchlist
*   **Status**: Implemented.
*   **Catatan**: Sudah ada endpoint CRUD watchlist + integrasi deep analysis.

---

## 🛠️ Prioritas Pengembangan

| Urutan | Fitur | Kategori | Keuntungan Utama |
| :--- | :--- | :--- | :--- |
| **1** | **Sentiment-Heatmap Cloud** | Visualisasi | Analisis Visual Cepat |
| **2** | **Multi-Document RAG** | AI / Intelligence | Kedalaman Analisis |
| **3** | **Automated Market Narrative** | AI / Intelligence | Efisiensi Waktu |
| **4** | **Knowledge Graph** | Data Mining | Pemahaman Ekosistem |

---
*Terakhir diperbarui: 2026-02-19*
