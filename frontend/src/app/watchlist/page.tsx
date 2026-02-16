'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
    ErrorDisplay,
    PageHeaderSkeleton,
    WatchlistGridSkeleton,
    CardSkeleton
} from '@/components/shared';
import { watchlistApi, type WatchlistItemWithAnalysis, type AlphaHunterAnalysis, type BandarmologyAnalysis } from '@/services/api';
import { useFilter } from '@/context/filter-context';
import {
    Star,
    Trash2,
    TrendingUp,
    TrendingDown,
    Plus,
    ExternalLink,
    Search,
    Target,
    Activity,
    Zap,
    AlertTriangle,
    CheckCircle2,
    XCircle,
    BarChart3
} from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function WatchlistPage() {
    const [watchlist, setWatchlist] = useState<WatchlistItemWithAnalysis[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [newTicker, setNewTicker] = useState('');
    const [adding, setAdding] = useState(false);
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
            case 'VERY_STRONG': return { label: 'Very Strong', color: 'text-emerald-600' };
            case 'STRONG': return { label: 'Strong', color: 'text-green-600' };
            case 'MODERATE': return { label: 'Moderate', color: 'text-yellow-600' };
            case 'WEAK': return { label: 'Weak', color: 'text-orange-600' };
            case 'AVOID': return { label: 'Avoid', color: 'text-red-600' };
            default: return { label: 'N/A', color: 'text-gray-400' };
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

    return (
        <div className="p-6">
            {/* Header */}
            <div className="flex items-center gap-2 mb-6">
                <Star className="w-6 h-6 text-yellow-500" />
                <h1 className="text-2xl font-bold">My Watchlist</h1>
                <Badge variant="secondary" className="ml-2">
                    {watchlist.length} tickers
                </Badge>
            </div>

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

                        return (
                            <Card key={item.ticker} className="p-4 hover:shadow-lg transition-shadow">
                                {/* Header */}
                                <div className="flex items-start justify-between mb-3">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-xl font-bold">{item.ticker}</h3>
                                            <Link
                                                href={`/dashboard`}
                                                onClick={() => handleViewTicker(item.ticker)}
                                            >
                                                <ExternalLink className="w-4 h-4 text-gray-400 hover:text-blue-500" />
                                            </Link>
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
                                            onClick={() => handleRemoveTicker(item.ticker)}
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
                                    <div className="flex items-center gap-2 text-sm text-gray-400 mb-3 p-3 bg-gray-50 rounded-lg">
                                        <XCircle className="w-4 h-4" />
                                        <span>No analysis data available</span>
                                    </div>
                                )}

                                {/* Quick Actions */}
                                <div className="flex gap-2 mt-3 pt-3 border-t">
                                    <Link href="/dashboard" className="flex-1">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full"
                                            onClick={() => handleViewTicker(item.ticker)}
                                        >
                                            Dashboard
                                        </Button>
                                    </Link>
                                    <Link href="/neobdm-tracker" className="flex-1">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full"
                                            onClick={() => handleViewTicker(item.ticker)}
                                        >
                                            Flow
                                        </Button>
                                    </Link>
                                    <Link href="/alpha-hunter" className="flex-1">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full"
                                            onClick={() => handleViewTicker(item.ticker)}
                                        >
                                            Analysis
                                        </Button>
                                    </Link>
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
