'use client';

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { bandarmologyApi, BandarmologyItem, DeepAnalysisStatus } from '@/services/api/bandarmology';
import {
    RefreshCcw,
    AlertCircle,
    ChevronUp,
    ChevronDown,
    Calendar,
    Target,
    TrendingUp,
    Zap,
    Eye,
    Filter,
    Download,
    ArrowUpDown,
    Microscope,
    Loader2,
    CheckCircle2,
    Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import StockDetailModal from '@/components/bandarmology/StockDetailModal';

type SortConfig = { key: string; direction: 'asc' | 'desc' } | null;

const TRADE_TYPE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
    'BOTH': { label: 'SWING + INTRA', color: 'text-yellow-300', bg: 'bg-yellow-500/20 border-yellow-500/30' },
    'SWING': { label: 'SWING', color: 'text-emerald-300', bg: 'bg-emerald-500/20 border-emerald-500/30' },
    'INTRADAY': { label: 'INTRADAY', color: 'text-cyan-300', bg: 'bg-cyan-500/20 border-cyan-500/30' },
    'WATCH': { label: 'WATCH', color: 'text-orange-300', bg: 'bg-orange-500/20 border-orange-500/30' },
    'SELL': { label: 'SELL', color: 'text-red-300', bg: 'bg-red-500/20 border-red-500/30' },
    '—': { label: '—', color: 'text-zinc-600', bg: 'bg-transparent' },
};

const CONFLUENCE_CONFIG: Record<string, { label: string; color: string }> = {
    'TRIPLE': { label: '●●●', color: 'text-yellow-400' },
    'DOUBLE': { label: '●●○', color: 'text-emerald-400' },
    'SINGLE': { label: '●○○', color: 'text-blue-400' },
    'NONE': { label: '○○○', color: 'text-zinc-600' },
};

function ScoreBar({ score, max = 100 }: { score: number; max?: number }) {
    const pct = Math.min((score / max) * 100, 100);
    let barColor = 'bg-zinc-600';
    if (pct >= 70) barColor = 'bg-emerald-500';
    else if (pct >= 50) barColor = 'bg-blue-500';
    else if (pct >= 30) barColor = 'bg-orange-500';
    else if (pct > 0) barColor = 'bg-red-500';

    return (
        <div className="flex items-center gap-1.5 w-full">
            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className={cn("h-full rounded-full transition-all", barColor)} style={{ width: `${pct}%` }} />
            </div>
            <span className={cn(
                "text-[10px] font-bold tabular-nums min-w-[24px] text-right",
                pct >= 70 ? 'text-emerald-400' : pct >= 50 ? 'text-blue-400' : pct >= 30 ? 'text-orange-400' : 'text-zinc-500'
            )}>
                {score}
            </span>
        </div>
    );
}

function FlowCell({ value }: { value: number }) {
    if (!value || value === 0) return <span className="text-zinc-700">—</span>;
    const isPositive = value > 0;
    const formatted = value.toLocaleString('id-ID', { maximumFractionDigits: 1 });
    return (
        <span className={cn("tabular-nums font-bold", isPositive ? 'text-emerald-400' : 'text-red-400')}>
            {isPositive ? '+' : ''}{formatted}
        </span>
    );
}

function FlagBadge({ active, label }: { active: boolean; label: string }) {
    if (!active) return <span className="text-zinc-700 text-[9px]">—</span>;
    return (
        <span className="text-pink-400 font-black text-[10px] bg-pink-500/15 px-1 py-0.5 rounded">
            {label}
        </span>
    );
}

