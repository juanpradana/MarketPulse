/**
 * Bandarmology API client
 * 
 * Handles bandarmology screening, scoring, and stock classification
 */

import { API_BASE_URL, buildParams } from './base';

export interface BandarmologyScores {
    pinky: number;
    crossing: number;
    unusual: number;
    likuid: number;
    confluence: number;
    accumulation: number;
    ma_position: number;
    momentum: number;
    institutional: number;
}

export interface InvBrokerDetail {
    code: string;
    net_lot: number;
    is_clean: boolean;
    is_tektok: boolean;
    side: 'ACCUM' | 'DISTRIB';
}

export interface DeepSignals {
    [key: string]: string;
}

export interface BandarmologyItem {
    symbol: string;
    total_score: number;
    max_score: number;
    trade_type: 'SWING' | 'INTRADAY' | 'BOTH' | 'WATCH' | '—';
    pinky: boolean;
    crossing: boolean;
    unusual: boolean;
    likuid: boolean;
    confluence_status: 'TRIPLE' | 'DOUBLE' | 'SINGLE' | 'NONE';
    positive_methods: string[];
    price: number;
    pct_1d: number;
    ma_above_count: number;

    // Accumulation
    w_4: number;
    w_3: number;
    w_2: number;
    w_1: number;
    d_4: number;
    d_3: number;
    d_2: number;
    d_0_mm: number;
    d_0_nr: number;
    d_0_ff: number;

    // Cumulative
    c_3: number;
    c_5: number;
    c_10: number;
    c_20: number;

    // Broker info
    inst_net_lot: number;
    foreign_net_lot: number;
    retail_net_lot: number;
    top_buyer: string | null;
    top_seller: string | null;
    brokers_buying: number;
    brokers_selling: number;

    // Score breakdown
    scores: BandarmologyScores;

    // Deep analysis fields (optional, present when deep data exists)
    deep_score?: number;
    combined_score?: number;
    max_combined_score?: number;
    deep_trade_type?: string;
    has_deep?: boolean;

    // Inventory deep
    inv_accum_brokers?: number;
    inv_distrib_brokers?: number;
    inv_clean_brokers?: number;
    inv_tektok_brokers?: number;
    inv_total_accum_lot?: number;
    inv_top_accum_broker?: string;
    inv_brokers_detail?: InvBrokerDetail[];

    // Transaction chart deep
    txn_mm_cum?: number;
    txn_foreign_cum?: number;
    txn_institution_cum?: number;
    txn_cross_index?: number;
    txn_mm_trend?: string;
    txn_foreign_trend?: string;

    // Broker summary deep
    broksum_avg_buy_price?: number;
    broksum_avg_sell_price?: number;
    broksum_floor_price?: number;
    broksum_total_buy_lot?: number;
    broksum_total_sell_lot?: number;
    broksum_net_institutional?: number;
    broksum_net_foreign?: number;
    broksum_top_buyers?: { broker: string; nlot: number; avg_price: number }[];
    broksum_top_sellers?: { broker: string; nlot: number; avg_price: number }[];

    // Entry/target prices
    entry_price?: number;
    target_price?: number;
    stop_loss?: number;
    risk_reward_ratio?: number;

    // Controlling broker analysis
    controlling_brokers?: ControllingBroker[];
    accum_start_date?: string | null;
    accum_phase?: string;
    bandar_avg_cost?: number;
    bandar_total_lot?: number;
    coordination_score?: number;
    phase_confidence?: string;
    breakout_signal?: string;
    bandar_peak_lot?: number;
    bandar_distribution_pct?: number;
    distribution_alert?: string;

    // Cross-reference: broker summary <-> inventory
    bandar_buy_today_count?: number;
    bandar_sell_today_count?: number;
    bandar_buy_today_lot?: number;
    bandar_sell_today_lot?: number;
    bandar_confirmation?: string;

    // Multi-day consistency
    broksum_days_analyzed?: number;
    broksum_consistency_score?: number;
    broksum_consistent_buyers?: ConsistentBroker[];
    broksum_consistent_sellers?: ConsistentBroker[];

    // Breakout probability
    breakout_probability?: number;
    breakout_factors?: Record<string, number>;

    // Accumulation duration
    accum_duration_days?: number;

    // Concentration risk
    concentration_broker?: string | null;
    concentration_pct?: number;
    concentration_risk?: string;

