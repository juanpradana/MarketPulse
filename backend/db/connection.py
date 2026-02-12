"""Base database connection and schema management."""
import sqlite3
import os
import config
from typing import Optional


class BaseRepository:
    """Base repository class with shared connection management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize repository with database connection.
        
        Args:
            db_path: Path to SQLite database file. Uses default if None.
        """
        self.db_path = db_path if db_path else os.path.join(config.DATA_DIR, "market_sentinel.db")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)


class DatabaseConnection:
    """Database connection and schema manager."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database with schema setup."""
        self.db_path = db_path if db_path else os.path.join(config.DATA_DIR, "market_sentinel.db")
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Initialize database and enable WAL mode."""
        conn = self._get_conn()
        try:
            # Enable Write Ahead Logging for concurrency/performance
            conn.execute("PRAGMA journal_mode=WAL;")
            self._create_tables(conn)
        finally:
            conn.close()
    
    def _create_tables(self, conn: sqlite3.Connection):
        """
        Create all database tables if they don't exist.
        
        Centralized schema definition for all modules.
        """
        # News table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                url TEXT PRIMARY KEY,
                timestamp TEXT,
                ticker TEXT,
                title TEXT,
                content TEXT,
                sentiment_label TEXT,
                sentiment_score REAL,
                summary TEXT
            );
        """)
        
        # IDX Disclosures table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS idx_disclosures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                title TEXT,
                published_date DATETIME,
                download_url TEXT UNIQUE,
                local_path TEXT,
                processed_status TEXT DEFAULT 'PENDING',
                ai_summary TEXT
            );
        """)
        
        # NeoBDM Records (Structured)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS neobdm_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scraped_at DATETIME,
                method TEXT,
                period TEXT,
                symbol TEXT,
                pinky TEXT,
                crossing TEXT,
                likuid TEXT,
                w_4 TEXT,
                w_3 TEXT,
                w_2 TEXT,
                w_1 TEXT,
                d_4 TEXT,
                d_3 TEXT,
                d_2 TEXT,
                d_0 TEXT,
                pct_1d TEXT,
                c_20 TEXT,
                c_10 TEXT,
                c_5 TEXT,
                c_3 TEXT,
                pct_3d TEXT,
                pct_5d TEXT,
                pct_10d TEXT,
                pct_20d TEXT,
                price TEXT,
                ma5 TEXT,
                ma10 TEXT,
                ma20 TEXT,
                ma50 TEXT,
                ma100 TEXT,
                unusual TEXT
            );
        """)
        
        # NeoBDM Summaries (Legacy JSON)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS neobdm_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scraped_at DATETIME,
                method TEXT,
                period TEXT,
                data_json TEXT
            );
        """)

        # NeoBDM Broker Summaries (Net Buy & Net Sell)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS neobdm_broker_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                trade_date TEXT,
                side TEXT,
                broker TEXT,
                nlot REAL,
                nval REAL,
                avg_price REAL,
                scraped_at DATETIME
            );
        """)

        # Broker 5% Watchlist (Manual CRUD)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broker_five_percent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                broker_code TEXT NOT NULL,
                label TEXT,
                created_at DATETIME DEFAULT (datetime('now')),
                updated_at DATETIME DEFAULT (datetime('now'))
            );
        """)

        # Migration: ensure broker_five_percent is per-ticker (no global unique broker_code)
        try:
            cursor = conn.execute("PRAGMA table_info(broker_five_percent)")
            columns = [row[1] for row in cursor.fetchall()]
            needs_rebuild = 'ticker' not in columns

            if not needs_rebuild:
                idx_cursor = conn.execute("PRAGMA index_list(broker_five_percent)")
                for idx in idx_cursor.fetchall():
                    idx_name = idx[1]
                    is_unique = idx[2]
                    if not is_unique:
                        continue
                    info = conn.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
                    idx_cols = [row[2] for row in info]
                    if idx_cols == ['broker_code']:
                        needs_rebuild = True
                        break

            if needs_rebuild:
                conn.execute("DROP TABLE IF EXISTS broker_five_percent_old;")
                conn.execute("ALTER TABLE broker_five_percent RENAME TO broker_five_percent_old;")
                conn.execute("""
                    CREATE TABLE broker_five_percent (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticker TEXT NOT NULL,
                        broker_code TEXT NOT NULL,
                        label TEXT,
                        created_at DATETIME DEFAULT (datetime('now')),
                        updated_at DATETIME DEFAULT (datetime('now'))
                    );
                """)
                conn.execute("""
                    INSERT INTO broker_five_percent (ticker, broker_code, label, created_at, updated_at)
                    SELECT '', broker_code, label, created_at, updated_at
                    FROM broker_five_percent_old;
                """)
                conn.execute("DROP TABLE broker_five_percent_old;")
        except sqlite3.OperationalError:
            pass

        # Market Analytics Cache (OHLCV Data)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_analytics_cache (
                ticker TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (ticker, date)
            );
        """)
        
        # Market Metadata Cache (Market Cap with TTL)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_metadata (
                symbol TEXT PRIMARY KEY,
                market_cap REAL NOT NULL,
                currency TEXT DEFAULT 'IDR',
                cached_at DATETIME NOT NULL,
                source TEXT DEFAULT 'yfinance',
                shares_outstanding REAL,
                last_price REAL
            );
        """)
        
        # Market Cap History (Daily snapshots for trend tracking)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_cap_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                market_cap REAL NOT NULL,
                shares_outstanding REAL,
                close_price REAL,
                calculated_at DATETIME DEFAULT (datetime('now')),
                source TEXT DEFAULT 'calculated',
                UNIQUE(ticker, trade_date)
            );
        """)
        
        # Volume Daily Records (Incremental Volume Data)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volume_daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                volume INTEGER NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                fetched_at TEXT DEFAULT (datetime('now')),
                UNIQUE(ticker, trade_date)
            );
        """)
        
        # Safe migration for existing tables
        try:
            conn.execute("ALTER TABLE news ADD COLUMN summary TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Migration: Add shares_outstanding and last_price to market_metadata
        try:
            conn.execute("ALTER TABLE market_metadata ADD COLUMN shares_outstanding REAL")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            conn.execute("ALTER TABLE market_metadata ADD COLUMN last_price REAL")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Optimization: Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker ON news(ticker);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_timestamp ON news(timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dis_ticker ON idx_disclosures(ticker);")
        
        # NeoBDM Optimization Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_neobdm_rec_lookup ON neobdm_records(method, period, scraped_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_neobdm_rec_symbol ON neobdm_records(symbol);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_neobdm_sum_lookup ON neobdm_summaries(method, period, scraped_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_neobdm_broker_lookup ON neobdm_broker_summaries(ticker, trade_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_broker_five_ticker ON broker_five_percent(ticker);")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_broker_five_unique ON broker_five_percent(ticker, broker_code);")
        
        # Market Metadata Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market_meta_symbol ON market_metadata(symbol);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market_meta_cached ON market_metadata(cached_at);")
        
        # Market Cap History Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mcap_hist_ticker_date ON market_cap_history(ticker, trade_date DESC);")
        
        # Volume Daily Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_volume_ticker_date ON volume_daily_records(ticker, trade_date DESC);")
        
        # Done Detail Records (Paste-based trade data)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS done_detail_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                trade_time TEXT,
                board TEXT,
                price REAL,
                qty INTEGER,
                buyer_type TEXT,
                buyer_code TEXT,
                seller_code TEXT,
                seller_type TEXT,
                created_at DATETIME DEFAULT (datetime('now')),
                processed_at DATETIME
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_done_detail_lookup ON done_detail_records(ticker, trade_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_done_detail_time ON done_detail_records(ticker, trade_date, trade_time);")
        
        # Migration: Add processed_at column if not exists (MUST be before index creation)
        try:
            conn.execute("ALTER TABLE done_detail_records ADD COLUMN processed_at DATETIME")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create index on processed_at (after migration ensures column exists)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_done_detail_cleanup ON done_detail_records(processed_at);")
        
        # Done Detail Synthesis (Pre-computed analysis results)
        # Stores synthesized analysis to avoid reprocessing raw data every request
        conn.execute("""
            CREATE TABLE IF NOT EXISTS done_detail_synthesis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                
                -- Versioning for algorithm updates
                analysis_version TEXT DEFAULT '1.0.0',
                calculated_at DATETIME DEFAULT (datetime('now')),
                
                -- Raw data metadata (for audit trail)
                raw_record_count INTEGER,
                raw_data_hash TEXT,
                
                -- Pre-computed analysis results (JSON blobs)
                imposter_data TEXT,      -- Imposter trades, by_broker, thresholds, summary
                speed_data TEXT,         -- Speed by broker, timeline, bursts, summary
                combined_data TEXT,      -- Signal, flow, power brokers, key metrics
                
                UNIQUE(ticker, trade_date)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_synthesis_lookup ON done_detail_synthesis(ticker, trade_date);")
        
        # Broker Stalker Watchlist (Tracked brokers)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broker_stalker_watchlist (
                broker_code TEXT PRIMARY KEY,
                broker_name TEXT,
                description TEXT,
                power_level INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT (datetime('now')),
                updated_at DATETIME DEFAULT (datetime('now'))
            );
        """)
        
        # Broker Stalker Tracking (Daily broker activity per ticker)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broker_stalker_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broker_code TEXT NOT NULL,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                total_buy REAL DEFAULT 0,
                total_sell REAL DEFAULT 0,
                net_value REAL DEFAULT 0,
                avg_price REAL,
                streak_days INTEGER DEFAULT 0,
                status TEXT,
                calculated_at DATETIME DEFAULT (datetime('now')),
                UNIQUE(broker_code, ticker, trade_date)
            );
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_broker_stalker_lookup ON broker_stalker_tracking(broker_code, ticker, trade_date DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_broker_stalker_ticker ON broker_stalker_tracking(ticker, trade_date DESC);")
        
        # Bandarmology Inventory Data (per-ticker broker accumulation from /inventory/)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bandarmology_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                broker_code TEXT NOT NULL,
                is_clean INTEGER DEFAULT 0,
                is_tektok INTEGER DEFAULT 0,
                is_accumulating INTEGER DEFAULT 0,
                final_net_lot REAL DEFAULT 0,
                start_net_lot REAL DEFAULT 0,
                data_points INTEGER DEFAULT 0,
                time_series_json TEXT,
                date_start TEXT,
                date_end TEXT,
                scraped_at DATETIME DEFAULT (datetime('now')),
                UNIQUE(ticker, broker_code, date_end)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_band_inv_ticker ON bandarmology_inventory(ticker, date_end);")
        
        # Bandarmology Transaction Chart Data (per-ticker flow data from /transaction_chart/)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bandarmology_txn_chart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                period TEXT DEFAULT '6m',
                
                -- Cumulative values (latest point)
                cum_mm REAL DEFAULT 0,
                cum_nr REAL DEFAULT 0,
                cum_smart REAL DEFAULT 0,
                cum_retail REAL DEFAULT 0,
                cum_foreign REAL DEFAULT 0,
                cum_institution REAL DEFAULT 0,
                cum_zombie REAL DEFAULT 0,
                
                -- Daily values (latest day)
                daily_mm REAL DEFAULT 0,
                daily_nr REAL DEFAULT 0,
                daily_smart REAL DEFAULT 0,
                daily_retail REAL DEFAULT 0,
                daily_foreign REAL DEFAULT 0,
                daily_institution REAL DEFAULT 0,
                daily_zombie REAL DEFAULT 0,
                
                -- Participation ratios (latest day, 0-1)
                part_foreign REAL DEFAULT 0,
                part_retail REAL DEFAULT 0,
                part_institution REAL DEFAULT 0,
                part_zombie REAL DEFAULT 0,
                
                -- Cross index (latest)
                cross_index REAL DEFAULT 0,
                
                -- Trend analysis (computed from time series)
                mm_trend TEXT,
                foreign_trend TEXT,
                institution_trend TEXT,
                
                -- Week-ago cumulative values (for velocity calculation)
                cum_mm_week_ago REAL DEFAULT 0,
                cum_foreign_week_ago REAL DEFAULT 0,
                cum_institution_week_ago REAL DEFAULT 0,
                cum_smart_week_ago REAL DEFAULT 0,
                cum_retail_week_ago REAL DEFAULT 0,
                
                -- Month-ago cumulative values (for acceleration calculation)
                cum_mm_month_ago REAL DEFAULT 0,
                cum_foreign_month_ago REAL DEFAULT 0,
                cum_institution_month_ago REAL DEFAULT 0,
                cum_smart_month_ago REAL DEFAULT 0,
                cum_retail_month_ago REAL DEFAULT 0,
                
                -- Full time series JSON for detailed analysis
                time_series_json TEXT,
                
                date_start TEXT,
                date_end TEXT,
                data_points INTEGER DEFAULT 0,
                scraped_at DATETIME DEFAULT (datetime('now')),
                UNIQUE(ticker, period, date_end)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_band_txn_ticker ON bandarmology_txn_chart(ticker, date_end);")
        
        # Bandarmology Deep Analysis Cache (enriched scoring results)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bandarmology_deep_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                analysis_date TEXT NOT NULL,
                
                -- Inventory summary
                inv_accum_brokers INTEGER DEFAULT 0,
                inv_distrib_brokers INTEGER DEFAULT 0,
                inv_clean_brokers INTEGER DEFAULT 0,
                inv_tektok_brokers INTEGER DEFAULT 0,
                inv_total_accum_lot REAL DEFAULT 0,
                inv_total_distrib_lot REAL DEFAULT 0,
                inv_top_accum_broker TEXT,
                inv_top_accum_lot REAL DEFAULT 0,
                
                -- Transaction chart summary
                txn_mm_cum REAL DEFAULT 0,
                txn_foreign_cum REAL DEFAULT 0,
                txn_institution_cum REAL DEFAULT 0,
                txn_retail_cum REAL DEFAULT 0,
                txn_cross_index REAL DEFAULT 0,
                txn_foreign_participation REAL DEFAULT 0,
                txn_institution_participation REAL DEFAULT 0,
                txn_mm_trend TEXT,
                txn_foreign_trend TEXT,
                
                -- Broker summary metrics
                broksum_total_buy_lot REAL DEFAULT 0,
                broksum_total_sell_lot REAL DEFAULT 0,
                broksum_total_buy_val REAL DEFAULT 0,
                broksum_total_sell_val REAL DEFAULT 0,
                broksum_avg_buy_price REAL DEFAULT 0,
                broksum_avg_sell_price REAL DEFAULT 0,
                broksum_floor_price REAL DEFAULT 0,
                broksum_target_price REAL DEFAULT 0,
                broksum_top_buyers_json TEXT,
                broksum_top_sellers_json TEXT,
                broksum_net_institutional REAL DEFAULT 0,
                broksum_net_foreign REAL DEFAULT 0,
                
                -- Enhanced scoring
                deep_score INTEGER DEFAULT 0,
                deep_trade_type TEXT,
                deep_signals_json TEXT,
                
                -- Entry/target analysis
                entry_price REAL DEFAULT 0,
                target_price REAL DEFAULT 0,
                stop_loss REAL DEFAULT 0,
                risk_reward_ratio REAL DEFAULT 0,
                
                -- Controlling broker analysis
                controlling_brokers_json TEXT,
                accum_start_date TEXT,
                accum_phase TEXT,
                bandar_avg_cost REAL DEFAULT 0,
                bandar_total_lot REAL DEFAULT 0,
                coordination_score INTEGER DEFAULT 0,
                phase_confidence TEXT,
                breakout_signal TEXT,
                bandar_peak_lot REAL DEFAULT 0,
                bandar_distribution_pct REAL DEFAULT 0,
                distribution_alert TEXT,
                
                -- Cross-reference: broker summary <-> inventory
                bandar_buy_today_count INTEGER DEFAULT 0,
                bandar_sell_today_count INTEGER DEFAULT 0,
                bandar_buy_today_lot REAL DEFAULT 0,
                bandar_sell_today_lot REAL DEFAULT 0,
                bandar_confirmation TEXT,
                
                -- Multi-day broker summary consistency
                broksum_days_analyzed INTEGER DEFAULT 0,
                broksum_consistency_score INTEGER DEFAULT 0,
                broksum_consistent_buyers_json TEXT,
                broksum_consistent_sellers_json TEXT,
                
                -- Breakout probability
                breakout_probability INTEGER DEFAULT 0,
                breakout_factors_json TEXT,
                
                -- Accumulation duration
                accum_duration_days INTEGER DEFAULT 0,
                
                -- Concentration risk
                concentration_broker TEXT,
                concentration_pct REAL DEFAULT 0,
                concentration_risk TEXT,
                
                -- Smart money vs retail divergence
                txn_smart_money_cum REAL DEFAULT 0,
                txn_retail_cum_deep REAL DEFAULT 0,
                smart_retail_divergence INTEGER DEFAULT 0,
                
                -- Volume context
                volume_score INTEGER DEFAULT 0,
                volume_signal TEXT,
                
                -- MA cross
                ma_cross_signal TEXT DEFAULT 'NONE',
                ma_cross_score INTEGER DEFAULT 0,
                
                -- Historical comparison
                prev_deep_score INTEGER DEFAULT 0,
                prev_phase TEXT DEFAULT '',
                phase_transition TEXT DEFAULT 'NONE',
                score_trend TEXT DEFAULT 'NONE',
                
                -- Flow velocity/acceleration
                flow_velocity_mm REAL DEFAULT 0,
                flow_velocity_foreign REAL DEFAULT 0,
                flow_velocity_institution REAL DEFAULT 0,
                flow_acceleration_mm REAL DEFAULT 0,
                flow_acceleration_signal TEXT DEFAULT 'NONE',
                flow_velocity_score INTEGER DEFAULT 0,
                
                -- Important dates broker summary analysis
                important_dates_json TEXT,
                important_dates_score INTEGER DEFAULT 0,
                important_dates_signal TEXT DEFAULT 'NONE',
                
                calculated_at DATETIME DEFAULT (datetime('now')),
                UNIQUE(ticker, analysis_date)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_band_deep_lookup ON bandarmology_deep_cache(ticker, analysis_date);")
        
        # Migration: Add new columns to existing bandarmology_deep_cache table
        new_columns = [
            ("broksum_total_buy_lot", "REAL DEFAULT 0"),
            ("broksum_total_sell_lot", "REAL DEFAULT 0"),
            ("broksum_total_buy_val", "REAL DEFAULT 0"),
            ("broksum_total_sell_val", "REAL DEFAULT 0"),
            ("broksum_avg_buy_price", "REAL DEFAULT 0"),
            ("broksum_avg_sell_price", "REAL DEFAULT 0"),
            ("broksum_floor_price", "REAL DEFAULT 0"),
            ("broksum_target_price", "REAL DEFAULT 0"),
            ("broksum_top_buyers_json", "TEXT"),
            ("broksum_top_sellers_json", "TEXT"),
            ("broksum_net_institutional", "REAL DEFAULT 0"),
            ("broksum_net_foreign", "REAL DEFAULT 0"),
            ("entry_price", "REAL DEFAULT 0"),
            ("target_price", "REAL DEFAULT 0"),
            ("stop_loss", "REAL DEFAULT 0"),
            ("risk_reward_ratio", "REAL DEFAULT 0"),
            ("controlling_brokers_json", "TEXT"),
            ("accum_start_date", "TEXT"),
            ("accum_phase", "TEXT"),
            ("bandar_avg_cost", "REAL DEFAULT 0"),
            ("bandar_total_lot", "REAL DEFAULT 0"),
            ("coordination_score", "INTEGER DEFAULT 0"),
            ("phase_confidence", "TEXT"),
            ("breakout_signal", "TEXT"),
            ("bandar_peak_lot", "REAL DEFAULT 0"),
            ("bandar_distribution_pct", "REAL DEFAULT 0"),
            ("distribution_alert", "TEXT"),
            # Cross-reference fields
            ("bandar_buy_today_count", "INTEGER DEFAULT 0"),
            ("bandar_sell_today_count", "INTEGER DEFAULT 0"),
            ("bandar_buy_today_lot", "REAL DEFAULT 0"),
            ("bandar_sell_today_lot", "REAL DEFAULT 0"),
            ("bandar_confirmation", "TEXT"),
            # Multi-day consistency fields
            ("broksum_days_analyzed", "INTEGER DEFAULT 0"),
            ("broksum_consistency_score", "INTEGER DEFAULT 0"),
            ("broksum_consistent_buyers_json", "TEXT"),
            ("broksum_consistent_sellers_json", "TEXT"),
            # Breakout probability fields
            ("breakout_probability", "INTEGER DEFAULT 0"),
            ("breakout_factors_json", "TEXT"),
            # Accumulation duration
            ("accum_duration_days", "INTEGER DEFAULT 0"),
            # Concentration risk
            ("concentration_broker", "TEXT"),
            ("concentration_pct", "REAL DEFAULT 0"),
            ("concentration_risk", "TEXT"),
            # Smart money vs retail divergence
            ("txn_smart_money_cum", "REAL DEFAULT 0"),
            ("txn_retail_cum_deep", "REAL DEFAULT 0"),
            ("smart_retail_divergence", "INTEGER DEFAULT 0"),
            # Volume context
            ("volume_score", "INTEGER DEFAULT 0"),
            ("volume_signal", "TEXT"),
            # MA cross
            ("ma_cross_signal", "TEXT DEFAULT 'NONE'"),
            ("ma_cross_score", "INTEGER DEFAULT 0"),
            # Historical comparison
            ("prev_deep_score", "INTEGER DEFAULT 0"),
            ("prev_phase", "TEXT DEFAULT ''"),
            ("phase_transition", "TEXT DEFAULT 'NONE'"),
            ("score_trend", "TEXT DEFAULT 'NONE'"),
            # Flow velocity/acceleration
            ("flow_velocity_mm", "REAL DEFAULT 0"),
            ("flow_velocity_foreign", "REAL DEFAULT 0"),
            ("flow_velocity_institution", "REAL DEFAULT 0"),
            ("flow_acceleration_mm", "REAL DEFAULT 0"),
            ("flow_acceleration_signal", "TEXT DEFAULT 'NONE'"),
            ("flow_velocity_score", "INTEGER DEFAULT 0"),
            # Important dates broker summary
            ("important_dates_json", "TEXT"),
            ("important_dates_score", "INTEGER DEFAULT 0"),
            ("important_dates_signal", "TEXT DEFAULT 'NONE'"),
        ]
        
        # Migration: Add week_ago/month_ago columns to bandarmology_txn_chart
        txn_chart_new_columns = [
            ("cum_mm_week_ago", "REAL DEFAULT 0"),
            ("cum_foreign_week_ago", "REAL DEFAULT 0"),
            ("cum_institution_week_ago", "REAL DEFAULT 0"),
            ("cum_smart_week_ago", "REAL DEFAULT 0"),
            ("cum_retail_week_ago", "REAL DEFAULT 0"),
            ("cum_mm_month_ago", "REAL DEFAULT 0"),
            ("cum_foreign_month_ago", "REAL DEFAULT 0"),
            ("cum_institution_month_ago", "REAL DEFAULT 0"),
            ("cum_smart_month_ago", "REAL DEFAULT 0"),
            ("cum_retail_month_ago", "REAL DEFAULT 0"),
        ]
        for col_name, col_type in txn_chart_new_columns:
            try:
                conn.execute(f"ALTER TABLE bandarmology_txn_chart ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
        
        for col_name, col_type in new_columns:
            try:
                conn.execute(f"ALTER TABLE bandarmology_deep_cache ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass  # Column already exists
        
        conn.commit()

