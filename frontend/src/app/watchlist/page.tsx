'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    ErrorDisplay,
    PageHeaderSkeleton,
    WatchlistGridSkeleton,
    CardSkeleton
} from '@/components/shared';
import { watchlistApi, type WatchlistItemWithAnalysis } from '@/services/api';
import { bandarmologyApi } from '@/services/api/bandarmology';
import { useFilter } from '@/context/filter-context';
import {
    Star,
    Trash2,
    TrendingUp,
    TrendingDown,
    Plus,
    Search,
    Target,
    Activity,
    Zap,
    AlertTriangle,
    CheckCircle2,
    XCircle,
    BarChart3,
    Copy,
    Download,
    FileText,
    ChevronRight,
    Wallet,
    LineChart,
    Gauge,
    ShieldAlert,
    Sparkles,
    ArrowUpRight,
    ArrowDownRight,
    RefreshCw,
    BrainCircuit
} from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function WatchlistPage() {
    const [watchlist, setWatchlist] = useState<WatchlistItemWithAnalysis[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [newTicker, setNewTicker] = useState('');
    const [adding, setAdding] = useState(false);
    const [selectedItem, setSelectedItem] = useState<WatchlistItemWithAnalysis | null>(null);
    const [copied, setCopied] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [analyzingTicker, setAnalyzingTicker] = useState<string | null>(null);
    const [analysisStatus, setAnalysisStatus] = useState<{
        running: boolean;
        progress: number;
        total: number;
        current_ticker: string;
        stage: string;
    } | null>(null);
    const { setTicker } = useFilter();

    const fetchWatchlist = useCallback(async () => {
        try {
            setLoading(true);
            const data = await watchlistApi.getWatchlistWithAnalysis();
            setWatchlist(data);
            setError(null);
        } catch (err) {
            setError('Failed to load watchlist');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchWatchlist();
    }, [fetchWatchlist]);

    // Poll for analysis status when analyzing
    useEffect(() => {
        if (!analyzing) return;

        const interval = setInterval(async () => {
            try {
                // Check bandarmology deep-status (primary) and watchlist analyze-status (fallback)
                const [bandResult, wlResult] = await Promise.allSettled([
                    bandarmologyApi.getDeepStatus(),
                    watchlistApi.getAnalysisStatus(),
                ]);

                const band = bandResult.status === 'fulfilled' ? bandResult.value : null;
                const wl = wlResult.status === 'fulfilled' ? wlResult.value : null;

                // Prefer whichever is actively running
                if (band?.running) {
                    setAnalysisStatus(prev => ({
                        running: band.running,
                        progress: band.progress,
                        total: band.total,
                        current_ticker: band.current_ticker,
                        stage: prev?.stage || 'bandarmology',
                    }));
                } else if (wl?.running) {
                    setAnalysisStatus(wl);
                } else if (wl) {
                    setAnalysisStatus(wl);
                }

                const isRunning = band?.running || wl?.running;
                if (!isRunning) {
                    setAnalyzing(false);
                    setAnalyzingTicker(null);
                    fetchWatchlist();
                }
            } catch (err) {
                console.error('Failed to fetch analysis status:', err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [analyzing, fetchWatchlist]);

    const handleDeepAnalyze = async (tickers: string[]) => {
        if (analyzing) return;
        try {
            setAnalyzing(true);
            if (tickers.length === 1) setAnalyzingTicker(tickers[0]);
            setAnalysisStatus({
                running: true,
                progress: 0,
                total: tickers.length * 2,
                current_ticker: tickers[0] || '',
                stage: 'starting',
            });
            // Use bandarmology deep-analyze-tickers (correct endpoint with full pipeline)
            await bandarmologyApi.triggerDeepAnalysisTickers(tickers.join(','));
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            // 409 means already running — still poll
            if (!msg.includes('409') && !msg.includes('already')) {
                setError('Failed to start deep analysis');
                setAnalyzing(false);
                setAnalyzingTicker(null);
            }
        }
    };

    const getTickersMissingData = () => {
        return watchlist
            .filter(item => !item.alpha_hunter?.has_signal && !item.bandarmology?.has_analysis)
            .map(item => item.ticker);
    };

    const handleAddTicker = async () => {
        if (!newTicker.trim()) return;

        try {
            setAdding(true);
            await watchlistApi.addTicker(newTicker.trim().toUpperCase());
            setNewTicker('');
            await fetchWatchlist();
        } catch (err) {
            setError('Failed to add ticker');
        } finally {
            setAdding(false);
        }
    };

    const handleRemoveTicker = async (ticker: string) => {
        try {
            await watchlistApi.removeTicker(ticker);
            await fetchWatchlist();
        } catch (err) {
            setError('Failed to remove ticker');
        }
    };

    const handleViewTicker = (ticker: string) => {
        setTicker(ticker);
    };

    // Helper function to get rating color
    const getRatingColor = (rating?: string) => {
        switch (rating) {
            case 'STRONG_BUY': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
            case 'BUY': return 'bg-green-100 text-green-800 border-green-200';
            case 'HOLD': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'AVOID': return 'bg-red-100 text-red-800 border-red-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    // Helper function to get recommendation icon
    const getRecommendationIcon = (rec?: string) => {
        switch (rec) {
            case 'STRONG_ACCUMULATION':
            case 'ACCUMULATING':
                return <TrendingUp className="w-4 h-4 text-emerald-500" />;
            case 'DISTRIBUTION_RISK':
            case 'CAUTION':
                return <AlertTriangle className="w-4 h-4 text-red-500" />;
            case 'MIXED_SIGNALS':
                return <Activity className="w-4 h-4 text-yellow-500" />;
            default:
                return <BarChart3 className="w-4 h-4 text-gray-400" />;
        }
    };

    // Helper to format signal strength
    const formatSignalStrength = (strength?: string) => {
        switch (strength) {
            case 'VERY_STRONG': return { label: 'Very Strong', color: 'text-emerald-600', bg: 'bg-emerald-50' };
            case 'STRONG': return { label: 'Strong', color: 'text-green-600', bg: 'bg-green-50' };
            case 'MODERATE': return { label: 'Moderate', color: 'text-yellow-600', bg: 'bg-yellow-50' };
            case 'WEAK': return { label: 'Weak', color: 'text-orange-600', bg: 'bg-orange-50' };
            case 'AVOID': return { label: 'Avoid', color: 'text-red-600', bg: 'bg-red-50' };
            default: return { label: 'N/A', color: 'text-gray-400', bg: 'bg-gray-50' };
        }
    };

    // Helper to format phase
    const formatPhase = (phase?: string) => {
        switch (phase) {
            case 'ACCUMULATION':
            case 'EARLY_ACCUM':
                return { label: 'Accumulating', color: 'text-emerald-600', bg: 'bg-emerald-50' };
            case 'DISTRIBUTION':
                return { label: 'Distributing', color: 'text-red-600', bg: 'bg-red-50' };
            case 'MARKUP':
                return { label: 'Markup', color: 'text-blue-600', bg: 'bg-blue-50' };
            case 'MARKDOWN':
                return { label: 'Markdown', color: 'text-orange-600', bg: 'bg-orange-50' };
            default:
                return { label: phase || 'Unknown', color: 'text-gray-500', bg: 'bg-gray-50' };
        }
    };

    // Generate analysis summary text for copy
    const generateAnalysisText = useCallback((item: WatchlistItemWithAnalysis) => {
        const alpha = item.alpha_hunter;
        const bandar = item.bandarmology;
        const price = item.latest_price;

        let text = `📊 ANALISIS SAHAM ${item.ticker}\n`;
        text += `${'='.repeat(40)}\n\n`;

        if (price) {
            text += `💰 Harga: Rp${price.price.toLocaleString()} (${price.change_percent >= 0 ? '+' : ''}${price.change_percent.toFixed(2)}%)\n`;
            text += `📈 Volume: ${(price.volume / 1000000).toFixed(1)}M\n\n`;
        }

        text += `🎯 RATING: ${item.combined_rating?.replace('_', ' ') || 'N/A'}\n`;
        text += `💡 REKOMENDASI: ${item.recommendation?.replace('_', ' ') || 'N/A'}\n\n`;

        text += `【ALPHA HUNTER SIGNAL】\n`;
        if (alpha.has_signal) {
            text += `• Kekuatan Sinyal: ${alpha.signal_strength} (${alpha.signal_score?.toFixed(0)}/100)\n`;
            text += `• Keyakinan: ${alpha.conviction}\n`;
            text += `• Flow: ${alpha.flow?.toFixed(1) || 'N/A'}\n`;
            text += `• Momentum: ${alpha.momentum_status}\n`;
            if (alpha.patterns.length > 0) {
                text += `• Pola: ${alpha.patterns.join(', ')}\n`;
            }
            if (alpha.warning_status && alpha.warning_status !== 'NONE') {
                text += `⚠️ Peringatan: ${alpha.warning_status}\n`;
            }
        } else {
            text += `• Tidak ada sinyal\n`;
        }
        text += `\n`;

        text += `【BANDARMOLOGY ANALYSIS】\n`;
        if (bandar.has_analysis) {
            text += `• Fase: ${bandar.phase || 'N/A'}\n`;
            text += `• Deep Score: ${bandar.deep_score?.toFixed(0) || 'N/A'}/100\n`;
            text += `• Trade Type: ${bandar.deep_trade_type || 'N/A'}\n`;
            if (bandar.bandar_avg_cost) {
                text += `• Bandar Avg Cost: Rp${bandar.bandar_avg_cost.toLocaleString()}\n`;
            }
            if (bandar.breakout_signal) {
                text += `• Breakout: ${bandar.breakout_signal}\n`;
            }
            if (bandar.distribution_alert) {
                text += `⚠️ Alert: ${bandar.distribution_alert}\n`;
            }
        } else {
            text += `• Tidak ada data analisis\n`;
        }

        text += `\n${'='.repeat(40)}\n`;
        text += `Generated by MarketPulse\n`;
        text += `Analisis ini hanya untuk referensi, bukan saran investasi.`;

        return text;
    }, []);

    // Copy analysis to clipboard
    const handleCopyAnalysis = useCallback(() => {
        if (!selectedItem) return;
        const text = generateAnalysisText(selectedItem);
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }, [selectedItem, generateAnalysisText]);

    // Download PDF summary
    const handleDownloadPDF = useCallback(() => {
        if (!selectedItem) return;

        const text = generateAnalysisText(selectedItem);
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Analysis_${selectedItem.ticker}_${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }, [selectedItem, generateAnalysisText]);

    // Calculate value estimate
    const calculateValue = (item: WatchlistItemWithAnalysis) => {
        const price = item.latest_price?.price;
        const bandarCost = item.bandarmology.bandar_avg_cost;

        if (!price || !bandarCost) return null;

        const upside = ((bandarCost - price) / price) * 100;
        return {
            current: price,
            intrinsic: bandarCost,
            upside: upside,
            verdict: upside > 10 ? 'UNDERVALUED' : upside > -5 ? 'FAIR' : 'OVERVALUED'
        };
    };

    if (loading) {
        return (
            <div className="p-4 sm:p-6 space-y-6">
                <PageHeaderSkeleton />
                <CardSkeleton />
                <WatchlistGridSkeleton count={6} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 sm:p-6 space-y-6">
                <div className="flex items-center gap-2 mb-6">
                    <Star className="w-6 h-6 text-yellow-500" />
                    <h1 className="text-2xl font-bold">My Watchlist</h1>
                </div>
                <ErrorDisplay message={error} onRetry={fetchWatchlist} />
            </div>
        );
    }

    const missingTickers = getTickersMissingData();
    const progressPct = analysisStatus && analysisStatus.total > 0
        ? Math.round((analysisStatus.progress / analysisStatus.total) * 100)
        : 0;

    return (
        <div className="p-4 sm:p-6">
            {/* Header */}
            <div className="mb-4 sm:mb-6">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2 min-w-0">
                        <Star className="w-5 h-5 sm:w-6 sm:h-6 text-yellow-500 flex-shrink-0" />
                        <h1 className="text-xl sm:text-2xl font-bold truncate">My Watchlist</h1>
                        <Badge variant="secondary" className="flex-shrink-0 text-xs">
                            {watchlist.length}
                        </Badge>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={fetchWatchlist}
                        disabled={loading}
                        className="flex-shrink-0 h-8 w-8 p-0"
                        title="Refresh"
                    >
                        <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
                    </Button>
                </div>
                {/* Action buttons */}
                <div className="flex flex-wrap gap-2">
                    {missingTickers.length > 0 && !analyzing && (
                        <Button
                            onClick={() => handleDeepAnalyze(missingTickers)}
                            size="sm"
                            className="bg-purple-600 hover:bg-purple-700 gap-1.5 h-8 text-xs"
                        >
                            <BrainCircuit className="w-3.5 h-3.5" />
                            Deep Analyze {missingTickers.length} Missing
                        </Button>
                    )}
                    {!analyzing && watchlist.length > 0 && (
                        <Button
                            onClick={() => handleDeepAnalyze(watchlist.map(i => i.ticker))}
                            size="sm"
                            variant="outline"
                            className="gap-1.5 h-8 text-xs border-purple-300 text-purple-700 hover:bg-purple-50"
                        >
                            <BrainCircuit className="w-3.5 h-3.5" />
                            Deep Analyze All
                        </Button>
                    )}
                    {analyzing && (
                        <Button disabled size="sm" className="gap-1.5 h-8 text-xs">
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            {analysisStatus?.current_ticker
                                ? `Analyzing ${analysisStatus.current_ticker}...`
                                : `Analyzing... ${progressPct}%`}
                        </Button>
                    )}
                </div>
            </div>

            {/* Analysis Progress Banner */}
            {analyzing && analysisStatus && (
                <Card className="p-3 sm:p-4 mb-4 sm:mb-6 bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800">
                    <div className="flex items-start gap-3">
                        <RefreshCw className="w-4 h-4 text-purple-600 animate-spin flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-purple-900 dark:text-purple-100">
                                Deep Analysis in Progress
                            </p>
                            <p className="text-xs text-purple-700 dark:text-purple-300 truncate mt-0.5">
                                {analysisStatus.stage === 'neobdm' && `Base analysis: ${analysisStatus.current_ticker}`}
                                {analysisStatus.stage === 'bandarmology' && `Deep: ${analysisStatus.current_ticker}`}
                                {analysisStatus.stage === 'completed' && '✓ Analysis complete!'}
                                {analysisStatus.stage === 'starting' && 'Initializing...'}
                                {!['neobdm','bandarmology','completed','starting'].includes(analysisStatus.stage) && (analysisStatus.current_ticker || 'Processing...')}
                            </p>
                            <div className="mt-2 h-1.5 bg-purple-200 dark:bg-purple-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-purple-600 transition-all duration-500 rounded-full"
                                    style={{ width: `${progressPct}%` }}
                                />
                            </div>
                            <p className="text-xs text-purple-500 mt-1">
                                {analysisStatus.progress}/{analysisStatus.total} ({progressPct}%)
                            </p>
                        </div>
                    </div>
                </Card>
            )}

            {/* Add Ticker */}
            <Card className="p-3 sm:p-4 mb-4 sm:mb-6">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <Input
                            placeholder="Ticker (e.g., BBCA)"
                            value={newTicker}
                            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddTicker()}
                            className="pl-10 h-9 text-sm"
                        />
                    </div>
                    <Button
                        onClick={handleAddTicker}
                        disabled={adding || !newTicker.trim()}
                        className="bg-blue-600 hover:bg-blue-700 h-9 px-3 sm:px-4 flex-shrink-0"
                        size="sm"
                    >
                        <Plus className="w-4 h-4 sm:mr-1.5" />
                        <span className="hidden sm:inline text-sm">Add</span>
                    </Button>
                </div>
            </Card>

            {/* Watchlist Grid */}
            {watchlist.length === 0 ? (
                <Card className="p-8 text-center">
                    <Star className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium mb-2">Your watchlist is empty</h3>
                    <p className="text-gray-500 text-sm">
                        Add tickers to track your favorite stocks with Alpha Hunter and Bandarmology analysis.
                    </p>
                </Card>
            ) : (
                <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                    {watchlist.map((item) => {
                        const alpha = item.alpha_hunter;
                        const bandar = item.bandarmology;
                        const signalInfo = formatSignalStrength(alpha.signal_strength);
                        const phaseInfo = formatPhase(bandar.phase);
                        const valueInfo = calculateValue(item);
                        const isThisAnalyzing = analyzing && (
                            analyzingTicker === item.ticker ||
                            analysisStatus?.current_ticker === item.ticker
                        );

                        return (
                            <Card
                                key={item.ticker}
                                className="p-3 sm:p-4 hover:shadow-lg transition-all cursor-pointer group"
                                onClick={() => setSelectedItem(item)}
                            >
                                {/* Card Header */}
                                <div className="flex items-start justify-between mb-3">
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-1.5">
                                            <h3 className="text-lg sm:text-xl font-bold group-hover:text-blue-600 transition-colors truncate">
                                                {item.ticker}
                                            </h3>
                                            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-400 flex-shrink-0" />
                                        </div>
                                        <p className="text-xs text-gray-500 truncate">
                                            {item.company_name || item.ticker}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                                        {item.combined_rating && (
                                            <Badge className={cn('border text-xs px-1.5 py-0', getRatingColor(item.combined_rating))}>
                                                {item.combined_rating.replace('_', ' ')}
                                            </Badge>
                                        )}
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={(e) => { e.stopPropagation(); handleRemoveTicker(item.ticker); }}
                                            className="h-7 w-7 p-0 text-red-400 hover:text-red-600 hover:bg-red-50"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </Button>
                                    </div>
                                </div>

                                {/* Price Info */}
                                {item.latest_price ? (
                                    <div className="mb-3">
                                        <div className="flex items-baseline gap-2 flex-wrap">
                                            <span className="text-xl sm:text-2xl font-bold">
                                                Rp{item.latest_price.price.toLocaleString()}
                                            </span>
                                            <Badge
                                                variant={item.latest_price.change_percent >= 0 ? 'default' : 'destructive'}
                                                className={cn(
                                                    'text-xs flex items-center gap-0.5',
                                                    item.latest_price.change_percent >= 0 ? 'bg-green-100 text-green-800 border-green-200' : ''
                                                )}
                                            >
                                                {item.latest_price.change_percent >= 0
                                                    ? <TrendingUp className="w-3 h-3" />
                                                    : <TrendingDown className="w-3 h-3" />}
                                                {item.latest_price.change_percent >= 0 ? '+' : ''}
                                                {item.latest_price.change_percent.toFixed(2)}%
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-gray-400 mt-0.5">
                                            Vol: {(item.latest_price.volume / 1_000_000).toFixed(1)}M · {item.latest_price.date}
                                        </p>
                                    </div>
                                ) : (
                                    <p className="text-xs text-gray-400 mb-3">No price data</p>
                                )}

                                {/* Value Assessment */}
                                {valueInfo && (
                                    <div className={cn(
                                        'p-2 rounded-lg mb-3 text-xs',
                                        valueInfo.verdict === 'UNDERVALUED' ? 'bg-emerald-50 border border-emerald-200' :
                                        valueInfo.verdict === 'OVERVALUED' ? 'bg-red-50 border border-red-200' :
                                        'bg-gray-50 border border-gray-200'
                                    )}>
                                        <div className="flex items-center justify-between">
                                            <span className="text-gray-500">Value:</span>
                                            <span className={cn(
                                                'font-semibold',
                                                valueInfo.verdict === 'UNDERVALUED' ? 'text-emerald-700' :
                                                valueInfo.verdict === 'OVERVALUED' ? 'text-red-700' : 'text-gray-700'
                                            )}>
                                                {valueInfo.verdict}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between mt-0.5">
                                            <span className="text-gray-400">Rp{valueInfo.intrinsic.toLocaleString()}</span>
                                            <span className={valueInfo.upside >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                                                {valueInfo.upside >= 0 ? '+' : ''}{valueInfo.upside.toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                )}

                                {/* Analysis Summary */}
                                <div className="space-y-1.5 mb-3 p-2.5 bg-gray-50 dark:bg-gray-800/50 rounded-lg min-h-[60px]">
                                    {(alpha.has_signal || bandar.has_analysis) ? (
                                        <>
                                            {item.recommendation && (
                                                <div className="flex items-center gap-1.5 text-xs font-medium">
                                                    {getRecommendationIcon(item.recommendation)}
                                                    <span className={cn(
                                                        item.recommendation.includes('ACCUM') ? 'text-emerald-700' :
                                                        item.recommendation.includes('RISK') ? 'text-red-700' : 'text-yellow-700'
                                                    )}>
                                                        {item.recommendation.replace(/_/g, ' ')}
                                                    </span>
                                                </div>
                                            )}
                                            {alpha.has_signal && (
                                                <div className="flex items-center justify-between text-xs">
                                                    <span className="flex items-center gap-1 text-gray-500">
                                                        <Zap className="w-3 h-3 text-yellow-500" />Signal
                                                    </span>
                                                    <span className={cn('font-medium', signalInfo.color)}>
                                                        {signalInfo.label}
                                                        {alpha.signal_score && <span className="text-gray-400 font-normal ml-1">({alpha.signal_score.toFixed(0)})</span>}
                                                    </span>
                                                </div>
                                            )}
                                            {bandar.phase && (
                                                <div className="flex items-center justify-between text-xs">
                                                    <span className="flex items-center gap-1 text-gray-500">
                                                        <Target className="w-3 h-3 text-blue-500" />Phase
                                                    </span>
                                                    <span className={cn('font-medium px-1.5 py-0.5 rounded text-xs', phaseInfo.bg, phaseInfo.color)}>
                                                        {phaseInfo.label}
                                                    </span>
                                                </div>
                                            )}
                                            {(alpha.warning_status?.includes('REPO') || bandar.pinky || bandar.distribution_alert) && (
                                                <div className="flex items-center gap-1 text-xs text-red-600">
                                                    <AlertTriangle className="w-3 h-3" /><span>Risk Alert</span>
                                                </div>
                                            )}
                                            {bandar.breakout_signal?.includes('BREAKOUT') && (
                                                <div className="flex items-center gap-1 text-xs text-emerald-600">
                                                    <CheckCircle2 className="w-3 h-3" /><span>Breakout Signal</span>
                                                </div>
                                            )}
                                            {alpha.patterns.length > 0 && (
                                                <div className="flex flex-wrap gap-1 pt-0.5">
                                                    {alpha.patterns.slice(0, 2).map((p: string, i: number) => (
                                                        <span key={i} className="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
                                                            {p.replace(/_/g, ' ')}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </>
                                    ) : (
                                        <div className="flex items-center gap-1.5 text-xs text-gray-400">
                                            <XCircle className="w-3.5 h-3.5" />
                                            <span>No analysis data</span>
                                        </div>
                                    )}
                                </div>

                                {/* Bottom Actions */}
                                <div className="flex gap-1.5 pt-2 border-t" onClick={(e) => e.stopPropagation()}>
                                    <Link href="/dashboard" className="flex-1" onClick={() => handleViewTicker(item.ticker)}>
                                        <Button variant="outline" size="sm" className="w-full h-7 text-xs">
                                            Dashboard
                                        </Button>
                                    </Link>
                                    <Link href="/neobdm-tracker" className="flex-1" onClick={() => handleViewTicker(item.ticker)}>
                                        <Button variant="outline" size="sm" className="w-full h-7 text-xs">
                                            Flow
                                        </Button>
                                    </Link>
                                    {isThisAnalyzing ? (
                                        <Button disabled size="sm" className="flex-1 h-7 text-xs gap-1">
                                            <RefreshCw className="w-3 h-3 animate-spin" />
                                        </Button>
                                    ) : (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1 h-7 text-xs gap-1 text-purple-600 border-purple-200 hover:bg-purple-50"
                                            disabled={analyzing}
                                            onClick={(e) => { e.stopPropagation(); handleDeepAnalyze([item.ticker]); }}
                                        >
                                            <BrainCircuit className="w-3 h-3" />
                                            Deep
                                        </Button>
                                    )}
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Detail Modal */}
            <Dialog open={!!selectedItem} onOpenChange={() => setSelectedItem(null)}>
                {selectedItem && (
                    <DialogContent className="w-full max-w-4xl h-[95vh] sm:h-auto sm:max-h-[90vh] p-0 overflow-hidden flex flex-col">
                        <DialogHeader className="p-4 sm:p-6 pb-3 sm:pb-4 border-b flex-shrink-0">
                            <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0 flex-1">
                                    <DialogTitle className="text-lg sm:text-2xl flex items-center gap-2 flex-wrap">
                                        <span>{selectedItem.ticker}</span>
                                        {selectedItem.combined_rating && (
                                            <Badge className={cn('border text-xs', getRatingColor(selectedItem.combined_rating))}>
                                                {selectedItem.combined_rating.replace('_', ' ')}
                                            </Badge>
                                        )}
                                    </DialogTitle>
                                    <DialogDescription className="mt-0.5 text-xs sm:text-sm truncate">
                                        {selectedItem.company_name || selectedItem.ticker}
                                        {selectedItem.latest_price && (
                                            <span className="ml-1.5">
                                                · Rp{selectedItem.latest_price.price.toLocaleString()}
                                                <span className={selectedItem.latest_price.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}>
                                                    {' '}({selectedItem.latest_price.change_percent >= 0 ? '+' : ''}{selectedItem.latest_price.change_percent.toFixed(2)}%)
                                                </span>
                                            </span>
                                        )}
                                    </DialogDescription>
                                </div>
                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleCopyAnalysis}
                                        className="h-8 gap-1.5 text-xs px-2"
                                    >
                                        {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                                        <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy'}</span>
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleDownloadPDF}
                                        className="h-8 gap-1.5 text-xs px-2"
                                    >
                                        <Download className="w-3.5 h-3.5" />
                                        <span className="hidden sm:inline">Download</span>
                                    </Button>
                                    {/* Deep Analyze in modal */}
                                    {!analyzing ? (
                                        <Button
                                            size="sm"
                                            className="h-8 gap-1.5 text-xs px-2 bg-purple-600 hover:bg-purple-700"
                                            onClick={() => handleDeepAnalyze([selectedItem.ticker])}
                                        >
                                            <BrainCircuit className="w-3.5 h-3.5" />
                                            <span className="hidden sm:inline">Deep</span>
                                        </Button>
                                    ) : (
                                        <Button disabled size="sm" className="h-8 text-xs px-2">
                                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                        </Button>
                                    )}
                                </div>
                            </div>
                        </DialogHeader>

                        <ScrollArea className="flex-1 overflow-auto">
                            <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
                                {/* Combined Summary */}
                                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 p-3 sm:p-4 rounded-xl border border-blue-200 dark:border-blue-800">
                                    <h4 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center gap-2 mb-3 text-sm sm:text-base">
                                        <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
                                        Combined Analysis Summary
                                    </h4>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
                                        <div className="text-center p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg">
                                            <p className="text-xs text-gray-500 mb-0.5">Rating</p>
                                            <p className={cn(
                                                'font-bold text-sm',
                                                selectedItem.combined_rating?.includes('BUY') ? 'text-emerald-600' :
                                                selectedItem.combined_rating?.includes('AVOID') ? 'text-red-600' : 'text-yellow-600'
                                            )}>
                                                {selectedItem.combined_rating?.replace(/_/g, ' ') || 'N/A'}
                                            </p>
                                        </div>
                                        <div className="text-center p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg">
                                            <p className="text-xs text-gray-500 mb-0.5">Rekomendasi</p>
                                            <p className="font-bold text-blue-600 text-xs sm:text-sm leading-tight">
                                                {selectedItem.recommendation?.replace(/_/g, ' ') || 'N/A'}
                                            </p>
                                        </div>
                                        <div className="text-center p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg">
                                            <p className="text-xs text-gray-500 mb-0.5">Alpha Score</p>
                                            <p className="font-bold text-purple-600 text-sm">
                                                {selectedItem.alpha_hunter.signal_score?.toFixed(0) || 'N/A'}
                                            </p>
                                        </div>
                                        <div className="text-center p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg">
                                            <p className="text-xs text-gray-500 mb-0.5">Bandar Score</p>
                                            <p className="font-bold text-indigo-600 text-sm">
                                                {selectedItem.bandarmology.deep_score?.toFixed(0) || 'N/A'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Two Column Layout */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                                    {/* Alpha Hunter Section */}
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2 pb-2 border-b">
                                            <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-500" />
                                            <h3 className="font-semibold text-sm sm:text-base">Alpha Hunter Signals</h3>
                                        </div>

                                        {selectedItem.alpha_hunter.has_signal ? (
                                            <div className="space-y-2">
                                                {[
                                                    { label: 'Signal Strength', icon: <Gauge className="w-3.5 h-3.5" />, value: (
                                                        <Badge className={cn('text-xs', formatSignalStrength(selectedItem.alpha_hunter.signal_strength).bg, formatSignalStrength(selectedItem.alpha_hunter.signal_strength).color)}>
                                                            {selectedItem.alpha_hunter.signal_strength}
                                                        </Badge>
                                                    )},
                                                    { label: 'Score', value: <span className="font-semibold text-sm">{selectedItem.alpha_hunter.signal_score?.toFixed(0)}/100</span> },
                                                    { label: 'Conviction', value: <span className="font-semibold text-sm">{selectedItem.alpha_hunter.conviction}</span> },
                                                    { label: 'Flow', value: (
                                                        <span className={cn('font-semibold text-sm', (selectedItem.alpha_hunter.flow || 0) > 0 ? 'text-emerald-600' : 'text-red-600')}>
                                                            {(selectedItem.alpha_hunter.flow || 0) > 0 ? '+' : ''}{selectedItem.alpha_hunter.flow?.toFixed(1)}
                                                        </span>
                                                    )},
                                                    { label: 'Momentum', value: <span className="font-semibold text-sm">{selectedItem.alpha_hunter.momentum_status}</span> },
                                                    ...(selectedItem.alpha_hunter.entry_zone ? [{ label: 'Entry Zone', value: <span className="font-semibold text-sm text-blue-600">{selectedItem.alpha_hunter.entry_zone}</span> }] : []),
                                                ].map(({ label, icon, value }) => (
                                                    <div key={label} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                                                        <span className="text-gray-500 text-xs flex items-center gap-1.5">{icon}{label}</span>
                                                        {value}
                                                    </div>
                                                ))}

                                                {selectedItem.alpha_hunter.patterns.length > 0 && (
                                                    <div className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                                                        <span className="text-gray-500 text-xs">Patterns:</span>
                                                        <div className="flex flex-wrap gap-1 mt-1">
                                                            {selectedItem.alpha_hunter.patterns.map((p, i) => (
                                                                <Badge key={i} variant="secondary" className="text-xs">{p.replace(/_/g, ' ')}</Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {selectedItem.alpha_hunter.warning_status && selectedItem.alpha_hunter.warning_status !== 'NONE' && (
                                                    <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
                                                        <div className="flex items-center gap-1.5 text-red-700">
                                                            <ShieldAlert className="w-3.5 h-3.5" />
                                                            <span className="font-semibold text-xs">Warning</span>
                                                        </div>
                                                        <p className="text-red-600 text-xs mt-0.5">{selectedItem.alpha_hunter.warning_status}</p>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-center py-6 text-gray-400">
                                                <Zap className="w-10 h-10 mx-auto mb-2 opacity-30" />
                                                <p className="text-sm">No Alpha Hunter signals</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Bandarmology Section */}
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2 pb-2 border-b">
                                            <Target className="w-4 h-4 sm:w-5 sm:h-5 text-blue-500" />
                                            <h3 className="font-semibold text-sm sm:text-base">Bandarmology Analysis</h3>
                                        </div>

                                        {selectedItem.bandarmology.has_analysis ? (
                                            <div className="space-y-2">
                                                {[
                                                    { label: 'Phase', value: (
                                                        <Badge className={cn('text-xs', formatPhase(selectedItem.bandarmology.phase).bg, formatPhase(selectedItem.bandarmology.phase).color)}>
                                                            {formatPhase(selectedItem.bandarmology.phase).label}
                                                        </Badge>
                                                    )},
                                                    { label: 'Deep Score', value: <span className="font-semibold text-sm">{selectedItem.bandarmology.deep_score?.toFixed(0)}/150</span> },
                                                    { label: 'Trade Type', value: <span className="font-semibold text-sm">{selectedItem.bandarmology.deep_trade_type || 'N/A'}</span> },
                                                    ...(selectedItem.bandarmology.bandar_avg_cost ? [{ label: 'Bandar Cost', icon: <Wallet className="w-3.5 h-3.5" />, value: <span className="font-semibold text-sm">Rp{selectedItem.bandarmology.bandar_avg_cost.toLocaleString()}</span> }] : []),
                                                    ...(selectedItem.bandarmology.breakout_signal ? [{ label: 'Breakout', icon: <LineChart className="w-3.5 h-3.5" />, value: (
                                                        <span className={cn('font-semibold text-xs', selectedItem.bandarmology.breakout_signal.includes('BREAKOUT') ? 'text-emerald-600' : 'text-gray-600')}>
                                                            {selectedItem.bandarmology.breakout_signal}
                                                        </span>
                                                    )}] : []),
                                                ].map(({ label, icon, value }) => (
                                                    <div key={label} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                                                        <span className="text-gray-500 text-xs flex items-center gap-1.5">{icon}{label}</span>
                                                        {value}
                                                    </div>
                                                ))}

                                                {selectedItem.bandarmology.distribution_alert && (
                                                    <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
                                                        <div className="flex items-center gap-1.5 text-red-700">
                                                            <AlertTriangle className="w-3.5 h-3.5" />
                                                            <span className="font-semibold text-xs">Distribution Alert</span>
                                                        </div>
                                                        <p className="text-red-600 text-xs mt-0.5">{selectedItem.bandarmology.distribution_alert}</p>
                                                    </div>
                                                )}

                                                <div className="grid grid-cols-3 gap-1.5">
                                                    {[
                                                        { label: 'Pinky', active: selectedItem.bandarmology.pinky, icon: '⚠️', activeClass: 'bg-red-100 text-red-700' },
                                                        { label: 'Crossing', active: selectedItem.bandarmology.crossing, icon: '⚡', activeClass: 'bg-yellow-100 text-yellow-700' },
                                                        { label: 'Unusual', active: selectedItem.bandarmology.unusual, icon: '🔥', activeClass: 'bg-orange-100 text-orange-700' },
                                                    ].map(({ label, active, icon, activeClass }) => (
                                                        <div key={label} className={cn('p-1.5 rounded-lg text-center', active ? activeClass : 'bg-gray-100 dark:bg-gray-800 text-gray-500')}>
                                                            <p className="text-xs font-medium">{label}</p>
                                                            <p className="text-base">{active ? icon : '✓'}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-center py-6 text-gray-400">
                                                <Target className="w-10 h-10 mx-auto mb-2 opacity-30" />
                                                <p className="text-sm">No Bandarmology analysis</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Investment Thesis */}
                                <div className="bg-slate-50 dark:bg-slate-900/50 p-3 sm:p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                                    <h4 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2 mb-2 text-sm sm:text-base">
                                        <FileText className="w-4 h-4 sm:w-5 sm:h-5" />
                                        Investment Thesis
                                    </h4>
                                    <div className="space-y-2 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                                        {selectedItem.recommendation?.includes('ACCUM') && (
                                            <p className="flex items-start gap-2">
                                                <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
                                                <span><strong>Accumulation:</strong> Signals indicate potential accumulation phase with positive flow.</span>
                                            </p>
                                        )}
                                        {selectedItem.recommendation?.includes('RISK') && (
                                            <p className="flex items-start gap-2">
                                                <ArrowDownRight className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                                                <span><strong>Caution:</strong> Distribution signals detected. Consider reducing position.</span>
                                            </p>
                                        )}
                                        {selectedItem.bandarmology.breakout_signal?.includes('BREAKOUT') && (
                                            <p className="flex items-start gap-2">
                                                <Sparkles className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                                                <span><strong>Breakout Potential:</strong> Technical setup suggests possible price breakout.</span>
                                            </p>
                                        )}
                                        {selectedItem.alpha_hunter.warning_status?.includes('REPO') && (
                                            <p className="flex items-start gap-2">
                                                <ShieldAlert className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                                                <span><strong>Repo Risk:</strong> Potential repo selling pressure. Be cautious.</span>
                                            </p>
                                        )}
                                        {selectedItem.recommendation === 'MIXED_SIGNALS' && (
                                            <p className="flex items-start gap-2">
                                                <Activity className="w-3.5 h-3.5 text-yellow-500 mt-0.5 flex-shrink-0" />
                                                <span><strong>Mixed Signals:</strong> Wait for clearer confirmation before entering.</span>
                                            </p>
                                        )}
                                        {!selectedItem.recommendation && (
                                            <p className="text-slate-400 text-xs">No specific thesis available. Run deep analysis for insights.</p>
                                        )}
                                    </div>
                                </div>

                                {/* Footer Actions */}
                                <div className="flex flex-wrap gap-2 pt-3 border-t">
                                    <Link href="/dashboard" className="flex-1 min-w-[80px]" onClick={() => { setSelectedItem(null); handleViewTicker(selectedItem.ticker); }}>
                                        <Button variant="outline" size="sm" className="w-full text-xs h-8">
                                            Dashboard
                                        </Button>
                                    </Link>
                                    <Link href="/alpha-hunter" className="flex-1 min-w-[80px]" onClick={() => { setSelectedItem(null); handleViewTicker(selectedItem.ticker); }}>
                                        <Button variant="outline" size="sm" className="w-full text-xs h-8">
                                            Alpha Hunter
                                        </Button>
                                    </Link>
                                    <Link href="/bandarmology" className="flex-1 min-w-[80px]" onClick={() => { setSelectedItem(null); handleViewTicker(selectedItem.ticker); }}>
                                        <Button size="sm" className="w-full bg-blue-600 hover:bg-blue-700 text-xs h-8">
                                            Bandarmology
                                        </Button>
                                    </Link>
                                </div>
                            </div>
                        </ScrollArea>
                    </DialogContent>
                )}
            </Dialog>
        </div>
    );
}
