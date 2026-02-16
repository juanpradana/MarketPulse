/**
 * Skeleton Loading Components
 *
 * Content-shaped placeholders for better perceived performance
 */

import { cn } from '@/lib/utils';

/**
 * Base skeleton element with pulse animation
 */
export function Skeleton({
    className = '',
    variant = 'default'
}: {
    className?: string;
    variant?: 'default' | 'circle' | 'card';
}) {
    const baseClasses = 'animate-pulse bg-gray-300';

    const variantClasses = {
        default: 'rounded',
        circle: 'rounded-full',
        card: 'rounded-lg'
    };

    return (
        <div className={cn(baseClasses, variantClasses[variant], className)} />
    );
}

/**
 * Text line skeleton
 */
export function TextSkeleton({
    width = '100%',
    height = 'h-4',
    className = ''
}: {
    width?: string;
    height?: string;
    className?: string;
}) {
    return (
        <div className={`animate-pulse bg-gray-300 rounded ${height} ${className}`} style={{ width }} />
    );
}

/**
 * Card skeleton with header, content, and optional image
 */
export function CardSkeleton({
    hasImage = false,
    lines = 3,
    className = ''
}: {
    hasImage?: boolean;
    lines?: number;
    className?: string;
}) {
    return (
        <div className={cn(
            "p-4 border rounded-lg space-y-4 bg-white",
            className
        )}>
            {hasImage && (
                <Skeleton className="w-full h-40 rounded-lg" />
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-6 w-16 rounded-full" />
            </div>

            {/* Content lines */}
            <div className="space-y-2">
                {Array.from({ length: lines }).map((_, i) => (
                    <Skeleton
                        key={i}
                        className={`h-4 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
                    />
                ))}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-20 rounded" />
            </div>
        </div>
    );
}

/**
 * Stats card skeleton
 */
export function StatsCardSkeleton() {
    return (
        <div className="p-4 border rounded-lg bg-white">
            <div className="flex items-center justify-between mb-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-8 rounded-full" />
            </div>
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-4 w-16" />
        </div>
    );
}

/**
 * Table skeleton with header and rows
 */
export function TableSkeleton({
    rows = 5,
    cols = 4,
    showHeader = true,
    className = ''
}: {
    rows?: number;
    cols?: number;
    showHeader?: boolean;
    className?: string;
}) {
    return (
        <div className={cn("space-y-2", className)}>
            {/* Header */}
            {showHeader && (
                <div className="flex gap-4 pb-2 border-b">
                    {Array.from({ length: cols }).map((_, i) => (
                        <Skeleton key={`header-${i}`} className="h-6 flex-1" />
                    ))}
                </div>
            )}

            {/* Rows */}
            <div className="space-y-2">
                {Array.from({ length: rows }).map((_, i) => (
                    <div key={i} className="flex gap-4 py-2">
                        {Array.from({ length: cols }).map((_, j) => (
                            <Skeleton
                                key={j}
                                className={`h-10 flex-1 ${j === 0 ? 'w-24' : ''}`}
                            />
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Chart skeleton
 */
export function ChartSkeleton({
    height = '300px',
    showLegend = true,
    className = ''
}: {
    height?: string;
    showLegend?: boolean;
    className?: string;
}) {
    return (
        <div className={cn("space-y-4", className)}>
            {/* Title */}
            <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-8 w-32 rounded" />
            </div>

            {/* Chart area */}
            <div
                className="relative border rounded-lg overflow-hidden"
                style={{ height }}
            >
                <Skeleton className="absolute inset-0" />

                {/* Chart lines simulation */}
                <div className="absolute inset-0 p-4">
                    <svg className="w-full h-full" preserveAspectRatio="none">
                        <rect className="animate-pulse fill-gray-300" width="100%" height="100%" />
                    </svg>
                </div>
            </div>

            {/* Legend */}
            {showLegend && (
                <div className="flex gap-4 justify-center">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-2">
                            <Skeleton className="w-3 h-3 rounded-full" />
                            <Skeleton className="h-4 w-20" />
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

/**
 * News item skeleton
 */
export function NewsItemSkeleton() {
    return (
        <div className="p-4 border-b last:border-b-0 space-y-3">
            <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <div className="flex items-center gap-4">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-20" />
            </div>
        </div>
    );
}

/**
 * News feed skeleton with multiple items
 */
export function NewsFeedSkeleton({ count = 5 }: { count?: number }) {
    return (
        <div className="border rounded-lg overflow-hidden">
            {Array.from({ length: count }).map((_, i) => (
                <NewsItemSkeleton key={i} />
            ))}
        </div>
    );
}

/**
 * Dashboard stats grid skeleton
 */
export function DashboardStatsSkeleton() {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
                <StatsCardSkeleton key={i} />
            ))}
        </div>
    );
}

/**
 * Watchlist item skeleton
 */
export function WatchlistItemSkeleton() {
    return (
        <div className="p-4 border rounded-lg space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <Skeleton className="h-6 w-20 mb-1" />
                    <Skeleton className="h-4 w-32" />
                </div>
                <Skeleton className="h-8 w-8 rounded" />
            </div>

            {/* Price */}
            <div className="space-y-2">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-5 w-20 rounded-full" />
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-2 border-t">
                <Skeleton className="h-8 flex-1 rounded" />
                <Skeleton className="h-8 flex-1 rounded" />
                <Skeleton className="h-8 flex-1 rounded" />
            </div>
        </div>
    );
}

/**
 * Watchlist grid skeleton
 */
export function WatchlistGridSkeleton({ count = 6 }: { count?: number }) {
    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: count }).map((_, i) => (
                <WatchlistItemSkeleton key={i} />
            ))}
        </div>
    );
}

/**
 * Page header skeleton
 */
export function PageHeaderSkeleton() {
    return (
        <div className="flex items-center gap-2 mb-6">
            <Skeleton className="h-6 w-6 rounded" />
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-6 w-16 rounded-full ml-2" />
        </div>
    );
}

/**
 * Filter bar skeleton
 */
export function FilterBarSkeleton() {
    return (
        <div className="flex flex-wrap gap-4 p-4 border rounded-lg mb-6">
            <Skeleton className="h-10 w-48 rounded" />
            <Skeleton className="h-10 w-48 rounded" />
            <Skeleton className="h-10 w-32 rounded ml-auto" />
        </div>
    );
}

/**
 * Full page skeleton for initial load
 */
export function PageSkeleton({
    showStats = true,
    showChart = true,
    showTable = true
}: {
    showStats?: boolean;
    showChart?: boolean;
    showTable?: boolean;
}) {
    return (
        <div className="p-6 space-y-6">
            <PageHeaderSkeleton />
            <FilterBarSkeleton />

            {showStats && <DashboardStatsSkeleton />}

            {showChart && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <ChartSkeleton />
                    <ChartSkeleton />
                </div>
            )}

            {showTable && <TableSkeleton rows={8} cols={5} />}
        </div>
    );
}

/**
 * Loading overlay with skeleton
 */
export function SkeletonOverlay({
    children,
    isLoading,
    skeleton
}: {
    children: React.ReactNode;
    isLoading: boolean;
    skeleton: React.ReactNode;
}) {
    if (!isLoading) return <>{children}</>;

    return (
        <div className="relative">
            <div className="opacity-50 pointer-events-none">
                {children}
            </div>
            <div className="absolute inset-0 bg-white/80 flex items-center justify-center z-10">
                {skeleton}
            </div>
        </div>
    );
}
