'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
    LayoutDashboard,
    Newspaper,
    MessageSquare,
    TrendingUp,
    ChevronLeft,
    ChevronRight,
    LineChart,
    BarChart3,
    ArrowRightLeft,
    ClipboardList,
    CandlestickChart,
    FlaskConical,
    Search,
    Target,
    Calculator,
    Menu,
    X
} from 'lucide-react';
import { ScraperControl } from './scraper-control';

const navGroups = [
    {
        title: 'Investigation',
        items: [
            { icon: FlaskConical, label: 'Alpha Hunter', href: '/alpha-hunter' },
            { icon: Target, label: 'Bandarmology', href: '/bandarmology' },
            { icon: Calculator, label: 'Adimology', href: '/adimology' },
        ]
    },
    {
        title: 'Core',
        items: [
            { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
            { icon: Newspaper, label: 'News Library', href: '/news-library' },
            { icon: Search, label: 'Story Finder', href: '/story-finder' },
        ]
    },
    {
        title: 'NeoBDM Analysis',
        items: [
            { icon: BarChart3, label: 'Market Summary', href: '/neobdm-summary' },
            { icon: ArrowRightLeft, label: 'Broker Summary', href: '/broker-summary' },
            { icon: LineChart, label: 'Flow Tracker', href: '/neobdm-tracker' },
            { icon: ClipboardList, label: 'Done Detail', href: '/done-detail' },

        ]
    },
    {
        title: 'Price Volume Analysis',
        items: [
            { icon: CandlestickChart, label: 'Price & Volume', href: '/price-volume' },
        ]
    },
    {
        title: 'Intelligence',
        items: [
            { icon: MessageSquare, label: 'RAG Chat', href: '/rag-chat' },
        ]
    }
];

interface SidebarProps {
    mobile?: boolean;
}

export const Sidebar = ({ mobile }: SidebarProps) => {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const pathname = usePathname();

    // Close mobile menu when route changes
    useEffect(() => {
        setIsMobileMenuOpen(false);
    }, [pathname]);

    // Prevent body scroll when mobile menu is open
    useEffect(() => {
        if (isMobileMenuOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [isMobileMenuOpen]);

    if (mobile) {
        return (
            <>
                {/* Mobile Header */}
                <header className="fixed top-0 left-0 right-0 h-14 bg-[#09090b]/95 backdrop-blur-md border-b border-zinc-800/40 z-50 flex items-center justify-between px-4">
                    <Link href="/dashboard" className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shrink-0 shadow-lg shadow-purple-500/20">
                            <TrendingUp className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-black tracking-tighter text-zinc-100 italic">
                            MarketPulse
                        </span>
                    </Link>
                    <button
                        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                        className="p-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-700 text-zinc-300 transition-colors"
                        aria-label="Toggle menu"
                    >
                        {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                    </button>
                </header>

                {/* Mobile Menu Overlay */}
                {isMobileMenuOpen && (
                    <div
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
                        onClick={() => setIsMobileMenuOpen(false)}
                    />
                )}

                {/* Mobile Navigation Drawer */}
                <div
                    className={cn(
                        "fixed top-14 left-0 right-0 bottom-0 bg-[#09090b] border-r border-zinc-800/40 z-50 transform transition-transform duration-300 ease-out overflow-hidden",
                        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
                    )}
                >
                    <div className="flex flex-col h-full p-4 gap-4 overflow-y-auto">
                        {navGroups.map((group) => (
                            <div key={group.title} className="space-y-2">
                                <div className="px-2 text-[10px] font-black text-zinc-500 uppercase tracking-widest opacity-60">
                                    {group.title}
                                </div>
                                <div className="flex flex-col gap-0.5">
                                    {group.items.map((item) => {
                                        const isActive = pathname === item.href;
                                        return (
                                            <Link
                                                key={item.href}
                                                href={item.href}
                                                className={cn(
                                                    "flex items-center gap-3 px-3 py-3 rounded-lg transition-all whitespace-nowrap border border-transparent",
                                                    isActive
                                                        ? "bg-blue-500/10 text-blue-400 border-blue-500/20 font-bold shadow-sm"
                                                        : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                                                )}
                                            >
                                                <item.icon className={cn(
                                                    "w-5 h-5 shrink-0",
                                                    isActive ? "text-blue-500" : "text-zinc-500"
                                                )} />
                                                <span className="text-sm tracking-tight">
                                                    {item.label}
                                                </span>
                                                {isActive && (
                                                    <div className="ml-auto w-1 h-3 rounded-full bg-blue-500" />
                                                )}
                                            </Link>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}

                        <div className="mt-auto">
                            <ScraperControl isCollapsed={false} />
                            <div className="px-2 py-4 text-[10px] text-zinc-600 border-t border-zinc-900">
                                v1.0.0 Alpha
                            </div>
                        </div>
                    </div>
                </div>
            </>
        );
    }

    // Desktop Sidebar
    return (
        <div className={cn(
            "h-full bg-[#09090b] border-r border-zinc-800/40 flex flex-col p-3 gap-4 transition-all duration-300 relative",
            isCollapsed ? "w-16" : "w-64"
        )}>
            {/* Toggle Button */}
            <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="absolute -right-3 top-10 bg-zinc-800 border border-zinc-700 rounded-full p-1 text-zinc-400 hover:text-white hover:bg-zinc-700 shadow-lg z-50"
            >
                {isCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
            </button>

            <div className={cn("flex items-center gap-2 px-2 py-4 overflow-hidden whitespace-nowrap")}>
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shrink-0 shadow-lg shadow-purple-500/20">
                    <TrendingUp className="w-5 h-5 text-white" />
                </div>
                {!isCollapsed && (
                    <span className="text-lg font-black tracking-tighter text-zinc-100 italic animate-in fade-in duration-500">MarketPulse</span>
                )}
            </div>


            <div className="flex-1 flex flex-col gap-6 overflow-y-auto overflow-x-hidden scrollbar-none px-1">
                {navGroups.map((group) => (
                    <div key={group.title} className="space-y-1.5">
                        {!isCollapsed && (
                            <div className="px-3 mb-2 text-[10px] font-black text-zinc-500 uppercase tracking-widest opacity-60">
                                {group.title}
                            </div>
                        )}
                        <div className="flex flex-col gap-0.5">
                            {group.items.map((item) => {
                                const isActive = pathname === item.href;
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        title={isCollapsed ? item.label : undefined}
                                        className={cn(
                                            "flex items-center gap-3 px-3 py-2 rounded-lg transition-all whitespace-nowrap border border-transparent group",
                                            isActive
                                                ? "bg-blue-500/10 text-blue-400 border-blue-500/20 font-bold shadow-sm"
                                                : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                                        )}
                                    >
                                        <item.icon className={cn(
                                            "w-5 h-5 shrink-0 transition-transform group-hover:scale-110",
                                            isActive ? "text-blue-500" : "text-zinc-500 group-hover:text-zinc-300"
                                        )} />
                                        {!isCollapsed && (
                                            <span className="text-xs animate-in fade-in slide-in-from-left-2 duration-300 tracking-tight">
                                                {item.label}
                                            </span>
                                        )}
                                        {!isCollapsed && isActive && (
                                            <div className="ml-auto w-1 h-3 rounded-full bg-blue-500 animate-in fade-in duration-500" />
                                        )}
                                    </Link>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            <ScraperControl isCollapsed={isCollapsed} />

            <div className={cn(
                "px-2 py-4 text-[10px] text-zinc-600 border-t border-zinc-900 overflow-hidden whitespace-nowrap transition-opacity",
                isCollapsed && "opacity-0 invisible"
            )}>
                v1.0.0 Alpha
            </div>
        </div>
    );
};
