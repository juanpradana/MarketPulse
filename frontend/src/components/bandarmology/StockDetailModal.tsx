'use client';

import React, { useEffect, useState } from 'react';
import { bandarmologyApi, StockDetailResponse } from '@/services/api/bandarmology';
import {
    X, TrendingUp, TrendingDown, Target, Shield, AlertTriangle,
    ArrowUpRight, ArrowDownRight, Loader2, BarChart3, Users, DollarSign,
    Crosshair, Activity, Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface StockDetailModalProps {
    ticker: string | null;
    date?: string;
    onClose: () => void;
}

function MetricCard({ label, value, sub, color = 'text-zinc-300', icon }: {
    label: string; value: string | number; sub?: string; color?: string;
    icon?: React.ReactNode;
}) {
    return (
        <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/30">
            <div className="flex items-center gap-1.5 mb-1">
                {icon}
                <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">{label}</span>
            </div>
            <div className={cn("text-lg font-black tabular-nums", color)}>{value}</div>
            {sub && <div className="text-[9px] text-zinc-500 mt-0.5">{sub}</div>}
        </div>
    );
}

function FlowBar({ label, value, maxAbs, color }: {
    label: string; value: number; maxAbs: number; color: string;
}) {
    const pct = maxAbs > 0 ? Math.min(Math.abs(value) / maxAbs * 100, 100) : 0;
    const isPositive = value > 0;
    return (
        <div className="flex items-center gap-2 text-[10px]">
            <span className="w-8 text-right text-zinc-500 font-bold">{label}</span>
            <div className="flex-1 h-3 bg-zinc-800 rounded-full overflow-hidden relative">
                <div
                    className={cn("h-full rounded-full transition-all", color)}
                    style={{ width: `${pct}%` }}
                />
            </div>
            <span className={cn("w-16 text-right font-bold tabular-nums",
                isPositive ? 'text-emerald-400' : value < 0 ? 'text-red-400' : 'text-zinc-600'
            )}>
                {isPositive ? '+' : ''}{value.toFixed(1)}B
            </span>
        </div>
    );
}

function SignalBadge({ signal, description }: { signal: string; description: string }) {
    const isPositive = signal.includes('accum') || signal.includes('buy') ||
        signal.includes('clean') || signal.includes('up') || signal.includes('inflow') ||
        signal.includes('positive') || signal.includes('strong') || signal.includes('low_cross') ||
        signal.includes('near_floor') || signal.includes('below_floor') ||
        signal.includes('dominated') || signal.includes('synergy') ||
        signal.includes('ctrl_clean') || signal.includes('ctrl_coordinated') ||
        signal.includes('ctrl_ready') || signal.includes('ctrl_near_cost') ||
        signal.includes('ctrl_below_cost') || signal.includes('ctrl_loading') ||
        signal.includes('xref_bandar_strong_buy') || signal.includes('xref_bandar_buying') ||
        signal.includes('xref_bandar_mild_buy') || signal.includes('consistency_high') ||
        signal.includes('consistency_bandar_buy');
    const isWarning = signal.includes('warning') || signal.includes('sell') ||
        signal.includes('outflow') || signal.includes('high_cross') || signal.includes('tektok') ||
        signal.includes('ctrl_distributing') || signal.includes('ctrl_far_above') ||
        signal.includes('ctrl_heavy_dist') || signal.includes('ctrl_full_exit') ||
        signal.includes('ctrl_moderate_dist') || signal.includes('ctrl_brokers_selling') ||
        signal.includes('xref_bandar_strong_sell') || signal.includes('xref_bandar_selling') ||
        signal.includes('xref_bandar_mild_sell') || signal.includes('consistency_bandar_sell');

    return (
        <div className={cn(
            "px-2 py-1 rounded text-[9px] border",
            isPositive ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
            isWarning ? "bg-red-500/10 border-red-500/20 text-red-400" :
            "bg-blue-500/10 border-blue-500/20 text-blue-400"
        )}>
            {description}
        </div>
    );
}

export default function StockDetailModal({ ticker, date, onClose }: StockDetailModalProps) {
    const [data, setData] = useState<StockDetailResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!ticker) return;
        const fetchDetail = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await bandarmologyApi.getStockDetail(ticker, date);
                setData(result);
            } catch (err: any) {
                setError(err.message || 'Failed to load stock detail');
            } finally {
                setLoading(false);
            }
        };
        fetchDetail();
    }, [ticker, date]);

    if (!ticker) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
            <div
                className="bg-[#13151b] border border-zinc-700/50 rounded-xl shadow-2xl w-[95vw] max-w-[1100px] max-h-[90vh] overflow-hidden flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-purple-900/60 to-blue-900/60 border-b border-zinc-700/30">
                    <div className="flex items-center gap-3">
                        <span className="text-xl font-black text-blue-300 tracking-tight">{ticker}</span>
                        {data && (
                            <>
                                <span className="text-zinc-300 font-bold text-lg tabular-nums">
                                    {data.price > 0 ? data.price.toLocaleString('id-ID') : '—'}
                                </span>
                                {data.pct_1d !== 0 && (
                                    <span className={cn(
                                        "text-sm font-bold flex items-center gap-0.5",
                                        data.pct_1d > 0 ? 'text-emerald-400' : 'text-red-400'
                                    )}>
                                        {data.pct_1d > 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                                        {data.pct_1d > 0 ? '+' : ''}{data.pct_1d.toFixed(1)}%
                                    </span>
                                )}
                                {data.trade_type && data.trade_type !== '—' && (
                                    <span className={cn(
                                        "text-[10px] font-black px-2 py-0.5 rounded border",
                                        (data.deep_trade_type || data.trade_type) === 'SELL' ? 'bg-red-500/20 border-red-500/30 text-red-300' :
                                        data.trade_type === 'BOTH' ? 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300' :
                                        data.trade_type === 'SWING' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300' :
                                        data.trade_type === 'INTRADAY' ? 'bg-cyan-500/20 border-cyan-500/30 text-cyan-300' :
                                        'bg-orange-500/20 border-orange-500/30 text-orange-300'
                                    )}>
                                        {data.deep_trade_type && data.deep_trade_type !== '—' ? data.deep_trade_type : data.trade_type}
                                    </span>
                                )}
                            </>
                        )}
                    </div>
                    <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors p-1 rounded hover:bg-zinc-700/50">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-5 space-y-5 scrollbar-thin scrollbar-thumb-zinc-800">
                    {loading && (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
                        </div>
                    )}

                    {error && (
                        <div className="text-red-400 text-sm text-center py-10">
                            <AlertTriangle className="w-6 h-6 mx-auto mb-2 opacity-50" />
                            {error}
                        </div>
                    )}

                    {data && !loading && (
                        <>
                            {/* Score Overview */}
                            <div className="grid grid-cols-6 gap-3">
                                <MetricCard
                                    label="Base Score"
                                    value={data.base_score}
                                    sub={`/ ${data.max_base_score}`}
                                    color={data.base_score >= 60 ? 'text-emerald-400' : data.base_score >= 40 ? 'text-blue-400' : 'text-orange-400'}
                                    icon={<BarChart3 className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label="Deep Score"
                                    value={data.deep_score ? `+${data.deep_score}` : '—'}
                                    sub={data.has_deep ? 'Analyzed' : 'Not analyzed'}
                                    color={data.deep_score && data.deep_score >= 40 ? 'text-amber-400' : data.deep_score && data.deep_score > 0 ? 'text-blue-400' : 'text-zinc-600'}
                                    icon={<Activity className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label="Combined"
                                    value={data.combined_score ?? data.base_score}
                                    sub={`/ ${data.max_combined_score ?? 200}`}
                                    color={(data.combined_score ?? data.base_score) >= 80 ? 'text-emerald-400' : (data.combined_score ?? data.base_score) >= 50 ? 'text-blue-400' : 'text-orange-400'}
                                    icon={<Target className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label="Breakout Prob"
                                    value={data.breakout_probability ? `${data.breakout_probability}%` : '—'}
                                    sub={data.breakout_probability ? (data.breakout_probability >= 70 ? 'HIGH' : data.breakout_probability >= 40 ? 'MEDIUM' : 'LOW') : ''}
                                    color={
                                        (data.breakout_probability ?? 0) >= 70 ? 'text-emerald-400' :
                                        (data.breakout_probability ?? 0) >= 40 ? 'text-amber-400' :
                                        (data.breakout_probability ?? 0) > 0 ? 'text-orange-400' : 'text-zinc-600'
                                    }
                                    icon={<Zap className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label="Entry Price"
                                    value={data.entry_price ? data.entry_price.toLocaleString('id-ID') : '—'}
                                    sub={data.entry_price && data.price ? `${((data.price - data.entry_price) / data.entry_price * 100).toFixed(1)}% from current` : ''}
                                    color="text-cyan-400"
                                    icon={<Crosshair className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label="Target Price"
                                    value={data.target_price ? data.target_price.toLocaleString('id-ID') : '—'}
                                    sub={data.risk_reward_ratio ? `R:R = 1:${data.risk_reward_ratio}` : ''}
                                    color="text-yellow-400"
                                    icon={<TrendingUp className="w-3 h-3 text-zinc-600" />}
                                />
                            </div>

                            {/* Entry/Target/SL Bar */}
                            {data.entry_price && data.target_price && data.stop_loss ? (
                                <div className="bg-zinc-800/30 rounded-lg p-3 border border-zinc-700/20">
                                    <div className="flex items-center justify-between text-[10px] mb-2">
                                        <span className="text-red-400 font-bold">SL: {data.stop_loss.toLocaleString('id-ID')}</span>
                                        <span className="text-cyan-400 font-bold">Entry: {data.entry_price.toLocaleString('id-ID')}</span>
                                        <span className="text-zinc-300 font-bold">Current: {data.price.toLocaleString('id-ID')}</span>
                                        <span className="text-yellow-400 font-bold">Target: {data.target_price.toLocaleString('id-ID')}</span>
                                    </div>
                                    <div className="relative h-3 bg-zinc-800 rounded-full overflow-hidden">
                                        {(() => {
                                            const min = data.stop_loss! * 0.99;
                                            const max = data.target_price! * 1.01;
                                            const range = max - min;
                                            const slPct = ((data.stop_loss! - min) / range) * 100;
                                            const entryPct = ((data.entry_price! - min) / range) * 100;
                                            const currentPct = ((data.price - min) / range) * 100;
                                            const targetPct = ((data.target_price! - min) / range) * 100;
                                            return (
                                                <>
                                                    <div className="absolute h-full bg-red-500/30" style={{ left: 0, width: `${slPct}%` }} />
                                                    <div className="absolute h-full bg-emerald-500/20" style={{ left: `${entryPct}%`, width: `${targetPct - entryPct}%` }} />
                                                    <div className="absolute w-0.5 h-full bg-red-500" style={{ left: `${slPct}%` }} />
                                                    <div className="absolute w-0.5 h-full bg-cyan-400" style={{ left: `${entryPct}%` }} />
                                                    <div className="absolute w-1.5 h-full bg-white rounded-full" style={{ left: `${currentPct}%`, transform: 'translateX(-50%)' }} />
                                                    <div className="absolute w-0.5 h-full bg-yellow-400" style={{ left: `${targetPct}%` }} />
                                                </>
                                            );
                                        })()}
                                    </div>
                                </div>
                            ) : null}

                            {/* Controlling Brokers & Accumulation Phase */}
                            {data.has_deep && data.controlling_brokers && data.controlling_brokers.length > 0 && (
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                                            <Shield className="w-3.5 h-3.5 text-amber-400" />
                                            Controlling Brokers (Bandarmology)
                                        </h3>
                                        <div className="flex items-center gap-2">
                                            {data.accum_phase && data.accum_phase !== 'UNKNOWN' && (
                                                <span className={cn(
                                                    "text-[9px] font-black px-2 py-0.5 rounded border",
                                                    data.accum_phase === 'ACCUMULATION' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300' :
                                                    data.accum_phase === 'HOLDING' ? 'bg-blue-500/20 border-blue-500/30 text-blue-300' :
                                                    data.accum_phase === 'DISTRIBUTION' ? 'bg-red-500/20 border-red-500/30 text-red-300' :
                                                    'bg-zinc-700/50 border-zinc-600/30 text-zinc-400'
                                                )}>
                                                    {data.accum_phase}
                                                </span>
                                            )}
                                            {data.breakout_signal && data.breakout_signal !== 'NONE' && (
                                                <span className={cn(
                                                    "text-[9px] font-black px-2 py-0.5 rounded border flex items-center gap-1",
                                                    data.breakout_signal === 'READY' ? 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300' :
                                                    data.breakout_signal === 'LAUNCHED' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300' :
                                                    data.breakout_signal === 'LOADING' ? 'bg-cyan-500/20 border-cyan-500/30 text-cyan-300' :
                                                    data.breakout_signal === 'DISTRIBUTING' ? 'bg-red-500/20 border-red-500/30 text-red-300' :
                                                    'bg-zinc-700/50 border-zinc-600/30 text-zinc-400'
                                                )}>
                                                    <Zap className="w-3 h-3" />
                                                    {data.breakout_signal}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Summary row */}
                                    <div className="flex items-center gap-4 text-[9px] mb-3 pb-2 border-b border-zinc-700/30">
                                        {data.accum_start_date && (
                                            <span className="text-zinc-500">
                                                Accumulation started: <span className="text-amber-400 font-bold">{data.accum_start_date}</span>
                                            </span>
                                        )}
                                        {data.bandar_avg_cost ? (
                                            <span className="text-zinc-500">
                                                Bandar avg cost: <span className="text-cyan-400 font-bold">{data.bandar_avg_cost.toLocaleString('id-ID')}</span>
                                            </span>
                                        ) : null}
                                        {data.coordination_score ? (
                                            <span className="text-zinc-500">
                                                Coordination: <span className={cn(
                                                    "font-bold",
                                                    data.coordination_score >= 80 ? 'text-emerald-400' :
                                                    data.coordination_score >= 60 ? 'text-blue-400' : 'text-orange-400'
                                                )}>{data.coordination_score}%</span>
                                            </span>
                                        ) : null}
                                        {data.phase_confidence && data.phase_confidence !== 'LOW' && (
                                            <span className="text-zinc-500">
                                                Confidence: <span className={cn(
                                                    "font-bold",
                                                    data.phase_confidence === 'HIGH' ? 'text-emerald-400' : 'text-blue-400'
                                                )}>{data.phase_confidence}</span>
                                            </span>
                                        )}
                                    </div>

                                    {/* Distribution Alert Banner */}
                                    {data.distribution_alert && data.distribution_alert !== 'NONE' && (
                                        <div className={cn(
                                            "flex items-center gap-2 px-3 py-2 rounded-lg mb-3 border text-[10px] font-bold",
                                            data.distribution_alert === 'FULL_EXIT' ? 'bg-red-500/20 border-red-500/40 text-red-300' :
                                            data.distribution_alert === 'HEAVY' ? 'bg-red-500/15 border-red-500/30 text-red-400' :
                                            data.distribution_alert === 'MODERATE' ? 'bg-orange-500/15 border-orange-500/30 text-orange-400' :
                                            'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                                        )}>
                                            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                                            <div className="flex-1">
                                                {data.distribution_alert === 'FULL_EXIT' && 'JUAL SEMUA! Bandar sudah hampir keluar sepenuhnya'}
                                                {data.distribution_alert === 'HEAVY' && 'BUANG BARANG! Bandar sudah distribusi >50% dari puncak kepemilikan'}
                                                {data.distribution_alert === 'MODERATE' && 'Hati-hati: Bandar mulai distribusi signifikan'}
                                                {data.distribution_alert === 'EARLY' && 'Perhatikan: Tanda awal distribusi terdeteksi'}
                                            </div>
                                            <div className="flex items-center gap-3 flex-shrink-0">
                                                <span className="text-[9px]">
                                                    Peak: <span className="text-white">{(data.bandar_peak_lot ?? 0).toLocaleString('id-ID')} lot</span>
                                                </span>
                                                <span className="text-[9px]">
                                                    Sold: <span className={cn(
                                                        "font-black",
                                                        (data.bandar_distribution_pct ?? 0) >= 50 ? 'text-red-300' :
                                                        (data.bandar_distribution_pct ?? 0) >= 25 ? 'text-orange-300' : 'text-yellow-300'
                                                    )}>{(data.bandar_distribution_pct ?? 0).toFixed(1)}%</span>
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Cross-Reference: Bandar Activity Today */}
                                    {data.bandar_confirmation && data.bandar_confirmation !== 'NONE' && data.bandar_confirmation !== 'NEUTRAL' && (
                                        <div className={cn(
                                            "flex items-center gap-2 px-3 py-2 rounded-lg mb-3 border text-[10px] font-bold",
                                            data.bandar_confirmation === 'STRONG_BUY' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' :
                                            data.bandar_confirmation === 'BUY' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' :
                                            data.bandar_confirmation === 'MILD_BUY' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                                            data.bandar_confirmation === 'STRONG_SELL' ? 'bg-red-500/20 border-red-500/40 text-red-300' :
                                            data.bandar_confirmation === 'SELL' ? 'bg-red-500/15 border-red-500/30 text-red-400' :
                                            'bg-orange-500/10 border-orange-500/20 text-orange-400'
                                        )}>
                                            {data.bandar_confirmation.includes('BUY') ? (
                                                <TrendingUp className="w-4 h-4 flex-shrink-0" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 flex-shrink-0" />
                                            )}
                                            <div className="flex-1">
                                                {data.bandar_confirmation === 'STRONG_BUY' && `Bandar AKTIF BELI hari ini (${data.bandar_buy_today_count} broker)`}
                                                {data.bandar_confirmation === 'BUY' && `Bandar beli hari ini (${data.bandar_buy_today_count} broker)`}
                                                {data.bandar_confirmation === 'MILD_BUY' && `Bandar beli hari ini (1 broker)`}
                                                {data.bandar_confirmation === 'STRONG_SELL' && `WARNING: Bandar JUAL hari ini (${data.bandar_sell_today_count} broker)`}
                                                {data.bandar_confirmation === 'SELL' && `Hati-hati: Bandar jual hari ini (${data.bandar_sell_today_count} broker)`}
                                                {data.bandar_confirmation === 'MILD_SELL' && `Bandar jual hari ini (1 broker)`}
                                            </div>
                                            <div className="flex items-center gap-3 flex-shrink-0 text-[9px]">
                                                {(data.bandar_buy_today_lot ?? 0) > 0 && (
                                                    <span>Buy: <span className="text-emerald-300 font-black">+{(data.bandar_buy_today_lot ?? 0).toLocaleString('id-ID')}</span></span>
                                                )}
                                                {(data.bandar_sell_today_lot ?? 0) > 0 && (
                                                    <span>Sell: <span className="text-red-300 font-black">-{(data.bandar_sell_today_lot ?? 0).toLocaleString('id-ID')}</span></span>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* Breakout Probability Factors */}
                                    {data.breakout_probability != null && data.breakout_probability > 0 && data.breakout_factors && (
                                        <div className="mb-3 p-3 bg-zinc-800/30 rounded-lg border border-zinc-700/20">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Breakout Probability Factors</span>
                                                <span className={cn(
                                                    "text-sm font-black",
                                                    data.breakout_probability >= 70 ? 'text-emerald-400' :
                                                    data.breakout_probability >= 40 ? 'text-amber-400' : 'text-orange-400'
                                                )}>{data.breakout_probability}%</span>
                                            </div>
                                            <div className="grid grid-cols-4 gap-x-4 gap-y-1">
                                                {Object.entries(data.breakout_factors).map(([key, val]) => (
                                                    <div key={key} className="flex items-center gap-1.5">
                                                        <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                                            <div
                                                                className={cn("h-full rounded-full",
                                                                    val >= 70 ? 'bg-emerald-500' :
                                                                    val >= 40 ? 'bg-amber-500' : 'bg-red-500'
                                                                )}
                                                                style={{ width: `${val}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-[8px] text-zinc-500 w-20 truncate">{key.replace(/_/g, ' ')}</span>
                                                        <span className={cn("text-[8px] font-bold w-6 text-right",
                                                            val >= 70 ? 'text-emerald-400' :
                                                            val >= 40 ? 'text-amber-400' : 'text-red-400'
                                                        )}>{val}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Multi-Day Consistency */}
                                    {(data.broksum_days_analyzed ?? 0) >= 2 && (
                                        <div className="mb-3 flex items-center gap-3 text-[9px] px-1">
                                            <span className="text-zinc-500">
                                                Consistency ({data.broksum_days_analyzed}d):
                                                <span className={cn(
                                                    "font-black ml-1",
                                                    (data.broksum_consistency_score ?? 0) >= 70 ? 'text-emerald-400' :
                                                    (data.broksum_consistency_score ?? 0) >= 40 ? 'text-amber-400' : 'text-orange-400'
                                                )}>{data.broksum_consistency_score ?? 0}/100</span>
                                            </span>
                                            {data.broksum_consistent_buyers && data.broksum_consistent_buyers.length > 0 && (
                                                <span className="text-zinc-500">
                                                    Consistent buyers: {data.broksum_consistent_buyers.slice(0, 5).map(b => (
                                                        <span key={b.code} className={cn("font-bold ml-0.5", b.is_bandar ? 'text-emerald-400' : 'text-zinc-400')}>
                                                            {b.code}{b.is_bandar ? '★' : ''}
                                                        </span>
                                                    ))}
                                                </span>
                                            )}
                                            {data.broksum_consistent_sellers && data.broksum_consistent_sellers.filter(s => s.is_bandar).length > 0 && (
                                                <span className="text-red-400">
                                                    Bandar selling: {data.broksum_consistent_sellers.filter(s => s.is_bandar).map(s => s.code).join(', ')}
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* Broker table */}
                                    <table className="w-full text-[10px]">
                                        <thead>
                                            <tr className="text-zinc-600 border-b border-zinc-700/30">
                                                <th className="text-left py-1 font-bold">Broker</th>
                                                <th className="text-right py-1 font-bold">Net Lot</th>
                                                <th className="text-right py-1 font-bold">Avg Buy</th>
                                                <th className="text-right py-1 font-bold">Buy Lots</th>
                                                <th className="text-right py-1 font-bold">Sell Lots</th>
                                                <th className="text-left py-1 font-bold pl-3">Turn Date</th>
                                                <th className="text-right py-1 font-bold">Peak Lot</th>
                                                <th className="text-right py-1 font-bold">Dist%</th>
                                                <th className="text-left py-1 font-bold pl-3">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.controlling_brokers.map((cb, i) => (
                                                <tr key={i} className="border-b border-zinc-800/20 hover:bg-zinc-800/30">
                                                    <td className="py-1 font-bold">
                                                        <span className={cn(
                                                            cb.is_clean ? 'text-emerald-400' :
                                                            cb.is_tektok ? 'text-orange-400' : 'text-zinc-300'
                                                        )}>
                                                            {cb.code}
                                                            {cb.is_clean && <span className="text-emerald-500 ml-0.5">✓</span>}
                                                            {cb.is_tektok && <span className="text-orange-500 ml-0.5">✗</span>}
                                                        </span>
                                                        {cb.broker_class && (
                                                            <span className="text-zinc-600 text-[8px] ml-1">{cb.broker_class}</span>
                                                        )}
                                                    </td>
                                                    <td className="py-1 text-right tabular-nums font-bold text-emerald-400">
                                                        +{cb.net_lot.toLocaleString('id-ID')}
                                                    </td>
                                                    <td className="py-1 text-right tabular-nums text-cyan-400 font-bold">
                                                        {cb.avg_buy_price ? cb.avg_buy_price.toLocaleString('id-ID') : '—'}
                                                    </td>
                                                    <td className="py-1 text-right tabular-nums text-zinc-400">
                                                        {cb.total_buy_lots ? cb.total_buy_lots.toLocaleString('id-ID') : '—'}
                                                    </td>
                                                    <td className="py-1 text-right tabular-nums text-zinc-500">
                                                        {cb.total_sell_lots ? cb.total_sell_lots.toLocaleString('id-ID') : '—'}
                                                    </td>
                                                    <td className="py-1 text-left pl-3 text-zinc-500">
                                                        {cb.turn_date || '—'}
                                                    </td>
                                                    <td className="py-1 text-right tabular-nums text-zinc-400">
                                                        {cb.peak_lot ? cb.peak_lot.toLocaleString('id-ID') : '—'}
                                                    </td>
                                                    <td className={cn(
                                                        "py-1 text-right tabular-nums font-bold",
                                                        cb.distribution_pct >= 50 ? 'text-red-400' :
                                                        cb.distribution_pct >= 25 ? 'text-orange-400' :
                                                        cb.distribution_pct >= 10 ? 'text-yellow-400' : 'text-zinc-500'
                                                    )}>
                                                        {cb.distribution_pct > 0 ? `${cb.distribution_pct.toFixed(1)}%` : '0%'}
                                                    </td>
                                                    <td className="py-1 text-left pl-3">
                                                        <span className={cn(
                                                            "text-[8px] font-bold px-1.5 py-0.5 rounded",
                                                            cb.distribution_pct >= 50 ? 'bg-red-500/20 text-red-400' :
                                                            cb.distribution_pct >= 25 ? 'bg-orange-500/20 text-orange-400' :
                                                            cb.avg_daily_last10 > 50 ? 'bg-emerald-500/20 text-emerald-400' :
                                                            cb.avg_daily_last10 < -50 ? 'bg-red-500/20 text-red-400' :
                                                            'bg-zinc-700/50 text-zinc-500'
                                                        )}>
                                                            {cb.distribution_pct >= 50 ? 'DISTRIBUSI' :
                                                             cb.distribution_pct >= 25 ? 'SELLING' :
                                                             cb.avg_daily_last10 > 50 ? 'BUYING' :
                                                             cb.avg_daily_last10 < -50 ? 'SELLING' : 'HOLDING'}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {/* Two Column Layout */}
                            <div className="grid grid-cols-2 gap-4">
                                {/* Left: Transaction Flow */}
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                        <Activity className="w-3.5 h-3.5 text-purple-400" />
                                        Transaction Flow (6M Cumulative)
                                    </h3>
                                    {data.has_deep ? (
                                        <div className="space-y-2">
                                            {(() => {
                                                const flows = [
                                                    { label: 'MM', value: data.txn_mm_cum ?? 0, color: 'bg-purple-500' },
                                                    { label: 'FGN', value: data.txn_foreign_cum ?? 0, color: 'bg-blue-500' },
                                                    { label: 'INST', value: data.txn_institution_cum ?? 0, color: 'bg-cyan-500' },
                                                    { label: 'RTL', value: data.txn_retail_cum ?? 0, color: 'bg-orange-500' },
                                                ];
                                                const maxAbs = Math.max(...flows.map(f => Math.abs(f.value)), 1);
                                                return flows.map(f => (
                                                    <FlowBar key={f.label} label={f.label} value={f.value} maxAbs={maxAbs} color={f.color} />
                                                ));
                                            })()}
                                            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-zinc-700/30">
                                                <span className="text-[9px] text-zinc-500">Cross Index:</span>
                                                <span className={cn(
                                                    "text-[10px] font-bold",
                                                    (data.txn_cross_index ?? 0) < 0.3 ? 'text-emerald-400' :
                                                    (data.txn_cross_index ?? 0) < 0.5 ? 'text-blue-400' : 'text-red-400'
                                                )}>
                                                    {(data.txn_cross_index ?? 0).toFixed(2)}
                                                </span>
                                                <span className="text-[9px] text-zinc-500 ml-2">MM Trend:</span>
                                                <span className={cn(
                                                    "text-[10px] font-bold",
                                                    data.txn_mm_trend?.includes('UP') ? 'text-emerald-400' :
                                                    data.txn_mm_trend?.includes('DOWN') ? 'text-red-400' : 'text-zinc-500'
                                                )}>
                                                    {data.txn_mm_trend || '—'}
                                                </span>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-zinc-600 text-[10px] text-center py-6">No deep analysis data. Run Deep Analyze first.</div>
                                    )}
                                </div>

                                {/* Right: Inventory Brokers */}
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                        <Users className="w-3.5 h-3.5 text-emerald-400" />
                                        Inventory Brokers
                                    </h3>
                                    {data.has_deep && (data.inv_accum_brokers ?? 0) > 0 ? (
                                        <div className="space-y-1.5">
                                            <div className="flex items-center gap-3 text-[9px] mb-2">
                                                <span className="text-emerald-400 font-bold">{data.inv_accum_brokers} Accumulating</span>
                                                <span className="text-red-400 font-bold">{data.inv_distrib_brokers} Distributing</span>
                                                <span className="text-cyan-400 font-bold">{data.inv_clean_brokers}&#10003;</span>
                                                {(data.inv_tektok_brokers ?? 0) > 0 && (
                                                    <span className="text-orange-400 font-bold">{data.inv_tektok_brokers} Tektok</span>
                                                )}
                                            </div>
                                            <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px]">
                                                <div className="text-zinc-500 font-bold border-b border-zinc-700/30 pb-0.5">Accum Lot</div>
                                                <div className="text-zinc-500 font-bold border-b border-zinc-700/30 pb-0.5 text-right">Distrib Lot</div>
                                                <div className="text-emerald-400 font-bold tabular-nums">
                                                    +{(data.inv_total_accum_lot ?? 0).toLocaleString('id-ID')}
                                                </div>
                                                <div className="text-red-400 font-bold tabular-nums text-right">
                                                    -{(data.inv_total_distrib_lot ?? 0).toLocaleString('id-ID')}
                                                </div>
                                            </div>
                                            {data.inv_top_accum_broker && (
                                                <div className="text-[9px] text-zinc-500 mt-1">
                                                    Top Accumulator: <span className="text-emerald-400 font-bold">{data.inv_top_accum_broker}</span>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="text-zinc-600 text-[10px] text-center py-6">No inventory data available.</div>
                                    )}
                                </div>
                            </div>

                            {/* Broker Summary */}
                            <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                    <DollarSign className="w-3.5 h-3.5 text-yellow-400" />
                                    Broker Summary (Today)
                                </h3>
                                {data.broker_summary && (data.broker_summary.buy.length > 0 || data.broker_summary.sell.length > 0) ? (
                                    <div className="grid grid-cols-2 gap-4">
                                        {/* Buy Side */}
                                        <div>
                                            <div className="text-[9px] font-bold text-emerald-400 uppercase mb-1.5">Net Buyers</div>
                                            <table className="w-full text-[10px]">
                                                <thead>
                                                    <tr className="text-zinc-600 border-b border-zinc-700/30">
                                                        <th className="text-left py-0.5 font-bold">Broker</th>
                                                        <th className="text-right py-0.5 font-bold">Net Lot</th>
                                                        <th className="text-right py-0.5 font-bold">Value</th>
                                                        <th className="text-right py-0.5 font-bold">Avg</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {data.broker_summary.buy.slice(0, 8).map((b, i) => (
                                                        <tr key={i} className="border-b border-zinc-800/20 hover:bg-zinc-800/30">
                                                            <td className="py-0.5 text-emerald-400 font-bold">{b.broker}</td>
                                                            <td className="py-0.5 text-right tabular-nums text-zinc-300">{Number(b.nlot).toLocaleString('id-ID')}</td>
                                                            <td className="py-0.5 text-right tabular-nums text-zinc-500">{b.nval ?? '—'}</td>
                                                            <td className="py-0.5 text-right tabular-nums text-zinc-400">{b.avg_price ? Number(b.avg_price).toLocaleString('id-ID') : '—'}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                            {data.broksum_avg_buy_price ? (
                                                <div className="mt-2 text-[9px] text-zinc-500">
                                                    Weighted Avg Buy: <span className="text-cyan-400 font-bold">{data.broksum_avg_buy_price.toLocaleString('id-ID')}</span>
                                                </div>
                                            ) : null}
                                        </div>

                                        {/* Sell Side */}
                                        <div>
                                            <div className="text-[9px] font-bold text-red-400 uppercase mb-1.5">Net Sellers</div>
                                            <table className="w-full text-[10px]">
                                                <thead>
                                                    <tr className="text-zinc-600 border-b border-zinc-700/30">
                                                        <th className="text-left py-0.5 font-bold">Broker</th>
                                                        <th className="text-right py-0.5 font-bold">Net Lot</th>
                                                        <th className="text-right py-0.5 font-bold">Value</th>
                                                        <th className="text-right py-0.5 font-bold">Avg</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {data.broker_summary.sell.slice(0, 8).map((s, i) => (
                                                        <tr key={i} className="border-b border-zinc-800/20 hover:bg-zinc-800/30">
                                                            <td className="py-0.5 text-red-400 font-bold">{s.broker}</td>
                                                            <td className="py-0.5 text-right tabular-nums text-zinc-300">{Number(s.nlot).toLocaleString('id-ID')}</td>
                                                            <td className="py-0.5 text-right tabular-nums text-zinc-500">{s.nval ?? '—'}</td>
                                                            <td className="py-0.5 text-right tabular-nums text-zinc-400">{s.avg_price ? Number(s.avg_price).toLocaleString('id-ID') : '—'}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                            {data.broksum_avg_sell_price ? (
                                                <div className="mt-2 text-[9px] text-zinc-500">
                                                    Weighted Avg Sell: <span className="text-orange-400 font-bold">{data.broksum_avg_sell_price.toLocaleString('id-ID')}</span>
                                                </div>
                                            ) : null}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-zinc-600 text-[10px] text-center py-4">No broker summary data. Run Deep Analyze to scrape.</div>
                                )}

                                {/* Institutional/Foreign Net */}
                                {data.has_deep && (data.broksum_net_institutional || data.broksum_net_foreign) ? (
                                    <div className="flex items-center gap-4 mt-3 pt-2 border-t border-zinc-700/30 text-[10px]">
                                        <span className="text-zinc-500">Institutional Net:</span>
                                        <span className={cn("font-bold", (data.broksum_net_institutional ?? 0) > 0 ? 'text-emerald-400' : 'text-red-400')}>
                                            {(data.broksum_net_institutional ?? 0) > 0 ? '+' : ''}{(data.broksum_net_institutional ?? 0).toLocaleString('id-ID')} lot
                                        </span>
                                        <span className="text-zinc-500 ml-2">Foreign Net:</span>
                                        <span className={cn("font-bold", (data.broksum_net_foreign ?? 0) > 0 ? 'text-emerald-400' : 'text-red-400')}>
                                            {(data.broksum_net_foreign ?? 0) > 0 ? '+' : ''}{(data.broksum_net_foreign ?? 0).toLocaleString('id-ID')} lot
                                        </span>
                                    </div>
                                ) : null}
                            </div>

                            {/* Weekly Flow + Signals */}
                            <div className="grid grid-cols-2 gap-4">
                                {/* Weekly Flow */}
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                        <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
                                        Weekly Accumulation
                                    </h3>
                                    <div className="grid grid-cols-4 gap-2 text-center">
                                        {[
                                            { label: 'W-4', value: data.w_4 },
                                            { label: 'W-3', value: data.w_3 },
                                            { label: 'W-2', value: data.w_2 },
                                            { label: 'W-1', value: data.w_1 },
                                        ].map(w => (
                                            <div key={w.label} className="bg-zinc-800/50 rounded p-2">
                                                <div className="text-[8px] text-zinc-600 font-bold">{w.label}</div>
                                                <div className={cn(
                                                    "text-sm font-black tabular-nums",
                                                    w.value > 0 ? 'text-emerald-400' : w.value < 0 ? 'text-red-400' : 'text-zinc-600'
                                                )}>
                                                    {w.value > 0 ? '+' : ''}{w.value?.toFixed(1) ?? '—'}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="grid grid-cols-3 gap-2 text-center mt-2">
                                        {[
                                            { label: 'D-0 MM', value: data.d_0_mm },
                                            { label: 'D-0 NR', value: data.d_0_nr },
                                            { label: 'D-0 FF', value: data.d_0_ff },
                                        ].map(d => (
                                            <div key={d.label} className="bg-zinc-800/50 rounded p-2">
                                                <div className="text-[8px] text-zinc-600 font-bold">{d.label}</div>
                                                <div className={cn(
                                                    "text-sm font-black tabular-nums",
                                                    d.value > 0 ? 'text-emerald-400' : d.value < 0 ? 'text-red-400' : 'text-zinc-600'
                                                )}>
                                                    {d.value > 0 ? '+' : ''}{d.value?.toFixed(1) ?? '—'}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Deep Signals */}
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                        <Zap className="w-3.5 h-3.5 text-amber-400" />
                                        Deep Analysis Signals
                                    </h3>
                                    {data.deep_signals && Object.keys(data.deep_signals).length > 0 ? (
                                        <div className="flex flex-wrap gap-1.5">
                                            {Object.entries(data.deep_signals).map(([key, desc]) => (
                                                <SignalBadge key={key} signal={key} description={desc} />
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-zinc-600 text-[10px] text-center py-6">No signals. Run Deep Analyze first.</div>
                                    )}
                                </div>
                            </div>

                            {/* Top Holders */}
                            {data.top_holders && data.top_holders.length > 0 && (
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                        <Shield className="w-3.5 h-3.5 text-cyan-400" />
                                        Top Holders (Cumulative Net Buy)
                                    </h3>
                                    <div className="flex gap-3">
                                        {data.top_holders.map((h, i) => (
                                            <div key={i} className="bg-zinc-800/50 rounded-lg p-2 text-center min-w-[80px] border border-zinc-700/20">
                                                <div className="text-emerald-400 font-black text-sm">{h.broker_code}</div>
                                                <div className="text-zinc-300 font-bold text-[10px] tabular-nums">
                                                    +{h.total_net_lot.toLocaleString('id-ID')} lot
                                                </div>
                                                <div className="text-zinc-600 text-[8px]">{h.trade_count} trades</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
