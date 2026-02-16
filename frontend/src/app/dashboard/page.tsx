'use client';

import React, { useEffect, useState } from 'react';
import { SentimentChart } from '@/components/dashboard/sentiment-chart';
import { TickerCloud } from '@/components/dashboard/ticker-cloud';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Users, Newspaper, Zap, Calendar as CalendarIcon, Search, HelpCircle } from 'lucide-react';
import { api } from '@/services/api';
import { useFilter } from '@/context/filter-context';
import { Line, LineChart, ResponsiveContainer } from 'recharts';
import { DashboardStatsSkeleton, ChartSkeleton, PageSkeleton } from '@/components/shared';

export default function DashboardPage() {
    const { ticker: globalTicker, dateRange } = useFilter();
    const [refreshing, setRefreshing] = useState(false);

    // Fallback for dashboard: if 'All' is selected, defaulting to IHSG (^JKSE) might be better for general market view,
    // or we could show an aggregate. For now let's default to ^JKSE if All.
    const ticker = globalTicker === 'All' ? '^JKSE' : globalTicker;

    const [metrics, setMetrics] = useState({
        price: 0,
        price_delta: 0,
        mood_score: 0,
        mood_label: 'Netral 😐',
        correlation: 0,
        volume: 0,
        trends: {
            price: [] as number[],
            mood: [] as number[],
            correlation: [] as number[],
            volume: [] as number[]
        }
    });
    const [hasData, setHasData] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    const fetchMetrics = async () => {
        setIsLoading(true);
        try {
            const stats = await api.getDashboardStats(ticker, dateRange.start, dateRange.end);
            // Check if we have meaningful data
            const hasPriceData = (stats.price ?? stats.current_price ?? 0) > 0;
            const hasNewsData = (stats.volume ?? stats.news_volume ?? 0) > 0;
            setHasData(hasPriceData || hasNewsData);

            // Map API response to local state structure
            setMetrics({
                price: stats.price ?? stats.current_price ?? 0,
                price_delta: stats.price_delta ?? stats.price_change ?? 0,
                mood_score: stats.mood_score || 0,
                mood_label: stats.mood_label ?? stats.market_mood ?? 'Netral 😐',
                correlation: stats.correlation || 0,
                volume: stats.volume ?? stats.news_volume ?? 0,
                trends: stats.trends || {
                    price: [],
                    mood: [],
                    correlation: [],
                    volume: []
                }
            });
        } catch (error) {
            console.error("Failed to fetch metrics:", error);
            setHasData(false);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        // Only fetch metrics on load - no auto-scraping
        // Scraping is now triggered manually via "Refresh Intelligence" button
        fetchMetrics();
    }, [ticker, dateRange.start, dateRange.end]);

    const [refreshKey, setRefreshKey] = useState(Date.now());

    const handleRefresh = async () => {
        if (refreshing) return;
        setRefreshing(true);
        try {
            // Scrape ALL news sources (except IDX) in parallel
            const sources = [
                "CNBC Indonesia",
                "EmitenNews",
                "Bisnis.com",
                "Investor.id",
                "Bloomberg Technoz"
            ];

            console.log("[Refresh] Triggering scrape for all sources:", sources.join(", "));

            await Promise.all(
                sources.map(source =>
                    api.runScraper(source, dateRange.start, dateRange.end)
                        .catch(err => console.warn(`[Refresh] ${source} failed:`, err))
                )
            );

            // Refresh metrics
            await fetchMetrics();

            // Note: Since we want the chart to also refresh, and it depends on ticker/date,
            // we could either rely on its internal useEffect OR force a reload if needed.
            // For a seamless "Auto" feel, let's just re-fetch the metrics.
            // If the user wants the CHART to also immediately show new candles,
            // we'll use a small trick: update a 'lastUpdate' timestamp to force re-renders.
            setRefreshKey(Date.now()); // Trigger chart update
        } catch (error) {
            console.error("Refresh failed:", error);
        } finally {
            setRefreshing(false);
        }
    };

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                    <div className="flex flex-col space-y-2">
                        <div className="h-8 w-64 bg-zinc-800 rounded animate-pulse" />
                        <div className="h-4 w-96 bg-zinc-800 rounded animate-pulse" />
                    </div>
                    <div className="h-10 w-40 bg-zinc-800 rounded animate-pulse" />
                </div>
                <DashboardStatsSkeleton />
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 lg:gap-6">
                    <div className="xl:col-span-2">
                        <ChartSkeleton height="400px" />
                    </div>
                    <div className="xl:col-span-1">
                        <ChartSkeleton height="400px" showLegend={false} />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6 lg:gap-8">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                <div className="flex flex-col">
                    <h1 className="text-2xl sm:text-3xl font-bold text-zinc-100 italic tracking-tight">Market Intelligence Dashboard</h1>
                    <p className="text-zinc-500 mt-1 text-sm sm:text-base">Real-time sentiment-price correlation and AI insights.</p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:opacity-50 text-white rounded-lg font-bold text-sm transition-all shadow-lg active:scale-95 shadow-blue-900/20 w-full sm:w-auto"
                >
                    <Zap className={`w-4 h-4 ${refreshing ? 'animate-pulse' : ''}`} />
                    {refreshing ? 'Refreshing...' : 'Refresh Intelligence'}
                </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                    title="Latest Price"
                    value={hasData && metrics.price > 0 ? metrics.price.toLocaleString() : 'No Data'}
                    delta={hasData && metrics.price > 0 ? `${metrics.price_delta > 0 ? '+' : ''}${metrics.price_delta.toFixed(2)}` : '-'}
                    icon={TrendingUp}
                    trend={metrics.price_delta >= 0 ? 'up' : 'down'}
                    sparklineData={metrics.trends.price}
                    hasData={hasData && metrics.price > 0}
                />
                <MetricCard
                    title="Market Mood"
                    value={hasData && metrics.volume > 0 ? metrics.mood_label : 'No Data'}
                    delta={hasData && metrics.volume > 0 ? `${metrics.mood_score.toFixed(2)} Index` : '-'}
                    icon={Zap}
                    trend={metrics.mood_score >= 0 ? 'up' : 'down'}
                    sparklineData={metrics.trends.mood}
                    hasData={hasData && metrics.volume > 0}
                />
                <MetricCard
                    title="Correlation (Pearson)"
                    value={hasData && metrics.volume > 0 ? `${metrics.correlation.toFixed(2)}` : 'No Data'}
                    delta={hasData && metrics.volume > 0 ? (metrics.correlation > 0.5 ? "Strong Pos" : metrics.correlation < -0.5 ? "Strong Neg" : "Weak") : '-'}
                    icon={Users}
                    trend={metrics.correlation >= 0 ? 'up' : 'down'}
                    sparklineData={metrics.trends.correlation}
                    tooltip="Measuring the linear relationship between stock price and sentiment. 1.0 = Perfect Positive, -1.0 = Perfect Negative."
                    hasData={hasData && metrics.volume > 0}
                />
                <MetricCard
                    title="News Volume"
                    value={hasData && metrics.volume > 0 ? (metrics.volume > 1000 ? `${(metrics.volume / 1000).toFixed(1)}k` : metrics.volume.toString()) : 'No Data'}
                    delta={hasData && metrics.volume > 0 ? "Total News" : '-'}
                    icon={Newspaper}
                    trend="neutral"
                    sparklineData={metrics.trends.volume}
                    hasData={hasData && metrics.volume > 0}
                />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 lg:gap-6">
                <div className="xl:col-span-2 min-h-[300px] lg:min-h-[400px]">
                    <SentimentChart
                        key={refreshKey}
                        ticker={ticker}
                        startDate={dateRange.start}
                        endDate={dateRange.end}
                    />
                </div>
                <div className="xl:col-span-1 min-h-[200px]">
                    <TickerCloud />
                </div>
            </div>
        </div>
    );
}

