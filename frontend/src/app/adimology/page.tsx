'use client';

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { cn } from '@/lib/utils';
import {
    Calculator,
    Zap,
    Target,
    TrendingUp,
    BarChart3,
    Trash2,
    Info,
    ArrowUpRight,
    ChevronDown,
    ChevronUp,
    History,
    Layers,
    Crosshair,
} from 'lucide-react';

// ─── IDX Tick Size Rules ────────────────────────────────────────────────────────
const FRAKSI_RANGES = [
    { min: 0, max: 200, tick: 1, label: 'Fraksi 1' },
    { min: 200, max: 500, tick: 2, label: 'Fraksi 2' },
    { min: 500, max: 2000, tick: 5, label: 'Fraksi 5' },
    { min: 2000, max: 5000, tick: 10, label: 'Fraksi 10' },
    { min: 5000, max: Infinity, tick: 25, label: 'Fraksi 25' },
];

function getTickSize(price: number): number {
    for (const r of FRAKSI_RANGES) {
        if (price < r.max) return r.tick;
    }
    return 25;
}

// Count how many ticks exist between ARB and ARA in each fraksi range
function calculateFraksi(arb: number, ara: number) {
    const result = { f1: 0, f2: 0, f5: 0, f10: 0, f25: 0, total: 0 };
    if (arb <= 0 || ara <= 0 || ara <= arb) return result;

    // Fraksi 1: price < 200, tick = 1
    if (arb < 200) {
        result.f1 = Math.max(0, Math.min(200, ara) - arb);
    }
    // Fraksi 2: price 200-500, tick = 2
    if (ara > 200) {
        result.f2 = Math.max(0, (Math.min(500, ara) - Math.max(200, arb)) / 2);
    }
    // Fraksi 5: price 500-2000, tick = 5
    if (ara > 500) {
        result.f5 = Math.max(0, (Math.min(2000, ara) - Math.max(500, arb)) / 5);
    }
    // Fraksi 10: price 2000-5000, tick = 10
    if (ara > 2000) {
        result.f10 = Math.max(0, (Math.min(5000, ara) - Math.max(2000, arb)) / 10);
    }
    // Fraksi 25: price > 5000, tick = 25
    if (ara > 5000) {
        result.f25 = Math.max(0, (ara - Math.max(5000, arb)) / 25);
    }

    result.total = result.f1 + result.f2 + result.f5 + result.f10 + result.f25;
    return result;
}

// Calculate target price by adding N ticks from startPrice
// Matches the Excel ADIIMOLLOGY formula exactly
function calculateTarget(startPrice: number, ticks: number): number {
    if (ticks <= 0 || startPrice <= 0) return startPrice;

    if (startPrice < 500) {
        // Complex logic: distribute ticks across fraksi 1 (tick=1) and fraksi 2 (tick=2)
        // Step 1: consume ticks in fraksi 1 range (price < 200)
        const f1Ticks = startPrice < 200 ? Math.min(ticks, 200 - startPrice) : 0;
        const remaining = ticks - f1Ticks;
        const priceAfterF1 = startPrice + f1Ticks;

        // Step 2: consume remaining ticks in fraksi 2 range (price 200-500)
        const f2Ticks = (remaining > 0 && priceAfterF1 < 500)
            ? Math.min(remaining, (500 - priceAfterF1) / 2)
            : 0;
        const rawResult = priceAfterF1 + 2 * f2Ticks;

        // Step 3: if result >= 200, round to nearest fraksi 2 tick (even number)
        if (rawResult < 200) {
            return rawResult;
        }
        return Math.round(rawResult / 2) * 2;
    }

    if (startPrice < 2000) return startPrice + ticks * 5;
    if (startPrice < 5000) return startPrice + ticks * 10;
    return startPrice + ticks * 25;
}

