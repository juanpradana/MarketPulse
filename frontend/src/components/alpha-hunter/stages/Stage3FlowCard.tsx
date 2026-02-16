"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
    RefreshCw,
    CheckCircle2,
    XCircle,
    AlertCircle,
    Loader2,
    Play,
    Square,
    TrendingUp,
    Shield,
    Users,
    ArrowRightLeft,
    Calendar,
    Database
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAlphaHunter } from "../AlphaHunterContext";
import StageCard from "./StageCard";

interface TradingDateInfo {
    date: string;
    has_data: boolean;
    selected: boolean;
    status: 'pending' | 'scraping' | 'complete' | 'error' | 'skipped';
    error?: string;
    buy_count?: number;
    sell_count?: number;
}

interface Stage3FlowCardProps {
    ticker: string;
}

export default function Stage3FlowCard({ ticker }: Stage3FlowCardProps) {
    const {
        investigations,
        updateStageStatus,
        updateStage3Data,
        canProceedToStage
    } = useAlphaHunter();

    const investigation = investigations[ticker];
    const stage2 = investigation?.stage2;
    const stage3 = investigation?.stage3;
    const [isLoadingDates, setIsLoadingDates] = useState(false);
    const [tradingDates, setTradingDates] = useState<TradingDateInfo[]>([]);
    const [isScraping, setIsScraping] = useState(false);
    const [scrapeLog, setScrapeLog] = useState<string[]>([]);
    const [analysisStep, setAnalysisStep] = useState("");
    const cancelRef = useRef(false);

    if (!investigation) return null;

    const canStart = canProceedToStage(ticker, 3);

    // Fetch trading dates from backend
    const fetchTradingDates = useCallback(async () => {
        setIsLoadingDates(true);
        try {
            const res = await fetch(`http://localhost:8000/api/alpha-hunter/stage3/trading-dates/${ticker}?days=7`);
            if (!res.ok) throw new Error("Failed to fetch trading dates");
            const data = await res.json();

            const dates: TradingDateInfo[] = (data.dates || []).map((d: { date: string; has_data: boolean }) => ({
                date: d.date,
                has_data: d.has_data,
                selected: !d.has_data, // Auto-select dates that need scraping
                status: d.has_data ? 'skipped' : 'pending'
            }));
            setTradingDates(dates);
        } catch (error) {
            console.error("Failed to fetch trading dates:", error);
        } finally {
            setIsLoadingDates(false);
        }
    }, [ticker]);

    // Load dates when Stage 2 completes
    useEffect(() => {
        if (canStart && stage3?.status === 'idle' && tradingDates.length === 0) {
            fetchTradingDates();
        }
    }, [canStart, stage3?.status, tradingDates.length, fetchTradingDates]);

    // Toggle date selection
    const toggleDateSelection = (date: string) => {
        setTradingDates(prev => prev.map(d =>
            d.date === date && !d.has_data ? { ...d, selected: !d.selected } : d
        ));
    };

    // Start real NeoBDM scraping
    const startScraping = async () => {
        const datesToScrape = tradingDates.filter(d => d.selected && !d.has_data);
        if (datesToScrape.length === 0) {
            // No dates to scrape - just run analysis directly
            await runFlowAnalysis();
            return;
        }

        updateStageStatus(ticker, 3, 'loading');
        setIsScraping(true);
        cancelRef.current = false;
        setScrapeLog([`Starting broker summary scraping for ${ticker}...`]);

        // Scrape each date sequentially using the backend API
        const updatedDates = [...tradingDates];

        for (let i = 0; i < updatedDates.length; i++) {
            if (cancelRef.current) break;
            const dateInfo = updatedDates[i];

            if (dateInfo.has_data || !dateInfo.selected) {
                continue; // Skip dates that already have data or aren't selected
            }

            // Mark as scraping
            updatedDates[i] = { ...updatedDates[i], status: 'scraping' };
            setTradingDates([...updatedDates]);
            setScrapeLog(prev => [...prev, `Scraping ${dateInfo.date}...`]);

            try {
                const res = await fetch(
                    `http://localhost:8000/api/neobdm-broker-summary?ticker=${ticker}&trade_date=${dateInfo.date}&scrape=true`
                );

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({ error: "Unknown error" }));
                    throw new Error(errData.error || `HTTP ${res.status}`);
                }

                const result = await res.json();
                const buyCount = (result.buy || []).length;
                const sellCount = (result.sell || []).length;

                updatedDates[i] = {
                    ...updatedDates[i],
                    status: 'complete',
                    has_data: true,
                    buy_count: buyCount,
                    sell_count: sellCount
                };
                setTradingDates([...updatedDates]);
                setScrapeLog(prev => [...prev, `  ✓ ${dateInfo.date}: ${buyCount} buyers, ${sellCount} sellers`]);

            } catch (error: unknown) {
                updatedDates[i] = {
                    ...updatedDates[i],
                    status: 'error',
                    error: error instanceof Error ? error.message : String(error)
                };
                setTradingDates([...updatedDates]);
                setScrapeLog(prev => [...prev, `  ✗ ${dateInfo.date}: ${error.message || error}`]);
            }
        }

        if (cancelRef.current) {
            setIsScraping(false);
            updateStageStatus(ticker, 3, 'idle');
            return;
        }

        // After scraping, run flow analysis
        await runFlowAnalysis();
        setIsScraping(false);
    };

    // Run flow analysis after scraping
    const runFlowAnalysis = async () => {
        setAnalysisStep("Running smart money flow analysis...");
        setScrapeLog(prev => [...prev, "Running flow analysis..."]);

        try {
            const response = await fetch(`http://localhost:8000/api/alpha-hunter/flow/${ticker}?days=7`);
            const data = await response.json();

            if (data.data_available) {
                updateStage3Data(ticker, {
                    ticker,
                    floor_price: data.floor_price_safe?.floor_price || 0,
                    current_price: data.floor_price_safe?.current_price || 0,
                    gap_pct: data.floor_price_safe?.gap_pct || 0,
                    conviction: data.overall_conviction || 'LOW',
                    smart_money_accumulation: data.smart_money_accumulation,
                    retail_capitulation: data.retail_capitulation,
                    smart_vs_retail: data.smart_vs_retail,
                    checks_passed: data.checks_passed || 0,
                    total_checks: data.total_checks || 4,
                    scraped_ranges: [],
                    last_scraped_at: new Date().toISOString()
                });
                setScrapeLog(prev => [...prev, `✓ Analysis complete. Conviction: ${data.overall_conviction}`]);
            } else {
                updateStageStatus(ticker, 3, 'error', 'No broker data available. Try scraping more dates.');
                setScrapeLog(prev => [...prev, "✗ No broker data available for analysis."]);
            }
        } catch (error) {
            updateStageStatus(ticker, 3, 'error', String(error));
            setScrapeLog(prev => [...prev, `✗ Analysis failed: ${error}`]);
        }
        setAnalysisStep("");
    };

    // Cancel scraping
    const cancelScraping = () => {
        cancelRef.current = true;
        setIsScraping(false);
        updateStageStatus(ticker, 3, 'idle');
    };

    // Count stats
    const selectedCount = tradingDates.filter(d => d.selected && !d.has_data).length;
    const alreadyScrapedCount = tradingDates.filter(d => d.has_data).length;
    const completedCount = tradingDates.filter(d => d.status === 'complete').length;
    const totalToScrape = tradingDates.filter(d => d.selected && d.status !== 'skipped').length;

    // Render content based on status
    const renderContent = () => {
        // IDLE state - show trading dates for scraping
        if (stage3.status === 'idle') {
            return (
                <div className="space-y-6">
                    {/* Info banner */}
                    <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <h4 className="text-sm font-semibold text-slate-400 uppercase mb-3">
                            📊 Broker Flow Data Collection
                        </h4>
                        <p className="text-xs text-slate-500 mb-3">
                            Scrape broker summary data from NeoBDM for recent trading dates to analyze smart money flow patterns.
                        </p>
                        <div className="grid grid-cols-3 gap-4">
                            <div>
                                <div className="text-xs text-slate-500">Total Dates</div>
                                <div className="text-lg font-bold text-white">{tradingDates.length}</div>
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Already in DB</div>
                                <div className="text-lg font-bold text-emerald-400">{alreadyScrapedCount}</div>
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Need Scraping</div>
                                <div className="text-lg font-bold text-amber-400">{selectedCount}</div>
                            </div>
                        </div>
                    </div>

                    {/* Date selection */}
                    {isLoadingDates ? (
                        <div className="text-center py-8">
                            <Loader2 className="w-8 h-8 mx-auto animate-spin text-slate-500" />
                            <p className="text-slate-500 mt-2">Fetching trading dates...</p>
                        </div>
                    ) : tradingDates.length === 0 ? (
                        <div className="text-center py-8">
                            <AlertCircle className="w-8 h-8 mx-auto text-amber-400 mb-2" />
                            <p className="text-slate-400">No trading dates found.</p>
                            <Button onClick={fetchTradingDates} variant="outline" size="sm" className="mt-2">
                                <RefreshCw className="w-3 h-3 mr-1" /> Retry
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <div className="text-sm text-slate-400 mb-3">
                                Select dates to scrape broker summary:
                            </div>

                            {tradingDates.map((dateInfo) => (
                                <div
                                    key={dateInfo.date}
                                    className={cn(
                                        "flex items-center gap-4 p-3 rounded-lg border transition-all",
                                        dateInfo.has_data
                                            ? "bg-emerald-950/10 border-emerald-500/20 opacity-70"
                                            : dateInfo.selected
                                                ? "bg-slate-800/50 border-emerald-500/30 cursor-pointer"
                                                : "bg-slate-950/30 border-slate-800 hover:border-slate-700 cursor-pointer"
                                    )}
                                    onClick={() => !dateInfo.has_data && toggleDateSelection(dateInfo.date)}
                                >
                                    <Checkbox
                                        checked={dateInfo.has_data || dateInfo.selected}
                                        disabled={dateInfo.has_data}
                                        className="data-[state=checked]:bg-emerald-500"
                                    />

                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <Calendar className="w-3.5 h-3.5 text-slate-500" />
                                            <span className="font-medium text-slate-200 font-mono">
                                                {dateInfo.date}
                                            </span>
                                        </div>
                                    </div>

                                    {dateInfo.has_data ? (
                                        <Badge variant="outline" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">
                                            <Database className="w-3 h-3 mr-1" /> In DB
                                        </Badge>
                                    ) : (
                                        <Badge variant="outline" className="bg-amber-500/20 text-amber-400 border-amber-500/50">
                                            Need Scrape
                                        </Badge>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Action bar */}
                    <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="text-sm text-slate-400">
                                    {selectedCount > 0 ? (
                                        <>To scrape: <span className="text-white font-bold">{selectedCount}</span> dates (~{selectedCount * 2} min)</>
                                    ) : alreadyScrapedCount > 0 ? (
                                        <span className="text-emerald-400">All dates already have data</span>
                                    ) : (
                                        <span>Select dates to scrape</span>
                                    )}
                                </div>
                            </div>

                            <Button
                                onClick={startScraping}
                                disabled={tradingDates.length === 0}
                                className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500"
                            >
                                <Play className="w-4 h-4 mr-2" />
                                {selectedCount > 0 ? "Scrape & Analyze" : "Run Analysis"}
                            </Button>
                        </div>
                    </div>

                    {/* Warning */}
                    <div className="flex items-start gap-2 text-xs text-amber-400/70">
                        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                        <div>
                            Each date takes ~1-2 minutes to scrape from NeoBDM. Dates already in the database will be skipped.
                        </div>
                    </div>
                </div>
            );
        }

        // LOADING state - show scraping progress
        if (stage3.status === 'loading') {
            const scrapingDates = tradingDates.filter(d => !d.has_data || d.status !== 'skipped');
            const completed = tradingDates.filter(d => d.status === 'complete').length;
            const total = tradingDates.filter(d => d.selected && d.status !== 'skipped').length;
            const overallProgress = total > 0 ? (completed / total) * 100 : 0;
            const currentDate = tradingDates.find(d => d.status === 'scraping');

            return (
                <div className="space-y-6">
                    {/* Overall progress */}
                    <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-slate-400">Scraping Progress</span>
                            <span className="text-white font-bold">{completed}/{total} dates</span>
                        </div>
                        <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all"
                                style={{ width: `${overallProgress}%` }}
                            />
                        </div>
                    </div>

                    {/* Date queue */}
                    <div className="space-y-2">
                        {tradingDates.map((dateInfo) => (
                            <div
                                key={dateInfo.date}
                                className={cn(
                                    "flex items-center gap-4 p-3 rounded-lg border transition-all",
                                    dateInfo.status === 'complete' && "bg-emerald-950/20 border-emerald-500/30",
                                    dateInfo.status === 'scraping' && "bg-amber-950/20 border-amber-500/30",
                                    dateInfo.status === 'pending' && "bg-slate-950/30 border-slate-800",
                                    dateInfo.status === 'error' && "bg-red-950/20 border-red-500/30",
                                    dateInfo.status === 'skipped' && "bg-slate-950/20 border-slate-800 opacity-50"
                                )}
                            >
                                <div className="w-6 h-6 flex items-center justify-center">
                                    {dateInfo.status === 'complete' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                                    {dateInfo.status === 'scraping' && <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />}
                                    {dateInfo.status === 'pending' && <div className="w-2 h-2 rounded-full bg-slate-600" />}
                                    {dateInfo.status === 'error' && <XCircle className="w-5 h-5 text-red-400" />}
                                    {dateInfo.status === 'skipped' && <CheckCircle2 className="w-5 h-5 text-slate-500" />}
                                </div>

                                <div className="flex-1">
                                    <span className="text-sm text-slate-200 font-mono">{dateInfo.date}</span>
                                </div>

                                <div className="text-xs">
                                    {dateInfo.status === 'complete' && (
                                        <span className="text-emerald-400">
                                            {dateInfo.buy_count}B / {dateInfo.sell_count}S
                                        </span>
                                    )}
                                    {dateInfo.status === 'scraping' && (
                                        <span className="text-amber-400">Scraping...</span>
                                    )}
                                    {dateInfo.status === 'pending' && (
                                        <span className="text-slate-500">Waiting...</span>
                                    )}
                                    {dateInfo.status === 'error' && (
                                        <span className="text-red-400" title={dateInfo.error}>Failed</span>
                                    )}
                                    {dateInfo.status === 'skipped' && (
                                        <span className="text-slate-500">Already in DB</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Current operation */}
                    {currentDate && (
                        <div className="bg-slate-950/50 rounded-lg p-4 border border-amber-500/30">
                            <div className="flex items-center gap-3">
                                <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                                <span className="text-slate-300 text-sm">
                                    Scraping broker summary for {currentDate.date} from NeoBDM...
                                </span>
                            </div>
                        </div>
                    )}

                    {analysisStep && (
                        <div className="bg-slate-950/50 rounded-lg p-4 border border-indigo-500/30">
                            <div className="flex items-center gap-3">
                                <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                                <span className="text-slate-300 text-sm">{analysisStep}</span>
                            </div>
                        </div>
                    )}

                    {/* Log */}
                    {scrapeLog.length > 0 && (
                        <div className="bg-slate-950 rounded-lg p-3 border border-slate-800 max-h-32 overflow-y-auto">
                            <div className="text-xs font-mono text-slate-500 space-y-0.5">
                                {scrapeLog.map((log, i) => (
                                    <div key={i}>{log}</div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Cancel button */}
                    <div className="flex items-center justify-center">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={cancelScraping}
                            className="text-red-400 border-red-500/30 hover:bg-red-950/20"
                        >
                            <Square className="w-4 h-4 mr-2" />
                            Cancel
                        </Button>
                    </div>
                </div>
            );
        }

        // ERROR state
        if (stage3.status === 'error') {
            return (
                <div className="text-center py-8">
                    <XCircle className="w-12 h-12 mx-auto text-red-400 mb-4" />
                    <h4 className="text-lg font-semibold text-red-400 mb-2">
                        Analysis Failed
                    </h4>
                    <p className="text-slate-500 text-sm mb-4">
                        {stage3.error || "An error occurred during analysis"}
                    </p>
                    <Button onClick={() => { updateStageStatus(ticker, 3, 'idle'); setTradingDates([]); }} variant="outline">
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Retry
                    </Button>
                </div>
            );
        }

        // READY state - show results
        const data = stage3.data;
        if (!data) return null;

        return (
            <div className="space-y-6">
                {/* Floor price analysis */}
                <div className="bg-slate-950/50 rounded-lg p-4 border border-emerald-500/30">
                    <h4 className="text-sm font-semibold text-slate-400 uppercase mb-4">
                        📊 Floor Price Analysis
                    </h4>
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <div className="text-xs text-slate-500">Calculated Floor</div>
                            <div className="text-2xl font-bold text-emerald-400">
                                Rp {data.floor_price.toLocaleString()}
                            </div>
                        </div>
                        <div>
                            <div className="text-xs text-slate-500">Current Price</div>
                            <div className="text-2xl font-bold text-white">
                                Rp {data.current_price.toLocaleString()}
                            </div>
                        </div>
                        <div>
                            <div className="text-xs text-slate-500">Margin of Safety</div>
                            <div className={cn(
                                "text-2xl font-bold",
                                data.gap_pct >= 5 ? "text-emerald-400" : data.gap_pct >= 0 ? "text-amber-400" : "text-red-400"
                            )}>
                                {data.gap_pct > 0 ? "+" : ""}{data.gap_pct.toFixed(1)}%
                            </div>
                        </div>
                    </div>
                    <div className="mt-4">
                        <Badge
                            variant="outline"
                            className={cn(
                                "text-sm px-3 py-1",
                                data.conviction === 'HIGH' && "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
                                data.conviction === 'MEDIUM' && "bg-amber-500/20 text-amber-400 border-amber-500/50",
                                data.conviction === 'LOW' && "bg-red-500/20 text-red-400 border-red-500/50"
                            )}
                        >
                            Conviction: {data.conviction}
                        </Badge>
                    </div>
                </div>

                {/* Checks grid */}
                <div className="grid grid-cols-2 gap-4">
                    <div className={cn(
                        "p-4 rounded-lg border",
                        data.smart_money_accumulation.passed
                            ? "bg-emerald-950/20 border-emerald-500/30"
                            : "bg-slate-950/50 border-slate-800"
                    )}>
                        <div className="flex items-center gap-2 mb-2">
                            <Users className={cn(
                                "w-4 h-4",
                                data.smart_money_accumulation.passed ? "text-emerald-400" : "text-slate-500"
                            )} />
                            <span className="text-sm font-semibold text-slate-300">Smart Money Accumulation</span>
                        </div>
                        <div className="text-xs text-slate-500">
                            Net {data.smart_money_accumulation.net_lot?.toLocaleString() || 0} lot
                            in {data.smart_money_accumulation.active_days || 0}/{data.smart_money_accumulation.total_days || 0} days
                        </div>
                    </div>

                    <div className={cn(
                        "p-4 rounded-lg border",
                        data.retail_capitulation.passed
                            ? "bg-emerald-950/20 border-emerald-500/30"
                            : "bg-slate-950/50 border-slate-800"
                    )}>
                        <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className={cn(
                                "w-4 h-4",
                                data.retail_capitulation.passed ? "text-emerald-400" : "text-slate-500"
                            )} />
                            <span className="text-sm font-semibold text-slate-300">Retail Capitulation</span>
                        </div>
                        <div className="text-xs text-slate-500">
                            Net {data.retail_capitulation.net_lot?.toLocaleString() || 0} lot
                        </div>
                    </div>

                    <div className={cn(
                        "p-4 rounded-lg border",
                        data.smart_vs_retail.passed
                            ? "bg-emerald-950/20 border-emerald-500/30"
                            : "bg-slate-950/50 border-slate-800"
                    )}>
                        <div className="flex items-center gap-2 mb-2">
                            <ArrowRightLeft className={cn(
                                "w-4 h-4",
                                data.smart_vs_retail.passed ? "text-emerald-400" : "text-slate-500"
                            )} />
                            <span className="text-sm font-semibold text-slate-300">Smart vs Retail</span>
                        </div>
                        <div className="text-xs text-slate-500">
                            Dominance: {data.smart_vs_retail.dominance_pct?.toFixed(1) || 0}%
                        </div>
                    </div>

                    <div className="p-4 rounded-lg border bg-slate-950/50 border-slate-800">
                        <div className="flex items-center gap-2 mb-2">
                            <Shield className="w-4 h-4 text-slate-400" />
                            <span className="text-sm font-semibold text-slate-300">Checks Passed</span>
                        </div>
                        <div className="text-xl font-bold text-white">
                            {data.checks_passed}/{data.total_checks}
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => { updateStageStatus(ticker, 3, 'idle'); setTradingDates([]); }}
                        >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Re-scrape
                        </Button>
                    </div>

                    <Button
                        className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500"
                    >
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Proceed to Stage 4 (Optional) →
                    </Button>
                </div>

                {/* Metadata */}
                <div className="text-xs text-slate-600 text-right">
                    Last updated: {new Date(data.last_scraped_at).toLocaleString()}
                </div>
            </div>
        );
    };

    return (
        <StageCard
            stageNumber={3}
            title="Smart Money Flow"
            description="Analyzing broker flow patterns and calculating floor price"
            status={stage3.status}
        >
            {renderContent()}
        </StageCard>
    );
}
