'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Bell } from 'lucide-react';

interface YahooFinanceScreeningData {
  ticker: string;
  float_control_pct: number | null;
  float_level: 'WEAK' | 'MODERATE' | 'STRONG' | 'DOMINANT' | null;
  power_score: number | null;
  power_rating: 'EXCELLENT' | 'GOOD' | 'MODERATE' | 'POOR' | null;
  volume_ratio: number | null;
  volume_signal: 'ACCUMULATION' | 'DISTRIBUTION' | 'NORMAL' | null;
  days_to_earnings: number | null;
  earnings_signal: string | null;
}

// Float Cell - colored dot + percentage
interface FloatCellProps {
  data: YahooFinanceScreeningData | undefined;
}

export function FloatCell({ data }: FloatCellProps) {
  if (!data || data.float_control_pct == null) {
    return <span className="text-zinc-800 text-[9px]">—</span>;
  }

  const pct = data.float_control_pct;
  const level = data.float_level;

  const dotColor = level === 'DOMINANT' ? 'bg-red-500' :
                   level === 'STRONG' ? 'bg-orange-500' :
                   level === 'MODERATE' ? 'bg-yellow-500' : 'bg-emerald-500';

  const textColor = level === 'DOMINANT' ? 'text-red-400' :
                    level === 'STRONG' ? 'text-orange-400' :
                    level === 'MODERATE' ? 'text-yellow-400' : 'text-emerald-400';

  return (
    <div className="flex items-center gap-1 justify-center" title={`Float Control: ${pct.toFixed(1)}% (${level})`}>
      <span className={cn("w-2 h-2 rounded-full", dotColor)} />
      <span className={cn("text-[10px] font-bold tabular-nums", textColor)}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

// Power Cell - colored badge with score
interface PowerCellProps {
  data: YahooFinanceScreeningData | undefined;
}

export function PowerCell({ data }: PowerCellProps) {
  if (!data || data.power_score == null) {
    return <span className="text-zinc-800 text-[9px]">—</span>;
  }

  const score = data.power_score;
  const rating = data.power_rating;

  const bgColor = rating === 'EXCELLENT' ? 'bg-emerald-500/20 border-emerald-500/40' :
                  rating === 'GOOD' ? 'bg-cyan-500/20 border-cyan-500/40' :
                  rating === 'MODERATE' ? 'bg-yellow-500/20 border-yellow-500/40' : 'bg-zinc-500/20 border-zinc-500/40';

  const textColor = rating === 'EXCELLENT' ? 'text-emerald-400' :
                    rating === 'GOOD' ? 'text-cyan-400' :
                    rating === 'MODERATE' ? 'text-yellow-400' : 'text-zinc-400';

  return (
    <div className="flex items-center justify-center" title={`Bandar Power: ${score}/100 (${rating})`}>
      <span className={cn(
        "text-[9px] font-bold tabular-nums px-1.5 py-0.5 rounded border",
        bgColor, textColor
      )}>
        {score}
      </span>
    </div>
  );
}

// Volume Cell - icon + ratio
interface VolumeCellProps {
  data: YahooFinanceScreeningData | undefined;
}

export function VolumeCell({ data }: VolumeCellProps) {
  if (!data || data.volume_ratio == null) {
    return <span className="text-zinc-800 text-[9px]">—</span>;
  }

  const ratio = data.volume_ratio;
  const signal = data.volume_signal;

  const isAccumulation = signal === 'ACCUMULATION';
  const isDistribution = signal === 'DISTRIBUTION';

  const iconColor = isAccumulation ? 'text-emerald-400' :
                    isDistribution ? 'text-red-400' : 'text-zinc-400';

  const textColor = isAccumulation ? 'text-emerald-400' :
                    isDistribution ? 'text-red-400' : 'text-zinc-400';

  return (
    <div className="flex items-center gap-0.5 justify-center" title={`Volume: ${ratio.toFixed(1)}x avg (${signal})`}>
      {isAccumulation ? (
        <TrendingUp className={cn("w-3 h-3", iconColor)} />
      ) : isDistribution ? (
        <TrendingDown className={cn("w-3 h-3", iconColor)} />
      ) : (
        <span className="w-3 h-3 rounded-full bg-zinc-600" />
      )}
      <span className={cn("text-[10px] font-bold tabular-nums", textColor)}>
        {ratio.toFixed(1)}x
      </span>
    </div>
  );
}

// Earnings Cell - days + alert icon
interface EarningsCellProps {
  data: YahooFinanceScreeningData | undefined;
}

export function EarningsCell({ data }: EarningsCellProps) {
  if (!data || data.days_to_earnings == null) {
    return <span className="text-zinc-800 text-[9px]">—</span>;
  }

  const days = data.days_to_earnings;
  const signal = data.earnings_signal;

  const isUrgent = days < 7 && signal?.includes('ACCUM');
  const isWatch = days < 14 && signal?.includes('ACCUM');

  const iconColor = isUrgent ? 'text-red-400' :
                    isWatch ? 'text-yellow-400' : 'text-emerald-400';

  const textColor = isUrgent ? 'text-red-400' :
                    isWatch ? 'text-yellow-400' : 'text-emerald-400';

  return (
    <div className="flex items-center gap-0.5 justify-center" title={`Earnings in ${days} days (${signal})`}>
      <span className={cn("text-[10px] font-bold tabular-nums", textColor)}>
        {days}d
      </span>
      {(isUrgent || isWatch) && (
        <Bell className={cn("w-3 h-3", iconColor)} />
      )}
    </div>
  );
}

// Combined row component for expandable view
interface YahooFinanceRowProps {
  data: YahooFinanceScreeningData | undefined;
}

export function YahooFinanceRow({ data }: YahooFinanceRowProps) {
  if (!data) {
    return (
      <div className="flex items-center gap-4 text-zinc-600 text-[9px]">
        <span>No Yahoo Finance data available</span>
      </div>
    );
  }

  const hasAnyData = data.float_control_pct != null ||
                     data.power_score != null ||
                     data.volume_ratio != null ||
                     data.days_to_earnings != null;

  if (!hasAnyData) {
    return (
      <div className="flex items-center gap-4 text-zinc-600 text-[9px]">
        <span>No Yahoo Finance data available</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4">
      {data.float_control_pct != null && (
        <div className="flex items-center gap-1" title="Float Control">
          <span className="text-zinc-500 text-[8px]">Float:</span>
          <FloatCell data={data} />
        </div>
      )}
      {data.power_score != null && (
        <div className="flex items-center gap-1" title="Bandar Power">
          <span className="text-zinc-500 text-[8px]">Power:</span>
          <PowerCell data={data} />
        </div>
      )}
      {data.volume_ratio != null && (
        <div className="flex items-center gap-1" title="Volume">
          <span className="text-zinc-500 text-[8px]">Vol:</span>
          <VolumeCell data={data} />
        </div>
      )}
      {data.days_to_earnings != null && (
        <div className="flex items-center gap-1" title="Earnings">
          <span className="text-zinc-500 text-[8px]">Earn:</span>
          <EarningsCell data={data} />
        </div>
      )}
    </div>
  );
}
