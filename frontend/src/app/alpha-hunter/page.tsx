"use client";

import React, { useState, useCallback } from "react";
import { AlphaHunterProvider, useAlphaHunter } from "@/components/alpha-hunter/AlphaHunterContext";
import { Stage1Data, Pattern, FlowSignal } from "@/components/alpha-hunter/types";
import WatchlistSidebar from "@/components/alpha-hunter/WatchlistSidebar";
import InvestigationHeader from "@/components/alpha-hunter/InvestigationHeader";
import AnomalyScanTable from "@/components/alpha-hunter/AnomalyScanTable";
import Stage1Summary from "@/components/alpha-hunter/stages/Stage1Summary";
import Stage2VPACard from "@/components/alpha-hunter/stages/Stage2VPACard";
import Stage3FlowCard from "@/components/alpha-hunter/stages/Stage3FlowCard";
import Stage4SupplyCard from "@/components/alpha-hunter/stages/Stage4SupplyCard";
import Stage5Conclusion from "@/components/alpha-hunter/stages/Stage5Conclusion";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

function AlphaHunterContent() {
    const { selectedTicker, investigations, isAtScanner, addInvestigation } = useAlphaHunter();
    const [refreshKey, setRefreshKey] = useState(0);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

    const handleRefresh = useCallback(() => {
        setRefreshKey(prev => prev + 1);
    }, []);

    const handleAddToInvestigation = useCallback((signal: FlowSignal) => {
        // Map the signal data to Stage1Data
        const stage1Data: Stage1Data = {
            signal_score: signal.signal_score,
            signal_strength: signal.signal_strength,
            conviction: String(signal.conviction || ''),
            patterns: (signal.patterns as Pattern[]) || [],
            flow: signal.flow,
            change: signal.change,
            price: signal.price,
            entry_zone: String(signal.entry_zone || ''),
            detected_at: new Date().toISOString()
        };

        addInvestigation(signal.symbol, stage1Data);
    }, [addInvestigation]);

    const toggleSidebar = useCallback(() => {
        setSidebarCollapsed(prev => !prev);
    }, []);

    return (
        <div className="flex h-full min-h-0 overflow-hidden bg-slate-950 text-slate-100">
            {/* Left Sidebar: Watchlist - Hidden on mobile */}
            <div className={cn(
                "shrink-0 transition-all hidden md:block",
                sidebarCollapsed ? "w-14" : "w-80"
            )}>
                <WatchlistSidebar isCollapsed={sidebarCollapsed} onToggle={toggleSidebar} />
            </div>

            {/* Mobile Watchlist Toggle */}
            <div className="md:hidden fixed bottom-4 right-4 z-50">
                <button
                    onClick={toggleSidebar}
                    className="w-12 h-12 rounded-full bg-blue-600 hover:bg-blue-500 text-white shadow-lg flex items-center justify-center"
                >
                    {sidebarCollapsed ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                </button>
            </div>

            {/* Mobile Watchlist Drawer */}
            <div className={cn(
                "fixed inset-y-0 left-0 z-40 w-[85vw] max-w-80 bg-slate-900 transform transition-transform duration-300 md:hidden",
                sidebarCollapsed ? "-translate-x-full" : "translate-x-0"
            )}>
                <WatchlistSidebar isCollapsed={false} onToggle={toggleSidebar} />
            </div>

            {/* Mobile Overlay */}
            {!sidebarCollapsed && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden"
                    onClick={() => setSidebarCollapsed(true)}
                />
            )}

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Dynamic Header */}
                <InvestigationHeader onRefresh={handleRefresh} />

                {/* Content Area */}
                <ScrollArea className="flex-1">
                    <div className="p-3 md:p-6">
                        {isAtScanner ? (
                            // Scanner View
                            <div className="space-y-6">
                                <div>
                                    <p className="text-slate-400">
                                        Detecting smart money accumulation patterns from NeoBDM fund flow data.
                                    </p>
                                </div>

                                <AnomalyScanTable
                                    key={refreshKey}
                                    onAddToWatchlist={handleRefresh}
                                    onAddToInvestigation={handleAddToInvestigation}
                                />
                            </div>
                        ) : selectedTicker && investigations[selectedTicker] ? (
                            // Investigation View
                            <div className="space-y-6 pb-20">
                                {/* Stage 1 Summary */}
                                <Stage1Summary ticker={selectedTicker} />

                                {/* Stage 2: VPA */}
                                <Stage2VPACard ticker={selectedTicker} />

                                {/* Stage 3: Smart Money Flow */}
                                <Stage3FlowCard ticker={selectedTicker} />

                                {/* Stage 4: Supply Analysis */}
                                <Stage4SupplyCard ticker={selectedTicker} />

                                {/* Stage 5: Final Conclusion */}
                                <Stage5Conclusion ticker={selectedTicker} />
                            </div>
                        ) : (
                            // Fallback: No ticker selected
                            <div className="flex items-center justify-center h-96">
                                <div className="text-center">
                                    <div className="text-4xl mb-4">🔍</div>
                                    <h3 className="text-xl font-semibold text-slate-400 mb-2">
                                        No Investigation Selected
                                    </h3>
                                    <p className="text-slate-500">
                                        Select a ticker from the watchlist or add one from the Scanner.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </div>
        </div>
    );
}

// Wrapper with Provider
export default function AlphaHunterPage() {
    return (
        <AlphaHunterProvider>
            <AlphaHunterContent />
        </AlphaHunterProvider>
    );
}
