/**
 * Alpha Hunter API client
 *
 * Handles Stage 1-4 analysis flows and investigation watchlist.
 */

import { API_BASE_URL, buildParams, handleResponse } from './base';

export interface Stage1ScanParams {
    min_score?: number;
    min_flow?: number;
    max_price_change?: number;
    strength_filter?: string;
    pattern_filter?: string[];
    price_value?: number | string;
    price_operator?: string;
    max_results?: number;
}

export interface Stage1ScanResponse {
    total_signals: number;
    filtered_count: number;
    total_matches?: number;
    signals: unknown[];
    stats?: unknown;
    message?: string;
}

export interface TradingDatesResponse {
    ticker: string;
    dates: Array<{ date: string; has_data: boolean }>;
    total: number;
    already_scraped: number;
    needs_scraping: number;
}

export const alphaHunterApi = {
    /**
     * Stage 1 flow-based scan
     */
    scanStage1: async (params: Stage1ScanParams): Promise<Stage1ScanResponse> => {
        const searchParams = buildParams({
            min_score: params.min_score,
            min_flow: params.min_flow,
            max_price_change: params.max_price_change,
            strength_filter: params.strength_filter,
            price_value: params.price_value,
            price_operator: params.price_operator,
            max_results: params.max_results
        });

        if (params.pattern_filter && params.pattern_filter.length > 0) {
            params.pattern_filter.forEach((pattern) => {
                searchParams.append('pattern_filter', pattern);
            });
        }

        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/stage1/scan?${searchParams}`);
        return await handleResponse(response, {
            total_signals: 0,
            filtered_count: 0,
            signals: []
        });
    },

    /**
     * Stage 1 custom ticker lookup
     */
    getStage1Ticker: async (ticker: string): Promise<unknown> => {
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/stage1/ticker/${encodeURIComponent(ticker)}`);
        return await handleResponse(response);
    },

    /**
     * Stage 2 VPA analysis
     */
    getStage2VPA: async (ticker: string): Promise<unknown> => {
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/stage2/vpa/${encodeURIComponent(ticker)}`);
        return await handleResponse(response);
    },

    /**
     * Stage 2 visualization payload
     */
    getStage2Visualization: async (ticker: string, sellingClimaxDate?: string): Promise<unknown> => {
        const params = buildParams({ selling_climax_date: sellingClimaxDate });
        const suffix = params.toString() ? `?${params}` : '';
        const response = await fetch(
            `${API_BASE_URL}/api/alpha-hunter/stage2/visualization/${encodeURIComponent(ticker)}${suffix}`
        );
        return await handleResponse(response);
    },

    /**
     * Stage 3 trading dates
     */
    getStage3TradingDates: async (ticker: string, days: number = 7): Promise<TradingDatesResponse> => {
        const params = buildParams({ days });
        const response = await fetch(
            `${API_BASE_URL}/api/alpha-hunter/stage3/trading-dates/${encodeURIComponent(ticker)}?${params}`
        );
        return await handleResponse(response);
    },

    /**
     * Stage 3 smart money flow
     */
    getFlowAnalysis: async (ticker: string, days: number = 7): Promise<unknown> => {
        const params = buildParams({ days });
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/flow/${encodeURIComponent(ticker)}?${params}`);
        return await handleResponse(response);
    },

    /**
     * Trigger broker scraping for specific dates
     */
    scrapeBrokerDates: async (ticker: string, dates: string[]): Promise<unknown> => {
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/scrape-broker/${encodeURIComponent(ticker)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dates)
        });
        return await handleResponse(response);
    },

    /**
     * Supply analysis (Stage 4)
     */
    getSupplyAnalysis: async (ticker: string, startDate?: string, endDate?: string): Promise<unknown> => {
        const params = buildParams({
            start_date: startDate,
            end_date: endDate
        });
        const suffix = params.toString() ? `?${params}` : '';
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/supply/${encodeURIComponent(ticker)}${suffix}`);
        return await handleResponse(response);
    },

    /**
     * Parse Done Detail pasted data
     */
    parseDoneDetail: async (ticker: string, rawData: string): Promise<unknown> => {
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/parse-done-detail`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, raw_data: rawData })
        });
        return await handleResponse(response);
    },

    /**
     * Get investigation watchlist
     */
    getWatchlist: async (): Promise<unknown> => {
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/watchlist`);
        return await handleResponse(response);
    },

    /**
     * Manage investigation watchlist
     */
    manageWatchlist: async (payload: { action: string; ticker: string; scan_data?: unknown }): Promise<unknown> => {
        const response = await fetch(`${API_BASE_URL}/api/alpha-hunter/watchlist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return await handleResponse(response);
    }
};