    // Smart money vs retail divergence
    txn_smart_money_cum?: number;
    txn_retail_cum_deep?: number;
    smart_retail_divergence?: number;

    // Volume context
    volume_score?: number;
    volume_signal?: string;
    volume_confirmation_multiplier?: number;

    // MA cross
    ma_cross_signal?: string;
    ma_cross_score?: number;

    // Historical comparison
    prev_deep_score?: number;
    prev_phase?: string;
    phase_transition?: string;
    score_trend?: string;

    // Flow velocity/acceleration
    flow_velocity_mm?: number;
    flow_velocity_foreign?: number;
    flow_velocity_institution?: number;
    flow_acceleration_mm?: number;
    flow_acceleration_signal?: string;
    flow_velocity_score?: number;

    // Important dates broker summary
    important_dates?: ImportantDateAnalysis[];
    important_dates_score?: number;
    important_dates_signal?: string;

    // Pump tomorrow prediction
    pump_tomorrow_score?: number;
    pump_tomorrow_signal?: string;
    pump_tomorrow_factors?: Record<string, number>;

    // Data freshness (Improvement 7)
    data_freshness?: number;
    data_source_date?: string;
    original_deep_score?: number;

    // Entry/target methods (Improvement 6)
    target_method?: string;
    stop_method?: string;

    // Relative context (Improvement 4)
    relative_context?: {
        market_context?: {
            stock_flow?: number;
            market_avg?: number;
            market_std?: number;
            z_score?: number;
            percentile?: number;
        };
        sector_context?: {
            sector?: string;
            stock_flow?: number;
            sector_avg?: number;
            sector_count?: number;
            diff_pct?: number;
        };
        relative_score?: number;
        z_score_used?: number;
    };

    // Conflict warning (Improvement 5)
    conflict_stats?: {
        mean: number;
        std: number;
        cv: number;
        sources: Record<string, number>;
        multiplier: number;
    } | null;
    data_source_conflict?: boolean;

    // Signals
    deep_signals?: DeepSignals;
}

export interface ImportantDateAnalysis {
    date: string;
    date_type: string;
    bandar_buy_count: number;
    bandar_sell_count: number;
    bandar_net_lot: number;
}

export interface ControllingBroker {
    code: string;
    net_lot: number;
    avg_buy_price: number;
    total_buy_lots: number;
    total_sell_lots: number;
    is_clean: boolean;
    is_tektok: boolean;
    turn_date: string | null;
    avg_daily_last10: number;
    broker_class: string;
    peak_lot: number;
    peak_date: string | null;
    distribution_pct: number;
}

export interface ConsistentBroker {
    code: string;
    buy_days?: number;
    sell_days?: number;
    total_days: number;
    total_lot: number;
    is_bandar: boolean;
}

export interface BrokerSummaryEntry {
    broker: string;
    nlot: number;
    nval?: number;
    avg_price: number;
    side?: string;
}

export interface StockDetailResponse {
    ticker: string;
    date: string;
    has_deep: boolean;

    // Base screening
    base_score: number;
    max_base_score: number;
    trade_type: string;
    price: number;
    pct_1d: number;
    ma_above_count: number;
    pinky: boolean;
    crossing: boolean;
    unusual: boolean;
    likuid: boolean;
    confluence_status: string;
    scores: BandarmologyScores;

    // Weekly/daily flows
    w_4: number;
    w_3: number;
    w_2: number;
    w_1: number;
    d_0_mm: number;
    d_0_nr: number;
    d_0_ff: number;

    // Deep analysis
    deep_score?: number;
    combined_score?: number;
    max_combined_score?: number;
    deep_trade_type?: string;
    deep_signals?: DeepSignals;

    // Inventory
    inv_accum_brokers?: number;
    inv_distrib_brokers?: number;
    inv_clean_brokers?: number;
    inv_tektok_brokers?: number;
    inv_total_accum_lot?: number;
    inv_total_distrib_lot?: number;
    inv_top_accum_broker?: string;

    // Transaction chart
    txn_mm_cum?: number;
    txn_foreign_cum?: number;
    txn_institution_cum?: number;
    txn_retail_cum?: number;
    txn_cross_index?: number;
    txn_mm_trend?: string;
    txn_foreign_trend?: string;

