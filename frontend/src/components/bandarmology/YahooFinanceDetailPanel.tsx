'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Bell, Target, BarChart3, Calendar, PieChart } from 'lucide-react';
import { YahooFinanceScreeningData } from '@/services/api/bandarmology';

interface YahooFinanceDetailPanelProps {
  data: YahooFinanceScreeningData | undefined;
}

export function YahooFinanceDetailPanel({ data }: YahooFinanceDetailPanelProps) {
  if (!data) {
    return (
      <div className="p-4 text-zinc-500 text-sm">
        No Yahoo Finance data available.
      </div>
    );
  }

  const hasAnyData = data.float_control_pct != null ||
                     data.power_score != null ||
                     data.volume_ratio != null ||
                     data.days_to_earnings != null;

  if (!hasAnyData) {
    return (
      <div className="p-4 text-zinc-500 text-sm">
        No Yahoo Finance data available. Run deep analysis to generate enhanced metrics.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-purple-400 mb-3">
        <BarChart3 className="w-4 h-4" />
        <span className="text-sm font-bold uppercase tracking-wider">Yahoo Finance Analysis</span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Float Control */}
        {data.float_control_pct != null && (
          <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/30">
            <div className="flex items-center gap-1.5 mb-2">
              <PieChart className="w-3 h-3 text-zinc-500" />
              <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Float Control</span>
            </div>
            <FloatControlBar
              pct={data.float_control_pct}
              level={data.float_level}
            />
          </div>
        )}

        {/* Power Score */}
        {data.power_score != null && (
          <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/30">
            <div className="flex items-center gap-1.5 mb-2">
              <Target className="w-3 h-3 text-zinc-500" />
              <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Bandar Power</span>
            </div>
            <PowerScoreBar
              score={data.power_score}
              rating={data.power_rating}
            />
          </div>
        )}

        {/* Volume */}
        {data.volume_ratio != null && (
          <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/30">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart3 className="w-3 h-3 text-zinc-500" />
              <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Volume</span>
            </div>
            <VolumeIndicator
              ratio={data.volume_ratio}
              signal={data.volume_signal}
            />
          </div>
        )}

        {/* Earnings */}
        {data.days_to_earnings != null && (
          <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/30">
            <div className="flex items-center gap-1.5 mb-2">
              <Calendar className="w-3 h-3 text-zinc-500" />
              <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Earnings</span>
            </div>
            <EarningsIndicator
              days={data.days_to_earnings}
              signal={data.earnings_signal}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// Float Control Visual
function FloatControlBar({ pct, level }: { pct: number; level: string | null }) {
  const normalizedPct = Math.min(pct, 30); // Cap at 30% for visual
  const barWidth = (normalizedPct / 30) * 100;

  const barColor = level === 'DOMINANT' ? 'bg-red-500' :
                   level === 'STRONG' ? 'bg-orange-500' :
                   level === 'MODERATE' ? 'bg-yellow-500' : 'bg-emerald-500';

  const textColor = level === 'DOMINANT' ? 'text-red-400' :
                    level === 'STRONG' ? 'text-orange-400' :
                    level === 'MODERATE' ? 'text-yellow-400' : 'text-emerald-400';

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className={cn("text-lg font-black tabular-nums", textColor)}>
          {pct.toFixed(1)}%
        </span>
        <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-700/50", textColor)}>
          {level}
        </span>
      </div>
      <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <div className="text-[8px] text-zinc-500">
        % of float controlled by bandar
      </div>
    </div>
  );
}

// Power Score Visual
function PowerScoreBar({ score, rating }: { score: number; rating: string | null }) {
  const barWidth = score;

  const barColor = rating === 'EXCELLENT' ? 'bg-emerald-500' :
                   rating === 'GOOD' ? 'bg-cyan-500' :
                   rating === 'MODERATE' ? 'bg-yellow-500' : 'bg-zinc-500';

  const textColor = rating === 'EXCELLENT' ? 'text-emerald-400' :
                    rating === 'GOOD' ? 'text-cyan-400' :
                    rating === 'MODERATE' ? 'text-yellow-400' : 'text-zinc-400';

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className={cn("text-lg font-black tabular-nums", textColor)}>
          {score}
        </span>
        <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-700/50", textColor)}>
          {rating}
        </span>
      </div>
      <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <div className="text-[8px] text-zinc-500">
        0-100 composite attractiveness score
      </div>
    </div>
  );
}

// Volume Indicator
function VolumeIndicator({ ratio, signal }: { ratio: number; signal: string | null }) {
  const isAccumulation = signal === 'ACCUMULATION';
  const isDistribution = signal === 'DISTRIBUTION';

  const iconColor = isAccumulation ? 'text-emerald-400' :
                    isDistribution ? 'text-red-400' : 'text-zinc-400';

  const textColor = isAccumulation ? 'text-emerald-400' :
                    isDistribution ? 'text-red-400' : 'text-zinc-400';

  const signalColor = isAccumulation ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' :
                      isDistribution ? 'bg-red-500/20 text-red-400 border-red-500/40' :
                      'bg-zinc-500/20 text-zinc-400 border-zinc-500/40';

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          {isAccumulation ? (
            <TrendingUp className={cn("w-4 h-4", iconColor)} />
          ) : isDistribution ? (
            <TrendingDown className={cn("w-4 h-4", iconColor)} />
          ) : (
            <div className="w-4 h-4 rounded-full bg-zinc-600" />
          )}
          <span className={cn("text-lg font-black tabular-nums", textColor)}>
            {ratio.toFixed(1)}x
          </span>
        </div>
      </div>
      <div className="text-[10px] text-zinc-400">
        Current vs 10-day avg volume
      </div>
      <span className={cn("inline-block text-[9px] font-bold px-1.5 py-0.5 rounded border", signalColor)}>
        {signal || 'NORMAL'}
      </span>
    </div>
  );
}

// Earnings Indicator
function EarningsIndicator({ days, signal }: { days: number; signal: string | null }) {
  const isUrgent = days < 7 && signal?.includes('ACCUM');
  const isWatch = days < 14 && signal?.includes('ACCUM');

  const iconColor = isUrgent ? 'text-red-400' :
                    isWatch ? 'text-yellow-400' : 'text-emerald-400';

  const textColor = isUrgent ? 'text-red-400' :
                    isWatch ? 'text-yellow-400' : 'text-emerald-400';

  const signalColor = isUrgent ? 'bg-red-500/20 text-red-400 border-red-500/40' :
                      isWatch ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' :
                      'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <Bell className={cn("w-4 h-4", iconColor)} />
        <span className={cn("text-lg font-black tabular-nums", textColor)}>
          {days}d
        </span>
      </div>
      <div className="text-[10px] text-zinc-400">
        Days until earnings report
      </div>
      {signal && (
        <span className={cn("inline-block text-[9px] font-bold px-1.5 py-0.5 rounded border", signalColor)}>
          {signal.replace(/_/g, ' ')}
        </span>
      )}
    </div>
  );
}
