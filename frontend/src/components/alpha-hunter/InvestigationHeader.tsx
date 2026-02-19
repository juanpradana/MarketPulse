"use client";

import React from "react";
import { ArrowLeft, RefreshCw, Settings, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAlphaHunter } from "./AlphaHunterContext";
import { cn } from "@/lib/utils";

interface InvestigationHeaderProps {
    onRefresh?: () => void;
}

export default function InvestigationHeader({ onRefresh }: InvestigationHeaderProps) {
    const { selectedTicker, investigations, isAtScanner, goToScanner } = useAlphaHunter();

    // Scanner view header
    if (isAtScanner) {
        return (
            <header className="border-b border-slate-800 bg-slate-900/50 px-3 py-3 backdrop-blur md:px-6 md:py-3 sticky top-0 z-10">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-lg md:text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                        🧪 Alpha Hunter Lab
                    </h1>
                    <p className="text-xs md:text-sm text-slate-400">
                        Stage 1: Flow-Based Signal Scanner
                    </p>
                </div>

                <div className="flex items-center gap-2 md:gap-3">
                    {/* Quick stats */}
                    <div className="flex items-center gap-2 text-xs md:text-sm">
                        <Badge variant="outline" className="border-slate-700 text-slate-400 text-[11px] md:text-xs">
                            {Object.keys(investigations).length} Active Cases
                        </Badge>
                    </div>

                    {onRefresh && (
                        <Button variant="ghost" size="icon" onClick={onRefresh} title="Refresh Scan">
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                    )}
                </div>
                </div>
            </header>
        );
    }

    // Investigation view header
    const investigation = selectedTicker ? investigations[selectedTicker] : null;

    // Calculate progress
    const getProgressInfo = () => {
        if (!investigation) return { completed: 0, total: 4, text: "0/4 stages" };

        let completed = 1; // Stage 1 always complete
        if (investigation.stage2.status === 'ready') completed++;
        if (investigation.stage3.status === 'ready') completed++;
        if (investigation.stage4.status === 'ready' || investigation.stage4.isSkipped) completed++;

        return {
            completed,
            total: 4,
            text: `${completed}/4 stages`
        };
    };

    const progress = getProgressInfo();
    const lastUpdated = investigation?.stage2.lastUpdated ||
        investigation?.stage3.lastUpdated ||
        investigation?.stage4.lastUpdated;

    const getRelativeTime = (isoString: string | null) => {
        if (!isoString) return "Never";
        const diff = Date.now() - new Date(isoString).getTime();
        const minutes = Math.floor(diff / 60000);
        if (minutes < 1) return "Just now";
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        return `${Math.floor(hours / 24)}d ago`;
    };

    return (
        <header className="border-b border-slate-800 bg-slate-900/50 px-3 py-3 backdrop-blur md:px-6 sticky top-0 z-10">
            <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2 md:gap-4 min-w-0">
                {/* Back button */}
                <Button
                    variant="ghost"
                    onClick={goToScanner}
                    className="flex items-center gap-1.5 px-2 md:px-3 text-slate-400 hover:text-emerald-400 hover:bg-slate-800"
                >
                    <ArrowLeft className="h-4 w-4" />
                    <span className="text-xs md:text-sm">Back</span>
                </Button>

                <div className="hidden md:block h-6 w-px bg-slate-700" />

                {/* Ticker info */}
                <div className="min-w-0">
                    <div className="flex items-center gap-2">
                        <h1 className="text-lg md:text-xl font-bold text-slate-100 truncate">
                            {selectedTicker}
                        </h1>
                        <span className="text-slate-500 text-xs md:text-sm">Investigation</span>
                        {investigation?.isComplete && (
                            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">
                                Complete
                            </Badge>
                        )}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 md:gap-3 text-[11px] md:text-xs text-slate-500">
                        {/* Progress bar mini */}
                        <div className="flex items-center gap-1">
                            {[1, 2, 3, 4].map((stage) => (
                                <div
                                    key={stage}
                                    className={cn(
                                        "w-4 h-1.5 rounded-full transition-colors",
                                        stage <= progress.completed
                                            ? "bg-emerald-500"
                                            : "bg-slate-700"
                                    )}
                                />
                            ))}
                            <span className="ml-1">{progress.text}</span>
                        </div>
                        <span className="hidden md:inline">•</span>
                        <span>Last updated: {getRelativeTime(lastUpdated || null)}</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-1 md:gap-2 shrink-0">
                {onRefresh && (
                    <Button variant="ghost" size="icon" onClick={onRefresh} title="Refresh Data">
                        <RefreshCw className="h-4 w-4" />
                    </Button>
                )}
                <Button variant="ghost" size="icon" title="Export Report">
                    <Download className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" title="Settings">
                    <Settings className="h-4 w-4" />
                </Button>
            </div>
            </div>
        </header>
    );
}
