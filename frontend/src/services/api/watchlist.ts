/**
 * Watchlist API Service
 *
 * For managing user's personalized ticker watchlist.
 */

import { API_BASE_URL } from './base';

export interface WatchlistItem {
    ticker: string;
    added_at: string;
    list_name?: string;
    company_name?: string;
    latest_price?: {
        price: number;
        change_percent: number;
        volume: number;
        date: string;
    };
}

export interface AlphaHunterAnalysis {
    signal_score?: number;
    signal_strength?: string;
    conviction?: string;
    patterns: string[];
    flow?: number;
    entry_zone?: string;
    momentum_status?: string;
    warning_status?: string;
    has_signal: boolean;
}

export interface BandarmologyAnalysis {
    total_score?: number;
    deep_score?: number;
    combined_score?: number;
    trade_type?: string;
    deep_trade_type?: string;
    phase?: string;
    bandar_avg_cost?: number;
    price_vs_cost_pct?: number;
    breakout_signal?: string;
    distribution_alert?: string;
    pinky: boolean;
    crossing: boolean;
    unusual: boolean;
    has_analysis: boolean;
}

export interface WatchlistItemWithAnalysis {
    ticker: string;
    added_at: string;
    list_name?: string;
    company_name?: string;
    latest_price?: {
        price: number;
        change_percent: number;
        volume: number;
        date: string;
    };
    alpha_hunter: AlphaHunterAnalysis;
    bandarmology: BandarmologyAnalysis;
    combined_rating?: string;
    recommendation?: string;
}

export interface WatchlistStats {
    count: number;
    tickers: string[];
    user_id: string;
    list_name?: string;
}

export interface WatchlistCollection {
    list_name: string;
    created_at?: string;
    updated_at?: string;
    ticker_count: number;
}

export interface WatchlistToggleResponse {
    status: 'added' | 'removed';
    ticker: string;
    in_watchlist: boolean;
    list_name?: string;
}

export const watchlistApi = {
    /**
     * Get full watchlist with details
     */
    getWatchlist: async (listName: string = 'Default'): Promise<WatchlistItem[]> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist?list_name=${encodeURIComponent(listName)}`);
        if (!response.ok) {
            throw new Error('Failed to fetch watchlist');
        }
        return await response.json();
    },

    /**
     * Get watchlist with Alpha Hunter and Bandarmology analysis
     */
    getWatchlistWithAnalysis: async (listName: string = 'Default'): Promise<WatchlistItemWithAnalysis[]> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/with-analysis?list_name=${encodeURIComponent(listName)}`);
        if (!response.ok) {
            throw new Error('Failed to fetch watchlist with analysis');
        }
        return await response.json();
    },

    /**
     * Get just ticker symbols
     */
    getTickers: async (listName: string = 'Default'): Promise<string[]> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/tickers?list_name=${encodeURIComponent(listName)}`);
        if (!response.ok) {
            throw new Error('Failed to fetch tickers');
        }
        const data = await response.json();
        return data.tickers;
    },

    /**
     * Add ticker to watchlist
     */
    addTicker: async (ticker: string, listName: string = 'Default'): Promise<{ status: string; message: string; list_name?: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, list_name: listName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add ticker');
        }
        return await response.json();
    },

    /**
     * Remove ticker from watchlist
     */
    removeTicker: async (ticker: string, listName: string = 'Default'): Promise<{ status: string; message: string; list_name?: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, list_name: listName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to remove ticker');
        }
        return await response.json();
    },

    /**
     * Toggle ticker in watchlist (add if not exists, remove if exists)
     */
    toggleTicker: async (ticker: string, listName: string = 'Default'): Promise<WatchlistToggleResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, list_name: listName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to toggle ticker');
        }
        return await response.json();
    },

    /**
     * Check if ticker is in watchlist
     */
    checkWatchlist: async (ticker: string, listName: string = 'Default'): Promise<{ ticker: string; in_watchlist: boolean; list_name?: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/check/${ticker}?list_name=${encodeURIComponent(listName)}`);
        if (!response.ok) {
            throw new Error('Failed to check watchlist');
        }
        return await response.json();
    },

    /**
     * Get watchlist stats
     */
    getStats: async (listName: string = 'Default'): Promise<WatchlistStats> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/stats?list_name=${encodeURIComponent(listName)}`);
        if (!response.ok) {
            throw new Error('Failed to fetch stats');
        }
        return await response.json();
    },

    /**
     * Trigger deep analysis for missing tickers
     */
    analyzeMissing: async (tickers: string[]): Promise<{
        status: string;
        message: string;
        tickers: string[];
        status_endpoint: string;
    }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/analyze-missing?tickers=${tickers.join(',')}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start analysis');
        }
        return await response.json();
    },

    /**
     * Get analysis status
     */
    getAnalysisStatus: async (): Promise<{
        running: boolean;
        progress: number;
        total: number;
        current_ticker: string;
        completed_tickers: string[];
        errors: Array<{ ticker: string; stage: string; error: string }>;
        stage: string;
    }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/analyze-status`);
        if (!response.ok) {
            throw new Error('Failed to fetch analysis status');
        }
        return await response.json();
    },

    /**
     * Get all watchlist collections
     */
    getLists: async (): Promise<WatchlistCollection[]> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/lists`);
        if (!response.ok) {
            throw new Error('Failed to fetch watchlist collections');
        }
        return await response.json();
    },

    /**
     * Create a watchlist collection
     */
    createList: async (listName: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/lists`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ list_name: listName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create watchlist');
        }
        return await response.json();
    },

    /**
     * Rename watchlist collection
     */
    renameList: async (oldName: string, newName: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/lists/${encodeURIComponent(oldName)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: newName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to rename watchlist');
        }
        return await response.json();
    },

    /**
     * Delete watchlist collection
     */
    deleteList: async (listName: string, moveToList?: string): Promise<{ status: string; message: string }> => {
        const url = new URL(`${API_BASE_URL}/api/watchlist/lists/${encodeURIComponent(listName)}`);
        if (moveToList) {
            url.searchParams.set('move_to_list', moveToList);
        }
        const response = await fetch(url.toString(), {
            method: 'DELETE'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete watchlist');
        }
        return await response.json();
    },

    /**
     * Move ticker between watchlist collections
     */
    moveTicker: async (ticker: string, fromListName: string, toListName: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/move-ticker`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker,
                from_list_name: fromListName,
                to_list_name: toListName,
            })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to move ticker');
        }
        return await response.json();
    }
};
