/**
 * Broker Stalker API client
 */
import { API_BASE_URL, handleResponse } from './base';

export interface BrokerWatchlistItem {
    broker_code: string;
    broker_name?: string | null;
    description?: string | null;
    power_level: number;
    created_at: string;
    updated_at: string;
}

export interface BrokerTrackingRecord {
    broker_code: string;
    ticker: string;
    trade_date: string;
    total_buy: number;
    total_sell: number;
    net_value: number;
    avg_price?: number | null;
    streak_days: number;
    status?: string | null;
    calculated_at: string;
}

export interface BrokerPortfolioPosition {
    ticker: string;
    total_net_value: number;
    trading_days: number;
    last_trade_date: string;
    avg_execution_price?: number | null;
    streak_days: number;
}

export interface BrokerAnalysis {
    broker_code: string;
    ticker: string;
    lookback_days: number;
    total_buy: number;
    total_sell: number;
    net_value: number;
    streak_days: number;
    status: string;
    daily_activity: Array<{
        date: string;
        buy_volume: number;
        sell_volume: number;
        net_value: number;
    }>;
}

export interface ChartDataPoint {
    date: string;
    buy: number;
    sell: number;
    net: number;
}

export interface ExecutionLedgerEntry {
    date: string;
    action: string;
    volume: number;
    avg_price?: number | null;
    status?: string | null;
}

export interface TickerBrokerActivity {
    broker_code: string;
    trade_date: string;
    total_buy: number;
    total_sell: number;
    net_value: number;
    avg_price?: number | null;
    streak_days: number;
    status?: string | null;
}

export const brokerStalkerApi = {
    getWatchlist: async (): Promise<{ status: string; count: number; brokers: BrokerWatchlistItem[] }> => {
        const response = await fetch(`${API_BASE_URL}/api/broker-stalker/watchlist`);
        return await handleResponse(response, { status: 'error', count: 0, brokers: [] });
    },

    addBrokerToWatchlist: async (payload: {
        broker_code: string;
        broker_name?: string;
        description?: string;
    }): Promise<{ status: string; message: string; broker_code: string; power_level: number }> => {
        const response = await fetch(`${API_BASE_URL}/api/broker-stalker/watchlist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to add broker to watchlist');
        }
        return await response.json();
    },

    removeBrokerFromWatchlist: async (brokerCode: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/broker-stalker/watchlist/${encodeURIComponent(brokerCode)}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to remove broker from watchlist');
        }
        return await response.json();
    },

    getBrokerPortfolio: async (
        brokerCode: string,
        minNetValue: number = 0
    ): Promise<{
        status: string;
        broker_code: string;
        total_positions: number;
        total_net_value: number;
        portfolio: BrokerPortfolioPosition[];
    }> => {
        const params = new URLSearchParams({ min_net_value: minNetValue.toString() });
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/portfolio/${encodeURIComponent(brokerCode)}?${params}`
        );
        return await handleResponse(response, {
            status: 'error',
            broker_code: brokerCode,
            total_positions: 0,
            total_net_value: 0,
            portfolio: []
        });
    },

    getBrokerAnalysis: async (
        brokerCode: string,
        ticker: string,
        lookbackDays: number = 30
    ): Promise<{ status: string; analysis: BrokerAnalysis }> => {
        const params = new URLSearchParams({ lookback_days: lookbackDays.toString() });
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/analysis/${encodeURIComponent(brokerCode)}/${encodeURIComponent(ticker)}?${params}`
        );
        return await handleResponse(response);
    },

    getChartData: async (
        brokerCode: string,
        ticker: string,
        days: number = 7
    ): Promise<{
        status: string;
        broker_code: string;
        ticker: string;
        days: number;
        data: ChartDataPoint[];
    }> => {
        const params = new URLSearchParams({ days: days.toString() });
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/chart/${encodeURIComponent(brokerCode)}/${encodeURIComponent(ticker)}?${params}`
        );
        return await handleResponse(response, {
            status: 'error',
            broker_code: brokerCode,
            ticker: ticker,
            days: days,
            data: []
        });
    },

    getExecutionLedger: async (
        brokerCode: string,
        ticker: string,
        limit: number = 10
    ): Promise<{
        status: string;
        broker_code: string;
        ticker: string;
        ledger: ExecutionLedgerEntry[];
    }> => {
        const params = new URLSearchParams({ limit: limit.toString() });
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/ledger/${encodeURIComponent(brokerCode)}/${encodeURIComponent(ticker)}?${params}`
        );
        return await handleResponse(response, {
            status: 'error',
            broker_code: brokerCode,
            ticker: ticker,
            ledger: []
        });
    },

    syncBrokerData: async (
        brokerCode: string,
        ticker?: string,
        days: number = 7
    ): Promise<{ status: string; sync_result: unknown }> => {
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/sync/${encodeURIComponent(brokerCode)}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, days })
            }
        );
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to sync broker data');
        }
        return await response.json();
    },

    getTickerBrokerActivity: async (
        ticker: string,
        days: number = 7
    ): Promise<{
        status: string;
        ticker: string;
        days: number;
        activity_count: number;
        activity: TickerBrokerActivity[];
    }> => {
        const params = new URLSearchParams({ days: days.toString() });
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/ticker/${encodeURIComponent(ticker)}/activity?${params}`
        );
        return await handleResponse(response, {
            status: 'error',
            ticker: ticker,
            days: days,
            activity_count: 0,
            activity: []
        });
    },

    calculatePowerLevel: async (
        brokerCode: string,
        lookbackDays: number = 30
    ): Promise<{
        status: string;
        broker_code: string;
        power_level: number;
        lookback_days: number;
    }> => {
        const params = new URLSearchParams({ lookback_days: lookbackDays.toString() });
        const response = await fetch(
            `${API_BASE_URL}/api/broker-stalker/power-level/${encodeURIComponent(brokerCode)}?${params}`
        );
        return await handleResponse(response);
    }
};