    // Broker summary
    broksum_total_buy_lot?: number;
    broksum_total_sell_lot?: number;
    broksum_avg_buy_price?: number;
    broksum_avg_sell_price?: number;
    broksum_floor_price?: number;
    broksum_net_institutional?: number;
    broksum_net_foreign?: number;
    broksum_top_buyers?: { broker: string; nlot: number; avg_price: number }[];
    broksum_top_sellers?: { broker: string; nlot: number; avg_price: number }[];

    // Entry/target
    entry_price?: number;
    target_price?: number;
    stop_loss?: number;
    risk_reward_ratio?: number;

    // Controlling broker analysis
    controlling_brokers?: ControllingBroker[];
    accum_start_date?: string | null;
    accum_phase?: string;
    bandar_avg_cost?: number;
    bandar_total_lot?: number;
    coordination_score?: number;
    phase_confidence?: string;
    breakout_signal?: string;
    bandar_peak_lot?: number;
    bandar_distribution_pct?: number;
    distribution_alert?: string;

    // Cross-reference
    bandar_buy_today_count?: number;
    bandar_sell_today_count?: number;
    bandar_buy_today_lot?: number;
    bandar_sell_today_lot?: number;
    bandar_confirmation?: string;

    // Multi-day consistency
    broksum_days_analyzed?: number;
    broksum_consistency_score?: number;
    broksum_consistent_buyers?: ConsistentBroker[];
    broksum_consistent_sellers?: ConsistentBroker[];

    // Breakout probability
    breakout_probability?: number;
    breakout_factors?: Record<string, number>;

    // Accumulation duration
    accum_duration_days?: number;

    // Concentration risk
    concentration_broker?: string | null;
    concentration_pct?: number;
    concentration_risk?: string;

    // Smart money vs retail divergence
    txn_smart_money_cum?: number;
    txn_retail_cum_deep?: number;
    smart_retail_divergence?: number;

    // Volume context
    volume_score?: number;
    volume_signal?: string;
    volume_confirmation_multiplier?: number;

    // MA cross
    ma_cross_signal?: string;
    ma_cross_score?: number;

    // Historical comparison
    prev_deep_score?: number;
    prev_phase?: string;
    phase_transition?: string;
    score_trend?: string;

    // Flow velocity/acceleration
    flow_velocity_mm?: number;
    flow_velocity_foreign?: number;
    flow_velocity_institution?: number;
    flow_acceleration_mm?: number;
    flow_acceleration_signal?: string;
    flow_velocity_score?: number;

    // Important dates broker summary
    important_dates?: ImportantDateAnalysis[];
    important_dates_score?: number;
    important_dates_signal?: string;

    // Pump tomorrow prediction
    pump_tomorrow_score?: number;
    pump_tomorrow_signal?: string;
    pump_tomorrow_factors?: Record<string, number>;

    // Data freshness (Improvement 7)
    data_freshness?: number;
    data_source_date?: string;
    original_deep_score?: number;

    // Entry/target methods (Improvement 6)
    target_method?: string;
    stop_method?: string;

    // Relative context (Improvement 4)
    relative_context?: {
        market_context?: {
            stock_flow?: number;
            market_avg?: number;
            market_std?: number;
            z_score?: number;
            percentile?: number;
        };
        sector_context?: {
            sector?: string;
            stock_flow?: number;
            sector_avg?: number;
            sector_count?: number;
            diff_pct?: number;
        };
        relative_score?: number;
        z_score_used?: number;
    };

    // Conflict warning (Improvement 5)
    conflict_stats?: {
        mean: number;
        std: number;
        cv: number;
        sources: Record<string, number>;
        multiplier: number;
    } | null;
    data_source_conflict?: boolean;

    // Yahoo Finance Enhanced Features
    // Float analysis
    bandar_float_pct?: number;
    float_control_level?: 'WEAK' | 'MODERATE' | 'STRONG' | 'DOMINANT';
    float_score?: number;

    // Volume anomaly
    volume_anomaly_score?: number;

    // Bandar power
    bandar_power_score?: number;
    bandar_power_rating?: 'EXCELLENT' | 'GOOD' | 'MODERATE' | 'POOR';
    bandar_power_components?: {
        float: number;
        volume: number;
        beta: number;
        position: number;
        institutional: number;
    };

    // Earnings timing
    earnings_score?: number;
    days_to_earnings?: number;
    earnings_signal?: string;

    // Detail data
    inventory_brokers: InvBrokerDetail[];
    txn_chart: Record<string, unknown> | null;
    broker_summary: { buy: BrokerSummaryEntry[]; sell: BrokerSummaryEntry[] };
    floor_analysis: Record<string, unknown>;
    top_holders: { broker_code: string; total_net_lot: number; total_net_value: number; trade_count: number }[];
}

