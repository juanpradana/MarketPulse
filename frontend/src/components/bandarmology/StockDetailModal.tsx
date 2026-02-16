'use client';

import React, { useEffect, useState } from 'react';
import { bandarmologyApi, StockDetailResponse } from '@/services/api/bandarmology';
import {
    X, TrendingUp, TrendingDown, Target, Shield, AlertTriangle,
    ArrowUpRight, ArrowDownRight, Loader2, BarChart3, Users, DollarSign,
    Crosshair, Activity, Zap, FileDown, Copy, Check
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
        signal.includes('consistency_bandar_buy') || signal.includes('sr_classic_bullish') ||
        signal.includes('sr_broad_buying') || signal.includes('sr_daily_divergence') ||
        signal.includes('vol_stealth_accum') || signal.includes('vol_quiet_accum') ||
        signal.includes('vol_active_breakout') || signal.includes('accum_duration_optimal') ||
        signal.includes('ma_golden_cross') || signal.includes('ma_perfect_alignment') ||
        signal.includes('ma_bullish_alignment') || signal.includes('phase_accum_to_hold') ||
        signal.includes('phase_hold_to_accum') || signal.includes('phase_dist_to_accum');
    const isWarning = signal.includes('warning') || signal.includes('sell') ||
        signal.includes('outflow') || signal.includes('high_cross') || signal.includes('tektok') ||
        signal.includes('ctrl_distributing') || signal.includes('ctrl_far_above') ||
        signal.includes('ctrl_heavy_dist') || signal.includes('ctrl_full_exit') ||
        signal.includes('ctrl_moderate_dist') || signal.includes('ctrl_brokers_selling') ||
        signal.includes('xref_bandar_strong_sell') || signal.includes('xref_bandar_selling') ||
        signal.includes('xref_bandar_mild_sell') || signal.includes('consistency_bandar_sell') ||
        signal.includes('sr_retail_trap') || signal.includes('sr_broad_selling') ||
        signal.includes('conc_high_risk') || signal.includes('conc_medium_risk') ||
        signal.includes('vol_dead_stock') || signal.includes('vol_distribution_complete') ||
        signal.includes('accum_duration_stale') ||
        signal.includes('ma_death_cross') || signal.includes('ma_bearish_alignment') ||
        signal.includes('phase_accum_to_dist') || signal.includes('phase_hold_to_dist');

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

function generateChatText(data: StockDetailResponse): string {
    const fmt = (n: number | undefined | null) => n != null ? n.toLocaleString('id-ID') : '—';
    const pct = (n: number | undefined | null) => n != null ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '—';
    const lines: string[] = [];

    lines.push(`📊 *BANDARMOLOGY INSIGHT: ${data.ticker}*`);
    lines.push(`📅 ${data.date}`);
    lines.push(`💰 Harga: ${fmt(data.price)} (${pct(data.pct_1d)})`);
    if (data.trade_type && data.trade_type !== '—') lines.push(`📋 Tipe: ${data.deep_trade_type || data.trade_type}`);
    lines.push('');

    lines.push(`⭐ *SKOR*`);
    lines.push(`  Base: ${data.base_score}/${data.max_base_score}`);
    if (data.has_deep) {
        lines.push(`  Deep: +${data.deep_score ?? 0}`);
        lines.push(`  Combined: ${data.combined_score ?? data.base_score}/${data.max_combined_score ?? 200}`);
    }
    if (data.breakout_probability) lines.push(`  Breakout Prob: ${data.breakout_probability}%`);
    if (data.pump_tomorrow_score) {
        const ptLabel = data.pump_tomorrow_signal === 'STRONG_PUMP' ? '🚀 STRONG' : data.pump_tomorrow_signal === 'LIKELY_PUMP' ? '📈 LIKELY' : data.pump_tomorrow_signal === 'POSSIBLE_PUMP' ? '🔄 POSSIBLE' : data.pump_tomorrow_signal === 'LOW_CHANCE' ? '⚠️ LOW' : '';
        lines.push(`  Pump Tomorrow: ${data.pump_tomorrow_score}% ${ptLabel}`);
    }
    lines.push('');

    if (data.entry_price || data.target_price) {
        lines.push(`🎯 *ENTRY / TARGET*`);
        if (data.entry_price) lines.push(`  Entry: ${fmt(data.entry_price)}`);
        if (data.target_price) lines.push(`  Target: ${fmt(data.target_price)} ${data.target_method ? `(${data.target_method})` : ''}`);
        if (data.stop_loss) lines.push(`  Stop Loss: ${fmt(data.stop_loss)} ${data.stop_method ? `(${data.stop_method})` : ''}`);
        if (data.risk_reward_ratio) lines.push(`  R:R = 1:${data.risk_reward_ratio}`);
        lines.push('');
    }

    // Data freshness warning
    if ((data.data_freshness ?? 1) < 1) {
        lines.push(`⚠️ *DATA FRESHNESS: ${(data.data_freshness! * 100).toFixed(0)}%*`);
        lines.push(`  Source Date: ${data.data_source_date || 'unknown'}`);
        if (data.original_deep_score && data.original_deep_score !== data.deep_score) {
            lines.push(`  Score adjusted: ${data.original_deep_score} → ${data.deep_score}`);
        }
        lines.push('');
    }

    // Volume confirmation
    if ((data.volume_confirmation_multiplier ?? 0) > 0) {
        const volMult = data.volume_confirmation_multiplier!;
        const volStatus = volMult > 1 ? '✓ Confirms' : volMult < 1 ? '! Contradicts' : '○ Neutral';
        lines.push(`📊 *VOLUME CONFIRMATION: ${volMult}x* ${volStatus}`);
        lines.push('');
    }

    // Conflict Warning
    if (data.data_source_conflict) {
        lines.push(`⚠️ *DATA SOURCE CONFLICT*`);
        lines.push(`  Data sources disagree on signals`);
        if (data.conflict_stats) {
            lines.push(`  CV: ${data.conflict_stats.cv.toFixed(2)} | Mean: ${data.conflict_stats.mean.toFixed(1)} | Std: ${data.conflict_stats.std.toFixed(1)}`);
        }
        lines.push('');
    }

    // Relative Context
    if (data.relative_context?.market_context) {
        const ctx = data.relative_context.market_context;
        lines.push(`📈 *MARKET CONTEXT*`);
        lines.push(`  Stock: ${ctx.stock_flow?.toFixed(1)}B vs Market Avg: ${ctx.market_avg?.toFixed(1)}B`);
        lines.push(`  Z-Score: ${ctx.z_score?.toFixed(2)} (Percentile: ${ctx.percentile?.toFixed(0)}%)`);
        if (data.relative_context.sector_context) {
            const sec = data.relative_context.sector_context;
            lines.push(`  Sector ${sec.sector}: ${sec.diff_pct?.toFixed(1)}% vs sector avg`);
        }
        if (data.relative_context.relative_score && data.relative_context.relative_score !== 1.0) {
            lines.push(`  Relative Multiplier: ${data.relative_context.relative_score}x`);
        }
        lines.push('');
    }

    if (data.has_deep && data.controlling_brokers && data.controlling_brokers.length > 0) {
        lines.push(`🏦 *CONTROLLING BROKERS*`);
        if (data.accum_phase && data.accum_phase !== 'UNKNOWN') lines.push(`  Fase: ${data.accum_phase}`);
        if (data.bandar_avg_cost) lines.push(`  Avg Cost Bandar: ${fmt(data.bandar_avg_cost)}`);
        if (data.coordination_score) lines.push(`  Koordinasi: ${data.coordination_score}%`);
        if (data.breakout_signal && data.breakout_signal !== 'NONE') lines.push(`  Breakout Signal: ${data.breakout_signal}`);
        if (data.distribution_alert && data.distribution_alert !== 'NONE') lines.push(`  ⚠️ Distribusi: ${data.distribution_alert}`);
        lines.push('');
        data.controlling_brokers.forEach(cb => {
            const status = cb.distribution_pct >= 50 ? '🔴DIST' : cb.distribution_pct >= 25 ? '🟠SELL' : cb.avg_daily_last10 > 50 ? '🟢BUY' : '⚪HOLD';
            lines.push(`  ${cb.code}${cb.is_clean ? '✓' : cb.is_tektok ? '✗' : ''} | Net: +${fmt(cb.net_lot)} | Avg: ${fmt(cb.avg_buy_price)} | ${status}`);
        });
        lines.push('');
    }

    if (data.bandar_confirmation && data.bandar_confirmation !== 'NONE' && data.bandar_confirmation !== 'NEUTRAL') {
        const emoji = data.bandar_confirmation.includes('BUY') ? '🟢' : '🔴';
        lines.push(`${emoji} *CROSS-REF*: Bandar ${data.bandar_confirmation}`);
        if (data.bandar_buy_today_lot) lines.push(`  Buy today: +${fmt(data.bandar_buy_today_lot)} lot`);
        if (data.bandar_sell_today_lot) lines.push(`  Sell today: -${fmt(data.bandar_sell_today_lot)} lot`);
        lines.push('');
    }

    // New improvement data
    if (data.has_deep) {
        const extras: string[] = [];
        if ((data.accum_duration_days ?? 0) > 0) {
            const dur = data.accum_duration_days!;
            const label = dur < 14 ? 'terlalu dini' : dur <= 56 ? 'optimal' : dur <= 90 ? 'mulai lama' : 'stale';
            extras.push(`⏱️ Durasi Akumulasi: ${dur} hari (${label})`);
        }
        if (data.concentration_risk && data.concentration_risk !== 'NONE' && data.concentration_risk !== 'LOW') {
            extras.push(`⚠️ Konsentrasi: ${data.concentration_broker} = ${(data.concentration_pct ?? 0).toFixed(0)}% (${data.concentration_risk})`);
        }
        if (data.txn_smart_money_cum != null && data.txn_retail_cum_deep != null &&
            (data.txn_smart_money_cum !== 0 || data.txn_retail_cum_deep !== 0)) {
            const label = (data.smart_retail_divergence ?? 0) > 30 ? 'BULLISH' :
                          (data.smart_retail_divergence ?? 0) < -30 ? 'BEARISH' : 'NEUTRAL';
            extras.push(`🧠 Smart vs Retail: SM ${data.txn_smart_money_cum > 0 ? '+' : ''}${data.txn_smart_money_cum.toFixed(1)}B | RTL ${data.txn_retail_cum_deep > 0 ? '+' : ''}${data.txn_retail_cum_deep.toFixed(1)}B → ${label}`);
        }
        if (data.volume_signal && data.volume_signal !== 'NONE' && data.volume_signal !== 'NEUTRAL') {
            const volLabels: Record<string, string> = {
                'STEALTH_ACCUM': 'Stealth Accumulation',
                'QUIET_ACCUM': 'Quiet Accumulation',
                'ACTIVE_BREAKOUT': 'Active Breakout',
                'DEAD': 'Dead Stock',
                'DIST_COMPLETE': 'Distribution Complete'
            };
            extras.push(`📊 Volume: ${volLabels[data.volume_signal] ?? data.volume_signal} (+${data.volume_score ?? 0}pts)`);
        }
        if (data.ma_cross_signal && data.ma_cross_signal !== 'NONE' && data.ma_cross_signal !== 'NEUTRAL') {
            const maLabels: Record<string, string> = {
                'GOLDEN_CROSS': '⚡ Golden Cross', 'DEATH_CROSS': '💀 Death Cross',
                'PERFECT_BULLISH': '🎯 Perfect Bullish', 'BULLISH_ALIGNMENT': '📈 Bullish Alignment',
                'BEARISH_ALIGNMENT': '📉 Bearish Alignment', 'CONVERGING': '🔄 MA Converging'
            };
            extras.push(`${maLabels[data.ma_cross_signal] ?? data.ma_cross_signal} (${(data.ma_cross_score ?? 0) > 0 ? '+' : ''}${data.ma_cross_score ?? 0}pts)`);
        }
        if (data.flow_acceleration_signal && data.flow_acceleration_signal !== 'NONE') {
            const accelLabels: Record<string, string> = {
                'STRONG_ACCELERATING': '🚀 Flow Akselerasi Kuat',
                'ACCELERATING': '📈 Flow Akselerasi',
                'MILD_ACCELERATING': '↗️ Flow Naik Perlahan',
                'STABLE': '➡️ Flow Stabil',
                'MILD_DECELERATING': '↘️ Flow Melambat',
                'DECELERATING': '📉 Flow Deselerasi'
            };
            extras.push(`${accelLabels[data.flow_acceleration_signal] ?? data.flow_acceleration_signal} (MM: ${(data.flow_velocity_mm ?? 0) > 0 ? '+' : ''}${(data.flow_velocity_mm ?? 0).toFixed(1)}B/d, ${(data.flow_velocity_score ?? 0) > 0 ? '+' : ''}${data.flow_velocity_score ?? 0}pts)`);
        }
        if (data.important_dates_signal && data.important_dates_signal !== 'NONE' && data.important_dates_signal !== 'NEUTRAL') {
            extras.push(`🏦 Tanggal Penting: ${data.important_dates_signal} (${(data.important_dates_score ?? 0) > 0 ? '+' : ''}${data.important_dates_score ?? 0}pts, ${(data.important_dates ?? []).length} tanggal dianalisis)`);
        }
        if (data.phase_transition && data.phase_transition !== 'NONE') {
            const parts = data.phase_transition.split('_TO_');
            extras.push(`🔄 Fase: ${parts[0]} → ${parts[1]}`);
        }
        if (data.score_trend && data.score_trend !== 'NONE' && data.score_trend !== 'STABLE' && (data.prev_deep_score ?? 0) > 0) {
            const arrow = data.score_trend.includes('IMPROVING') ? '↑' : '↓';
            extras.push(`${arrow} Score: ${data.prev_deep_score} → ${data.deep_score} (${data.score_trend.replace('_', ' ')})`);
        }
        if (extras.length > 0) {
            lines.push(`🔍 *ANALISIS LANJUTAN*`);
            extras.forEach(e => lines.push(`  ${e}`));
            lines.push('');
        }
    }

    if (data.has_deep) {
        lines.push(`📈 *TRANSACTION FLOW (6M)*`);
        lines.push(`  MM: ${(data.txn_mm_cum ?? 0).toFixed(1)}B | FGN: ${(data.txn_foreign_cum ?? 0).toFixed(1)}B`);
        lines.push(`  INST: ${(data.txn_institution_cum ?? 0).toFixed(1)}B | RTL: ${(data.txn_retail_cum ?? 0).toFixed(1)}B`);
        if (data.txn_cross_index != null) lines.push(`  Cross Index: ${data.txn_cross_index.toFixed(2)}`);
        lines.push('');
    }

    if (data.broker_summary && (data.broker_summary.buy.length > 0 || data.broker_summary.sell.length > 0)) {
        lines.push(`💹 *BROKER SUMMARY (Today)*`);
        if (data.broker_summary.buy.length > 0) {
            lines.push(`  Top Buyers: ${data.broker_summary.buy.slice(0, 5).map(b => `${b.broker}(${fmt(Number(b.nlot))})`).join(', ')}`);
        }
        if (data.broker_summary.sell.length > 0) {
            lines.push(`  Top Sellers: ${data.broker_summary.sell.slice(0, 5).map(s => `${s.broker}(${fmt(Number(s.nlot))})`).join(', ')}`);
        }
        if (data.broksum_net_institutional) lines.push(`  Inst Net: ${fmt(data.broksum_net_institutional)} lot`);
        if (data.broksum_net_foreign) lines.push(`  Foreign Net: ${fmt(data.broksum_net_foreign)} lot`);
        lines.push('');
    }

    if (data.deep_signals && Object.keys(data.deep_signals).length > 0) {
        lines.push(`🔔 *SIGNALS*`);
        Object.values(data.deep_signals).forEach(desc => {
            lines.push(`  • ${desc}`);
        });
        lines.push('');
    }

    lines.push(`— MarketPulse Bandarmology`);
    return lines.join('\n');
}

function generatePdfHtml(data: StockDetailResponse): string {
    const fmt = (n: number | undefined | null) => n != null ? n.toLocaleString('id-ID') : '—';
    const pct = (n: number | undefined | null) => n != null ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '—';
    const scoreColor = (v: number, max: number) => {
        const p = (v / max) * 100;
        return p >= 70 ? '#34d399' : p >= 50 ? '#60a5fa' : p >= 30 ? '#fb923c' : '#ef4444';
    };

    let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Bandarmology - ${data.ticker}</title>
<style>
  @page { size: A4; margin: 15mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; font-size: 11px; color: #1a1a2e; background: #fff; line-height: 1.4; }
  .header { background: linear-gradient(135deg, #1e1b4b, #1e3a5f); color: #fff; padding: 16px 20px; border-radius: 8px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
  .header h1 { font-size: 22px; font-weight: 900; letter-spacing: -0.5px; }
  .header .sub { font-size: 11px; opacity: 0.7; margin-top: 2px; }
  .header .price { text-align: right; }
  .header .price .val { font-size: 20px; font-weight: 800; }
  .header .price .chg { font-size: 12px; }
  .section { margin-bottom: 12px; }
  .section-title { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: #6366f1; border-bottom: 2px solid #e5e7eb; padding-bottom: 4px; margin-bottom: 8px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .grid4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; }
  .grid6 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; }
  .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; }
  .card .label { font-size: 8px; font-weight: 700; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px; }
  .card .value { font-size: 16px; font-weight: 900; margin-top: 2px; }
  .card .sub { font-size: 8px; color: #94a3b8; margin-top: 1px; }
  table { width: 100%; border-collapse: collapse; font-size: 10px; }
  th { background: #f1f5f9; font-weight: 700; text-transform: uppercase; font-size: 8px; letter-spacing: 0.3px; color: #64748b; padding: 5px 6px; text-align: left; border-bottom: 2px solid #e2e8f0; }
  td { padding: 4px 6px; border-bottom: 1px solid #f1f5f9; }
  tr:hover { background: #f8fafc; }
  .pos { color: #059669; font-weight: 700; }
  .neg { color: #dc2626; font-weight: 700; }
  .warn { color: #d97706; font-weight: 700; }
  .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 700; }
  .badge-green { background: #d1fae5; color: #065f46; }
  .badge-red { background: #fee2e2; color: #991b1b; }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-yellow { background: #fef3c7; color: #92400e; }
  .badge-purple { background: #ede9fe; color: #5b21b6; }
  .bar-container { height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-top: 3px; }
  .bar-fill { height: 100%; border-radius: 4px; }
  .signal-list { display: flex; flex-wrap: wrap; gap: 4px; }
  .signal { padding: 2px 6px; border-radius: 3px; font-size: 8px; font-weight: 600; background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
  .footer { margin-top: 16px; padding-top: 8px; border-top: 1px solid #e2e8f0; font-size: 9px; color: #94a3b8; text-align: center; }
  @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
</style></head><body>`;

    // Header
    html += `<div class="header">
      <div><h1>${data.ticker}</h1><div class="sub">Bandarmology Deep Analysis Report — ${data.date}</div>
        ${data.trade_type && data.trade_type !== '—' ? `<span class="badge badge-purple" style="margin-top:4px;display:inline-block;">${data.deep_trade_type || data.trade_type}</span>` : ''}
      </div>
      <div class="price"><div class="val">${fmt(data.price)}</div>
        <div class="chg" style="color:${data.pct_1d >= 0 ? '#34d399' : '#f87171'}">${pct(data.pct_1d)}</div>
      </div></div>`;

    // Score Cards
    html += `<div class="section"><div class="section-title">Score Overview</div><div class="grid6">`;
    const scoreCards = [
        { label: 'Base Score', value: `${data.base_score}`, sub: `/ ${data.max_base_score}`, color: scoreColor(data.base_score, data.max_base_score) },
        { label: 'Deep Score', value: data.has_deep ? `+${data.deep_score ?? 0}` : '—', sub: data.has_deep ? 'Analyzed' : 'N/A', color: '#60a5fa' },
        { label: 'Combined', value: `${data.combined_score ?? data.base_score}`, sub: `/ ${data.max_combined_score ?? 200}`, color: scoreColor(data.combined_score ?? data.base_score, data.max_combined_score ?? 200) },
        { label: 'Breakout Prob', value: data.breakout_probability ? `${data.breakout_probability}%` : '—', sub: data.breakout_probability ? (data.breakout_probability >= 70 ? 'HIGH' : data.breakout_probability >= 40 ? 'MEDIUM' : 'LOW') : '', color: (data.breakout_probability ?? 0) >= 70 ? '#34d399' : (data.breakout_probability ?? 0) >= 40 ? '#f59e0b' : '#94a3b8' },
        { label: 'Pump Tomorrow', value: data.pump_tomorrow_score ? `${data.pump_tomorrow_score}%` : '—', sub: data.pump_tomorrow_signal === 'STRONG_PUMP' ? '🚀 STRONG' : data.pump_tomorrow_signal === 'LIKELY_PUMP' ? '📈 LIKELY' : data.pump_tomorrow_signal === 'POSSIBLE_PUMP' ? '🔄 POSSIBLE' : data.pump_tomorrow_signal === 'LOW_CHANCE' ? '⚠️ LOW' : '', color: (data.pump_tomorrow_score ?? 0) >= 75 ? '#34d399' : (data.pump_tomorrow_score ?? 0) >= 55 ? '#06b6d4' : (data.pump_tomorrow_score ?? 0) >= 40 ? '#f59e0b' : '#94a3b8' },
        { label: 'Entry Price', value: data.entry_price ? fmt(data.entry_price) : '—', sub: data.entry_price && data.price ? `${((data.price - data.entry_price) / data.entry_price * 100).toFixed(1)}% from current` : '', color: '#06b6d4' },
        { label: 'Target Price', value: data.target_price ? fmt(data.target_price) : '—', sub: data.risk_reward_ratio ? `R:R = 1:${data.risk_reward_ratio}` : '', color: '#eab308' },
    ];
    scoreCards.forEach(c => {
        html += `<div class="card"><div class="label">${c.label}</div><div class="value" style="color:${c.color}">${c.value}</div><div class="sub">${c.sub}</div></div>`;
    });
    html += `</div></div>`;

    // Entry/Target/SL Bar
    if (data.entry_price && data.target_price && data.stop_loss) {
        html += `<div class="section"><div class="section-title">Price Levels</div><div class="grid4">
          <div class="card"><div class="label">Stop Loss</div><div class="value neg">${fmt(data.stop_loss)}</div></div>
          <div class="card"><div class="label">Entry</div><div class="value" style="color:#06b6d4">${fmt(data.entry_price)}</div></div>
          <div class="card"><div class="label">Current</div><div class="value">${fmt(data.price)}</div></div>
          <div class="card"><div class="label">Target</div><div class="value" style="color:#eab308">${fmt(data.target_price)}</div></div>
        </div></div>`;
    }

    // Controlling Brokers
    if (data.has_deep && data.controlling_brokers && data.controlling_brokers.length > 0) {
        html += `<div class="section"><div class="section-title">Controlling Brokers (Bandarmology)</div>`;
        // Summary badges
        html += `<div style="margin-bottom:8px;display:flex;gap:6px;flex-wrap:wrap;">`;
        if (data.accum_phase && data.accum_phase !== 'UNKNOWN') {
            const phaseClass = data.accum_phase === 'ACCUMULATION' ? 'badge-green' : data.accum_phase === 'DISTRIBUTION' ? 'badge-red' : 'badge-blue';
            html += `<span class="badge ${phaseClass}">${data.accum_phase}</span>`;
        }
        if (data.breakout_signal && data.breakout_signal !== 'NONE') html += `<span class="badge badge-yellow">⚡ ${data.breakout_signal}</span>`;
        if (data.accum_start_date) html += `<span class="badge badge-blue">Since ${data.accum_start_date}</span>`;
        if (data.bandar_avg_cost) html += `<span class="badge badge-blue">Avg Cost: ${fmt(data.bandar_avg_cost)}</span>`;
        if (data.coordination_score) html += `<span class="badge ${data.coordination_score >= 70 ? 'badge-green' : 'badge-yellow'}">Coordination: ${data.coordination_score}%</span>`;
        html += `</div>`;

        // Distribution alert
        if (data.distribution_alert && data.distribution_alert !== 'NONE') {
            html += `<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:6px 10px;margin-bottom:8px;font-weight:700;color:#991b1b;font-size:10px;">⚠️ Distribution Alert: ${data.distribution_alert} — Peak: ${fmt(data.bandar_peak_lot)} lot, Sold: ${(data.bandar_distribution_pct ?? 0).toFixed(1)}%</div>`;
        }

        // Broker table
        html += `<table><thead><tr><th>Broker</th><th style="text-align:right">Net Lot</th><th style="text-align:right">Avg Buy</th><th style="text-align:right">Buy Lots</th><th style="text-align:right">Sell Lots</th><th>Turn Date</th><th style="text-align:right">Peak</th><th style="text-align:right">Dist%</th><th>Status</th></tr></thead><tbody>`;
        data.controlling_brokers.forEach(cb => {
            const status = cb.distribution_pct >= 50 ? 'DISTRIBUSI' : cb.distribution_pct >= 25 ? 'SELLING' : cb.avg_daily_last10 > 50 ? 'BUYING' : cb.avg_daily_last10 < -50 ? 'SELLING' : 'HOLDING';
            const statusClass = status === 'BUYING' ? 'pos' : status === 'DISTRIBUSI' || status === 'SELLING' ? 'neg' : '';
            html += `<tr>
              <td><strong>${cb.code}</strong>${cb.is_clean ? ' <span class="pos">✓</span>' : ''}${cb.is_tektok ? ' <span class="warn">✗</span>' : ''}${cb.broker_class ? ` <span style="color:#94a3b8;font-size:8px">${cb.broker_class}</span>` : ''}</td>
              <td style="text-align:right" class="pos">+${fmt(cb.net_lot)}</td>
              <td style="text-align:right;color:#06b6d4;font-weight:700">${cb.avg_buy_price ? fmt(cb.avg_buy_price) : '—'}</td>
              <td style="text-align:right">${cb.total_buy_lots ? fmt(cb.total_buy_lots) : '—'}</td>
              <td style="text-align:right">${cb.total_sell_lots ? fmt(cb.total_sell_lots) : '—'}</td>
              <td>${cb.turn_date || '—'}</td>
              <td style="text-align:right">${cb.peak_lot ? fmt(cb.peak_lot) : '—'}</td>
              <td style="text-align:right" class="${cb.distribution_pct >= 50 ? 'neg' : cb.distribution_pct >= 25 ? 'warn' : ''}">${cb.distribution_pct > 0 ? cb.distribution_pct.toFixed(1) + '%' : '0%'}</td>
              <td><span class="badge ${status === 'BUYING' ? 'badge-green' : status === 'DISTRIBUSI' ? 'badge-red' : status === 'SELLING' ? 'badge-red' : 'badge-blue'}">${status}</span></td>
            </tr>`;
        });
        html += `</tbody></table></div>`;
    }

    // Two column: Transaction Flow + Inventory
    html += `<div class="grid2">`;
    // Transaction Flow
    html += `<div class="section"><div class="section-title">Transaction Flow (6M Cumulative)</div>`;
    if (data.has_deep) {
        const flows = [
            { label: 'Market Maker', value: data.txn_mm_cum ?? 0 },
            { label: 'Foreign', value: data.txn_foreign_cum ?? 0 },
            { label: 'Institution', value: data.txn_institution_cum ?? 0 },
            { label: 'Retail', value: data.txn_retail_cum ?? 0 },
        ];
        flows.forEach(f => {
            html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
              <span style="width:70px;font-size:9px;font-weight:700;color:#64748b">${f.label}</span>
              <span style="width:60px;text-align:right;font-weight:800;font-size:10px" class="${f.value > 0 ? 'pos' : f.value < 0 ? 'neg' : ''}">${f.value > 0 ? '+' : ''}${f.value.toFixed(1)}B</span>
            </div>`;
        });
        if (data.txn_cross_index != null) html += `<div style="font-size:9px;color:#64748b;margin-top:4px">Cross Index: <strong>${data.txn_cross_index.toFixed(2)}</strong> | MM Trend: <strong>${data.txn_mm_trend || '—'}</strong></div>`;
    } else {
        html += `<div style="color:#94a3b8;font-size:10px;text-align:center;padding:12px">No deep analysis data</div>`;
    }
    html += `</div>`;

    // Inventory
    html += `<div class="section"><div class="section-title">Inventory Brokers</div>`;
    if (data.has_deep && (data.inv_accum_brokers ?? 0) > 0) {
        html += `<div style="display:flex;gap:8px;margin-bottom:6px;font-size:9px">
          <span class="pos">${data.inv_accum_brokers} Accumulating</span>
          <span class="neg">${data.inv_distrib_brokers} Distributing</span>
          <span style="color:#06b6d4;font-weight:700">${data.inv_clean_brokers}✓ Clean</span>
        </div>`;
        html += `<div class="grid2"><div class="card"><div class="label">Total Accum</div><div class="value pos">+${fmt(data.inv_total_accum_lot)}</div></div>
          <div class="card"><div class="label">Total Distrib</div><div class="value neg">-${fmt(data.inv_total_distrib_lot)}</div></div></div>`;
        if (data.inv_top_accum_broker) html += `<div style="font-size:9px;color:#64748b;margin-top:4px">Top Accumulator: <strong class="pos">${data.inv_top_accum_broker}</strong></div>`;
    } else {
        html += `<div style="color:#94a3b8;font-size:10px;text-align:center;padding:12px">No inventory data</div>`;
    }
    html += `</div></div>`;

    // Broker Summary
    if (data.broker_summary && (data.broker_summary.buy.length > 0 || data.broker_summary.sell.length > 0)) {
        html += `<div class="section"><div class="section-title">Broker Summary (Today)</div><div class="grid2">`;
        // Buy side
        html += `<div><div style="font-size:9px;font-weight:700;color:#059669;margin-bottom:4px">NET BUYERS</div><table><thead><tr><th>Broker</th><th style="text-align:right">Net Lot</th><th style="text-align:right">Value</th><th style="text-align:right">Avg</th></tr></thead><tbody>`;
        data.broker_summary.buy.slice(0, 8).forEach(b => {
            html += `<tr><td class="pos">${b.broker}</td><td style="text-align:right">${fmt(Number(b.nlot))}</td><td style="text-align:right;color:#94a3b8">${b.nval ?? '—'}</td><td style="text-align:right">${b.avg_price ? fmt(Number(b.avg_price)) : '—'}</td></tr>`;
        });
        html += `</tbody></table>`;
        if (data.broksum_avg_buy_price) html += `<div style="font-size:9px;color:#64748b;margin-top:4px">Weighted Avg: <strong style="color:#06b6d4">${fmt(data.broksum_avg_buy_price)}</strong></div>`;
        html += `</div>`;
        // Sell side
        html += `<div><div style="font-size:9px;font-weight:700;color:#dc2626;margin-bottom:4px">NET SELLERS</div><table><thead><tr><th>Broker</th><th style="text-align:right">Net Lot</th><th style="text-align:right">Value</th><th style="text-align:right">Avg</th></tr></thead><tbody>`;
        data.broker_summary.sell.slice(0, 8).forEach(s => {
            html += `<tr><td class="neg">${s.broker}</td><td style="text-align:right">${fmt(Number(s.nlot))}</td><td style="text-align:right;color:#94a3b8">${s.nval ?? '—'}</td><td style="text-align:right">${s.avg_price ? fmt(Number(s.avg_price)) : '—'}</td></tr>`;
        });
        html += `</tbody></table>`;
        if (data.broksum_avg_sell_price) html += `<div style="font-size:9px;color:#64748b;margin-top:4px">Weighted Avg: <strong style="color:#f59e0b">${fmt(data.broksum_avg_sell_price)}</strong></div>`;
        html += `</div></div>`;
        if (data.broksum_net_institutional || data.broksum_net_foreign) {
            html += `<div style="display:flex;gap:16px;font-size:10px;margin-top:6px;padding-top:6px;border-top:1px solid #e2e8f0">`;
            if (data.broksum_net_institutional != null) html += `<span>Institutional Net: <strong class="${data.broksum_net_institutional > 0 ? 'pos' : 'neg'}">${data.broksum_net_institutional > 0 ? '+' : ''}${fmt(data.broksum_net_institutional)} lot</strong></span>`;
            if (data.broksum_net_foreign != null) html += `<span>Foreign Net: <strong class="${data.broksum_net_foreign > 0 ? 'pos' : 'neg'}">${data.broksum_net_foreign > 0 ? '+' : ''}${fmt(data.broksum_net_foreign)} lot</strong></span>`;
            html += `</div>`;
        }
        html += `</div>`;
    }

    // Advanced Analysis (new improvements)
    const advItems: string[] = [];
    if ((data.accum_duration_days ?? 0) > 0) {
        const dur = data.accum_duration_days!;
        const label = dur < 14 ? 'Terlalu Dini' : dur <= 56 ? 'Optimal' : dur <= 90 ? 'Mulai Lama' : 'Stale';
        const color = dur >= 14 && dur <= 56 ? '#059669' : dur > 90 ? '#dc2626' : '#3b82f6';
        advItems.push(`<div class="card"><div class="label">Durasi Akumulasi</div><div class="value" style="color:${color}">${dur} hari</div><div class="sub">${label}</div></div>`);
    }
    if (data.concentration_risk && data.concentration_risk !== 'NONE' && data.concentration_risk !== 'LOW') {
        const color = data.concentration_risk === 'HIGH' ? '#dc2626' : '#d97706';
        advItems.push(`<div class="card"><div class="label">Risiko Konsentrasi</div><div class="value" style="color:${color}">${data.concentration_broker} (${(data.concentration_pct ?? 0).toFixed(0)}%)</div><div class="sub">${data.concentration_risk}</div></div>`);
    }
    if (data.txn_smart_money_cum != null && data.txn_retail_cum_deep != null && (data.txn_smart_money_cum !== 0 || data.txn_retail_cum_deep !== 0)) {
        const div = data.smart_retail_divergence ?? 0;
        const label = div > 30 ? 'BULLISH' : div < -30 ? 'BEARISH' : 'NEUTRAL';
        const color = div > 30 ? '#059669' : div < -30 ? '#dc2626' : '#64748b';
        advItems.push(`<div class="card"><div class="label">Smart Money vs Retail</div><div class="value" style="color:${color}">SM ${data.txn_smart_money_cum > 0 ? '+' : ''}${data.txn_smart_money_cum.toFixed(1)}B / RTL ${data.txn_retail_cum_deep > 0 ? '+' : ''}${data.txn_retail_cum_deep.toFixed(1)}B</div><div class="sub">${label}</div></div>`);
    }
    if (data.volume_signal && data.volume_signal !== 'NONE' && data.volume_signal !== 'NEUTRAL') {
        const volLabels: Record<string, string> = { 'STEALTH_ACCUM': 'Stealth Accumulation', 'QUIET_ACCUM': 'Quiet Accumulation', 'ACTIVE_BREAKOUT': 'Active Breakout', 'DEAD': 'Dead Stock', 'DIST_COMPLETE': 'Distribution Complete' };
        const color = data.volume_signal.includes('ACCUM') || data.volume_signal === 'ACTIVE_BREAKOUT' ? '#059669' : '#dc2626';
        advItems.push(`<div class="card"><div class="label">Volume Context</div><div class="value" style="color:${color}">${volLabels[data.volume_signal] ?? data.volume_signal}</div><div class="sub">+${data.volume_score ?? 0} pts</div></div>`);
    }
    if (data.ma_cross_signal && data.ma_cross_signal !== 'NONE' && data.ma_cross_signal !== 'NEUTRAL') {
        const maLabels: Record<string, string> = { 'GOLDEN_CROSS': 'Golden Cross', 'DEATH_CROSS': 'Death Cross', 'PERFECT_BULLISH': 'Perfect Bullish', 'BULLISH_ALIGNMENT': 'Bullish Alignment', 'BEARISH_ALIGNMENT': 'Bearish Alignment', 'CONVERGING': 'MA Converging' };
        const color = data.ma_cross_signal === 'GOLDEN_CROSS' || data.ma_cross_signal === 'PERFECT_BULLISH' ? '#059669' : data.ma_cross_signal === 'DEATH_CROSS' || data.ma_cross_signal === 'BEARISH_ALIGNMENT' ? '#dc2626' : '#3b82f6';
        advItems.push(`<div class="card"><div class="label">MA Cross</div><div class="value" style="color:${color}">${maLabels[data.ma_cross_signal] ?? data.ma_cross_signal}</div><div class="sub">${(data.ma_cross_score ?? 0) > 0 ? '+' : ''}${data.ma_cross_score ?? 0} pts</div></div>`);
    }
    if (data.flow_acceleration_signal && data.flow_acceleration_signal !== 'NONE') {
        const accelLabels: Record<string, string> = { 'STRONG_ACCELERATING': '🚀 Strong Accel', 'ACCELERATING': '📈 Accelerating', 'MILD_ACCELERATING': '↗️ Mild Accel', 'STABLE': '➡️ Stable', 'MILD_DECELERATING': '↘️ Mild Decel', 'DECELERATING': '📉 Decelerating' };
        const color = data.flow_acceleration_signal.includes('ACCELERATING') ? '#059669' : data.flow_acceleration_signal === 'DECELERATING' ? '#dc2626' : '#64748b';
        advItems.push(`<div class="card"><div class="label">Flow Velocity</div><div class="value" style="color:${color}">${accelLabels[data.flow_acceleration_signal] ?? data.flow_acceleration_signal}</div><div class="sub">MM: ${(data.flow_velocity_mm ?? 0) > 0 ? '+' : ''}${(data.flow_velocity_mm ?? 0).toFixed(1)}B/d | ${(data.flow_velocity_score ?? 0) > 0 ? '+' : ''}${data.flow_velocity_score ?? 0} pts</div></div>`);
    }
    if (data.important_dates_signal && data.important_dates_signal !== 'NONE' && data.important_dates_signal !== 'NEUTRAL') {
        const color = data.important_dates_signal === 'STRONG_ACCUMULATION' ? '#059669' : data.important_dates_signal.includes('ACCUMULATION') ? '#3b82f6' : '#dc2626';
        advItems.push(`<div class="card"><div class="label">Important Dates</div><div class="value" style="color:${color}">${data.important_dates_signal.replace('_', ' ')}</div><div class="sub">${(data.important_dates ?? []).length} dates, ${(data.important_dates_score ?? 0) > 0 ? '+' : ''}${data.important_dates_score ?? 0} pts</div></div>`);
    }
    if (data.phase_transition && data.phase_transition !== 'NONE') {
        const parts = data.phase_transition.split('_TO_');
        const color = data.phase_transition.includes('TO_DISTRIBUTION') ? '#dc2626' : data.phase_transition.includes('TO_HOLDING') ? '#d97706' : '#059669';
        advItems.push(`<div class="card"><div class="label">Phase Transition</div><div class="value" style="color:${color}">${parts[0]} → ${parts[1]}</div><div class="sub">Score: ${data.prev_deep_score ?? 0} → ${data.deep_score ?? 0}</div></div>`);
    } else if (data.score_trend && data.score_trend !== 'NONE' && data.score_trend !== 'STABLE' && (data.prev_deep_score ?? 0) > 0) {
        const color = data.score_trend.includes('IMPROVING') ? '#059669' : '#dc2626';
        advItems.push(`<div class="card"><div class="label">Score Trend</div><div class="value" style="color:${color}">${data.prev_deep_score} → ${data.deep_score}</div><div class="sub">${data.score_trend.replace('_', ' ')}</div></div>`);
    }
    if (advItems.length > 0) {
        html += `<div class="section"><div class="section-title">Analisis Lanjutan</div><div class="grid4">${advItems.join('')}</div></div>`;
    }

    // Weekly Flow
    html += `<div class="section"><div class="section-title">Weekly Accumulation</div><div class="grid4">`;
    [{ l: 'W-4', v: data.w_4 }, { l: 'W-3', v: data.w_3 }, { l: 'W-2', v: data.w_2 }, { l: 'W-1', v: data.w_1 }].forEach(w => {
        html += `<div class="card" style="text-align:center"><div class="label">${w.l}</div><div class="value ${w.v > 0 ? 'pos' : w.v < 0 ? 'neg' : ''}">${w.v > 0 ? '+' : ''}${w.v?.toFixed(1) ?? '—'}</div></div>`;
    });
    html += `</div></div>`;

    // Signals
    if (data.deep_signals && Object.keys(data.deep_signals).length > 0) {
        html += `<div class="section"><div class="section-title">Deep Analysis Signals</div><div class="signal-list">`;
        Object.entries(data.deep_signals).forEach(([key, desc]) => {
            const isPos = key.includes('accum') || key.includes('buy') || key.includes('clean') || key.includes('up') || key.includes('inflow') || key.includes('positive');
            const isNeg = key.includes('sell') || key.includes('outflow') || key.includes('warning') || key.includes('dist');
            html += `<span class="signal" style="${isPos ? 'background:#d1fae5;color:#065f46;border-color:#a7f3d0' : isNeg ? 'background:#fee2e2;color:#991b1b;border-color:#fecaca' : ''}">${desc}</span>`;
        });
        html += `</div></div>`;
    }

    // Breakout Factors
    if (data.breakout_probability != null && data.breakout_probability > 0 && data.breakout_factors) {
        html += `<div class="section"><div class="section-title">Breakout Probability Factors (${data.breakout_probability}%)</div><div class="grid4">`;
        Object.entries(data.breakout_factors).forEach(([key, val]) => {
            const color = val >= 70 ? '#059669' : val >= 40 ? '#d97706' : '#dc2626';
            html += `<div class="card"><div class="label">${key.replace(/_/g, ' ')}</div><div class="value" style="color:${color}">${val}</div><div class="bar-container"><div class="bar-fill" style="width:${val}%;background:${color}"></div></div></div>`;
        });
        html += `</div></div>`;
    }

    // Pump Tomorrow Factors
    if (data.pump_tomorrow_score != null && data.pump_tomorrow_score > 0 && data.pump_tomorrow_factors) {
        const ptSignalLabel = data.pump_tomorrow_signal === 'STRONG_PUMP' ? '🚀 STRONG PUMP' : data.pump_tomorrow_signal === 'LIKELY_PUMP' ? '📈 LIKELY' : data.pump_tomorrow_signal === 'POSSIBLE_PUMP' ? '🔄 POSSIBLE' : data.pump_tomorrow_signal === 'LOW_CHANCE' ? '⚠️ LOW' : '';
        html += `<div class="section"><div class="section-title">🚀 Pump Tomorrow Prediction (${data.pump_tomorrow_score}% ${ptSignalLabel})</div><div class="grid4">`;
        Object.entries(data.pump_tomorrow_factors).forEach(([key, val]) => {
            const color = val >= 70 ? '#059669' : val >= 40 ? '#d97706' : '#dc2626';
            html += `<div class="card"><div class="label">${key.replace(/_/g, ' ')}</div><div class="value" style="color:${color}">${val}</div><div class="bar-container"><div class="bar-fill" style="width:${val}%;background:${color}"></div></div></div>`;
        });
        html += `</div></div>`;
    }

    // Top Holders
    if (data.top_holders && data.top_holders.length > 0) {
        html += `<div class="section"><div class="section-title">Top Holders (Cumulative Net Buy)</div><div style="display:flex;gap:8px">`;
        data.top_holders.forEach(h => {
            html += `<div class="card" style="text-align:center;min-width:80px"><div class="value pos">${h.broker_code}</div><div style="font-size:9px;font-weight:700">+${fmt(h.total_net_lot)} lot</div><div class="sub">${h.trade_count} trades</div></div>`;
        });
        html += `</div></div>`;
    }

    html += `<div class="footer">Generated by MarketPulse Bandarmology — ${new Date().toLocaleString('id-ID')}</div>`;
    html += `</body></html>`;
    return html;
}

export default function StockDetailModal({ ticker, date, onClose }: StockDetailModalProps) {
    const [data, setData] = useState<StockDetailResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    const handleDownloadPdf = () => {
        if (!data) return;
        const html = generatePdfHtml(data);
        const printWindow = window.open('', '_blank', 'width=900,height=700');
        if (!printWindow) return;
        printWindow.document.write(html);
        printWindow.document.close();
        setTimeout(() => { printWindow.print(); }, 400);
    };

    const handleCopyChat = async () => {
        if (!data) return;
        const text = generateChatText(data);
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    useEffect(() => {
        if (!ticker) return;
        const fetchDetail = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await bandarmologyApi.getStockDetail(ticker, date);
                setData(result);
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : 'Failed to load stock detail');
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
                <div className="flex flex-col sm:flex-row sm:items-center justify-between px-3 sm:px-5 py-3 bg-gradient-to-r from-purple-900/60 to-blue-900/60 border-b border-zinc-700/30 gap-2 sm:gap-0">
                    <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
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
                    <div className="flex items-center gap-1.5 flex-wrap justify-end">
                        {data && !loading && (
                            <>
                                <button
                                    onClick={handleCopyChat}
                                    className={cn(
                                        "flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-bold transition-all",
                                        copied
                                            ? "bg-emerald-500/20 border border-emerald-500/40 text-emerald-300"
                                            : "bg-zinc-700/50 border border-zinc-600/30 text-zinc-300 hover:bg-zinc-600/50 hover:text-white"
                                    )}
                                    title="Copy insight ke clipboard untuk dikirim via chat"
                                >
                                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                                    {copied ? 'Copied!' : 'Copy Chat'}
                                </button>
                                <button
                                    onClick={handleDownloadPdf}
                                    className="flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-bold bg-zinc-700/50 border border-zinc-600/30 text-zinc-300 hover:bg-zinc-600/50 hover:text-white transition-all"
                                    title="Download laporan PDF"
                                >
                                    <FileDown className="w-3.5 h-3.5" />
                                    PDF
                                </button>
                            </>
                        )}
                        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors p-1 rounded hover:bg-zinc-700/50">
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-3 sm:p-5 space-y-5 scrollbar-thin scrollbar-thumb-zinc-800">
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
                            {/* Data Freshness Warning */}
                            {(data.data_freshness ?? 1) < 1 && (
                                <div className="bg-amber-900/20 border border-amber-700/30 rounded-lg p-3 flex items-start gap-2">
                                    <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <div className="text-[11px] font-bold text-amber-400">Data Freshness Warning</div>
                                        <div className="text-[10px] text-amber-300/80">
                                            This analysis is based on data from {data.data_source_date || 'unknown date'}.
                                            Confidence: {(data.data_freshness! * 100).toFixed(0)}%
                                            {data.original_deep_score && data.original_deep_score !== data.deep_score && (
                                                <span className="ml-1">
                                                    (Original score: {data.original_deep_score}, Adjusted: {data.deep_score})
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Conflict Warning */}
                            {data.data_source_conflict && (
                                <div className="bg-red-900/20 border border-red-700/30 rounded-lg p-3 flex items-start gap-2">
                                    <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <div className="text-[11px] font-bold text-red-400">⚠️ Data Source Conflict</div>
                                        <div className="text-[10px] text-red-300/80">
                                            Data sources disagree on accumulation/distribution signals.
                                            {data.conflict_stats && (
                                                <span className="block mt-1">
                                                    CV: {data.conflict_stats.cv.toFixed(2)} |
                                                    Mean: {data.conflict_stats.mean.toFixed(1)} |
                                                    Std: {data.conflict_stats.std.toFixed(1)}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Relative Context */}
                            {data.relative_context?.market_context && (
                                <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-3">
                                    <div className="text-[11px] font-bold text-blue-400 mb-2 flex items-center gap-1">
                                        <TrendingUp className="w-3 h-3" />
                                        Market/Sector Context
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[10px]">
                                        <div>
                                            <div className="text-zinc-500">Market Comparison</div>
                                            <div className="text-zinc-300">
                                                Stock: {data.relative_context.market_context.stock_flow?.toFixed(1)}B<br/>
                                                Market Avg: {data.relative_context.market_context.market_avg?.toFixed(1)}B<br/>
                                                Z-Score: {data.relative_context.market_context.z_score?.toFixed(2)}<br/>
                                                Percentile: {data.relative_context.market_context.percentile?.toFixed(0)}%
                                            </div>
                                        </div>
                                        {data.relative_context.sector_context && (
                                            <div>
                                                <div className="text-zinc-500">Sector: {data.relative_context.sector_context.sector}</div>
                                                <div className="text-zinc-300">
                                                    Stock: {data.relative_context.sector_context.stock_flow?.toFixed(1)}B<br/>
                                                    Sector Avg: {data.relative_context.sector_context.sector_avg?.toFixed(1)}B<br/>
                                                    Diff: {data.relative_context.sector_context.diff_pct?.toFixed(1)}%
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    {data.relative_context.relative_score && data.relative_context.relative_score !== 1.0 && (
                                        <div className="mt-2 text-[10px] text-blue-300/80">
                                            Relative Score Multiplier: {data.relative_context.relative_score}x
                                            ({data.relative_context.relative_score >= 1.1 ? 'Above Average' : data.relative_context.relative_score <= 0.9 ? 'Below Average' : 'Neutral'})
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Score Overview */}
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
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
                                    label="Pump Tomorrow"
                                    value={data.pump_tomorrow_score ? `${data.pump_tomorrow_score}%` : '—'}
                                    sub={data.pump_tomorrow_signal ? (
                                        data.pump_tomorrow_signal === 'STRONG_PUMP' ? '🚀 STRONG' :
                                        data.pump_tomorrow_signal === 'LIKELY_PUMP' ? '📈 LIKELY' :
                                        data.pump_tomorrow_signal === 'POSSIBLE_PUMP' ? '🔄 POSSIBLE' :
                                        data.pump_tomorrow_signal === 'LOW_CHANCE' ? '⚠️ LOW' : '—'
                                    ) : ''}
                                    color={
                                        (data.pump_tomorrow_score ?? 0) >= 75 ? 'text-emerald-400' :
                                        (data.pump_tomorrow_score ?? 0) >= 55 ? 'text-cyan-400' :
                                        (data.pump_tomorrow_score ?? 0) >= 40 ? 'text-amber-400' :
                                        (data.pump_tomorrow_score ?? 0) > 0 ? 'text-orange-400' : 'text-zinc-600'
                                    }
                                    icon={<TrendingUp className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label="Entry Price"
                                    value={data.entry_price ? data.entry_price.toLocaleString('id-ID') : '—'}
                                    sub={data.entry_price && data.price ? `${((data.price - data.entry_price) / data.entry_price * 100).toFixed(1)}% from current` : ''}
                                    color="text-cyan-400"
                                    icon={<Crosshair className="w-3 h-3 text-zinc-600" />}
                                />
                                <MetricCard
                                    label={`Target Price ${data.target_method ? `(${data.target_method})` : ''}`}
                                    value={data.target_price ? data.target_price.toLocaleString('id-ID') : '—'}
                                    sub={data.risk_reward_ratio ? `R:R = 1:${data.risk_reward_ratio}` : ''}
                                    color="text-yellow-400"
                                    icon={<TrendingUp className="w-3 h-3 text-zinc-600" />}
                                />
                            </div>

                            {/* Entry/Target/SL Bar */}
                            {data.entry_price && data.target_price && data.stop_loss ? (
                                <div className="bg-zinc-800/30 rounded-lg p-3 border border-zinc-700/20">
                                    <div className="grid grid-cols-2 sm:flex sm:items-center sm:justify-between text-[10px] mb-2 gap-1 sm:gap-0">
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
                                    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-[9px] mb-3 pb-2 border-b border-zinc-700/30">
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
                                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-2">
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

                                    {/* Pump Tomorrow Factors */}
                                    {data.pump_tomorrow_score != null && data.pump_tomorrow_score > 0 && data.pump_tomorrow_factors && (
                                        <div className="mb-3 p-3 bg-zinc-800/30 rounded-lg border border-zinc-700/20">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">🚀 Pump Tomorrow Prediction</span>
                                                <span className={cn(
                                                    "text-sm font-black",
                                                    data.pump_tomorrow_score >= 75 ? 'text-emerald-400' :
                                                    data.pump_tomorrow_score >= 55 ? 'text-cyan-400' :
                                                    data.pump_tomorrow_score >= 40 ? 'text-amber-400' : 'text-orange-400'
                                                )}>{data.pump_tomorrow_score}%
                                                    <span className="text-[9px] font-normal text-zinc-500 ml-1">
                                                        {data.pump_tomorrow_signal === 'STRONG_PUMP' ? '🚀 STRONG PUMP' :
                                                         data.pump_tomorrow_signal === 'LIKELY_PUMP' ? '📈 LIKELY' :
                                                         data.pump_tomorrow_signal === 'POSSIBLE_PUMP' ? '🔄 POSSIBLE' :
                                                         data.pump_tomorrow_signal === 'LOW_CHANCE' ? '⚠️ LOW' : ''}
                                                    </span>
                                                </span>
                                            </div>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-2">
                                                {Object.entries(data.pump_tomorrow_factors).map(([key, val]) => (
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
                                                        <span className="text-[8px] text-zinc-500 w-24 truncate">{key.replace(/_/g, ' ')}</span>
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
                                        <div className="mb-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 text-[9px] px-1">
                                            <span className="text-zinc-500">
                                                Consistency ({data.broksum_days_analyzed}d):
                                                <span className={cn(
                                                    "font-black ml-1",
                                                    (data.broksum_consistency_score ?? 0) >= 70 ? 'text-emerald-400' :
                                                    (data.broksum_consistency_score ?? 0) >= 40 ? 'text-amber-400' : 'text-orange-400'
                                                )}>{data.broksum_consistency_score ?? 0}/100</span>
                                            </span>
                                            {data.broksum_consistent_buyers && data.broksum_consistent_buyers.length > 0 && (
                                                <span className="text-zinc-500 truncate">
                                                    Consistent buyers: {data.broksum_consistent_buyers.slice(0, 5).map(b => (
                                                        <span key={b.code} className={cn("font-bold ml-0.5", b.is_bandar ? 'text-emerald-400' : 'text-zinc-400')}>
                                                            {b.code}{b.is_bandar ? '★' : ''}
                                                        </span>
                                                    ))}
                                                </span>
                                            )}
                                            {data.broksum_consistent_sellers && data.broksum_consistent_sellers.filter(s => s.is_bandar).length > 0 && (
                                                <span className="text-red-400 truncate">
                                                    Bandar selling: {data.broksum_consistent_sellers.filter(s => s.is_bandar).map(s => s.code).join(', ')}
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* New Improvement Banners */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
                                        {/* Accumulation Duration */}
                                        {(data.accum_duration_days ?? 0) > 0 && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                (data.accum_duration_days ?? 0) >= 14 && (data.accum_duration_days ?? 0) <= 56
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : (data.accum_duration_days ?? 0) > 90
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-blue-500/10 border-blue-500/20'
                                            )}>
                                                <Activity className="w-3.5 h-3.5 flex-shrink-0 text-zinc-500" />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Durasi Akumulasi</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        (data.accum_duration_days ?? 0) >= 14 && (data.accum_duration_days ?? 0) <= 56
                                                            ? 'text-emerald-400'
                                                            : (data.accum_duration_days ?? 0) > 90
                                                            ? 'text-red-400'
                                                            : 'text-blue-400'
                                                    )}>
                                                        {data.accum_duration_days} hari
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            ({(data.accum_duration_days ?? 0) < 14 ? 'terlalu dini' :
                                                              (data.accum_duration_days ?? 0) <= 56 ? 'optimal' :
                                                              (data.accum_duration_days ?? 0) <= 90 ? 'mulai lama' : 'stale'})
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Concentration Risk */}
                                        {data.concentration_risk && data.concentration_risk !== 'NONE' && data.concentration_risk !== 'LOW' && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.concentration_risk === 'HIGH'
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-orange-500/10 border-orange-500/20'
                                            )}>
                                                <AlertTriangle className={cn(
                                                    "w-3.5 h-3.5 flex-shrink-0",
                                                    data.concentration_risk === 'HIGH' ? 'text-red-400' : 'text-orange-400'
                                                )} />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Risiko Konsentrasi</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.concentration_risk === 'HIGH' ? 'text-red-400' : 'text-orange-400'
                                                    )}>
                                                        {data.concentration_broker} menguasai {(data.concentration_pct ?? 0).toFixed(0)}%
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            (single-entity risk {data.concentration_risk})
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Smart Money vs Retail Divergence */}
                                        {(data.txn_smart_money_cum != null || data.txn_retail_cum_deep != null) &&
                                         (data.txn_smart_money_cum !== 0 || data.txn_retail_cum_deep !== 0) && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                (data.smart_retail_divergence ?? 0) > 30
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : (data.smart_retail_divergence ?? 0) < -30
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-blue-500/10 border-blue-500/20'
                                            )}>
                                                <Users className="w-3.5 h-3.5 flex-shrink-0 text-zinc-500" />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Smart Money vs Retail</div>
                                                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                                        <span className={cn("font-bold",
                                                            (data.txn_smart_money_cum ?? 0) > 0 ? 'text-emerald-400' :
                                                            (data.txn_smart_money_cum ?? 0) < 0 ? 'text-red-400' : 'text-zinc-500'
                                                        )}>
                                                            SM: {(data.txn_smart_money_cum ?? 0) > 0 ? '+' : ''}{(data.txn_smart_money_cum ?? 0).toFixed(1)}B
                                                        </span>
                                                        <span className={cn("font-bold",
                                                            (data.txn_retail_cum_deep ?? 0) > 0 ? 'text-emerald-400' :
                                                            (data.txn_retail_cum_deep ?? 0) < 0 ? 'text-red-400' : 'text-zinc-500'
                                                        )}>
                                                            RTL: {(data.txn_retail_cum_deep ?? 0) > 0 ? '+' : ''}{(data.txn_retail_cum_deep ?? 0).toFixed(1)}B
                                                        </span>
                                                        <span className={cn("text-[9px] font-black px-1.5 py-0.5 rounded",
                                                            (data.smart_retail_divergence ?? 0) > 30 ? 'bg-emerald-500/20 text-emerald-300' :
                                                            (data.smart_retail_divergence ?? 0) < -30 ? 'bg-red-500/20 text-red-300' :
                                                            'bg-zinc-700/50 text-zinc-400'
                                                        )}>
                                                            {(data.smart_retail_divergence ?? 0) > 30 ? 'BULLISH' :
                                                             (data.smart_retail_divergence ?? 0) < -30 ? 'BEARISH' : 'NEUTRAL'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* MA Cross Signal */}
                                        {data.ma_cross_signal && data.ma_cross_signal !== 'NONE' && data.ma_cross_signal !== 'NEUTRAL' && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.ma_cross_signal === 'GOLDEN_CROSS' || data.ma_cross_signal === 'PERFECT_BULLISH'
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : data.ma_cross_signal === 'BULLISH_ALIGNMENT'
                                                    ? 'bg-cyan-500/10 border-cyan-500/20'
                                                    : data.ma_cross_signal === 'DEATH_CROSS' || data.ma_cross_signal === 'BEARISH_ALIGNMENT'
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-blue-500/10 border-blue-500/20'
                                            )}>
                                                <TrendingUp className={cn(
                                                    "w-3.5 h-3.5 flex-shrink-0",
                                                    data.ma_cross_signal === 'GOLDEN_CROSS' || data.ma_cross_signal === 'PERFECT_BULLISH' ? 'text-emerald-400' :
                                                    data.ma_cross_signal === 'DEATH_CROSS' || data.ma_cross_signal === 'BEARISH_ALIGNMENT' ? 'text-red-400' :
                                                    'text-zinc-500'
                                                )} />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">MA Cross Signal</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.ma_cross_signal === 'GOLDEN_CROSS' ? 'text-emerald-400' :
                                                        data.ma_cross_signal === 'PERFECT_BULLISH' ? 'text-emerald-400' :
                                                        data.ma_cross_signal === 'BULLISH_ALIGNMENT' ? 'text-cyan-400' :
                                                        data.ma_cross_signal === 'DEATH_CROSS' ? 'text-red-400' :
                                                        data.ma_cross_signal === 'BEARISH_ALIGNMENT' ? 'text-red-400' :
                                                        'text-blue-400'
                                                    )}>
                                                        {data.ma_cross_signal === 'GOLDEN_CROSS' && '⚡ Golden Cross'}
                                                        {data.ma_cross_signal === 'DEATH_CROSS' && '💀 Death Cross'}
                                                        {data.ma_cross_signal === 'PERFECT_BULLISH' && '🎯 Perfect Bullish'}
                                                        {data.ma_cross_signal === 'BULLISH_ALIGNMENT' && '📈 Bullish Alignment'}
                                                        {data.ma_cross_signal === 'BEARISH_ALIGNMENT' && '📉 Bearish Alignment'}
                                                        {data.ma_cross_signal === 'CONVERGING' && '🔄 MA Converging'}
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            ({(data.ma_cross_score ?? 0) > 0 ? '+' : ''}{data.ma_cross_score ?? 0} pts)
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Phase Transition / Historical Comparison */}
                                        {data.phase_transition && data.phase_transition !== 'NONE' && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.phase_transition.includes('TO_DISTRIBUTION')
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : data.phase_transition.includes('TO_HOLDING')
                                                    ? 'bg-amber-500/10 border-amber-500/20'
                                                    : data.phase_transition.includes('TO_ACCUMULATION')
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : 'bg-blue-500/10 border-blue-500/20'
                                            )}>
                                                <Activity className={cn(
                                                    "w-3.5 h-3.5 flex-shrink-0",
                                                    data.phase_transition.includes('TO_DISTRIBUTION') ? 'text-red-400' :
                                                    data.phase_transition.includes('TO_HOLDING') ? 'text-amber-400' :
                                                    'text-emerald-400'
                                                )} />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Phase Transition</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.phase_transition.includes('TO_DISTRIBUTION') ? 'text-red-400' :
                                                        data.phase_transition.includes('TO_HOLDING') ? 'text-amber-400' :
                                                        'text-emerald-400'
                                                    )}>
                                                        {data.prev_phase} → {data.phase_transition.split('_TO_')[1]}
                                                    </div>
                                                    {data.score_trend && data.score_trend !== 'NONE' && (
                                                        <div className={cn(
                                                            "text-[9px] mt-0.5",
                                                            data.score_trend.includes('IMPROVING') ? 'text-emerald-500' :
                                                            data.score_trend.includes('DECLINING') ? 'text-red-500' :
                                                            'text-zinc-500'
                                                        )}>
                                                            Score: {data.prev_deep_score ?? 0} → {data.deep_score ?? 0}
                                                            ({data.score_trend.replace('_', ' ')})
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Score Trend (when no phase transition but score changed) */}
                                        {(!data.phase_transition || data.phase_transition === 'NONE') &&
                                         data.score_trend && data.score_trend !== 'NONE' && data.score_trend !== 'STABLE' &&
                                         (data.prev_deep_score ?? 0) > 0 && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.score_trend.includes('IMPROVING')
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : 'bg-red-500/10 border-red-500/20'
                                            )}>
                                                {data.score_trend.includes('IMPROVING') ? (
                                                    <TrendingUp className="w-3.5 h-3.5 flex-shrink-0 text-emerald-400" />
                                                ) : (
                                                    <TrendingDown className="w-3.5 h-3.5 flex-shrink-0 text-red-400" />
                                                )}
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Score Trend</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.score_trend.includes('IMPROVING') ? 'text-emerald-400' : 'text-red-400'
                                                    )}>
                                                        {data.prev_deep_score ?? 0} → {data.deep_score ?? 0}
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            ({data.score_trend === 'STRONG_IMPROVING' ? '↑↑ Strong Improving' :
                                                              data.score_trend === 'IMPROVING' ? '↑ Improving' :
                                                              data.score_trend === 'STRONG_DECLINING' ? '↓↓ Strong Declining' :
                                                              '↓ Declining'})
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Volume Context */}
                                        {data.volume_signal && data.volume_signal !== 'NONE' && data.volume_signal !== 'NEUTRAL' && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.volume_signal === 'STEALTH_ACCUM' || data.volume_signal === 'QUIET_ACCUM'
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : data.volume_signal === 'ACTIVE_BREAKOUT'
                                                    ? 'bg-cyan-500/10 border-cyan-500/20'
                                                    : data.volume_signal === 'DEAD' || data.volume_signal === 'DIST_COMPLETE'
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-blue-500/10 border-blue-500/20'
                                            )}>
                                                <BarChart3 className="w-3.5 h-3.5 flex-shrink-0 text-zinc-500" />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Volume Context</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.volume_signal === 'STEALTH_ACCUM' ? 'text-emerald-400' :
                                                        data.volume_signal === 'QUIET_ACCUM' ? 'text-emerald-400' :
                                                        data.volume_signal === 'ACTIVE_BREAKOUT' ? 'text-cyan-400' :
                                                        'text-red-400'
                                                    )}>
                                                        {data.volume_signal === 'STEALTH_ACCUM' && 'Stealth Accumulation'}
                                                        {data.volume_signal === 'QUIET_ACCUM' && 'Quiet Accumulation'}
                                                        {data.volume_signal === 'ACTIVE_BREAKOUT' && 'Active Breakout'}
                                                        {data.volume_signal === 'DEAD' && 'Dead Stock'}
                                                        {data.volume_signal === 'DIST_COMPLETE' && 'Distribution Complete'}
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            (+{data.volume_score ?? 0} pts)
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Flow Velocity / Acceleration */}
                                        {data.flow_acceleration_signal && data.flow_acceleration_signal !== 'NONE' && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.flow_acceleration_signal === 'STRONG_ACCELERATING'
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : data.flow_acceleration_signal === 'ACCELERATING' || data.flow_acceleration_signal === 'MILD_ACCELERATING'
                                                    ? 'bg-cyan-500/10 border-cyan-500/20'
                                                    : data.flow_acceleration_signal === 'DECELERATING'
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-zinc-500/10 border-zinc-500/20'
                                            )}>
                                                <Activity className={cn(
                                                    "w-3.5 h-3.5 flex-shrink-0",
                                                    data.flow_acceleration_signal.includes('ACCELERATING') ? 'text-emerald-400' :
                                                    data.flow_acceleration_signal === 'DECELERATING' ? 'text-red-400' :
                                                    'text-zinc-500'
                                                )} />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Flow Velocity</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.flow_acceleration_signal === 'STRONG_ACCELERATING' ? 'text-emerald-400' :
                                                        data.flow_acceleration_signal.includes('ACCELERATING') ? 'text-cyan-400' :
                                                        data.flow_acceleration_signal === 'DECELERATING' ? 'text-red-400' :
                                                        'text-zinc-400'
                                                    )}>
                                                        {data.flow_acceleration_signal === 'STRONG_ACCELERATING' && '🚀 Strong Accelerating'}
                                                        {data.flow_acceleration_signal === 'ACCELERATING' && '📈 Accelerating'}
                                                        {data.flow_acceleration_signal === 'MILD_ACCELERATING' && '↗️ Mild Accelerating'}
                                                        {data.flow_acceleration_signal === 'STABLE' && '➡️ Stable'}
                                                        {data.flow_acceleration_signal === 'MILD_DECELERATING' && '↘️ Mild Decelerating'}
                                                        {data.flow_acceleration_signal === 'DECELERATING' && '📉 Decelerating'}
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            ({(data.flow_velocity_score ?? 0) > 0 ? '+' : ''}{data.flow_velocity_score ?? 0} pts)
                                                        </span>
                                                    </div>
                                                    <div className="text-[9px] text-zinc-500 mt-0.5 flex flex-wrap gap-x-2">
                                                        <span>MM: {(data.flow_velocity_mm ?? 0) > 0 ? '+' : ''}{(data.flow_velocity_mm ?? 0).toFixed(1)}B/d</span>
                                                        <span>FGN: {(data.flow_velocity_foreign ?? 0) > 0 ? '+' : ''}{(data.flow_velocity_foreign ?? 0).toFixed(1)}B/d</span>
                                                        <span>INST: {(data.flow_velocity_institution ?? 0) > 0 ? '+' : ''}{(data.flow_velocity_institution ?? 0).toFixed(1)}B/d</span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Important Dates Broker Summary */}
                                        {data.important_dates_signal && data.important_dates_signal !== 'NONE' && data.important_dates_signal !== 'NEUTRAL' && (
                                            <div className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-[10px]",
                                                data.important_dates_signal === 'STRONG_ACCUMULATION'
                                                    ? 'bg-emerald-500/10 border-emerald-500/20'
                                                    : data.important_dates_signal === 'ACCUMULATION' || data.important_dates_signal === 'MILD_ACCUMULATION'
                                                    ? 'bg-cyan-500/10 border-cyan-500/20'
                                                    : data.important_dates_signal === 'DISTRIBUTION'
                                                    ? 'bg-red-500/10 border-red-500/20'
                                                    : 'bg-zinc-500/10 border-zinc-500/20'
                                            )}>
                                                <BarChart3 className={cn(
                                                    "w-3.5 h-3.5 flex-shrink-0",
                                                    data.important_dates_signal.includes('ACCUMULATION') ? 'text-emerald-400' :
                                                    data.important_dates_signal === 'DISTRIBUTION' ? 'text-red-400' :
                                                    'text-zinc-500'
                                                )} />
                                                <div>
                                                    <div className="text-[8px] text-zinc-500 font-bold uppercase">Important Dates Analysis</div>
                                                    <div className={cn(
                                                        "font-black",
                                                        data.important_dates_signal === 'STRONG_ACCUMULATION' ? 'text-emerald-400' :
                                                        data.important_dates_signal.includes('ACCUMULATION') ? 'text-cyan-400' :
                                                        data.important_dates_signal === 'DISTRIBUTION' ? 'text-red-400' :
                                                        'text-zinc-400'
                                                    )}>
                                                        {data.important_dates_signal === 'STRONG_ACCUMULATION' && '🏦 Strong Accumulation'}
                                                        {data.important_dates_signal === 'ACCUMULATION' && '📊 Accumulation'}
                                                        {data.important_dates_signal === 'MILD_ACCUMULATION' && '📈 Mild Accumulation'}
                                                        {data.important_dates_signal === 'DISTRIBUTION' && '⚠️ Distribution'}
                                                        <span className="text-zinc-500 font-normal ml-1">
                                                            ({(data.important_dates_score ?? 0) > 0 ? '+' : ''}{data.important_dates_score ?? 0} pts)
                                                        </span>
                                                    </div>
                                                    {data.important_dates && data.important_dates.length > 0 && (
                                                        <div className="text-[9px] text-zinc-500 mt-0.5">
                                                            {data.important_dates.length} tanggal: {data.important_dates.map(d =>
                                                                `${d.date.slice(5)} (${d.bandar_net_lot > 0 ? '+' : ''}${d.bandar_net_lot})`
                                                            ).join(', ')}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Broker table */}
                                    <div className="overflow-x-auto -mx-2 px-2">
                                    <table className="w-full text-[10px] min-w-[600px]">
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
                                </div>
                            )}

                            {/* Two Column Layout */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] mb-2">
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
                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                        {/* Buy Side */}
                                        <div>
                                            <div className="text-[9px] font-bold text-emerald-400 uppercase mb-1.5">Net Buyers</div>
                                            <div className="overflow-x-auto -mx-1 px-1">
                                            <table className="w-full text-[10px] min-w-[200px]">
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
                                            </div>
                                            {data.broksum_avg_buy_price ? (
                                                <div className="mt-2 text-[9px] text-zinc-500">
                                                    Weighted Avg Buy: <span className="text-cyan-400 font-bold">{data.broksum_avg_buy_price.toLocaleString('id-ID')}</span>
                                                </div>
                                            ) : null}
                                        </div>

                                        {/* Sell Side */}
                                        <div>
                                            <div className="text-[9px] font-bold text-red-400 uppercase mb-1.5">Net Sellers</div>
                                            <div className="overflow-x-auto -mx-1 px-1">
                                            <table className="w-full text-[10px] min-w-[200px]">
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
                                            </div>
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
                                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-3 pt-2 border-t border-zinc-700/30 text-[10px]">
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
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {/* Weekly Flow */}
                                <div className="bg-zinc-800/20 rounded-lg p-4 border border-zinc-700/20">
                                    <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                        <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
                                        Weekly Accumulation
                                    </h3>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
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
                                    <div className="flex flex-wrap gap-3">
                                        {data.top_holders.map((h, i) => (
                                            <div key={i} className="bg-zinc-800/50 rounded-lg p-2 text-center min-w-[80px] flex-1 sm:flex-none border border-zinc-700/20">
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
