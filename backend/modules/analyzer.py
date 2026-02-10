import torch
from transformers import pipeline
from tqdm import tqdm
import json
import os
import time
import datetime
import logging
import config

logger = logging.getLogger(__name__)

# ── Singleton Instance ──────────────────────────────────────
_engine_instance: "SentimentEngine | None" = None


def get_engine() -> "SentimentEngine":
    """Return a lazily-initialised, process-wide SentimentEngine singleton.
    
    The model is loaded ONCE and reused across all scraper calls,
    avoiding the ~2-4 s overhead of re-loading weights every time.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SentimentEngine()
    return _engine_instance

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

class SentimentEngine:
    def __init__(self):
        # ── GPU / CPU detection with diagnostics ────────────────
        cuda_available = torch.cuda.is_available()
        self.device = 0 if cuda_available else -1
        self.dtype = torch.float16 if self.device == 0 else torch.float32

        # Dynamic batch size: GPU can handle larger batches
        # 16 is safe for 4GB VRAM (zero-shot runs model 3x per batch for 3 labels)
        self.batch_size = 16 if self.device == 0 else 8

        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"[*] Initializing Sentiment Model on GPU ({gpu_name}, {gpu_mem:.1f} GB)...")
            print(f"    -> FP16 Precision | Batch Size: {self.batch_size}")
        else:
            print(f"[*] Initializing Sentiment Model on CPU...")
            print(f"    -> Tip: Install PyTorch with CUDA for 10-50x faster inference")
            print(f"       pip install torch --index-url https://download.pytorch.org/whl/cu121")
            print(f"    -> Batch Size: {self.batch_size}")

        # Set HF_TOKEN from env if available (suppresses rate-limit warnings)
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            os.environ["HF_TOKEN"] = hf_token  # ensure transformers picks it up

        self.classifier = pipeline(
            "zero-shot-classification",
            model=config.MODEL_NAME,
            device=self.device,
            # 'torch_dtype' is deprecated in newer transformers; use 'dtype'
            dtype=self.dtype,
        )

    # ── Warm-up (optional, called at startup) ───────────────
    def warmup(self):
        """Run a tiny dummy inference so the first real call is fast."""
        try:
            self.classifier(
                "warmup",
                config.SENTIMENT_LABELS,
                multi_label=False,
                hypothesis_template=config.HYPOTHESIS_TEMPLATE,
            )
            print("[*] Sentiment Engine warm-up complete.")
        except Exception as e:
            logger.warning(f"Warm-up failed (non-fatal): {e}")

    def chunk_text(self, text, max_len=512, overlap=50):
        """Splits text into chunks with overlap."""
        if len(text) <= max_len:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_len, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += (max_len - overlap)
        return chunks

    def prepare_chunks(self, title, text):
        """
        Prepares chunks for a single article but DOES NOT run inference.
        Returns a list of chunk strings.
        """
        if not text: text = ""
        if not title: title = ""

        # Combine Title + Text
        combined_text = f"{title}. {text}"
        
        # Split into chunks
        chunks = self.chunk_text(combined_text, max_len=config.MAX_LENGTH)
        return chunks

    def process_and_save(self, news_data=None):
        """
        Runs analysis using BATCH PROCESSING.
        """
        if news_data is None:
            if os.path.exists(config.NEWS_DATA_FILE):
                with open(config.NEWS_DATA_FILE, 'r', encoding='utf-8') as f:
                    news_data = json.load(f)
            else:
                print("[!] No news data found to analyze.")
                return []
        
        total_articles = len(news_data)
        print(f"[*] Starting Batch Analysis for {total_articles} articles...")
        start_time = time.time()
        
        # --- STAGE 1: PREPARE BATCHES ---
        # We need to map Chunk -> Article ID (index) to reassemble later
        all_chunks = []
        chunk_map = [] # Stores tuple (article_index, chunk_index_in_article)
        
        print("    -> Preparing text chunks...")
        for idx, article in enumerate(news_data):
            title = article.get('title', 'Unknown')
            text = article.get('clean_text', '')
            
            chunks = self.prepare_chunks(title, text)
            
            for chunk_idx, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                chunk_map.append(idx)
        
        total_chunks = len(all_chunks)
        print(f"    -> Generated {total_chunks} chunks from {total_articles} articles.")
        
        # --- STAGE 2: BATCH INFERENCE ---
        batch_size = self.batch_size
        device_label = f"GPU (bs={batch_size})" if self.device == 0 else f"CPU (bs={batch_size})"
        print(f"    -> Running Inference on {device_label}...")
        
        batch_results = []
        
        for i in tqdm(range(0, total_chunks, batch_size), desc="    Inference Progress"):
            batch_slice = all_chunks[i : i + batch_size]
            results = self.classifier(
                batch_slice, 
                config.SENTIMENT_LABELS, 
                multi_label=False,
                hypothesis_template=config.HYPOTHESIS_TEMPLATE,
                batch_size=batch_size
            )
            # Pipeline returns a list if input is a list, or single dict if single input.
            if isinstance(results, dict): results = [results]
            batch_results.extend(results)

        # --- STAGE 3: REASSEMBLE ---
        print("    -> Reassembling results...")
        
        # Temporary storage for article results: {article_idx: [results]}
        article_results_map = {i: [] for i in range(total_articles)}
        
        for i, res in enumerate(batch_results):
            article_idx = chunk_map[i]
            article_results_map[article_idx].append({
                "label": res['labels'][0],
                "score": res['scores'][0]
            })
            
        # --- STAGE 4: AGGREGATE & ASSIGN ---
        analyzed_results = []
        
        for i, article in enumerate(news_data):
            chunk_res = article_results_map[i]
            
            if not chunk_res:
                # Fallback if no chunks (empty text)
                article['sentiment_label'] = "Netral"
                article['sentiment_score'] = 0.0
            else:
                # 1. Prioritize Strong Signals (> 0.5)
                strong_signals = [
                    r for r in chunk_res 
                    if r['label'] in ['Bullish', 'Bearish'] and r['score'] > 0.5
                ]
                
                if strong_signals:
                    best = max(strong_signals, key=lambda x: x['score'])
                    final_label = best['label']
                    final_score = best['score']
                else:
                    # 2. Fallback to highest confidence
                    best = max(chunk_res, key=lambda x: x['score'])
                    final_label = best['label']
                    final_score = best['score']
            
            article['sentiment_label'] = final_label
            article['sentiment_score'] = final_score
            analyzed_results.append(article)

        # Save results using the global DateTimeEncoder
        with open(config.ANALYZED_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(analyzed_results, f, indent=4, ensure_ascii=False, cls=DateTimeEncoder)
            
        elapsed = time.time() - start_time
        print(f"[*] Analysis complete in {elapsed:.2f}s.")
        print(f"[*] Results saved to {config.ANALYZED_DATA_FILE}")
        
        return analyzed_results
