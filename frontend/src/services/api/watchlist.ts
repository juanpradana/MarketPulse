/**
 * Watchlist API Service
 *
 * For managing user's personalized ticker watchlist.
 */

import { API_BASE_URL } from './base';

export interface WatchlistItem {
    ticker: string;
    added_at: string;
    company_name?: string;
    latest_price?: {
        price: number;
        change_percent: number;
        volume: number;
        date: string;
    };
}

export interface WatchlistStats {
    count: number;
    tickers: string[];
    user_id: string;
}

export interface WatchlistToggleResponse {
    status: 'added' | 'removed';
    ticker: string;
    in_watchlist: boolean;
}

export const watchlistApi = {
    /**
     * Get full watchlist with details
     */
    getWatchlist: async (): Promise<WatchlistItem[]> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist`);
        if (!response.ok) {
            throw new Error('Failed to fetch watchlist');
        }
        return await response.json();
    },

    /**
     * Get just ticker symbols
     */
    getTickers: async (): Promise<string[]> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/tickers`);
        if (!response.ok) {
            throw new Error('Failed to fetch tickers');
        }
        const data = await response.json();
        return data.tickers;
    },

    /**
     * Add ticker to watchlist
     */
    addTicker: async (ticker: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
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
    removeTicker: async (ticker: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
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
    toggleTicker: async (ticker: string): Promise<WatchlistToggleResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
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
    checkWatchlist: async (ticker: string): Promise<{ ticker: string; in_watchlist: boolean }> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/check/${ticker}`);
        if (!response.ok) {
            throw new Error('Failed to check watchlist');
        }
        return await response.json();
    },

    /**
     * Get watchlist stats
     */
    getStats: async (): Promise<WatchlistStats> => {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/stats`);
        if (!response.ok) {
            throw new Error('Failed to fetch stats');
        }
        return await response.json();
    }
};
