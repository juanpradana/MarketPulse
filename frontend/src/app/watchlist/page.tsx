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
    X,
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
    const [analysisStatus, setAnalysisStatus] = useState<{
        running: boolean;
        progress: number;
        total: number;
        current_ticker: string;
        stage: string;
    } | null>(null);
    const { setTicker } = useFilter();

    const fetchWatchlist = async () => {
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
    };

    useEffect(() => {
        fetchWatchlist();
    }, []);

    // Poll for analysis status when analyzing
    useEffect(() => {
        if (!analyzing) return;

        const interval = setInterval(async () => {
            try {
                const status = await watchlistApi.getAnalysisStatus();
                setAnalysisStatus(status);

                if (!status.running) {
                    setAnalyzing(false);
                    fetchWatchlist(); // Refresh data after analysis
                }
            } catch (err) {
                console.error('Failed to fetch analysis status:', err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [analyzing]);

    const handleDeepAnalyze = async (tickers: string[]) => {
        try {
            setAnalyzing(true);
            setAnalysisStatus({
                running: true,
                progress: 0,
                total: tickers.length * 2,
                current_ticker: tickers[0],
                stage: 'starting'
            });

            await watchlistApi.analyzeMissing(tickers);
        } catch (err) {
            setError('Failed to start deep analysis');
            setAnalyzing(false);
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
            <div className="p-6 space-y-6">
                <PageHeaderSkeleton />
                <CardSkeleton />
                <WatchlistGridSkeleton count={6} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 space-y-6">
                <div className="flex items-center gap-2 mb-6">
                    <Star className="w-6 h-6 text-yellow-500" />
                    <h1 className="text-2xl font-bold">My Watchlist</h1>
                </div>
                <ErrorDisplay message={error} onRetry={fetchWatchlist} />
            </div>
        );
    }

    const missingTickers = getTickersMissingData();

    return (
        <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Star className="w-6 h-6 text-yellow-500" />
                    <h1 className="text-2xl font-bold">My Watchlist</h1>
                    <Badge variant="secondary" className="ml-2">
                        {watchlist.length} tickers
                    </Badge>
                </div>
                {missingTickers.length > 0 && !analyzing && (
                    <Button
                        onClick={() => handleDeepAnalyze(missingTickers)}
                        className="bg-purple-600 hover:bg-purple-700 gap-2"
                    >
                        <BrainCircuit className="w-4 h-4" />
                        Deep Analyze {missingTickers.length} Missing
                    </Button>
                )}
                {analyzing && (
                    <Button disabled className="gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Analyzing... {analysisStatus?.progress || 0}/{analysisStatus?.total || 0}
                    </Button>
                )}
            </div>

            {/* Analysis Progress */}
            {analyzing && analysisStatus && (
                <Card className="p-4 mb-6 bg-purple-50 border-purple-200">
                    <div className="flex items-center gap-3">
                        <RefreshCw className="w-5 h-5 text-purple-600 animate-spin" />
                        <div className="flex-1">
                            <p className="text-sm font-medium text-purple-900">
                                Deep Analysis in Progress
                            </p>
                            <p className="text-xs text-purple-700">
                                {analysisStatus.stage === 'neobdm' && `Running Alpha Hunter analysis on ${analysisStatus.current_ticker}...`}
                                {analysisStatus.stage === 'bandarmology' && `Running Bandarmology deep analysis on ${analysisStatus.current_ticker}...`}
                                {analysisStatus.stage === 'completed' && 'Analysis complete!'}
                                {analysisStatus.stage === 'starting' && 'Initializing...'}
                            </p>
                        </div>
                        <div className="w-32">
                            <div className="h-2 bg-purple-200 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-purple-600 transition-all duration-300"
                                    style={{ width: `${(analysisStatus!.progress / analysisStatus!.total) * 100}%` }}
                                />
                            </div>
                        </div>
                    </div>
                </Card>
            )}

            {/* Add Ticker */}
            <Card className="p-4 mb-6">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <Input
                            placeholder="Enter ticker (e.g., BBCA, ASII)"
                            value={newTicker}
                            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddTicker()}
                            className="pl-10"
                        />
                    </div>
                    <Button
                        onClick={handleAddTicker}
                        disabled={adding || !newTicker.trim()}
                        className="bg-blue-600 hover:bg-blue-700"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        Add
                    </Button>
                </div>
            </Card>

            {/* Watchlist Grid */}
            {watchlist.length === 0 ? (
                <Card className="p-8 text-center">
                    <Star className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium mb-2">Your watchlist is empty</h3>
                    <p className="text-gray-500 mb-4">
                        Add tickers to track your favorite stocks with Alpha Hunter and Bandarmology analysis.
                    </p>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {watchlist.map((item) => {
                        const alpha = item.alpha_hunter;
                        const bandar = item.bandarmology;
                        const signalInfo = formatSignalStrength(alpha.signal_strength);
                        const phaseInfo = formatPhase(bandar.phase);
                        const valueInfo = calculateValue(item);

                        return (
                            <Card
                                key={item.ticker}
                                className="p-4 hover:shadow-lg transition-all cursor-pointer group"
                                onClick={() => setSelectedItem(item)}
                            >
                                {/* Header */}
                                <div className="flex items-start justify-between mb-3">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-xl font-bold group-hover:text-blue-600 transition-colors">
                                                {item.ticker}
                                            </h3>
                                            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-400" />
                                        </div>
                                        <p className="text-sm text-gray-500 truncate">
                                            {item.company_name || item.ticker}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {item.combined_rating && (
                                            <Badge className={cn("border", getRatingColor(item.combined_rating))}>
                                                {item.combined_rating.replace('_', ' ')}
                                            </Badge>
                                        )}
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleRemoveTicker(item.ticker);
                                            }}
                                            className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>

                                {/* Price Info */}
                                {item.latest_price ? (
                                    <div className="space-y-2 mb-3">
                                        <div className="flex items-baseline gap-2">
                                            <span className="text-2xl font-bold">
                                                Rp{item.latest_price.price.toLocaleString()}
                                            </span>
                                            <Badge
                                                variant={item.latest_price.change_percent >= 0 ? 'default' : 'destructive'}
                                                className={item.latest_price.change_percent >= 0 ? 'bg-green-100 text-green-800' : ''}
                                            >
                                                {item.latest_price.change_percent >= 0 ? (
                                                    <TrendingUp className="w-3 h-3 mr-1" />
                                                ) : (
                                                    <TrendingDown className="w-3 h-3 mr-1" />
                                                )}
                                                {item.latest_price.change_percent >= 0 ? '+' : ''}
                                                {item.latest_price.change_percent.toFixed(2)}%
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-gray-400">
                                            Vol: {(item.latest_price.volume / 1000000).toFixed(1)}M | {item.latest_price.date}
                                        </p>
                                    </div>
                                ) : (
                                    <p className="text-sm text-gray-400 mb-3">No price data available</p>
                                )}

                                {/* Value Assessment */}
                                {valueInfo && (
                                    <div className={cn(
                                        "p-2 rounded-lg mb-3 text-xs",
                                        valueInfo.verdict === 'UNDERVALUED' ? 'bg-emerald-50 border border-emerald-200' :
                                        valueInfo.verdict === 'OVERVALUED' ? 'bg-red-50 border border-red-200' :
                                        'bg-gray-50 border border-gray-200'
                                    )}>
                                        <div className="flex items-center justify-between">
                                            <span className="text-gray-600">Value:</span>
                                            <span className={cn(
                                                "font-semibold",
                                                valueInfo.verdict === 'UNDERVALUED' ? 'text-emerald-700' :
                                                valueInfo.verdict === 'OVERVALUED' ? 'text-red-700' :
                                                'text-gray-700'
                                            )}>
                                                {valueInfo.verdict}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between mt-1">
                                            <span className="text-gray-500">Intrinsic: Rp{valueInfo.intrinsic.toLocaleString()}</span>
                                            <span className={valueInfo.upside >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                                                {valueInfo.upside >= 0 ? '+' : ''}{valueInfo.upside.toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                )}

                                {/* Analysis Summary */}
                                {(alpha.has_signal || bandar.has_analysis) && (
                                    <div className="space-y-2 mb-3 p-3 bg-gray-50 rounded-lg">
                                        {/* Combined Recommendation */}
                                        {item.recommendation && (
                                            <div className="flex items-center gap-2 text-sm font-medium">
                                                {getRecommendationIcon(item.recommendation)}
                                                <span className={cn(
                                                    item.recommendation.includes('ACCUM') ? 'text-emerald-700' :
                                                    item.recommendation.includes('RISK') ? 'text-red-700' :
                                                    'text-yellow-700'
                                                )}>
                                                    {item.recommendation.replace('_', ' ')}
                                                </span>
                                            </div>
                                        )}

                                        {/* Alpha Hunter Signal */}
                                        {alpha.has_signal && (
                                            <div className="flex items-center justify-between text-sm">
                                                <div className="flex items-center gap-1.5">
                                                    <Zap className="w-3.5 h-3.5 text-yellow-500" />
                                                    <span className="text-gray-600">Signal:</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className={cn("font-medium", signalInfo.color)}>
                                                        {signalInfo.label}
                                                    </span>
                                                    {alpha.signal_score && (
                                                        <span className="text-xs text-gray-400">
                                                            ({alpha.signal_score.toFixed(0)})
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Bandarmology Phase */}
                                        {bandar.phase && (
                                            <div className="flex items-center justify-between text-sm">
                                                <div className="flex items-center gap-1.5">
                                                    <Target className="w-3.5 h-3.5 text-blue-500" />
                                                    <span className="text-gray-600">Phase:</span>
                                                </div>
                                                <span className={cn("font-medium px-2 py-0.5 rounded text-xs", phaseInfo.bg, phaseInfo.color)}>
                                                    {phaseInfo.label}
                                                </span>
                                            </div>
                                        )}

                                        {/* Warnings */}
                                        {(alpha.warning_status?.includes('REPO') || bandar.pinky || bandar.distribution_alert) && (
                                            <div className="flex items-center gap-1.5 text-sm text-red-600">
                                                <AlertTriangle className="w-3.5 h-3.5" />
                                                <span>Risk Alert</span>
                                            </div>
                                        )}

                                        {/* Breakout Signal */}
                                        {bandar.breakout_signal && bandar.breakout_signal.includes('BREAKOUT') && (
                                            <div className="flex items-center gap-1.5 text-sm text-emerald-600">
                                                <CheckCircle2 className="w-3.5 h-3.5" />
                                                <span>Breakout Signal</span>
                                            </div>
                                        )}

                                        {/* Pattern Tags */}
                                        {alpha.patterns.length > 0 && (
                                            <div className="flex flex-wrap gap-1 pt-1">
                                                {alpha.patterns.slice(0, 2).map((pattern: string, i: number) => (
                                                    <span key={i} className="text-xs px-2 py-0.5 bg-gray-200 text-gray-700 rounded">
                                                        {pattern.replace('_', ' ')}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* No Analysis Message */}
                                {!alpha.has_signal && !bandar.has_analysis && (
                                    <div className="mb-3 p-3 bg-gray-50 rounded-lg">
                                        <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                                            <XCircle className="w-4 h-4" />
                                            <span>No analysis data available</span>
                                        </div>
                                        {!analyzing && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="w-full gap-2 text-purple-600 border-purple-200 hover:bg-purple-50"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDeepAnalyze([item.ticker]);
                                                }}
                                            >
                                                <BrainCircuit className="w-4 h-4" />
                                                Deep Analyze
                                            </Button>
                                        )}
                                        {analyzing && analysisStatus?.current_ticker === item.ticker && (
                                            <Button
                                                disabled
                                                size="sm"
                                                className="w-full gap-2"
                                            >
                                                <RefreshCw className="w-4 h-4 animate-spin" />
                                                Analyzing...
                                            </Button>
                                        )}
                                    </div>
                                )}

                                {/* Quick Actions */}
                                <div className="flex gap-2 mt-3 pt-3 border-t">
                                    <Link href="/dashboard" className="flex-1" onClick={(e) => e.stopPropagation()}>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full"
                                            onClick={() => handleViewTicker(item.ticker)}
                                        >
                                            Dashboard
                                        </Button>
                                    </Link>
                                    <Link href="/neobdm-tracker" className="flex-1" onClick={(e) => e.stopPropagation()}>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full"
                                            onClick={() => handleViewTicker(item.ticker)}
                                        >
                                            Flow
                                        </Button>
                                    </Link>
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Detail Modal */}
            <Dialog open={!!selectedItem} onOpenChange={() => setSelectedItem(null)}>
                {selectedItem && (
                    <DialogContent className="max-w-4xl max-h-[90vh] p-0 overflow-hidden">
                        <DialogHeader className="p-6 pb-4 border-b">
                            <div className="flex items-start justify-between">
                                <div>
                                    <DialogTitle className="text-2xl flex items-center gap-3">
                                        <span>{selectedItem.ticker}</span>
                                        {selectedItem.combined_rating && (
                                            <Badge className={cn("border", getRatingColor(selectedItem.combined_rating))}>
                                                {selectedItem.combined_rating.replace('_', ' ')}
                                            </Badge>
                                        )}
                                    </DialogTitle>
                                    <DialogDescription className="mt-1">
                                        {selectedItem.company_name || selectedItem.ticker}
                                        {selectedItem.latest_price && (
                                            <span className="ml-2">
                                                • Rp{selectedItem.latest_price.price.toLocaleString()}
                                                <span className={selectedItem.latest_price.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}>
                                                    {' '}({selectedItem.latest_price.change_percent >= 0 ? '+' : ''}{selectedItem.latest_price.change_percent.toFixed(2)}%)
                                                </span>
                                            </span>
                                        )}
                                    </DialogDescription>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleCopyAnalysis}
                                        className="gap-2"
                                    >
                                        {copied ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                                        {copied ? 'Copied!' : 'Copy'}
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleDownloadPDF}
                                        className="gap-2"
                                    >
                                        <Download className="w-4 h-4" />
                                        Download
                                    </Button>
                                </div>
                            </div>
                        </DialogHeader>

                        <ScrollArea className="max-h-[calc(90vh-140px)]">
                            <div className="p-6 space-y-6">
                                {/* Combined Summary */}
                                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-xl border border-blue-200">
                                    <h4 className="font-semibold text-blue-900 flex items-center gap-2 mb-3">
                                        <Sparkles className="w-5 h-5" />
                                        Combined Analysis Summary
                                    </h4>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="text-center p-3 bg-white rounded-lg">
                                            <p className="text-xs text-gray-500 mb-1">Rating</p>
                                            <p className={cn(
                                                "font-bold",
                                                selectedItem.combined_rating?.includes('BUY') ? 'text-emerald-600' :
                                                selectedItem.combined_rating?.includes('AVOID') ? 'text-red-600' :
                                                'text-yellow-600'
                                            )}>
                                                {selectedItem.combined_rating?.replace('_', ' ') || 'N/A'}
                                            </p>
                                        </div>
                                        <div className="text-center p-3 bg-white rounded-lg">
                                            <p className="text-xs text-gray-500 mb-1">Recommendation</p>
                                            <p className="font-bold text-blue-600">
                                                {selectedItem.recommendation?.replace('_', ' ') || 'N/A'}
                                            </p>
                                        </div>
                                        <div className="text-center p-3 bg-white rounded-lg">
                                            <p className="text-xs text-gray-500 mb-1">Alpha Score</p>
                                            <p className="font-bold text-purple-600">
                                                {selectedItem.alpha_hunter.signal_score?.toFixed(0) || 'N/A'}
                                            </p>
                                        </div>
                                        <div className="text-center p-3 bg-white rounded-lg">
                                            <p className="text-xs text-gray-500 mb-1">Bandar Score</p>
                                            <p className="font-bold text-indigo-600">
                                                {selectedItem.bandarmology.deep_score?.toFixed(0) || 'N/A'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Two Column Layout */}
                                <div className="grid md:grid-cols-2 gap-6">
                                    {/* Alpha Hunter Section */}
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 pb-2 border-b">
                                            <Zap className="w-5 h-5 text-yellow-500" />
                                            <h3 className="font-semibold text-lg">Alpha Hunter Signals</h3>
                                        </div>

                                        {selectedItem.alpha_hunter.has_signal ? (
                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600 flex items-center gap-2">
                                                        <Gauge className="w-4 h-4" />
                                                        Signal Strength
                                                    </span>
                                                    <Badge className={cn(
                                                        formatSignalStrength(selectedItem.alpha_hunter.signal_strength).bg,
                                                        formatSignalStrength(selectedItem.alpha_hunter.signal_strength).color
                                                    )}>
                                                        {selectedItem.alpha_hunter.signal_strength}
                                                    </Badge>
                                                </div>

                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Signal Score</span>
                                                    <span className="font-semibold">{selectedItem.alpha_hunter.signal_score?.toFixed(0)}/100</span>
                                                </div>

                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Conviction</span>
                                                    <span className="font-semibold">{selectedItem.alpha_hunter.conviction}</span>
                                                </div>

                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Flow</span>
                                                    <span className={cn(
                                                        "font-semibold",
                                                        (selectedItem.alpha_hunter.flow || 0) > 0 ? 'text-emerald-600' : 'text-red-600'
                                                    )}>
                                                        {(selectedItem.alpha_hunter.flow || 0) > 0 ? '+' : ''}
                                                        {selectedItem.alpha_hunter.flow?.toFixed(1)}
                                                    </span>
                                                </div>

                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Momentum</span>
                                                    <span className="font-semibold">{selectedItem.alpha_hunter.momentum_status}</span>
                                                </div>

                                                {selectedItem.alpha_hunter.entry_zone && (
                                                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                        <span className="text-gray-600">Entry Zone</span>
                                                        <span className="font-semibold text-blue-600">{selectedItem.alpha_hunter.entry_zone}</span>
                                                    </div>
                                                )}

                                                {selectedItem.alpha_hunter.patterns.length > 0 && (
                                                    <div className="p-3 bg-gray-50 rounded-lg">
                                                        <span className="text-gray-600 text-sm">Patterns Detected:</span>
                                                        <div className="flex flex-wrap gap-2 mt-2">
                                                            {selectedItem.alpha_hunter.patterns.map((pattern, i) => (
                                                                <Badge key={i} variant="secondary" className="text-xs">
                                                                    {pattern.replace('_', ' ')}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {selectedItem.alpha_hunter.warning_status && selectedItem.alpha_hunter.warning_status !== 'NONE' && (
                                                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                                                        <div className="flex items-center gap-2 text-red-700">
                                                            <ShieldAlert className="w-4 h-4" />
                                                            <span className="font-semibold text-sm">Warnings</span>
                                                        </div>
                                                        <p className="text-red-600 text-sm mt-1">{selectedItem.alpha_hunter.warning_status}</p>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-center py-8 text-gray-400">
                                                <Zap className="w-12 h-12 mx-auto mb-2 opacity-30" />
                                                <p>No Alpha Hunter signals available</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Bandarmology Section */}
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 pb-2 border-b">
                                            <Target className="w-5 h-5 text-blue-500" />
                                            <h3 className="font-semibold text-lg">Bandarmology Analysis</h3>
                                        </div>

                                        {selectedItem.bandarmology.has_analysis ? (
                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Phase</span>
                                                    <Badge className={cn(
                                                        formatPhase(selectedItem.bandarmology.phase).bg,
                                                        formatPhase(selectedItem.bandarmology.phase).color
                                                    )}>
                                                        {formatPhase(selectedItem.bandarmology.phase).label}
                                                    </Badge>
                                                </div>

                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Deep Score</span>
                                                    <span className="font-semibold">{selectedItem.bandarmology.deep_score?.toFixed(0)}/100</span>
                                                </div>

                                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <span className="text-gray-600">Trade Type</span>
                                                    <span className="font-semibold">{selectedItem.bandarmology.deep_trade_type || 'N/A'}</span>
                                                </div>

                                                {selectedItem.bandarmology.bandar_avg_cost && (
                                                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                        <span className="text-gray-600 flex items-center gap-2">
                                                            <Wallet className="w-4 h-4" />
                                                            Bandar Avg Cost
                                                        </span>
                                                        <span className="font-semibold">
                                                            Rp{selectedItem.bandarmology.bandar_avg_cost.toLocaleString()}
                                                        </span>
                                                    </div>
                                                )}

                                                {selectedItem.bandarmology.breakout_signal && (
                                                    <div className={cn(
                                                        "flex items-center justify-between p-3 rounded-lg",
                                                        selectedItem.bandarmology.breakout_signal.includes('BREAKOUT')
                                                            ? 'bg-emerald-50 border border-emerald-200'
                                                            : 'bg-gray-50'
                                                    )}>
                                                        <span className="text-gray-600 flex items-center gap-2">
                                                            <LineChart className="w-4 h-4" />
                                                            Breakout Signal
                                                        </span>
                                                        <span className={cn(
                                                            "font-semibold",
                                                            selectedItem.bandarmology.breakout_signal.includes('BREAKOUT')
                                                                ? 'text-emerald-600'
                                                                : 'text-gray-600'
                                                        )}>
                                                            {selectedItem.bandarmology.breakout_signal}
                                                        </span>
                                                    </div>
                                                )}

                                                {selectedItem.bandarmology.distribution_alert && (
                                                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                                                        <div className="flex items-center gap-2 text-red-700">
                                                            <AlertTriangle className="w-4 h-4" />
                                                            <span className="font-semibold text-sm">Distribution Alert</span>
                                                        </div>
                                                        <p className="text-red-600 text-sm mt-1">{selectedItem.bandarmology.distribution_alert}</p>
                                                    </div>
                                                )}

                                                {/* Status Indicators */}
                                                <div className="grid grid-cols-3 gap-2">
                                                    <div className={cn(
                                                        "p-2 rounded-lg text-center",
                                                        selectedItem.bandarmology.pinky ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                                                    )}>
                                                        <p className="text-xs font-medium">Pinky</p>
                                                        <p className="text-lg">{selectedItem.bandarmology.pinky ? '⚠️' : '✓'}</p>
                                                    </div>
                                                    <div className={cn(
                                                        "p-2 rounded-lg text-center",
                                                        selectedItem.bandarmology.crossing ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
                                                    )}>
                                                        <p className="text-xs font-medium">Crossing</p>
                                                        <p className="text-lg">{selectedItem.bandarmology.crossing ? '⚡' : '✓'}</p>
                                                    </div>
                                                    <div className={cn(
                                                        "p-2 rounded-lg text-center",
                                                        selectedItem.bandarmology.unusual ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-500'
                                                    )}>
                                                        <p className="text-xs font-medium">Unusual</p>
                                                        <p className="text-lg">{selectedItem.bandarmology.unusual ? '🔥' : '✓'}</p>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-center py-8 text-gray-400">
                                                <Target className="w-12 h-12 mx-auto mb-2 opacity-30" />
                                                <p>No Bandarmology analysis available</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Investment Thesis */}
                                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                                    <h4 className="font-semibold text-slate-900 flex items-center gap-2 mb-3">
                                        <FileText className="w-5 h-5" />
                                        Investment Thesis
                                    </h4>
                                    <div className="space-y-2 text-sm text-slate-700">
                                        {selectedItem.recommendation?.includes('ACCUM') && (
                                            <p className="flex items-start gap-2">
                                                <ArrowUpRight className="w-4 h-4 text-emerald-500 mt-0.5" />
                                                <span>
                                                    <strong>Accumulation Opportunity:</strong> Both Alpha Hunter and Bandarmology signals indicate
                                                    potential accumulation phase with positive flow and institutional interest.
                                                </span>
                                            </p>
                                        )}
                                        {selectedItem.recommendation?.includes('RISK') && (
                                            <p className="flex items-start gap-2">
                                                <ArrowDownRight className="w-4 h-4 text-red-500 mt-0.5" />
                                                <span>
                                                    <strong>Caution Advised:</strong> Distribution signals detected. Consider reducing position
                                                    or waiting for clearer entry signals.
                                                </span>
                                            </p>
                                        )}
                                        {selectedItem.bandarmology.breakout_signal?.includes('BREAKOUT') && (
                                            <p className="flex items-start gap-2">
                                                <Sparkles className="w-4 h-4 text-blue-500 mt-0.5" />
                                                <span>
                                                    <strong>Breakout Potential:</strong> Technical setup suggests possible price breakout.
                                                    Monitor volume and price action closely.
                                                </span>
                                            </p>
                                        )}
                                        {selectedItem.alpha_hunter.warning_status?.includes('REPO') && (
                                            <p className="flex items-start gap-2">
                                                <ShieldAlert className="w-4 h-4 text-red-500 mt-0.5" />
                                                <span>
                                                    <strong>Repo Risk:</strong> Potential repo selling pressure detected. Be cautious of
                                                    sudden downward moves.
                                                </span>
                                            </p>
                                        )}
                                        {selectedItem.recommendation === 'MIXED_SIGNALS' && (
                                            <p className="flex items-start gap-2">
                                                <Activity className="w-4 h-4 text-yellow-500 mt-0.5" />
                                                <span>
                                                    <strong>Mixed Signals:</strong> Alpha Hunter and Bandarmology showing different directions.
                                                    Consider waiting for clearer confirmation before entering.
                                                </span>
                                            </p>
                                        )}
                                    </div>
                                </div>

                                {/* Footer Actions */}
                                <div className="flex gap-3 pt-4 border-t">
                                    <Link href="/dashboard" className="flex-1" onClick={() => setSelectedItem(null)}>
                                        <Button
                                            variant="outline"
                                            className="w-full"
                                            onClick={() => handleViewTicker(selectedItem.ticker)}
                                        >
                                            View Dashboard
                                        </Button>
                                    </Link>
                                    <Link href="/alpha-hunter" className="flex-1" onClick={() => setSelectedItem(null)}>
                                        <Button
                                            variant="outline"
                                            className="w-full"
                                            onClick={() => handleViewTicker(selectedItem.ticker)}
                                        >
                                            Alpha Hunter
                                        </Button>
                                    </Link>
                                    <Link href="/bandarmology" className="flex-1" onClick={() => setSelectedItem(null)}>
                                        <Button
                                            className="w-full bg-blue-600 hover:bg-blue-700"
                                            onClick={() => handleViewTicker(selectedItem.ticker)}
                                        >
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
