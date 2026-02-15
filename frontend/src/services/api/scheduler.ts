/**
 * Scheduler API Service
 *
 * For monitoring and controlling the background task scheduler.
 * Manual triggers are also available here (for frontend buttons).
 */

import { API_BASE_URL, buildParams } from './base';

export interface ScheduledJob {
    id: string;
    name: string;
    next_run: string | null;
    trigger: string;
}

export interface SchedulerStatus {
    running: boolean;
    job_count: number;
    jobs: ScheduledJob[];
}

export interface ScheduleConfig {
    timezone: string;
    schedules: Array<{
        job_id: string;
        name: string;
        frequency: string;
        description: string;
    }>;
}

export const schedulerApi = {
    /**
     * Get scheduler status and list of scheduled jobs
     */
    getStatus: async (): Promise<SchedulerStatus> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/status`);
        if (!response.ok) {
            throw new Error('Failed to fetch scheduler status');
        }
        return await response.json();
    },

    /**
     * Start the background scheduler
     */
    start: async (): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/start`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to start scheduler');
        }
        return await response.json();
    },

    /**
     * Stop the background scheduler
     */
    stop: async (): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/stop`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to stop scheduler');
        }
        return await response.json();
    },

    /**
     * Get schedule configuration
     */
    getScheduleConfig: async (): Promise<ScheduleConfig> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/schedule`);
        if (!response.ok) {
            throw new Error('Failed to fetch schedule config');
        }
        return await response.json();
    },

    // =========================================================================
    // MANUAL TRIGGERS (Keep frontend buttons working)
    // =========================================================================

    /**
     * Manually trigger news scraping
     * Called by Dashboard "Refresh Intelligence" button
     */
    manualNewsScrape: async (): Promise<{ status: string; message: string; details: any[] }> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/manual/news`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to scrape news');
        }
        return await response.json();
    },

    /**
     * Manually trigger NeoBDM batch scrape
     */
    manualNeoBDMScrape: async (): Promise<{ status: string; message?: string; error?: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/manual/neobdm`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to scrape NeoBDM');
        }
        return await response.json();
    },

    /**
     * Manually trigger data cleanup
     */
    manualCleanup: async (): Promise<{ status: string; deleted_records?: number; error?: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/manual/cleanup`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to run cleanup');
        }
        return await response.json();
    },

    /**
     * Manually run a specific scheduled job by ID
     */
    runJob: async (jobId: string): Promise<{ status: string; message: string }> => {
        const response = await fetch(`${API_BASE_URL}/api/scheduler/run/${jobId}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Failed to run job ${jobId}`);
        }
        return await response.json();
    }
};
