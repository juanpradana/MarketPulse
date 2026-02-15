/**
 * Modular API Clients Export
 * 
 * Centralized export for all domain-specific API clients
 */

export * from './base';
export * from './dashboard';
export * from './news';
export * from './disclosures';
export * from './neobdm';
export * from './brokerFive';
export * from './doneDetail';
export * from './brokerStalker';
export * from './bandarmology';
export * from './scheduler';

// Re-export for convenience
import { dashboardApi } from './dashboard';
import { newsApi } from './news';
import { disclosuresApi } from './disclosures';
import { neobdmApi } from './neobdm';
import { scrapersApi } from './scrapers';
import { brokerFiveApi } from './brokerFive';
import { doneDetailApi } from './doneDetail';
import { brokerStalkerApi } from './brokerStalker';
import { bandarmologyApi } from './bandarmology';
import { schedulerApi } from './scheduler';

const api = {
    ...dashboardApi,
    ...newsApi,
    ...disclosuresApi,
    ...neobdmApi,
    ...scrapersApi,
    ...brokerFiveApi,
    ...doneDetailApi,
    ...brokerStalkerApi,
    ...bandarmologyApi,
    ...schedulerApi
};

export {
    dashboardApi,
    newsApi,
    disclosuresApi,
    neobdmApi,
    scrapersApi,
    brokerFiveApi,
    doneDetailApi,
    brokerStalkerApi,
    bandarmologyApi,
    schedulerApi,
    api
};
