'use client';

import React, { useState } from 'react';
import {
    RefreshCcw,
    Newspaper,
    TrendingUp,
    TrendingDown,
    Zap,
    AlertTriangle,
    CheckCircle2,
    SkipForward,
    Copy,
    Check,
    ChevronDown,
    ChevronUp,
    ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { schedulerApi, MarketSummaryResponse } from '@/services/api/scheduler';

type SummaryData = NonNullable<MarketSummaryResponse['summary']>;

interface NewsItem {
    ticker: string;
    title: string;
    score: number;
    sentiment_label: string;
    source: string;
    timestamp: string;
    url: string;
}

interface VolumeItem {
    ticker: string;
    date: string;
    ratio: number;
    price_change: number;
    category: string;
}

interface AccumItem {
    ticker: string;
    signal_score: number;
    signal_strength: string;
    flow: number;
    change: number;
    confluence_status: string;
}

function StatusBadge({ status }: { status: MarketSummaryResponse['status'] }) {
    if (status === 'success') return (
        <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" /> Generated
        </span>
    );
    if (status === 'skipped') return (
        <span className="flex items-center gap-1.5 text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 px-2.5 py-1 rounded-full font-medium">
            <SkipForward className="w-3.5 h-3.5" /> Skipped – no data
        </span>
    );
    return (
        <span className="flex items-center gap-1.5 text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full font-medium">
            <AlertTriangle className="w-3.5 h-3.5" /> Failed
        </span>
    );
}

function BreadthBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
    const pct = total > 0 ? Math.round((value / total) * 100) : 0;
    return (
        <div className="flex items-center gap-3">
            <span className="w-16 text-xs text-zinc-500 shrink-0">{label}</span>
            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className={cn('h-full rounded-full transition-all duration-500', color)} style={{ width: `${pct}%` }} />
            </div>
            <span className="w-8 text-right text-xs font-mono text-zinc-400">{value}</span>
        </div>
    );
}

function CategoryBadge({ category }: { category: string }) {
    const map: Record<string, string> = {
        extreme: 'bg-red-500/15 text-red-400 border-red-500/30',
        high: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
        elevated: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    };
    return (
        <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded border uppercase tracking-wide', map[category] ?? 'bg-zinc-800 text-zinc-400 border-zinc-700')}>
            {category}
        </span>
    );
}

