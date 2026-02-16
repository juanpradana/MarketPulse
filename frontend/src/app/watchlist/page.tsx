'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Loading } from '@/components/shared';
import { ErrorDisplay } from '@/components/shared';
import { watchlistApi, type WatchlistItem } from '@/services/api';
import { useFilter } from '@/context/filter-context';
import {
    Star,
    Trash2,
    TrendingUp,
    TrendingDown,
    Plus,
    ExternalLink,
    Search
} from 'lucide-react';
import Link from 'next/link';

export default function WatchlistPage() {
    const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [newTicker, setNewTicker] = useState('');
    const [adding, setAdding] = useState(false);
    const { setTicker } = useFilter();

    const fetchWatchlist = async () => {
        try {
            setLoading(true);
            const data = await watchlistApi.getWatchlist();
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

    if (loading) {
        return (
            <div className="p-6">
                <div className="flex items-center gap-2 mb-6">
                    <Star className="w-6 h-6 text-yellow-500" />
                    <h1 className="text-2xl font-bold">My Watchlist</h1>
                </div>
                <Loading text="Loading watchlist..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
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
                        Add tickers to track your favorite stocks and get quick access to their data.
                    </p>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {watchlist.map((item) => (
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
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleRemoveTicker(item.ticker)}
                                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </Button>
                            </div>

                            {/* Price Info */}
                            {item.latest_price ? (
                                <div className="space-y-2">
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
                                <p className="text-sm text-gray-400">No price data available</p>
                            )}

                            {/* Quick Actions */}
                            <div className="flex gap-2 mt-4 pt-3 border-t">
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
                    ))}
                </div>
            )}
        </div>
    );
}