export default function BandarmologyPage() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<BandarmologyItem[]>([]);
    const [analysisDate, setAnalysisDate] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>("");
    const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'total_score', direction: 'desc' });
    const [tradeTypeFilter, setTradeTypeFilter] = useState<string>("");
    const [minScoreFilter, setMinScoreFilter] = useState<number>(0);
    const [searchTicker, setSearchTicker] = useState<string>("");
    const [flagFilters, setFlagFilters] = useState<Record<string, boolean>>({});
    const [currentPage, setCurrentPage] = useState(1);
    const [deepStatus, setDeepStatus] = useState<DeepAnalysisStatus | null>(null);
    const [deepLoading, setDeepLoading] = useState(false);
    const [hasDeepData, setHasDeepData] = useState(false);
    const [expandedRow, setExpandedRow] = useState<string | null>(null);
    const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
    const deepPollRef = useRef<NodeJS.Timeout | null>(null);
    const pageSize = 50;

    const loadData = async (dateOverride?: string) => {
        setLoading(true);
        setError(null);
        try {
            const result = await bandarmologyApi.getScreening(
                dateOverride ?? (selectedDate || undefined),
                0  // fetch all, we filter client-side
            );
            setData(result.data);
            setAnalysisDate(result.date);
            setHasDeepData(result.has_deep_data || false);
            if (result.deep_analysis_running) {
                startDeepPolling();
            }
        } catch (err: any) {
            setError(err.message || "Failed to load bandarmology data");
        } finally {
            setLoading(false);
        }
    };

    // Fetch dates + initial data on mount
    const mountedRef = React.useRef(false);
    useEffect(() => {
        const init = async () => {
            try {
                const result = await bandarmologyApi.getDates();
                if (result.dates && result.dates.length > 0) {
                    setAvailableDates(result.dates);
                }
            } catch (e) {
                console.error("Failed to fetch bandarmology dates", e);
            }
            await loadData();
        };
        init();
        mountedRef.current = true;
    }, []);

    // Reload when selectedDate changes (skip initial mount)
    useEffect(() => {
        if (mountedRef.current) {
            loadData();
        }
    }, [selectedDate]);

    // Deep analysis polling
    const startDeepPolling = useCallback(() => {
        if (deepPollRef.current) clearInterval(deepPollRef.current);
        deepPollRef.current = setInterval(async () => {
            try {
                const status = await bandarmologyApi.getDeepStatus();
                setDeepStatus(status);
                if (!status.running) {
                    if (deepPollRef.current) clearInterval(deepPollRef.current);
                    deepPollRef.current = null;
                    // Reload data to get enriched results
                    await loadData();
                }
            } catch (e) {
                console.error('Deep poll error', e);
            }
        }, 3000);
    }, [selectedDate]);

    useEffect(() => {
        return () => {
            if (deepPollRef.current) clearInterval(deepPollRef.current);
        };
    }, []);

    const handleTriggerDeep = async () => {
        setDeepLoading(true);
        try {
            await bandarmologyApi.triggerDeepAnalysis(
                selectedDate || undefined,
                30,
                20
            );
            startDeepPolling();
            const status = await bandarmologyApi.getDeepStatus();
            setDeepStatus(status);
        } catch (err: any) {
            setError(err.message || 'Failed to trigger deep analysis');
        } finally {
            setDeepLoading(false);
        }
    };

    // Processing pipeline: filter → sort → paginate
    const processedData = useMemo(() => {
        let result = [...data];

        // Score filter
        if (minScoreFilter > 0) {
            result = result.filter(r => r.total_score >= minScoreFilter);
        }

        // Trade type filter
        if (tradeTypeFilter) {
            if (tradeTypeFilter === 'SWING') {
                result = result.filter(r => r.trade_type === 'SWING' || r.trade_type === 'BOTH');
            } else if (tradeTypeFilter === 'INTRADAY') {
                result = result.filter(r => r.trade_type === 'INTRADAY' || r.trade_type === 'BOTH');
            } else {
                result = result.filter(r => r.trade_type === tradeTypeFilter);
            }
        }

        // Ticker search
        if (searchTicker) {
            const query = searchTicker.toUpperCase();
            result = result.filter(r => r.symbol.includes(query));
        }

        // Flag filters (pinky, crossing, unusual, likuid)
        if (flagFilters.pinky) result = result.filter(r => r.pinky);
        if (flagFilters.crossing) result = result.filter(r => r.crossing);
        if (flagFilters.unusual) result = result.filter(r => r.unusual);
        if (flagFilters.likuid) result = result.filter(r => r.likuid);

        // Sort
        if (sortConfig) {
            result.sort((a, b) => {
                const key = sortConfig.key as keyof BandarmologyItem;
                let valA = a[key];
                let valB = b[key];

                // Handle numeric
                const numA = typeof valA === 'number' ? valA : parseFloat(String(valA || '0'));
                const numB = typeof valB === 'number' ? valB : parseFloat(String(valB || '0'));

                if (!isNaN(numA) && !isNaN(numB)) {
                    return sortConfig.direction === 'asc' ? numA - numB : numB - numA;
                }

                // String fallback
                const strA = String(valA || '').toLowerCase();
                const strB = String(valB || '').toLowerCase();
                if (strA < strB) return sortConfig.direction === 'asc' ? -1 : 1;
                if (strA > strB) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }

        return result;
    }, [data, minScoreFilter, tradeTypeFilter, searchTicker, flagFilters, sortConfig]);

    // Pagination
    const totalPages = Math.ceil(processedData.length / pageSize);
    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * pageSize;
        return processedData.slice(start, start + pageSize);
    }, [processedData, currentPage]);

    // Reset page on filter change
    useEffect(() => {
        setCurrentPage(1);
    }, [minScoreFilter, tradeTypeFilter, searchTicker, flagFilters, selectedDate]);

    const handleSort = (key: string) => {
        if (sortConfig?.key === key) {
            if (sortConfig.direction === 'desc') {
                setSortConfig({ key, direction: 'asc' });
            } else {
                setSortConfig(null);
            }
        } else {
            setSortConfig({ key, direction: 'desc' });
        }
    };

    const toggleFlagFilter = (flag: string) => {
        setFlagFilters(prev => ({ ...prev, [flag]: !prev[flag] }));
    };

    // Stats
    const stats = useMemo(() => {
        const swing = data.filter(d => d.trade_type === 'SWING' || d.trade_type === 'BOTH').length;
        const intraday = data.filter(d => d.trade_type === 'INTRADAY' || d.trade_type === 'BOTH').length;
        const high = data.filter(d => (d.combined_score ?? d.total_score) >= 60).length;
        const triple = data.filter(d => d.confluence_status === 'TRIPLE').length;
        const deepCount = data.filter(d => (d.deep_score ?? 0) > 0).length;
        return { swing, intraday, high, triple, deepCount };
    }, [data]);

    const handleExportCSV = () => {
        if (processedData.length === 0) return;
        const headers = ['Symbol', 'Score', 'Type', 'Pinky', 'Crossing', 'Unusual', 'Likuid', 'Confluence',
            'Price', '%1d', 'MA>', 'W-4', 'W-3', 'W-2', 'W-1', 'D-0 MM', 'D-0 NR', 'D-0 FF',
            'Inst Net', 'Foreign Net', 'Top Buyer', 'Top Seller'];
        const rows = processedData.map(r => [
            r.symbol, r.total_score, r.trade_type,
            r.pinky ? 'V' : '', r.crossing ? 'V' : '', r.unusual ? 'V' : '', r.likuid ? 'V' : '',
            r.confluence_status, r.price, r.pct_1d, r.ma_above_count,
            r.w_4, r.w_3, r.w_2, r.w_1, r.d_0_mm, r.d_0_nr, r.d_0_ff,
            r.inst_net_lot, r.foreign_net_lot, r.top_buyer || '', r.top_seller || ''
        ]);
        const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bandarmology_${analysisDate || 'latest'}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const SortableHeader = ({ label, sortKey, className = "" }: { label: string; sortKey: string; className?: string }) => {
        const isSorted = sortConfig?.key === sortKey;
        return (
            <th
                onClick={() => handleSort(sortKey)}
                className={cn(
                    "px-1.5 py-2 text-[10px] font-bold uppercase tracking-tight cursor-pointer hover:bg-zinc-700/50 transition-colors select-none whitespace-nowrap border-r border-zinc-700/30",
                    className
                )}
            >
                <div className="flex items-center justify-center gap-0.5">
                    {label}
                    <div className="flex flex-col">
                        <ChevronUp className={cn("w-2 h-2 opacity-20", isSorted && sortConfig?.direction === 'asc' && "opacity-100 text-blue-400")} />
                        <ChevronDown className={cn("w-2 h-2 -mt-0.5 opacity-20", isSorted && sortConfig?.direction === 'desc' && "opacity-100 text-blue-400")} />
                    </div>
                </div>
            </th>
        );
    };

    return (
        <>
        <div className="flex flex-col gap-0 p-0 min-h-screen bg-[#0f1115] text-zinc-100 font-mono">
            {/* Header Bar */}
            <div className="bg-[#181a1f] border-b border-zinc-800/60 sticky top-0 z-50 backdrop-blur-md bg-opacity-95">
                <div className="flex flex-wrap items-center justify-between gap-2 p-2">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Target className="w-5 h-5 text-purple-400" />
                            <h1 className="text-[16px] font-black tracking-tight text-zinc-100">
                                BANDARMOLOGY
                            </h1>
                        </div>
                        <div className="h-5 w-px bg-zinc-700" />

                        {/* Date Selector */}
                        <div className="space-y-0">
                            <label className="text-[8px] text-zinc-500 font-bold uppercase tracking-wider block flex items-center gap-0.5">
                                <Calendar className="w-2 h-2" /> Tanggal
                            </label>
                            <select
                                value={selectedDate}
                                onChange={(e) => setSelectedDate(e.target.value)}
                                className="block w-32 bg-[#23252b] border border-zinc-700/50 text-yellow-400 font-bold text-[10px] rounded-sm py-0.5 px-1 outline-none focus:border-yellow-500/50 cursor-pointer"
                            >
                                <option value="">Latest</option>
                                {availableDates.map(date => (
                                    <option key={date} value={date}>{date}</option>
                                ))}
                            </select>
                        </div>

                        {/* Trade Type Filter */}
                        <div className="space-y-0">
                            <label className="text-[8px] text-zinc-500 font-bold uppercase tracking-wider block">Tipe</label>
                            <select
                                value={tradeTypeFilter}
                                onChange={(e) => setTradeTypeFilter(e.target.value)}
                                className="block w-28 bg-[#23252b] border border-zinc-700/50 text-zinc-200 text-[10px] rounded-sm py-0.5 px-1 outline-none focus:border-blue-500/50 cursor-pointer"
                            >
                                <option value="">All Types</option>
                                <option value="BOTH">Swing + Intra</option>
                                <option value="SWING">Swing</option>
                                <option value="INTRADAY">Intraday</option>
                                <option value="WATCH">Watch</option>
                            </select>
                        </div>

                        {/* Min Score */}
                        <div className="space-y-0">
                            <label className="text-[8px] text-zinc-500 font-bold uppercase tracking-wider block">Min Score</label>
                            <select
                                value={minScoreFilter}
                                onChange={(e) => setMinScoreFilter(Number(e.target.value))}
                                className="block w-16 bg-[#23252b] border border-zinc-700/50 text-zinc-200 text-[10px] rounded-sm py-0.5 px-1 outline-none focus:border-blue-500/50 cursor-pointer"
                            >
                                <option value={0}>0+</option>
                                <option value={20}>20+</option>
                                <option value={30}>30+</option>
                                <option value={40}>40+</option>
                                <option value={50}>50+</option>
                                <option value={60}>60+</option>
                                <option value={70}>70+</option>
                            </select>
                        </div>

                        {/* Ticker Search */}
                        <div className="space-y-0">
                            <label className="text-[8px] text-zinc-500 font-bold uppercase tracking-wider block">Ticker</label>
                            <input
                                type="text"
                                value={searchTicker}
                                onChange={(e) => setSearchTicker(e.target.value)}
                                placeholder="Search..."
                                className="block w-24 bg-[#23252b] border border-zinc-700/50 text-zinc-200 text-[10px] rounded-sm py-0.5 px-1.5 outline-none focus:border-blue-500/50 placeholder:text-zinc-700"
                            />
                        </div>

                        {/* Flag Filters */}
                        <div className="flex gap-1 items-end">
                            {(['pinky', 'crossing', 'unusual', 'likuid'] as const).map(flag => (
                                <button
                                    key={flag}
                                    onClick={() => toggleFlagFilter(flag)}
                                    className={cn(
                                        "px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border transition-all",
                                        flagFilters[flag]
                                            ? "bg-pink-500/20 border-pink-500/50 text-pink-300"
                                            : "bg-zinc-800/50 border-zinc-700/30 text-zinc-500 hover:text-zinc-300"
                                    )}
                                >
                                    {flag === 'likuid' ? 'LQ' : flag.slice(0, 2).toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleTriggerDeep}
                            disabled={loading || deepLoading || (deepStatus?.running ?? false)}
                            className="bg-gradient-to-r from-amber-600 to-orange-600 hover:opacity-90 disabled:opacity-50 text-white px-3 py-1 rounded-sm text-[10px] font-bold shadow-lg transition-all active:scale-95 flex items-center gap-1"
                            title="Scrape inventory + transaction chart for top 30 stocks"
                        >
                            {deepStatus?.running ? (
                                <><Loader2 className="w-2.5 h-2.5 animate-spin" /> Deep {deepStatus.progress}/{deepStatus.total}</>
                            ) : (
                                <><Microscope className="w-2.5 h-2.5" /> Deep Analyze</>
                            )}
                        </button>
                        <button
                            onClick={() => loadData()}
                            disabled={loading}
                            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:opacity-90 disabled:opacity-50 text-white px-3 py-1 rounded-sm text-[10px] font-bold shadow-lg transition-all active:scale-95 flex items-center gap-1"
                        >
                            {loading && <RefreshCcw className="w-2.5 h-2.5 animate-spin" />}
                            {loading ? "Analyzing..." : "Refresh"}
                        </button>
                    </div>
                </div>

                {/* Stats Bar */}
                <div className="flex items-center gap-4 px-3 py-1 bg-[#12141a] border-t border-zinc-800/40 text-[9px]">
                    <div className="flex items-center gap-1.5">
                        <span className="text-zinc-500">TOTAL:</span>
                        <span className="text-zinc-300 font-bold">{processedData.length}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <TrendingUp className="w-2.5 h-2.5 text-emerald-500" />
                        <span className="text-zinc-500">SWING:</span>
                        <span className="text-emerald-400 font-bold">{stats.swing}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <Zap className="w-2.5 h-2.5 text-cyan-500" />
                        <span className="text-zinc-500">INTRADAY:</span>
                        <span className="text-cyan-400 font-bold">{stats.intraday}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <Target className="w-2.5 h-2.5 text-yellow-500" />
                        <span className="text-zinc-500">HIGH SCORE (60+):</span>
                        <span className="text-yellow-400 font-bold">{stats.high}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <span className="text-zinc-500">TRIPLE CONFLUENCE:</span>
                        <span className="text-yellow-400 font-bold">{stats.triple}</span>
                    </div>
                    {stats.deepCount > 0 && (
                        <div className="flex items-center gap-1.5">
                            <Microscope className="w-2.5 h-2.5 text-amber-500" />
                            <span className="text-zinc-500">DEEP:</span>
                            <span className="text-amber-400 font-bold">{stats.deepCount}</span>
                        </div>
                    )}
                    {analysisDate && (
                        <div className="ml-auto text-zinc-500">
                            DATA: <span className="text-zinc-300 font-bold">{analysisDate}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Table */}
            <div className="flex-1 overflow-hidden relative bg-[#0f1115]">
                {loading && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-30 flex flex-col items-center justify-center gap-3">
                        <RefreshCcw className="w-10 h-10 text-purple-500 animate-spin" />
                        <span className="text-purple-400 text-xs font-mono animate-pulse">
                            Running Bandarmology Analysis...
                        </span>
                    </div>
                )}

                <div className="overflow-auto h-full scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
                    <table className="w-auto text-left text-[11px] border-collapse leading-none tracking-tight table-fixed">
                        <thead className="sticky top-0 z-20 shadow-md">
                            <tr className="bg-gradient-to-r from-purple-900/80 to-blue-900/80 text-zinc-200 border-b border-purple-500/30">
                                <SortableHeader label="#" sortKey="total_score" className="w-[30px]" />
                                <SortableHeader label="TICKER" sortKey="symbol" className="w-[80px]" />
                                <SortableHeader label="SCORE" sortKey="combined_score" className="w-[90px]" />
                                <SortableHeader label="DEEP" sortKey="deep_score" className="w-[50px]" />
                                <SortableHeader label="TYPE" sortKey="trade_type" className="w-[95px]" />
                                <th className="px-1 py-2 text-[10px] font-bold uppercase tracking-tight text-center border-r border-zinc-700/30 w-[35px]">PK</th>
                                <th className="px-1 py-2 text-[10px] font-bold uppercase tracking-tight text-center border-r border-zinc-700/30 w-[35px]">CR</th>
                                <th className="px-1 py-2 text-[10px] font-bold uppercase tracking-tight text-center border-r border-zinc-700/30 w-[35px]">UN</th>
                                <th className="px-1 py-2 text-[10px] font-bold uppercase tracking-tight text-center border-r border-zinc-700/30 w-[35px]">LQ</th>
                                <SortableHeader label="CONFL" sortKey="confluence_status" className="w-[55px]" />
                                <SortableHeader label="PRICE" sortKey="price" className="w-[70px]" />
                                <SortableHeader label="%1D" sortKey="pct_1d" className="w-[55px]" />
                                <SortableHeader label="MA>" sortKey="ma_above_count" className="w-[40px]" />
                                <SortableHeader label="W-4" sortKey="w_4" className="w-[60px]" />
                                <SortableHeader label="W-3" sortKey="w_3" className="w-[60px]" />
                                <SortableHeader label="W-2" sortKey="w_2" className="w-[60px]" />
                                <SortableHeader label="W-1" sortKey="w_1" className="w-[60px]" />
                                <SortableHeader label="D-0 MM" sortKey="d_0_mm" className="w-[65px]" />
                                <SortableHeader label="D-0 NR" sortKey="d_0_nr" className="w-[65px]" />
                                <SortableHeader label="D-0 FF" sortKey="d_0_ff" className="w-[65px]" />
                                <SortableHeader label="INST" sortKey="inst_net_lot" className="w-[65px]" />
                                <SortableHeader label="FRGN" sortKey="foreign_net_lot" className="w-[65px]" />
                                <SortableHeader label="INV" sortKey="inv_accum_brokers" className="w-[55px]" />
                                <SortableHeader label="MM" sortKey="txn_mm_cum" className="w-[60px]" />
                                <SortableHeader label="F.CUM" sortKey="txn_foreign_cum" className="w-[60px]" />
                                <th className="px-1 py-2 text-[10px] font-bold uppercase tracking-tight text-center border-r border-zinc-700/30 w-[40px]">TOP B</th>
                                <th className="px-1 py-2 text-[10px] font-bold uppercase tracking-tight text-center w-[40px]">TOP S</th>
                            </tr>
                        </thead>

                        <tbody className="bg-[#0f1115] divide-y divide-zinc-800/30">
                            {paginatedData.length > 0 ? (
                                paginatedData.map((row, idx) => {
                                    const rank = (currentPage - 1) * pageSize + idx + 1;
                                    const typeConfig = TRADE_TYPE_CONFIG[row.trade_type] || TRADE_TYPE_CONFIG['—'];
                                    const conflConfig = CONFLUENCE_CONFIG[row.confluence_status] || CONFLUENCE_CONFIG['NONE'];

                                    return (
                                        <tr key={row.symbol} className="hover:bg-zinc-800/40 transition-colors group h-[32px]">
                                            {/* Rank */}
                                            <td className="px-1.5 py-1 text-center text-zinc-600 text-[10px] border-r border-zinc-800/30 font-mono">
                                                {rank}
                                            </td>

                                            {/* Symbol */}
                                            <td className="px-2 py-1 border-r border-zinc-800/30">
                                                <button
                                                    onClick={() => setSelectedTicker(row.symbol)}
                                                    className="text-blue-300 font-black text-[12px] tracking-tight hover:text-blue-200 hover:underline cursor-pointer transition-colors"
                                                >
                                                    {row.symbol}
                                                </button>
                                            </td>

                                            {/* Score (combined or base) */}
                                            <td className="px-1.5 py-1 border-r border-zinc-800/30">
                                                <ScoreBar score={row.combined_score ?? row.total_score} max={row.max_combined_score ?? 100} />
                                            </td>

                                            {/* Deep Score */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                {(row.deep_score ?? 0) > 0 ? (
                                                    <span className={cn(
                                                        "text-[10px] font-bold tabular-nums",
                                                        (row.deep_score ?? 0) >= 40 ? 'text-amber-400' :
                                                        (row.deep_score ?? 0) >= 20 ? 'text-blue-400' : 'text-zinc-500'
                                                    )}>
                                                        +{row.deep_score}
                                                    </span>
                                                ) : <span className="text-zinc-800 text-[9px]">—</span>}
                                            </td>

                                            {/* Trade Type */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <span className={cn(
                                                    "text-[9px] font-black px-1.5 py-0.5 rounded border",
                                                    typeConfig.bg, typeConfig.color
                                                )}>
                                                    {typeConfig.label}
                                                </span>
                                            </td>

                                            {/* Flags */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <FlagBadge active={row.pinky} label="PK" />
                                            </td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <FlagBadge active={row.crossing} label="CR" />
                                            </td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <FlagBadge active={row.unusual} label="UN" />
                                            </td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <FlagBadge active={row.likuid} label="LQ" />
                                            </td>

                                            {/* Confluence */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <span className={cn("text-[11px] tracking-widest", conflConfig.color)} title={`${row.confluence_status}: ${row.positive_methods.join(', ')}`}>
                                                    {conflConfig.label}
                                                </span>
                                            </td>

                                            {/* Price */}
                                            <td className="px-1.5 py-1 text-right border-r border-zinc-800/30 tabular-nums text-zinc-300 font-bold text-[11px]">
                                                {row.price > 0 ? row.price.toLocaleString('id-ID') : '—'}
                                            </td>

                                            {/* %1d */}
                                            <td className="px-1.5 py-1 text-right border-r border-zinc-800/30">
                                                {row.pct_1d !== 0 ? (
                                                    <span className={cn(
                                                        "tabular-nums font-bold text-[11px]",
                                                        row.pct_1d > 0 ? 'text-emerald-400' : 'text-red-400'
                                                    )}>
                                                        {row.pct_1d > 0 ? '+' : ''}{row.pct_1d.toFixed(1)}%
                                                    </span>
                                                ) : <span className="text-zinc-700">0%</span>}
                                            </td>

                                            {/* MA Above Count */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <span className={cn(
                                                    "text-[10px] font-bold",
                                                    row.ma_above_count >= 4 ? 'text-emerald-400' :
                                                    row.ma_above_count >= 2 ? 'text-blue-400' :
                                                    row.ma_above_count >= 1 ? 'text-orange-400' : 'text-zinc-600'
                                                )}>
                                                    {row.ma_above_count}/5
                                                </span>
                                            </td>

                                            {/* Weekly Accumulation */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.w_4} /></td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.w_3} /></td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.w_2} /></td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.w_1} /></td>

                                            {/* Daily Flow per method */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.d_0_mm} /></td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.d_0_nr} /></td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.d_0_ff} /></td>

                                            {/* Institutional & Foreign Net */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.inst_net_lot} /></td>
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30"><FlowCell value={row.foreign_net_lot} /></td>

                                            {/* Inventory Accum Brokers */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                {(row.inv_accum_brokers ?? 0) > 0 ? (
                                                    <span className="text-[9px] font-bold">
                                                        <span className="text-emerald-400">{row.inv_accum_brokers}A</span>
                                                        {(row.inv_tektok_brokers ?? 0) > 0 && (
                                                            <span className="text-red-400 ml-0.5">{row.inv_tektok_brokers}T</span>
                                                        )}
                                                        {(row.inv_clean_brokers ?? 0) > 0 && (
                                                            <span className="text-cyan-400 ml-0.5">{row.inv_clean_brokers}✓</span>
                                                        )}
                                                    </span>
                                                ) : <span className="text-zinc-800 text-[9px]">—</span>}
                                            </td>

                                            {/* Txn MM Cumulative */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                {row.txn_mm_cum != null && row.txn_mm_cum !== 0 ? (
                                                    <span className={cn(
                                                        "text-[9px] font-bold tabular-nums",
                                                        row.txn_mm_cum > 0 ? 'text-emerald-400' : 'text-red-400'
                                                    )}>
                                                        {row.txn_mm_cum > 0 ? '+' : ''}{row.txn_mm_cum.toFixed(0)}
                                                    </span>
                                                ) : <span className="text-zinc-800 text-[9px]">—</span>}
                                            </td>

                                            {/* Txn Foreign Cumulative */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                {row.txn_foreign_cum != null && row.txn_foreign_cum !== 0 ? (
                                                    <span className={cn(
                                                        "text-[9px] font-bold tabular-nums",
                                                        row.txn_foreign_cum > 0 ? 'text-emerald-400' : 'text-red-400'
                                                    )}>
                                                        {row.txn_foreign_cum > 0 ? '+' : ''}{row.txn_foreign_cum.toFixed(0)}
                                                    </span>
                                                ) : <span className="text-zinc-800 text-[9px]">—</span>}
                                            </td>

                                            {/* Top Buyer & Seller */}
                                            <td className="px-1 py-1 text-center border-r border-zinc-800/30">
                                                <span className="text-emerald-400 font-bold text-[10px]">{row.top_buyer || '—'}</span>
                                            </td>
                                            <td className="px-1 py-1 text-center">
                                                <span className="text-red-400 font-bold text-[10px]">{row.top_seller || '—'}</span>
                                            </td>
                                        </tr>
                                    );
                                })
                            ) : (
                                <tr>
                                    <td colSpan={27} className="px-4 py-32 text-center text-zinc-600 italic">
                                        <div className="flex flex-col items-center gap-2">
                                            <AlertCircle className="w-6 h-6 opacity-20" />
                                            <span>{data.length === 0 ? "No data available. Run a Full Sync on Market Summary first." : "No stocks match your filter criteria."}</span>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Footer */}
            <div className="bg-[#181a1f] border-t border-zinc-800 px-3 py-1 text-[9px] text-zinc-500 flex justify-between items-center select-none h-[28px]">
                <div className="flex gap-4 items-center">
                    <span>Showing {paginatedData.length} of {processedData.length} stocks</span>
                    {error && <span className="text-red-500 flex items-center gap-1 font-bold"><AlertCircle className="w-3 h-3" /> {error}</span>}
                </div>

                {/* Pagination */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-1.5 py-0.5 bg-zinc-800 rounded hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed text-zinc-300 text-[8px]"
                    >
                        Prev
                    </button>
                    <span className="text-zinc-400 text-[8px] mx-1">Page {currentPage} of {totalPages || 1}</span>
                    <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages || totalPages === 0}
                        className="px-1.5 py-0.5 bg-zinc-800 rounded hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed text-zinc-300 text-[8px]"
                    >
                        Next
                    </button>
                </div>

                <button
                    onClick={handleExportCSV}
                    className="flex items-center gap-1 opacity-50 hover:opacity-100 transition-opacity cursor-pointer text-[8px]"
                >
                    <Download className="w-2.5 h-2.5" /> Export CSV
                </button>
            </div>
        </div>

        {/* Stock Detail Modal */}
        <StockDetailModal
            ticker={selectedTicker}
            date={analysisDate || undefined}
            onClose={() => setSelectedTicker(null)}
        />
        </>
    );
}