// ─── Types ──────────────────────────────────────────────────────────────────────
interface AdimologyResult {
    id: string;
    timestamp: string;
    emiten: string;
    broker: string;
    buyLot: number;
    buyAvg: number;
    arb: number;
    ara: number;
    totalBid: number;
    totalOffer: number;
    // Calculated
    totalBidOffer: number;
    fraksi: { f1: number; f2: number; f5: number; f10: number; f25: number; total: number };
    avgBidOffer: number;
    powerFraksi: number;
    target5pct: number;
    targetLow: number;
    targetHigh: number;
    pctLow: number;
    pctHigh: number;
}

// ─── Components ─────────────────────────────────────────────────────────────────
function InputField({
    label, value, onChange, placeholder, suffix, info, type = 'number',
}: {
    label: string; value: string; onChange: (v: string) => void;
    placeholder?: string; suffix?: string; info?: string; type?: string;
}) {
    return (
        <div className="space-y-1">
            <div className="flex items-center gap-1.5">
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">{label}</label>
                {info && (
                    <div className="group relative">
                        <Info className="w-3 h-3 text-zinc-600 cursor-help" />
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-[9px] text-zinc-300 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                            {info}
                        </div>
                    </div>
                )}
            </div>
            <div className="relative">
                <input
                    type={type}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder}
                    className="w-full bg-zinc-900/80 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                {suffix && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-zinc-600 font-bold">{suffix}</span>
                )}
            </div>
        </div>
    );
}

function ResultCard({
    label, value, sub, color, icon, large,
}: {
    label: string; value: string | number; sub?: string; color: string; icon: React.ReactNode; large?: boolean;
}) {
    return (
        <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-xl p-3 space-y-1">
            <div className="flex items-center gap-1.5 text-zinc-500">
                {icon}
                <span className="text-[9px] font-bold uppercase tracking-wider">{label}</span>
            </div>
            <div className={cn("font-black", large ? "text-2xl" : "text-lg", color)}>
                {typeof value === 'number' ? value.toLocaleString('id-ID') : value}
            </div>
            {sub && <div className="text-[10px] text-zinc-500">{sub}</div>}
        </div>
    );
}

function FraksiBar({ label, value, total, tick }: { label: string; value: number; total: number; tick: number }) {
    const pct = total > 0 ? (value / total) * 100 : 0;
    return (
        <div className="flex items-center gap-2">
            <span className="text-[9px] text-zinc-500 w-14 text-right font-mono">{label}</span>
            <div className="flex-1 h-4 bg-zinc-900 rounded-full overflow-hidden">
                <div
                    className={cn(
                        "h-full rounded-full transition-all duration-500",
                        tick === 1 ? 'bg-blue-500' :
                        tick === 2 ? 'bg-cyan-500' :
                        tick === 5 ? 'bg-emerald-500' :
                        tick === 10 ? 'bg-amber-500' : 'bg-purple-500'
                    )}
                    style={{ width: `${Math.max(pct, value > 0 ? 2 : 0)}%` }}
                />
            </div>
            <span className="text-[10px] text-zinc-400 w-10 text-right font-bold">{value}</span>
            <span className="text-[8px] text-zinc-600 w-8">({pct.toFixed(0)}%)</span>
        </div>
    );
}

