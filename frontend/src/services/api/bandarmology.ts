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

    // Signals
    deep_signals?: DeepSignals;
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

    // Detail data
    inventory_brokers: InvBrokerDetail[];
    txn_chart: Record<string, unknown> | null;
    broker_summary: { buy: BrokerSummaryEntry[]; sell: BrokerSummaryEntry[] };
    floor_analysis: Record<string, unknown>;
    top_holders: { broker_code: string; total_net_lot: number; total_net_value: number; trade_count: number }[];
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
    current_ticker: string;
    completed_tickers: string[];
    errors: string[];
    date?: string;
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
        minBaseScore: number = 20
    ): Promise<{ message: string; tickers: string[]; date: string }> => {
        const params = buildParams({
            date,
            top_n: topN.toString(),
            min_base_score: minBaseScore.toString()
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
        date?: string
    ): Promise<{ message: string; tickers: string[]; date: string }> => {
        const params = buildParams({ tickers, date });
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
};