export default function MarketSummaryPage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<MarketSummaryResponse | null>(null);
    const [copied, setCopied] = useState(false);
    const [newsExpanded, setNewsExpanded] = useState(true);

    const generate = async () => {
        setLoading(true);
        try {
            const data = await schedulerApi.manualMarketSummary();
            setResult(data);
        } catch (err) {
            setResult({ status: 'failed', error: String(err) });
        } finally {
            setLoading(false);
        }
    };

    const copyNewsletter = async () => {
        const text = result?.summary?.narrative?.newsletter ?? '';
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
        } catch {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const summary: SummaryData | undefined = result?.summary;
    const breadth = summary?.market_breadth;
    const narrative = summary?.narrative;
    const totalNews = (breadth?.bullish_count ?? 0) + (breadth?.bearish_count ?? 0) + (breadth?.neutral_count ?? 0);

    return (
        <div className="flex flex-col min-h-screen bg-[#09090b] text-zinc-100 p-6 gap-6">

            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-xl font-black tracking-tight text-zinc-100">Market Summary</h1>
                    <p className="text-sm text-zinc-500 mt-0.5">Daily narrative — news sentiment, unusual volume, accumulation signals.</p>
                </div>
                <button
                    onClick={generate}
                    disabled={loading}
                    className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all border',
                        loading
                            ? 'bg-zinc-800 border-zinc-700 text-zinc-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-500 border-blue-500/50 text-white shadow-lg shadow-blue-500/20'
                    )}
                >
                    <RefreshCcw className={cn('w-4 h-4', loading && 'animate-spin')} />
                    {loading ? 'Generating…' : 'Generate Summary'}
                </button>
            </div>

            {/* Status row */}
            {result && (
                <div className="flex items-center gap-3 flex-wrap">
                    <StatusBadge status={result.status} />
                    {summary?.date && (
                        <span className="text-xs text-zinc-600">Tanggal: <span className="text-zinc-400">{summary.date}</span></span>
                    )}
                    {summary?.generated_at && (
                        <span className="text-xs text-zinc-600">
                            Generated: <span className="text-zinc-400">{new Date(summary.generated_at).toLocaleTimeString('id-ID')}</span>
                        </span>
                    )}
                    {result.status === 'failed' && result.error && (
                        <span className="text-xs text-red-400 font-mono">{result.error}</span>
                    )}
                </div>
            )}

            {/* Empty state */}
            {!result && !loading && (
                <div className="flex flex-col items-center justify-center py-24 gap-4 text-zinc-600">
                    <Newspaper className="w-10 h-10 opacity-20" />
                    <span className="text-sm">Klik <span className="text-zinc-400 font-semibold">Generate Summary</span> untuk membuat ringkasan harian.</span>
                </div>
            )}

            {/* Loading skeleton */}
            {loading && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-28 rounded-xl bg-zinc-800/60" />
                    ))}
                </div>
            )}

            {/* Main content */}
            {summary && !loading && (
                <div className="flex flex-col gap-6">

                    {/* === NARRATIVE === */}
                    {narrative?.headline && (
                        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 flex flex-col gap-4">
                            <div className="flex items-start justify-between gap-3 flex-wrap">
                                <h2 className="text-base font-bold text-zinc-100 leading-snug">{narrative.headline}</h2>
                                <button
                                    onClick={copyNewsletter}
                                    className={cn(
                                        'flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all shrink-0',
                                        copied
                                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                                            : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600'
                                    )}
                                >
                                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                                    {copied ? 'Tersalin!' : 'Copy'}
                                </button>
                            </div>

                            {/* Bullets */}
                            {narrative.bullets && narrative.bullets.length > 0 && (
                                <ul className="flex flex-col gap-1.5">
                                    {narrative.bullets.map((b, i) => (
                                        <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                                            <span className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                                            {b}
                                        </li>
                                    ))}
                                </ul>
                            )}

                            {/* Newsletter text */}
                            <p className="text-sm text-zinc-400 leading-relaxed border-t border-zinc-800 pt-4">
                                {narrative.newsletter}
                            </p>
                        </div>
                    )}

                    {/* === MARKET BREADTH === */}
                    {breadth && (
                        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
                            <h3 className="text-xs font-black uppercase tracking-widest text-zinc-500 mb-4">Market Breadth</h3>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                                {[
                                    { label: 'Total Berita', val: breadth.news_count, color: 'text-zinc-300' },
                                    { label: 'Avg Sentiment', val: breadth.avg_sentiment_score.toFixed(3), color: breadth.avg_sentiment_score >= 0 ? 'text-emerald-400' : 'text-red-400' },
                                    { label: 'Bullish', val: breadth.bullish_count, color: 'text-emerald-400' },
                                    { label: 'Bearish', val: breadth.bearish_count, color: 'text-red-400' },
                                ].map(({ label, val, color }) => (
                                    <div key={label} className="flex flex-col gap-0.5">
                                        <span className="text-[10px] text-zinc-600 uppercase tracking-wider">{label}</span>
                                        <span className={cn('text-xl font-black tabular-nums', color)}>{val}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="flex flex-col gap-2">
                                <BreadthBar label="Bullish" value={breadth.bullish_count} total={totalNews} color="bg-emerald-500" />
                                <BreadthBar label="Bearish" value={breadth.bearish_count} total={totalNews} color="bg-red-500" />
                                <BreadthBar label="Netral" value={breadth.neutral_count} total={totalNews} color="bg-zinc-600" />
                            </div>
                        </div>
                    )}

                    {/* === 2-COL: News Positive + News Negative === */}
                    {((summary.top_positive_news?.length ?? 0) > 0 || (summary.top_negative_news?.length ?? 0) > 0) && (
                        <div>
                            <button
                                onClick={() => setNewsExpanded(v => !v)}
                                className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-zinc-500 mb-3 hover:text-zinc-300 transition-colors"
                            >
                                {newsExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                Top News
                            </button>
                            {newsExpanded && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Positive */}
                                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col gap-3">
                                        <div className="flex items-center gap-2 text-xs text-emerald-400 font-semibold">
                                            <TrendingUp className="w-3.5 h-3.5" /> Top Positive
                                        </div>
                                        {(summary.top_positive_news as NewsItem[]).map((n, i) => (
                                            <div key={i} className="flex flex-col gap-0.5 border-t border-zinc-800 pt-3 first:border-0 first:pt-0">
                                                <div className="flex items-center gap-2">
                                                    {n.ticker && n.ticker !== '-' && (
                                                        <span className="text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">{n.ticker}</span>
                                                    )}
                                                    <span className="text-[10px] text-zinc-600">{n.source}</span>
                                                    <span className="ml-auto text-[10px] font-mono text-emerald-500">+{n.score.toFixed(3)}</span>
                                                </div>
                                                <span className="text-xs text-zinc-300 leading-snug">{n.title}</span>
                                                {n.url && n.url !== 'None' && (
                                                    <a href={n.url} target="_blank" rel="noopener noreferrer"
                                                        className="flex items-center gap-1 text-[10px] text-zinc-600 hover:text-blue-400 transition-colors mt-0.5">
                                                        <ExternalLink className="w-3 h-3" /> Buka artikel
                                                    </a>
                                                )}
                                            </div>
                                        ))}
                                    </div>

                                    {/* Negative */}
                                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col gap-3">
                                        <div className="flex items-center gap-2 text-xs text-red-400 font-semibold">
                                            <TrendingDown className="w-3.5 h-3.5" /> Top Negative
                                        </div>
                                        {(summary.top_negative_news as NewsItem[]).map((n, i) => (
                                            <div key={i} className="flex flex-col gap-0.5 border-t border-zinc-800 pt-3 first:border-0 first:pt-0">
                                                <div className="flex items-center gap-2">
                                                    {n.ticker && n.ticker !== '-' && (
                                                        <span className="text-[10px] font-bold bg-red-500/15 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded">{n.ticker}</span>
                                                    )}
                                                    <span className="text-[10px] text-zinc-600">{n.source}</span>
                                                    <span className="ml-auto text-[10px] font-mono text-red-500">{n.score.toFixed(3)}</span>
                                                </div>
                                                <span className="text-xs text-zinc-300 leading-snug">{n.title}</span>
                                                {n.url && n.url !== 'None' && (
                                                    <a href={n.url} target="_blank" rel="noopener noreferrer"
                                                        className="flex items-center gap-1 text-[10px] text-zinc-600 hover:text-blue-400 transition-colors mt-0.5">
                                                        <ExternalLink className="w-3 h-3" /> Buka artikel
                                                    </a>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* === 2-COL: Unusual Volume + Strong Accumulation === */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Unusual Volume */}
                        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col gap-3">
                            <div className="flex items-center gap-2 text-xs text-amber-400 font-semibold uppercase tracking-wider">
                                <Zap className="w-3.5 h-3.5" /> Anomali Volume
                            </div>
                            {(summary.unusual_volume_tickers as VolumeItem[]).length === 0 ? (
                                <p className="text-xs text-zinc-600 italic">Tidak ada anomali terdeteksi.</p>
                            ) : (
                                <div className="flex flex-col gap-2">
                                    {(summary.unusual_volume_tickers as VolumeItem[]).map((v, i) => (
                                        <div key={i} className="flex items-center gap-2 bg-zinc-800/40 rounded-lg px-3 py-2">
                                            <span className="text-xs font-bold text-zinc-200 w-16 shrink-0">{v.ticker}</span>
                                            <CategoryBadge category={v.category} />
                                            <span className="text-xs font-mono text-amber-400 ml-auto">{v.ratio}x</span>
                                            <span className={cn('text-xs font-mono w-14 text-right', v.price_change >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                                                {v.price_change >= 0 ? '+' : ''}{v.price_change}%
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Strong Accumulation */}
                        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col gap-3">
                            <div className="flex items-center gap-2 text-xs text-purple-400 font-semibold uppercase tracking-wider">
                                <TrendingUp className="w-3.5 h-3.5" /> Akumulasi Kuat
                            </div>
                            {(summary.strong_accumulation as AccumItem[]).length === 0 ? (
                                <p className="text-xs text-zinc-600 italic">Tidak ada sinyal akumulasi saat ini.</p>
                            ) : (
                                <div className="flex flex-col gap-2">
                                    {(summary.strong_accumulation as AccumItem[]).map((a, i) => (
                                        <div key={i} className="flex items-center gap-2 bg-zinc-800/40 rounded-lg px-3 py-2">
                                            <span className="text-xs font-bold text-zinc-200 w-16 shrink-0">{a.ticker}</span>
                                            <span className={cn(
                                                'text-[10px] font-semibold px-1.5 py-0.5 rounded border uppercase tracking-wide',
                                                a.signal_strength === 'STRONG' ? 'bg-purple-500/15 text-purple-400 border-purple-500/30' : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                                            )}>
                                                {a.signal_strength ?? '-'}
                                            </span>
                                            <span className="text-xs font-mono text-purple-400 ml-auto">{a.signal_score}</span>
                                            <span className={cn('text-xs font-mono w-14 text-right', (a.change ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                                                {(a.change ?? 0) >= 0 ? '+' : ''}{(a.change ?? 0).toFixed(1)}%
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                </div>
            )}
        </div>
    );
}