// ─── Main Page ──────────────────────────────────────────────────────────────────
export default function AdimologyPage() {
    // Input state
    const [emiten, setEmiten] = useState('');
    const [broker, setBroker] = useState('');
    const [buyLot, setBuyLot] = useState('');
    const [buyAvg, setBuyAvg] = useState('');
    const [arb, setArb] = useState('');
    const [ara, setAra] = useState('');
    const [totalBid, setTotalBid] = useState('');
    const [totalOffer, setTotalOffer] = useState('');

    // History
    const [history, setHistory] = useState<AdimologyResult[]>([]);
    const [showHistory, setShowHistory] = useState(true);

    // Load history from localStorage
    useEffect(() => {
        try {
            const saved = localStorage.getItem('adimology_history');
            if (saved) setHistory(JSON.parse(saved));
        } catch { /* ignore */ }
    }, []);

    // Save history to localStorage
    useEffect(() => {
        try {
            localStorage.setItem('adimology_history', JSON.stringify(history));
        } catch { /* ignore */ }
    }, [history]);

    // Live calculation
    const result = useMemo(() => {
        const bLot = parseFloat(buyLot) || 0;
        const bAvg = parseFloat(buyAvg) || 0;
        const arbVal = parseFloat(arb) || 0;
        const araVal = parseFloat(ara) || 0;
        const tBid = parseFloat(totalBid) || 0;
        const tOffer = parseFloat(totalOffer) || 0;

        if (bLot <= 0 || bAvg <= 0) return null;

        const totalBidOffer = tBid + tOffer;
        const fraksi = calculateFraksi(arbVal, araVal);

        if (fraksi.total <= 0 || totalBidOffer <= 0) return null;

        const avgBidOffer = totalBidOffer / fraksi.total;
        const powerFraksi = Math.floor(bLot / avgBidOffer);
        const target5pct = Math.floor(bAvg * 1.05);
        const targetLow = calculateTarget(target5pct, Math.floor(powerFraksi / 2));
        const targetHigh = calculateTarget(target5pct, powerFraksi);

        const pctLow = bAvg > 0 ? ((targetLow - bAvg) / bAvg) * 100 : 0;
        const pctHigh = bAvg > 0 ? ((targetHigh - bAvg) / bAvg) * 100 : 0;

        return {
            totalBidOffer,
            fraksi,
            avgBidOffer: Math.round(avgBidOffer * 100) / 100,
            powerFraksi,
            target5pct,
            targetLow,
            targetHigh,
            pctLow: Math.round(pctLow * 100) / 100,
            pctHigh: Math.round(pctHigh * 100) / 100,
        };
    }, [buyLot, buyAvg, arb, ara, totalBid, totalOffer]);

    // Add to history
    const handleCalculate = useCallback(() => {
        if (!result) return;
        const entry: AdimologyResult = {
            id: Date.now().toString(),
            timestamp: new Date().toLocaleString('id-ID'),
            emiten: emiten.toUpperCase() || '—',
            broker: broker.toUpperCase() || '—',
            buyLot: parseFloat(buyLot) || 0,
            buyAvg: parseFloat(buyAvg) || 0,
            arb: parseFloat(arb) || 0,
            ara: parseFloat(ara) || 0,
            totalBid: parseFloat(totalBid) || 0,
            totalOffer: parseFloat(totalOffer) || 0,
            ...result,
        };
        setHistory(prev => [entry, ...prev].slice(0, 50));
    }, [result, emiten, broker, buyLot, buyAvg, arb, ara, totalBid, totalOffer]);

    const clearHistory = useCallback(() => setHistory([]), []);

    const loadFromHistory = useCallback((item: AdimologyResult) => {
        setEmiten(item.emiten);
        setBroker(item.broker);
        setBuyLot(item.buyLot.toString());
        setBuyAvg(item.buyAvg.toString());
        setArb(item.arb.toString());
        setAra(item.ara.toString());
        setTotalBid(item.totalBid.toString());
        setTotalOffer(item.totalOffer.toString());
    }, []);

    // Power level indicator
    const powerLevel = useMemo(() => {
        if (!result) return { label: '—', color: 'text-zinc-600', bg: 'bg-zinc-800' };
        const p = result.powerFraksi;
        if (p >= 30) return { label: 'EXTREME', color: 'text-red-400', bg: 'bg-red-500/10' };
        if (p >= 20) return { label: 'VERY HIGH', color: 'text-orange-400', bg: 'bg-orange-500/10' };
        if (p >= 10) return { label: 'HIGH', color: 'text-amber-400', bg: 'bg-amber-500/10' };
        if (p >= 5) return { label: 'MODERATE', color: 'text-blue-400', bg: 'bg-blue-500/10' };
        if (p >= 2) return { label: 'LOW', color: 'text-cyan-400', bg: 'bg-cyan-500/10' };
        return { label: 'MINIMAL', color: 'text-zinc-400', bg: 'bg-zinc-800' };
    }, [result]);

    // Price bar visualization
    const priceBar = useMemo(() => {
        if (!result) return null;
        const bAvg = parseFloat(buyAvg) || 0;
        const arbVal = parseFloat(arb) || 0;
        const araVal = parseFloat(ara) || 0;
        if (arbVal <= 0 || araVal <= 0 || bAvg <= 0) return null;

        const min = Math.min(arbVal, bAvg) * 0.98;
        const max = Math.max(araVal, result.targetHigh) * 1.02;
        const range = max - min;
        if (range <= 0) return null;

        const pct = (v: number) => ((v - min) / range) * 100;

        return { min, max, range, pct, arbVal, araVal, bAvg };
    }, [result, buyAvg, arb, ara]);

    return (
        <div className="space-y-6 max-w-[1400px] mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                        <Calculator className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight text-zinc-100">ADIMOLOGY</h1>
                        <p className="text-[10px] text-zinc-500 tracking-wide">Analisis Daya Investasi — Broker Power Calculator</p>
                    </div>
                </div>
            </div>

            {/* Main Grid */}
            <div className="grid grid-cols-12 gap-4">
                {/* ─── Left: Input Form ─── */}
                <div className="col-span-4 space-y-4">
                    <div className="bg-zinc-900/30 border border-zinc-800/40 rounded-2xl p-5 space-y-4">
                        <div className="flex items-center gap-2 text-zinc-400 mb-1">
                            <Layers className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-wider">Input Data</span>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <InputField
                                label="Emiten"
                                value={emiten}
                                onChange={setEmiten}
                                placeholder="BBCA"
                                type="text"
                                info="Kode saham"
                            />
                            <InputField
                                label="Broker"
                                value={broker}
                                onChange={setBroker}
                                placeholder="CC"
                                type="text"
                                info="Kode broker"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <InputField
                                label="Buy Lot"
                                value={buyLot}
                                onChange={setBuyLot}
                                placeholder="100000"
                                suffix="lot"
                                info="Jumlah lot yang dibeli broker"
                            />
                            <InputField
                                label="Buy Avg"
                                value={buyAvg}
                                onChange={setBuyAvg}
                                placeholder="1250"
                                suffix="Rp"
                                info="Harga rata-rata beli"
                            />
                        </div>

                        <div className="h-px bg-zinc-800/50" />

                        <div className="grid grid-cols-2 gap-3">
                            <InputField
                                label="ARB"
                                value={arb}
                                onChange={setArb}
                                placeholder="191"
                                suffix="Rp"
                                info="Auto Reject Bawah"
                            />
                            <InputField
                                label="ARA"
                                value={ara}
                                onChange={setAra}
                                placeholder="280"
                                suffix="Rp"
                                info="Auto Reject Atas"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <InputField
                                label="Total Bid"
                                value={totalBid}
                                onChange={setTotalBid}
                                placeholder="205792"
                                suffix="lot"
                                info="Total volume bid di order book"
                            />
                            <InputField
                                label="Total Offer"
                                value={totalOffer}
                                onChange={setTotalOffer}
                                placeholder="683327"
                                suffix="lot"
                                info="Total volume offer di order book"
                            />
                        </div>

                        <button
                            onClick={handleCalculate}
                            disabled={!result}
                            className={cn(
                                "w-full py-2.5 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2",
                                result
                                    ? "bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white hover:from-violet-500 hover:to-fuchsia-500 shadow-lg shadow-violet-500/20 cursor-pointer"
                                    : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                            )}
                        >
                            <Calculator className="w-4 h-4" />
                            Simpan ke History
                        </button>
                    </div>

                    {/* Fraksi Breakdown */}
                    {result && (
                        <div className="bg-zinc-900/30 border border-zinc-800/40 rounded-2xl p-5 space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-zinc-400">
                                    <BarChart3 className="w-4 h-4" />
                                    <span className="text-xs font-bold uppercase tracking-wider">Fraksi Breakdown</span>
                                </div>
                                <span className="text-xs font-black text-zinc-300">
                                    Total: <span className="text-violet-400">{result.fraksi.total}</span> ticks
                                </span>
                            </div>

                            <div className="space-y-1.5">
                                <FraksiBar label="Rp 1" value={result.fraksi.f1} total={result.fraksi.total} tick={1} />
                                <FraksiBar label="Rp 2" value={result.fraksi.f2} total={result.fraksi.total} tick={2} />
                                <FraksiBar label="Rp 5" value={result.fraksi.f5} total={result.fraksi.total} tick={5} />
                                <FraksiBar label="Rp 10" value={result.fraksi.f10} total={result.fraksi.total} tick={10} />
                                <FraksiBar label="Rp 25" value={result.fraksi.f25} total={result.fraksi.total} tick={25} />
                            </div>

                            <div className="pt-2 border-t border-zinc-800/50 grid grid-cols-2 gap-3 text-[10px]">
                                <div>
                                    <span className="text-zinc-500">Total Bid+Offer</span>
                                    <div className="text-zinc-200 font-bold">{result.totalBidOffer.toLocaleString('id-ID')} lot</div>
                                </div>
                                <div>
                                    <span className="text-zinc-500">Avg per Tick</span>
                                    <div className="text-zinc-200 font-bold">{result.avgBidOffer.toLocaleString('id-ID')} lot</div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* ─── Right: Results ─── */}
                <div className="col-span-8 space-y-4">
                    {/* Power & Targets */}
                    {result ? (
                        <>
                            {/* Power Fraksi Hero */}
                            <div className={cn(
                                "rounded-2xl border p-6 transition-all duration-500",
                                "bg-gradient-to-br from-zinc-900/80 to-zinc-900/40 border-zinc-800/40"
                            )}>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <div className="flex items-center gap-2 text-zinc-500 mb-2">
                                            <Zap className="w-4 h-4" />
                                            <span className="text-[10px] font-bold uppercase tracking-wider">Power Fraksi</span>
                                        </div>
                                        <div className="flex items-baseline gap-3">
                                            <span className={cn("text-6xl font-black", powerLevel.color)}>
                                                {result.powerFraksi}
                                            </span>
                                            <span className="text-lg text-zinc-500 font-bold">ticks</span>
                                        </div>
                                        <div className={cn(
                                            "mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black border",
                                            powerLevel.bg,
                                            powerLevel.color,
                                            powerLevel.color === 'text-red-400' ? 'border-red-500/30' :
                                            powerLevel.color === 'text-orange-400' ? 'border-orange-500/30' :
                                            powerLevel.color === 'text-amber-400' ? 'border-amber-500/30' :
                                            powerLevel.color === 'text-blue-400' ? 'border-blue-500/30' :
                                            powerLevel.color === 'text-cyan-400' ? 'border-cyan-500/30' : 'border-zinc-700'
                                        )}>
                                            <Zap className="w-3 h-3" />
                                            {powerLevel.label}
                                        </div>
                                    </div>

                                    <div className="text-right space-y-1">
                                        <div className="text-[10px] text-zinc-500">
                                            {emiten.toUpperCase() || '—'} / {broker.toUpperCase() || '—'}
                                        </div>
                                        <div className="text-[10px] text-zinc-600">
                                            Buy: {(parseFloat(buyLot) || 0).toLocaleString('id-ID')} lot @ {(parseFloat(buyAvg) || 0).toLocaleString('id-ID')}
                                        </div>
                                        <div className="text-[10px] text-zinc-600">
                                            Avg Bid/Offer per tick: {result.avgBidOffer.toLocaleString('id-ID')} lot
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Target Cards */}
                            <div className="grid grid-cols-4 gap-3">
                                <ResultCard
                                    label="Buy Average"
                                    value={(parseFloat(buyAvg) || 0).toLocaleString('id-ID')}
                                    sub="Harga beli rata-rata"
                                    color="text-zinc-200"
                                    icon={<Crosshair className="w-3 h-3" />}
                                />
                                <ResultCard
                                    label="Target 5%"
                                    value={result.target5pct.toLocaleString('id-ID')}
                                    sub={`+5% dari buy avg`}
                                    color="text-blue-400"
                                    icon={<Target className="w-3 h-3" />}
                                />
                                <ResultCard
                                    label="Target Low"
                                    value={result.targetLow.toLocaleString('id-ID')}
                                    sub={`+${result.pctLow.toFixed(1)}% (½ power)`}
                                    color="text-emerald-400"
                                    icon={<TrendingUp className="w-3 h-3" />}
                                />
                                <ResultCard
                                    label="Target High"
                                    value={result.targetHigh.toLocaleString('id-ID')}
                                    sub={`+${result.pctHigh.toFixed(1)}% (full power)`}
                                    color="text-amber-400"
                                    icon={<ArrowUpRight className="w-3 h-3" />}
                                    large
                                />
                            </div>

                            {/* Price Bar Visualization */}
                            {priceBar && (
                                <div className="bg-zinc-900/30 border border-zinc-800/40 rounded-2xl p-5 space-y-3">
                                    <div className="flex items-center gap-2 text-zinc-400">
                                        <TrendingUp className="w-4 h-4" />
                                        <span className="text-xs font-bold uppercase tracking-wider">Price Range Visualization</span>
                                    </div>

                                    <div className="relative h-16 mt-4 mb-8">
                                        {/* ARB-ARA range background */}
                                        <div
                                            className="absolute top-0 h-full bg-zinc-800/40 rounded-lg border border-zinc-700/30"
                                            style={{
                                                left: `${priceBar.pct(priceBar.arbVal)}%`,
                                                width: `${priceBar.pct(priceBar.araVal) - priceBar.pct(priceBar.arbVal)}%`,
                                            }}
                                        />

                                        {/* Buy Avg marker */}
                                        <div
                                            className="absolute top-0 h-full w-0.5 bg-zinc-400"
                                            style={{ left: `${priceBar.pct(priceBar.bAvg)}%` }}
                                        >
                                            <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[8px] text-zinc-400 font-bold whitespace-nowrap">
                                                Buy {priceBar.bAvg.toLocaleString('id-ID')}
                                            </div>
                                        </div>

                                        {/* Target 5% marker */}
                                        <div
                                            className="absolute top-0 h-full w-0.5 bg-blue-500/60"
                                            style={{ left: `${priceBar.pct(result.target5pct)}%` }}
                                        >
                                            <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[8px] text-blue-400 font-bold whitespace-nowrap">
                                                T5% {result.target5pct.toLocaleString('id-ID')}
                                            </div>
                                        </div>

                                        {/* Target Low zone */}
                                        <div
                                            className="absolute top-1 h-[calc(100%-8px)] bg-emerald-500/15 rounded border-l-2 border-emerald-500/50"
                                            style={{
                                                left: `${priceBar.pct(result.target5pct)}%`,
                                                width: `${Math.max(priceBar.pct(result.targetLow) - priceBar.pct(result.target5pct), 0.5)}%`,
                                            }}
                                        />

                                        {/* Target High zone */}
                                        <div
                                            className="absolute top-1 h-[calc(100%-8px)] bg-amber-500/10 rounded border-l-2 border-amber-500/50"
                                            style={{
                                                left: `${priceBar.pct(result.targetLow)}%`,
                                                width: `${Math.max(priceBar.pct(result.targetHigh) - priceBar.pct(result.targetLow), 0.5)}%`,
                                            }}
                                        />

                                        {/* Target Low marker */}
                                        <div
                                            className="absolute top-0 h-full w-0.5 bg-emerald-500"
                                            style={{ left: `${priceBar.pct(result.targetLow)}%` }}
                                        >
                                            <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[8px] text-emerald-400 font-bold whitespace-nowrap">
                                                Low {result.targetLow.toLocaleString('id-ID')}
                                            </div>
                                        </div>

                                        {/* Target High marker */}
                                        <div
                                            className="absolute top-0 h-full w-0.5 bg-amber-500"
                                            style={{ left: `${Math.min(priceBar.pct(result.targetHigh), 99)}%` }}
                                        >
                                            <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[8px] text-amber-400 font-bold whitespace-nowrap">
                                                High {result.targetHigh.toLocaleString('id-ID')}
                                            </div>
                                        </div>

                                        {/* ARB label */}
                                        <div
                                            className="absolute -bottom-5 text-[8px] text-red-400/60 font-bold"
                                            style={{ left: `${priceBar.pct(priceBar.arbVal)}%` }}
                                        >
                                            ARB {priceBar.arbVal.toLocaleString('id-ID')}
                                        </div>

                                        {/* ARA label */}
                                        <div
                                            className="absolute -bottom-5 text-[8px] text-green-400/60 font-bold"
                                            style={{ left: `${priceBar.pct(priceBar.araVal)}%`, transform: 'translateX(-100%)' }}
                                        >
                                            ARA {priceBar.araVal.toLocaleString('id-ID')}
                                        </div>
                                    </div>

                                    {/* Legend */}
                                    <div className="flex items-center gap-4 text-[9px] text-zinc-500 pt-2 border-t border-zinc-800/50">
                                        <div className="flex items-center gap-1">
                                            <div className="w-2 h-2 rounded-full bg-zinc-400" /> Buy Avg
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="w-2 h-2 rounded-full bg-blue-500" /> Target 5%
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500" /> Target Low (½ power)
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="w-2 h-2 rounded-full bg-amber-500" /> Target High (full power)
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="w-3 h-2 rounded bg-zinc-800 border border-zinc-700/50" /> ARB—ARA range
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* How it works */}
                            <div className="bg-zinc-900/20 border border-zinc-800/30 rounded-2xl p-4">
                                <div className="flex items-center gap-2 text-zinc-500 mb-3">
                                    <Info className="w-4 h-4" />
                                    <span className="text-[10px] font-bold uppercase tracking-wider">Cara Kerja Adimology</span>
                                </div>
                                <div className="grid grid-cols-4 gap-3 text-[10px] text-zinc-500">
                                    <div className="space-y-1">
                                        <div className="text-violet-400 font-bold">1. Hitung Fraksi</div>
                                        <div>Jumlah tick harga antara ARB dan ARA berdasarkan aturan fraksi IDX (Rp1/2/5/10/25)</div>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="text-violet-400 font-bold">2. Avg Bid/Offer</div>
                                        <div>Rata-rata volume bid+offer per tick = (Total Bid + Total Offer) / Total Fraksi</div>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="text-violet-400 font-bold">3. Power Fraksi</div>
                                        <div>Berapa tick broker bisa gerakkan harga = Buy Lot / Avg Bid Offer per tick</div>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="text-violet-400 font-bold">4. Target Realistis</div>
                                        <div>Target 5% + power fraksi ticks. Low = ½ power, High = full power</div>
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="col-span-8 flex items-center justify-center h-96 bg-zinc-900/20 border border-zinc-800/30 rounded-2xl">
                            <div className="text-center space-y-3">
                                <Calculator className="w-12 h-12 text-zinc-700 mx-auto" />
                                <div className="text-zinc-500 text-sm font-bold">Masukkan data untuk mulai kalkulasi</div>
                                <div className="text-zinc-600 text-xs max-w-md">
                                    Isi semua field input di sebelah kiri: Emiten, Broker, Buy Lot, Buy Avg, ARB, ARA, Total Bid, dan Total Offer.
                                    Hasil kalkulasi akan muncul secara otomatis.
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* ─── History Table ─── */}
            <div className="bg-zinc-900/30 border border-zinc-800/40 rounded-2xl overflow-hidden">
                <div
                    className="flex items-center justify-between px-5 py-3 cursor-pointer hover:bg-zinc-800/20 transition-colors"
                    onClick={() => setShowHistory(!showHistory)}
                >
                    <div className="flex items-center gap-2 text-zinc-400">
                        <History className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Calculation History</span>
                        <span className="text-[10px] text-zinc-600">({history.length})</span>
                    </div>
                    <div className="flex items-center gap-2">
                        {history.length > 0 && (
                            <button
                                onClick={(e) => { e.stopPropagation(); clearHistory(); }}
                                className="text-[10px] text-red-400/60 hover:text-red-400 flex items-center gap-1 transition-colors"
                            >
                                <Trash2 className="w-3 h-3" />
                                Clear
                            </button>
                        )}
                        {showHistory ? <ChevronUp className="w-4 h-4 text-zinc-600" /> : <ChevronDown className="w-4 h-4 text-zinc-600" />}
                    </div>
                </div>

                {showHistory && (
                    <div className="border-t border-zinc-800/40">
                        {history.length === 0 ? (
                            <div className="px-5 py-8 text-center text-zinc-600 text-xs">
                                Belum ada history. Klik &quot;Simpan ke History&quot; setelah kalkulasi.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-[11px]">
                                    <thead>
                                        <tr className="text-zinc-500 text-left border-b border-zinc-800/40">
                                            <th className="px-4 py-2 font-bold">Waktu</th>
                                            <th className="px-3 py-2 font-bold">Emiten</th>
                                            <th className="px-3 py-2 font-bold">Broker</th>
                                            <th className="px-3 py-2 font-bold text-right">Buy Lot</th>
                                            <th className="px-3 py-2 font-bold text-right">Buy Avg</th>
                                            <th className="px-3 py-2 font-bold text-right">ARB</th>
                                            <th className="px-3 py-2 font-bold text-right">ARA</th>
                                            <th className="px-3 py-2 font-bold text-right">Power</th>
                                            <th className="px-3 py-2 font-bold text-right">T5%</th>
                                            <th className="px-3 py-2 font-bold text-right">Target Low</th>
                                            <th className="px-3 py-2 font-bold text-right">Target High</th>
                                            <th className="px-3 py-2 font-bold text-right">%High</th>
                                            <th className="px-3 py-2 font-bold text-center">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {history.map((item) => (
                                            <tr
                                                key={item.id}
                                                className="border-b border-zinc-800/20 hover:bg-zinc-800/20 transition-colors cursor-pointer"
                                                onClick={() => loadFromHistory(item)}
                                            >
                                                <td className="px-4 py-2 text-zinc-500">{item.timestamp}</td>
                                                <td className="px-3 py-2 font-bold text-zinc-200">{item.emiten}</td>
                                                <td className="px-3 py-2 text-zinc-400">{item.broker}</td>
                                                <td className="px-3 py-2 text-right text-zinc-300">{item.buyLot.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right text-zinc-300">{item.buyAvg.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right text-red-400/60">{item.arb.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right text-green-400/60">{item.ara.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right">
                                                    <span className={cn(
                                                        "font-black",
                                                        item.powerFraksi >= 20 ? 'text-orange-400' :
                                                        item.powerFraksi >= 10 ? 'text-amber-400' :
                                                        item.powerFraksi >= 5 ? 'text-blue-400' : 'text-zinc-400'
                                                    )}>
                                                        {item.powerFraksi}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-right text-blue-400">{item.target5pct.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right text-emerald-400 font-bold">{item.targetLow.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right text-amber-400 font-bold">{item.targetHigh.toLocaleString('id-ID')}</td>
                                                <td className="px-3 py-2 text-right">
                                                    <span className={cn(
                                                        "font-bold",
                                                        item.pctHigh >= 10 ? 'text-emerald-400' :
                                                        item.pctHigh >= 5 ? 'text-blue-400' : 'text-zinc-400'
                                                    )}>
                                                        +{item.pctHigh.toFixed(1)}%
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-center">
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setHistory(prev => prev.filter(h => h.id !== item.id));
                                                        }}
                                                        className="text-zinc-600 hover:text-red-400 transition-colors"
                                                    >
                                                        <Trash2 className="w-3 h-3" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