export interface WatchlistAlert {
    ticker: string;
    alert_type: 'PHASE_READY' | 'HOLDING_NEAR_COST' | 'PHASE_EXIT' | 'GOLDEN_CROSS' | 'SCORE_SURGE';
    priority: 'HIGH' | 'MEDIUM' | 'LOW';
    description: string;
    phase: string;
    prev_phase: string;
    price: number;
    bandar_cost: number;
    price_vs_cost_pct: number;
    deep_score: number;
}

export interface WatchlistAlertsResponse {
    date: string | null;
    total_alerts: number;
    alerts: WatchlistAlert[];
}

export interface BandarmologyResponse {
    date: string | null;
    total_stocks: number;
    has_deep_data?: boolean;
    deep_analysis_running?: boolean;
    data: BandarmologyItem[];
}

export interface DeepAnalysisStatus {
    running: boolean;
    progress: number;
    total: number;
    requested?: number;
    qualified?: number;
    processed?: number;
    failed?: number;
    already_fresh_today?: number;
    concurrency?: number;
    current_ticker: string;
    active_tickers?: string[];
    completed_tickers: string[];
    failed_tickers?: string[];
    fresh_tickers?: string[];
    errors: string[];
    date?: string;
}

// Yahoo Finance Enhanced Interfaces
export interface FloatAnalysisData {
    ticker: string;
    shares_outstanding: number;
    float_shares: number;
    float_ratio: number;
    cached_at: string;
    source: string;
}

export interface BandarControlData extends FloatAnalysisData {
    bandar_lots: number;
    bandar_shares: number;
    bandar_float_pct: number;
    control_level: 'WEAK' | 'MODERATE' | 'STRONG' | 'DOMINANT';
}

export interface VolumeMetrics {
    ticker: string;
    current_volume: number;
    avg_volume_10d: number;
    avg_volume_3m: number;
    volume_ratio: number;
    is_spike: boolean;
    is_strong_spike: boolean;
    price_change: number;
    signal: 'ACCUMULATION' | 'DISTRIBUTION' | 'NORMAL';
    confidence: number;
    signal_description: string;
    calculated_at: string;
}

export interface BandarPowerScore {
    ticker: string;
    score: number;
    rating: 'EXCELLENT' | 'GOOD' | 'MODERATE' | 'POOR';
    calculated_at: string;
}

export interface BandarPowerDetail extends BandarPowerScore {
    components: {
        float: number;
        volume: number;
        beta: number;
        position: number;
        institutional: number;
    };
    metadata: {
        market_cap: number;
        float_shares: number;
        beta: number;
        position_52w_pct: number;
        foreign_flow_trend: string;
        volume_ratio: number;
    };
}

export interface EarningsEvent {
    ticker: string;
    earnings_date: string;
    days_until: number;
    fiscal_quarter: string;
    eps_estimate?: number;
    eps_actual?: number;
    surprise_pct?: number;
}

export interface PreEarningsPattern {
    ticker: string;
    signal: string;
    confidence: number;
    days_until: number;
    earnings_date: string;
    bandar_activity: {
        deep_score: number;
        phase: string;
        mm_flow: number;
    };
    message: string;
}

/**
 * Bandarmology API client
 */