function MetricCard({ title, value, delta, icon: Icon, trend, sparklineData, tooltip, hasData = true }: { title: string; value: string | number; delta?: string; icon: React.ElementType; trend?: 'up' | 'down' | 'neutral'; sparklineData?: number[]; tooltip?: string; hasData?: boolean }) {
    const chartData = (sparklineData || []).map((val: number, i: number) => ({ val, i }));

    return (
        <Card className={`bg-zinc-950/50 border-zinc-900 backdrop-blur-sm shadow-xl relative overflow-hidden group ${!hasData ? 'opacity-70' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-6">
                <div className="flex items-center gap-1.5">
                    <CardTitle className="text-[10px] sm:text-xs font-semibold text-zinc-500 uppercase tracking-wider">{title}</CardTitle>
                    {tooltip && hasData && (
                        <div className="group/tooltip relative hidden sm:block">
                            <HelpCircle className="w-3 h-3 text-zinc-700 cursor-help" />
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-[10px] text-zinc-400 invisible group-hover/tooltip:visible z-50 shadow-2xl backdrop-blur-md">
                                {tooltip}
                            </div>
                        </div>
                    )}
                </div>
                <Icon className={`h-3 w-3 sm:h-4 sm:w-4 transition-colors ${hasData ? 'text-zinc-600 group-hover:text-zinc-400' : 'text-zinc-700'}`} />
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
                <div className="flex items-end justify-between">
                    <div className="min-w-0 flex-1">
                        <div className={`text-lg sm:text-2xl font-bold truncate ${hasData ? 'text-zinc-100' : 'text-zinc-600'}`}>{value}</div>
                        <div className={`text-[10px] sm:text-xs mt-1 font-medium ${!hasData ? 'text-zinc-600' : trend === 'up' ? 'text-emerald-500' : trend === 'down' ? 'text-rose-500' : 'text-zinc-500'}`}>
                            {delta} {trend !== 'neutral' && hasData && <span className="text-zinc-600 font-normal ml-1 hidden sm:inline">vs prev</span>}
                        </div>
                    </div>
                    {hasData && chartData.length > 0 && (
                        <div className="h-8 sm:h-10 w-16 sm:w-20 mb-1 opacity-50 group-hover:opacity-100 transition-opacity flex-shrink-0">
                            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                                <LineChart data={chartData}>
                                    <Line
                                        type="monotone"
                                        dataKey="val"
                                        stroke={trend === 'up' ? '#10b981' : trend === 'down' ? '#f43f5e' : '#3b82f6'}
                                        strokeWidth={2}
                                        dot={false}
                                        isAnimationActive={true}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
