'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
    AlertTriangle,
    BarChart3,
    Calendar,
    Loader2,
    Plus,
    RefreshCw,
    Search,
    SearchCheck,
    Target,
    Trash2,
    TrendingUp,
    Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { brokerStalkerApi, type BrokerAnalysis, type BrokerWatchlistItem, type ChartDataPoint, type ExecutionLedgerEntry, type BrokerPortfolioPosition } from '@/services/api/brokerStalker';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    LineChart,
    Line
} from 'recharts';

const formatCompactCurrency = (value: number): string => {
    const abs = Math.abs(value);
    if (abs >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
    if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
    if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    return value.toLocaleString('id-ID');
};

const toChartLabel = (date: string): string => {
    if (!date) return '-';
    const parts = date.split('-');
    if (parts.length !== 3) return date;
    return `${parts[2]}/${parts[1]}`;
};

export default function BrokerStalkerAdvanced() {
    const [brokers, setBrokers] = useState<BrokerWatchlistItem[]>([]);
    const [selectedBroker, setSelectedBroker] = useState<string>('');
    const [portfolio, setPortfolio] = useState<BrokerPortfolioPosition[]>([]);
    const [selectedTicker, setSelectedTicker] = useState<string>('');
    const [analysis, setAnalysis] = useState<BrokerAnalysis | null>(null);
    const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
    const [ledger, setLedger] = useState<ExecutionLedgerEntry[]>([]);

    const [loading, setLoading] = useState(true);
    const [detailLoading, setDetailLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [searchTerm, setSearchTerm] = useState('');
    const [newBrokerCode, setNewBrokerCode] = useState('');

    const selectedBrokerData = useMemo(
        () => brokers.find((b) => b.broker_code === selectedBroker) || null,
        [brokers, selectedBroker]
    );

    const filteredBrokers = useMemo(() => {
        if (!searchTerm.trim()) return brokers;
        const q = searchTerm.trim().toUpperCase();
        return brokers.filter((b) =>
            b.broker_code.includes(q) || (b.broker_name || '').toUpperCase().includes(q)
        );
    }, [brokers, searchTerm]);

    const selectedPortfolioItem = useMemo(
        () => portfolio.find((item) => item.ticker === selectedTicker) || null,
        [portfolio, selectedTicker]
    );

    const chartWithLabel = useMemo(
        () => chartData.map((p) => ({ ...p, day: toChartLabel(p.date) })),
        [chartData]
    );

    const loadBrokers = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await brokerStalkerApi.getWatchlist();
            const items = result.brokers || [];
            setBrokers(items);

            if (items.length > 0) {
                setSelectedBroker((prev) => (items.some((b) => b.broker_code === prev) ? prev : items[0].broker_code));
            } else {
                setSelectedBroker('');
                setPortfolio([]);
                setSelectedTicker('');
                setAnalysis(null);
                setChartData([]);
                setLedger([]);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load broker watchlist');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadBrokers();
    }, []);

    useEffect(() => {
        const run = async () => {
            if (!selectedBroker) return;
            setDetailLoading(true);
            setError(null);
            try {
                const p = await brokerStalkerApi.getBrokerPortfolio(selectedBroker);
                const items = p.portfolio || [];
                setPortfolio(items);
                setSelectedTicker((prev) => (items.some((i) => i.ticker === prev) ? prev : (items[0]?.ticker || '')));
            } catch (err) {
                setPortfolio([]);
                setSelectedTicker('');
                setError(err instanceof Error ? err.message : 'Failed to load broker portfolio');
            } finally {
                setDetailLoading(false);
            }
        };
        void run();
    }, [selectedBroker]);

    useEffect(() => {
        const run = async () => {
            if (!selectedBroker || !selectedTicker) {
                setAnalysis(null);
                setChartData([]);
                setLedger([]);
                return;
            }
            setDetailLoading(true);
            setError(null);
            try {
                const [a, c, l] = await Promise.all([
                    brokerStalkerApi.getBrokerAnalysis(selectedBroker, selectedTicker, 30),
                    brokerStalkerApi.getChartData(selectedBroker, selectedTicker, 14),
                    brokerStalkerApi.getExecutionLedger(selectedBroker, selectedTicker, 12),
                ]);
                setAnalysis(a.analysis);
                setChartData(c.data || []);
                setLedger(l.ledger || []);
            } catch (err) {
                setAnalysis(null);
                setChartData([]);
                setLedger([]);
                setError(err instanceof Error ? err.message : 'Failed to load broker analysis detail');
            } finally {
                setDetailLoading(false);
            }
        };
        void run();
    }, [selectedBroker, selectedTicker]);

    const handleSync = async () => {
        if (!selectedBroker) return;
        setSyncing(true);
        setError(null);
        try {
            await brokerStalkerApi.syncBrokerData(selectedBroker, undefined, 14);
            await loadBrokers();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to sync broker data');
        } finally {
            setSyncing(false);
        }
    };

    const handleAddBroker = async () => {
        const code = newBrokerCode.trim().toUpperCase();
        if (!code) return;
        setError(null);
        try {
            await brokerStalkerApi.addBrokerToWatchlist({ broker_code: code });
            setNewBrokerCode('');
            await loadBrokers();
            setSelectedBroker(code);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add broker');
        }
    };

    const handleRemoveBroker = async (brokerCode: string) => {
        setError(null);
        try {
            await brokerStalkerApi.removeBrokerFromWatchlist(brokerCode);
            await loadBrokers();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to remove broker');
        }
    };

    const currentNetVal = selectedPortfolioItem?.total_net_value ?? analysis?.net_value ?? 0;
    const currentAvgPrice = selectedPortfolioItem?.avg_execution_price ?? 0;

    return (
        <div className="min-h-screen bg-[#050507] text-slate-100 font-sans selection:bg-blue-500/30 overflow-x-hidden">
            {/* Background Grain/Glow */}
            <div className="fixed inset-0 pointer-events-none opacity-20">
                <div className="absolute top-[-20%] left-[-10%] w-full h-full bg-blue-600/20 blur-[150px] rounded-full" />
                <div className="absolute bottom-[-20%] right-[-10%] w-full h-full bg-emerald-600/10 blur-[150px] rounded-full" />
            </div>

            {/* Header */}
            <header className="sticky top-0 z-30 lg:z-40 border-b border-white/5 bg-[#050507]/80 backdrop-blur-2xl px-4 lg:px-8 py-3 lg:py-4 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-5">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-400/30">
                        <Target className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-black tracking-tight flex items-center gap-2">
                            BROKER STALKER
                            <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20">LIVE API</span>
                        </h1>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-2">
                            Tracking: <span className="text-white font-black">{selectedBrokerData?.broker_name || 'Select Broker'} ({selectedBrokerData?.broker_code || '-'})</span>
                        </p>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <div className="relative flex items-center bg-white/5 border border-white/10 rounded-2xl px-4 py-2.5 transition-all w-72 group">
                        <Search className="w-4 h-4 text-slate-500 mr-2" />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value.toUpperCase())}
                            placeholder="SEARCH BROKER..."
                            className="bg-transparent border-none outline-none text-xs font-bold w-full placeholder:text-slate-600 font-mono"
                        />
                    </div>

                    <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-2xl px-3 py-2">
                        <input
                            type="text"
                            value={newBrokerCode}
                            onChange={(e) => setNewBrokerCode(e.target.value.toUpperCase())}
                            placeholder="ADD CODE"
                            className="bg-transparent border-none outline-none text-xs font-bold w-20 placeholder:text-slate-600 font-mono"
                        />
                        <button
                            onClick={handleAddBroker}
                            className="inline-flex items-center gap-1 rounded-md bg-blue-500/20 px-2 py-1 text-[10px] font-bold text-blue-300 hover:bg-blue-500/30"
                        >
                            <Plus className="w-3 h-3" />
                            Add
                        </button>
                    </div>

                    <button
                        onClick={handleSync}
                        disabled={syncing || !selectedBroker}
                        className="inline-flex items-center gap-1 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={cn('w-3.5 h-3.5', syncing && 'animate-spin')} />
                        Sync 14D
                    </button>

                    <button
                        onClick={() => void loadBrokers()}
                        disabled={loading}
                        className="inline-flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-bold text-slate-200 hover:bg-white/10 disabled:opacity-50"
                    >
                        <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
                        Refresh
                    </button>
                </div>
            </header>

            <main className="p-8 max-w-[1600px] mx-auto space-y-8">
                {error && (
                    <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
                        <AlertTriangle className="w-4 h-4" />
                        {error}
                    </div>
                )}

                {/* Dashboard Grid */}
                <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">

                    {/* Left Panel: Portfolio / Stalked Stocks */}
                    <div className="xl:col-span-4 space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                                <Target className="w-4 h-4 text-blue-500" />
                                Broker Watchlist
                            </h3>
                        </div>

                        <div className="space-y-3">
                            {loading ? (
                                <div className="rounded-3xl border border-white/10 bg-[#0c0c0e] p-6 text-center text-slate-400">
                                    <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />
                                    Loading brokers...
                                </div>
                            ) : filteredBrokers.length === 0 ? (
                                <div className="rounded-3xl border border-white/10 bg-[#0c0c0e] p-6 text-center text-slate-500">
                                    No brokers found.
                                </div>
                            ) : (
                                filteredBrokers.map((broker) => (
                                    <div
                                        key={broker.broker_code}
                                        onClick={() => setSelectedBroker(broker.broker_code)}
                                        className={cn(
                                            "p-5 rounded-3xl border transition-all cursor-pointer group",
                                            selectedBroker === broker.broker_code
                                                ? "bg-blue-600/10 border-blue-500/30 shadow-[0_0_30px_rgba(59,130,246,0.1)]"
                                                : "bg-[#0c0c0e] border-white/5 hover:border-white/10"
                                        )}
                                    >
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm",
                                                selectedBroker === broker.broker_code ? "bg-blue-500 text-white" : "bg-white/5 text-slate-400"
                                            )}>
                                                {broker.broker_code}
                                            </div>
                                            <div>
                                                <div className="text-base font-black tracking-tight">{broker.broker_name || broker.broker_code}</div>
                                                <div className="text-[10px] font-bold text-slate-500 uppercase">Code: {broker.broker_code}</div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                void handleRemoveBroker(broker.broker_code);
                                            }}
                                            className="rounded-md border border-rose-500/30 bg-rose-500/10 p-1 text-rose-300 hover:bg-rose-500/20"
                                            title="Remove broker"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                    </div>

                                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                        <div className="bg-black/20 p-2 rounded-xl border border-white/5">
                                            <div className="text-[8px] font-black text-slate-600 uppercase mb-0.5">Power Level</div>
                                            <div className="text-xs font-bold text-slate-300">{broker.power_level}</div>
                                        </div>
                                        <div className="bg-black/20 p-2 rounded-xl border border-white/5">
                                            <div className="text-[8px] font-black text-slate-600 uppercase mb-0.5">Updated</div>
                                            <div className="text-xs font-bold text-slate-300">{broker.updated_at?.slice(0, 10) || '-'}</div>
                                        </div>
                                    </div>
                                    </div>
                                ))
                            )}

                            <div className="rounded-2xl border border-white/10 bg-[#0c0c0e] p-4">
                                <h4 className="mb-2 text-[10px] font-black uppercase tracking-widest text-slate-500">Tracked Portfolio</h4>
                                {detailLoading ? (
                                    <div className="text-xs text-slate-400">Loading portfolio...</div>
                                ) : portfolio.length === 0 ? (
                                    <div className="text-xs text-slate-500">No portfolio records for selected broker.</div>
                                ) : (
                                    <div className="space-y-2">
                                        {portfolio.map((item) => (
                                            <button
                                                key={item.ticker}
                                                onClick={() => setSelectedTicker(item.ticker)}
                                                className={cn(
                                                    'w-full rounded-lg border px-3 py-2 text-left text-xs transition-all',
                                                    selectedTicker === item.ticker
                                                        ? 'border-blue-500/40 bg-blue-500/10 text-blue-200'
                                                        : 'border-white/10 bg-black/20 text-slate-300 hover:border-white/20'
                                                )}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span className="font-black">{item.ticker}</span>
                                                    <span className={cn('font-bold', item.streak_days >= 0 ? 'text-emerald-400' : 'text-rose-400')}>
                                                        {item.streak_days >= 0 ? `+${item.streak_days}` : item.streak_days}d
                                                    </span>
                                                </div>
                                                <div className="mt-1 text-[10px] text-slate-500">
                                                    Net: {formatCompactCurrency(item.total_net_value)}
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Panel: Advanced Analytics */}
                    <div className="xl:col-span-8 space-y-8">

                        {/* Summary Header */}
                        <div className="bg-gradient-to-br from-blue-600/20 to-transparent border border-blue-500/20 rounded-[2.5rem] p-8 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-8 opacity-10">
                                <Zap className="w-32 h-32 text-blue-500" />
                            </div>
                            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-3">
                                        <h2 className="text-3xl font-black">{selectedTicker || '-'} <span className="text-slate-500 font-medium">Surveillance</span></h2>
                                    </div>
                                    <p className="text-sm text-slate-400 max-w-md font-medium">
                                        Deep tracking for <span className="text-white font-bold">{selectedBroker || '-'}</span> activity.
                                        {analysis?.status ? ` Status: ${analysis.status}.` : ' Select broker and ticker to view analysis.'}
                                    </p>
                                </div>
                                <div className="flex gap-4">
                                    <div className="text-right">
                                        <div className="text-[10px] font-black text-slate-500 uppercase mb-1">Total Net (30D)</div>
                                        <div className={cn('text-2xl font-black', currentNetVal >= 0 ? 'text-emerald-400' : 'text-rose-400')}>
                                            {formatCompactCurrency(currentNetVal)}
                                        </div>
                                    </div>
                                    <div className="w-1 px-4 border-r border-white/10" />
                                    <div className="text-right">
                                        <div className="text-[10px] font-black text-slate-500 uppercase mb-1">Avg Buy Price</div>
                                        <div className="text-2xl font-black text-blue-400">Rp {Math.round(currentAvgPrice || 0).toLocaleString('id-ID')}</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Chart Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                            {/* Daily Volume Bar Chart */}
                            <div className="bg-[#0c0c0e] border border-white/5 rounded-[2rem] p-6 space-y-6">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-[11px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <BarChart3 className="w-4 h-4 text-blue-500" />
                                        Buy vs Sell Volume (B)
                                    </h4>
                                    <div className="flex gap-4">
                                        <div className="flex items-center gap-1.5 pt-0.5">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                            <span className="text-[9px] font-black text-slate-600">BUY</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 pt-0.5">
                                            <div className="w-2 h-2 rounded-full bg-red-500" />
                                            <span className="text-[9px] font-black text-slate-600">SELL</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="h-[250px] w-full">
                                    <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                                        <BarChart data={chartWithLabel}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff05" />
                                            <XAxis
                                                dataKey="day"
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fill: '#475569', fontSize: 10, fontWeight: 700 }}
                                            />
                                            <YAxis hide />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#0c0c0e', border: '1px solid #ffffff10', borderRadius: '12px' }}
                                                itemStyle={{ fontSize: '10px', fontWeight: 900, textTransform: 'uppercase' }}
                                            />
                                            <Bar dataKey="buy" fill="#10b981" radius={[4, 4, 0, 0]} barSize={12} />
                                            <Bar dataKey="sell" fill="#ef4444" radius={[4, 4, 0, 0]} barSize={12} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Net Flow Area Chart */}
                            <div className="bg-[#0c0c0e] border border-white/5 rounded-[2rem] p-6 space-y-6">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-[11px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                                        Cumulative Net Flow
                                    </h4>
                                    <div className="px-2 py-1 bg-emerald-500/10 rounded border border-emerald-500/20 text-[9px] font-black text-emerald-400">
                                        UPWARD TREND
                                    </div>
                                </div>

                                <div className="h-[250px] w-full">
                                    <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                                        <LineChart data={chartWithLabel}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff05" />
                                            <XAxis
                                                dataKey="day"
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fill: '#475569', fontSize: 10, fontWeight: 700 }}
                                            />
                                            <YAxis hide />
                                            <Tooltip />
                                            <Line
                                                type="monotone"
                                                dataKey="net"
                                                stroke="#10b981"
                                                strokeWidth={3}
                                                dot={{ r: 4, fill: '#10b981', strokeWidth: 0 }}
                                                activeDot={{ r: 6, strokeWidth: 0 }}
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </div>

                        {/* Interactive Data Table */}
                        <div className="bg-[#0c0c0e] border border-white/5 rounded-[2.5rem] overflow-hidden">
                            <div className="p-6 border-b border-white/5 flex items-center justify-between">
                                <h4 className="text-[11px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                    <Calendar className="w-4 h-4 text-blue-500" />
                                    Daily Execution Ledger
                                </h4>
                                <SearchCheck className="w-4 h-4 text-slate-600" />
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-[9px] font-black text-slate-600 uppercase tracking-[0.1em] border-b border-white/5">
                                            <th className="p-6">Execution Date</th>
                                            <th className="p-6">Total Buy</th>
                                            <th className="p-6">Total Sell</th>
                                            <th className="p-6">Net Flow</th>
                                            <th className="p-6 text-right">Avg Price</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {ledger.map((log, i) => (
                                            <tr key={`${log.date}-${i}`} className="hover:bg-white/[0.02] transition-colors group">
                                                <td className="p-6 text-xs font-bold text-slate-400 font-mono">{log.date}</td>
                                                <td className="p-6 text-xs font-black text-emerald-400/80">{log.action === 'BUY' ? formatCompactCurrency(log.volume) : '-'}</td>
                                                <td className="p-6 text-xs font-black text-red-400/80">{log.action === 'SELL' ? formatCompactCurrency(log.volume) : '-'}</td>
                                                <td className="p-6">
                                                    <div className={cn(
                                                        "text-xs font-black px-2 py-1 rounded-lg inline-block",
                                                        log.action === 'SELL' ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'
                                                    )}>
                                                        {log.action}
                                                    </div>
                                                </td>
                                                <td className="p-6 text-right text-xs font-black text-slate-200">
                                                    Rp {Math.round(log.avg_price || 0).toLocaleString('id-ID')}
                                                </td>
                                            </tr>
                                        ))}
                                        {ledger.length === 0 && (
                                            <tr>
                                                <td colSpan={5} className="p-6 text-center text-xs text-slate-500">
                                                    {detailLoading ? 'Loading ledger...' : 'No execution ledger data available.'}
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Status */}
                <footer className="bg-white/[0.02] border border-white/10 rounded-full p-4 flex items-center justify-center gap-8">
                    <div className="flex items-center gap-3">
                        <div className={cn('w-2 h-2 rounded-full animate-pulse', detailLoading ? 'bg-amber-500' : 'bg-emerald-500')} />
                        <span className="text-[10px] font-black text-slate-500 uppercase">
                            System Status: {detailLoading ? 'Loading' : 'Live'}
                        </span>
                    </div>
                    <div className="h-4 border-r border-white/10" />
                    <div className="flex items-center gap-3">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                            {selectedBroker ? `Broker: ${selectedBroker}` : 'No broker selected'}
                        </span>
                    </div>
                </footer>

            </main>
        </div>
    );
}
