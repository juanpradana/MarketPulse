/**
 * Backward-compatible API client wrapper
 * 
 * This file maintains the original `api` object interface while delegating to new modular clients.
 * Allows existing code to work without changes during migration.
 * 
 * @deprecated Import specific API clients from '@/services/api' instead
 * @example
 * // Old way (still works)
 * import { api } from '@/services/api';
 * api.getDashboardStats(ticker);
 * 
 * // New way (preferred)
 * import { dashboardApi } from '@/services/api';
 * dashboardApi.getDashboardStats(ticker);
 */

import { StockData } from '@/types/market';
import { dashboardApi } from './api/dashboard';
import { newsApi, NewsItem } from './api/news';
import { disclosuresApi, Disclosure } from './api/disclosures';
import { neobdmApi } from './api/neobdm';
import { scrapersApi } from './api/scrapers';
import { brokerFiveApi } from './api/brokerFive';
import { doneDetailApi } from './api/doneDetail';
import { priceVolumeApi } from './api/priceVolume';
import { bandarmologyApi } from './api/bandarmology';
import { watchlistApi, type WatchlistItem, type WatchlistStats, type WatchlistToggleResponse } from './api/watchlist';

// Re-export types for backward compatibility
export type { NewsItem, Disclosure, WatchlistItem, WatchlistStats, WatchlistToggleResponse };
export type { NewsItem, Disclosure };

/**
 * Legacy API object - delegates to new modular clients
 */
export const api = {
    // Dashboard APIs
    getTickers: dashboardApi.getTickers,
    getIssuerTickers: dashboardApi.getIssuerTickers,
    getDashboardStats: dashboardApi.getDashboardStats,
    getMarketData: dashboardApi.getMarketData,
    getSentimentHistory: dashboardApi.getSentimentHistory,

    // News APIs
    getNews: newsApi.getNews,
    getBriefNews: newsApi.getBriefNews,
    getSingleNewsBrief: newsApi.getSingleNewsBrief,
    getWordCloud: newsApi.getWordCloud,
    getTickerCounts: newsApi.getTickerCounts,

    // Disclosures & RAG APIs
    getDisclosures: disclosuresApi.getDisclosures,
    sendChatMessage: disclosuresApi.sendChatMessage,
    openFile: disclosuresApi.openFile,
    syncDisclosures: disclosuresApi.syncDisclosures,

    // NeoBDM APIs
    getNeoBDMSummary: neobdmApi.getNeoBDMSummary,
    getNeoBDMDates: neobdmApi.getNeoBDMDates,
    runNeoBDMBatchScrape: neobdmApi.runNeoBDMBatchScrape,
    getNeoBDMHistory: neobdmApi.getNeoBDMHistory,
    getNeoBDMTickers: neobdmApi.getNeoBDMTickers,
    getNeoBDMHotList: neobdmApi.getNeoBDMHotList,
    getNeoBDMBrokerSummary: neobdmApi.getNeoBDMBrokerSummary,
    runNeoBDMBrokerSummaryBatch: neobdmApi.runNeoBDMBrokerSummaryBatch,
    getVolumeDaily: neobdmApi.getVolumeDaily,
    getAvailableDatesForTicker: neobdmApi.getAvailableDatesForTicker,
    getBrokerJourney: neobdmApi.getBrokerJourney,
    getBrokerFiveList: brokerFiveApi.getBrokerFiveList,
    createBrokerFive: brokerFiveApi.createBrokerFive,
    updateBrokerFive: brokerFiveApi.updateBrokerFive,
    deleteBrokerFive: brokerFiveApi.deleteBrokerFive,

    // Scraper APIs
    runScraper: scrapersApi.runScraper,

    // Bandarmology APIs
    getBandarmologyScreening: bandarmologyApi.getScreening,
    getBandarmologyDates: bandarmologyApi.getDates,

    // Watchlist APIs
    getWatchlist: watchlistApi.getWatchlist,
    getWatchlistTickers: watchlistApi.getTickers,
    addTickerToWatchlist: watchlistApi.addTicker,
    removeTickerFromWatchlist: watchlistApi.removeTicker,
    toggleWatchlistTicker: watchlistApi.toggleTicker,
    checkWatchlist: watchlistApi.checkWatchlist,
    getWatchlistStats: watchlistApi.getStats,
};

/**
 * Export modular clients for new code
 */
export {
    dashboardApi,
    newsApi,
    disclosuresApi,
    neobdmApi,
    scrapersApi,
    brokerFiveApi,
    doneDetailApi,
    priceVolumeApi,
    bandarmologyApi,
    watchlistApi
};