export const bandarmologyApi = {
    /**
     * Get bandarmology screening results
     */
    getScreening: async (
        date?: string,
        minScore: number = 0,
        tradeType?: string
    ): Promise<BandarmologyResponse> => {
        const params = buildParams({
            date,
            min_score: minScore.toString(),
            trade_type: tradeType
        });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch bandarmology data');
        }
        return await response.json();
    },

    /**
     * Get available dates for analysis
     */
    getDates: async (): Promise<{ dates: string[] }> => {
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/dates`);
        if (!response.ok) {
            throw new Error('Failed to fetch bandarmology dates');
        }
        return await response.json();
    },

    /**
     * Trigger deep analysis for top N stocks
     */
    triggerDeepAnalysis: async (
        date?: string,
        topN: number = 30,
        minBaseScore: number = 20,
        concurrency: number = 4
    ): Promise<{
        message: string;
        tickers: string[];
        date: string;
        requested: number;
        qualified: number;
        to_process: number;
        concurrency: number;
    }> => {
        const params = buildParams({
            date,
            top_n: topN.toString(),
            min_base_score: minBaseScore.toString(),
            concurrency: concurrency.toString(),
        });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/deep-analyze?${params}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to trigger deep analysis');
        }
        return await response.json();
    },

    /**
     * Get deep analysis status
     */
    getDeepStatus: async (): Promise<DeepAnalysisStatus> => {
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/deep-status`);
        if (!response.ok) {
            throw new Error('Failed to fetch deep analysis status');
        }
        return await response.json();
    },

    /**
     * Trigger deep analysis for specific tickers (manual input)
     */
    triggerDeepAnalysisTickers: async (
        tickers: string,
        date?: string,
        concurrency: number = 4
    ): Promise<{
        message: string;
        tickers: string[];
        date: string;
        requested: number;
        qualified: number;
        to_process: number;
        concurrency: number;
    }> => {
        const params = buildParams({ tickers, date, concurrency: concurrency.toString() });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/deep-analyze-tickers?${params}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to trigger manual deep analysis');
        }
        return await response.json();
    },

    /**
     * Get detailed deep analysis for a single stock
     */
    getStockDetail: async (ticker: string, date?: string): Promise<StockDetailResponse> => {
        const params = buildParams({ date });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/${ticker}/detail?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch stock detail');
        }
        return await response.json();
    },

    /**
     * Get watchlist alerts (phase transitions, golden crosses, etc.)
     */
    getWatchlistAlerts: async (date?: string): Promise<WatchlistAlertsResponse> => {
        const params = buildParams({ date });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/watchlist-alerts?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch watchlist alerts');
        }
        return await response.json();
    },

    /**
     * Get float analysis for a ticker
     */
    getFloatAnalysis: async (ticker: string, forceRefresh?: boolean): Promise<BandarControlData> => {
        const params = buildParams({ force_refresh: forceRefresh });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/float-analysis/${ticker}?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch float analysis');
        }
        return await response.json();
    },

    /**
     * Get volume metrics for anomaly detection
     */
    getVolumeMetrics: async (ticker: string, forceRefresh?: boolean): Promise<VolumeMetrics> => {
        const params = buildParams({ force_refresh: forceRefresh });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/volume-metrics/${ticker}?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch volume metrics');
        }
        return await response.json();
    },

    /**
     * Get Bandar Power Score rankings
     */
    getBandarPowerScores: async (limit: number = 50, minRating?: string): Promise<{
        scores: BandarPowerScore[];
        count: number;
        max_score: number;
        rating_thresholds: Record<string, number>;
    }> => {
        const params = buildParams({ limit: limit.toString(), min_rating: minRating });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/power-scores?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch power scores');
        }
        return await response.json();
    },

    /**
     * Get detailed Bandar Power Score for a ticker
     */
    getBandarPowerDetail: async (ticker: string, forceRefresh?: boolean): Promise<BandarPowerDetail> => {
        const params = buildParams({ force_refresh: forceRefresh });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/power-scores/${ticker}?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch bandar power detail');
        }
        return await response.json();
    },

    /**
     * Get earnings calendar
     */
    getEarningsCalendar: async (days?: number, ticker?: string): Promise<{
        earnings: EarningsEvent[];
        count: number;
        days_ahead: number;
    }> => {
        const params = buildParams({ days: days?.toString(), ticker });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/earnings-calendar?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch earnings calendar');
        }
        return await response.json();
    },

    /**
     * Get earnings data for a specific ticker
     */
    getTickerEarnings: async (ticker: string, days?: number, forceRefresh?: boolean): Promise<{
        ticker: string;
        upcoming_earnings: EarningsEvent[];
        earnings_history: EarningsEvent[];
        pattern_detection: PreEarningsPattern;
    }> => {
        const params = buildParams({ days: days?.toString(), force_refresh: forceRefresh });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/earnings-calendar/${ticker}?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch ticker earnings');
        }
        return await response.json();
    },

    /**
     * Get pre-earnings opportunities with accumulation patterns
     */
    getPreEarningsOpportunities: async (minConfidence: number = 60): Promise<{
        opportunities: PreEarningsPattern[];
        count: number;
        min_confidence: number;
    }> => {
        const params = buildParams({ min_confidence: minConfidence.toString() });
        const response = await fetch(`${API_BASE_URL}/api/bandarmology/pre-earnings-opportunities?${params}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch pre-earnings opportunities');
        }
        return await response.json();
    },
};
