"use client";

import React, { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
    CheckCircle2,
    Target,
    Shield,
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    Award,
    ArrowRight,
    X,
    ChevronDown,
    ChevronUp,
    FileCheck
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAlphaHunter } from "../AlphaHunterContext";
import StageCard from "./StageCard";

interface Stage5ConclusionProps {
    ticker: string;
}

export default function Stage5Conclusion({ ticker }: Stage5ConclusionProps) {
    const { investigations, markComplete } = useAlphaHunter();
    const [showDetails, setShowDetails] = useState(false);
    const [isCompleting, setIsCompleting] = useState(false);
    const [isComplete, setIsComplete] = useState(false);

    const investigation = investigations[ticker];
    const stage1 = investigation?.stage1?.data;
    const stage2 = investigation?.stage2?.data;
    const stage3 = investigation?.stage3?.data;
    const stage4 = investigation?.stage4?.data;
    const isStage4Skipped = investigation?.stage4?.isSkipped;

    // Calculate final recommendation based on all stages
    const recommendation = useMemo(() => {
        if (!stage1 || !stage2 || !stage3) return null;

        let score = 0;
        let maxScore = 0;
        let reasons: string[] = [];
        let warnings: string[] = [];

        // Stage 1: Initial Signal (20 points)
        maxScore += 20;
        if (stage1.conviction === 'VERY_HIGH') {
            score += 20;
            reasons.push("Very high initial conviction");
        } else if (stage1.conviction === 'HIGH') {
            score += 15;
            reasons.push("High initial conviction");
        } else if (stage1.conviction === 'MEDIUM') {
            score += 10;
            reasons.push("Medium initial conviction");
        } else {
            score += 5;
            warnings.push("Low initial conviction");
        }

        // Stage 2: VPA Analysis (30 points)
        maxScore += 30;
        const s2Score = stage2.scores?.adjusted_health_score || 0;
        if (s2Score >= 70) {
            score += 30;
            reasons.push("Strong VPA health score");
        } else if (s2Score >= 50) {
            score += 20;
            reasons.push("Moderate VPA health");
        } else if (s2Score >= 30) {
            score += 10;
            warnings.push("Weak VPA health");
        } else {
            warnings.push("Poor VPA health");
        }

        // Stage 2: Breakout Status (10 points)
        maxScore += 10;
        if (stage2.breakout_setup?.status === 'ENTRY') {
            score += 10;
            reasons.push("Optimal entry setup");
        } else if (stage2.breakout_setup?.status === 'NEAR_BREAKOUT') {
            score += 7;
            reasons.push("Near breakout");
        } else if (stage2.breakout_setup?.status === 'WAITING') {
            score += 4;
            warnings.push("Waiting for setup");
        } else {
            warnings.push("No clear setup");
        }

        // Stage 3: Smart Money Flow (25 points)
        maxScore += 25;
        const s3Checks = stage3.checks_passed || 0;
        if (s3Checks >= 3) {
            score += 25;
            reasons.push("Strong smart money flow");
        } else if (s3Checks === 2) {
            score += 17;
            reasons.push("Moderate smart money flow");
        } else if (s3Checks === 1) {
            score += 8;
            warnings.push("Weak smart money flow");
        } else {
            warnings.push("No smart money confirmation");
        }

        // Stage 3: Floor Price Safety (5 points)
        maxScore += 5;
        if (stage3.gap_pct >= 5) {
            score += 5;
            reasons.push("Good margin of safety");
        } else if (stage3.gap_pct >= 0) {
            score += 3;
            reasons.push("Near floor price");
        } else {
            warnings.push("Below floor price");
        }

        // Stage 4: Supply Analysis (10 points - optional)
        if (!isStage4Skipped && stage4) {
            maxScore += 10;
            if (stage4.overall_signal === 'GO') {
                score += 10;
                reasons.push("Supply analysis confirms GO");
            } else if (stage4.overall_signal === 'CAUTION') {
                score += 5;
                warnings.push("Supply analysis shows caution");
            } else {
                warnings.push("Supply analysis indicates risk");
            }
        }

        // Calculate final score percentage
        const percentage = (score / maxScore) * 100;

        // Determine action
        let action: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'AVOID';
        if (percentage >= 80) {
            action = 'STRONG_BUY';
        } else if (percentage >= 60) {
            action = 'BUY';
        } else if (percentage >= 40) {
            action = 'HOLD';
        } else {
            action = 'AVOID';
        }

        // Calculate entry zone
        const currentPrice = stage3.current_price || stage1.price;
        const floorPrice = stage3.floor_price || currentPrice * 0.95;
        const entryLow = Math.min(currentPrice * 0.98, floorPrice * 1.02);
        const entryHigh = currentPrice * 1.02;

        // Calculate stop loss and targets
        const stopLoss = Math.min(floorPrice * 0.97, currentPrice * 0.95);
        const risk = entryHigh - stopLoss;
        const target1 = entryHigh + (risk * 2);
        const target2 = entryHigh + (risk * 3);

        return {
            action,
            score,
            maxScore,
            percentage,
            reasons,
            warnings,
            entry_zone: { low: entryLow, high: entryHigh },
            stop_loss: stopLoss,
            targets: [target1, target2],
            risk_reward: risk > 0 ? (target1 - entryHigh) / risk : 0,
        };
    }, [stage1, stage2, stage3, stage4, isStage4Skipped]);

    if (!recommendation) {
        return (
            <StageCard
                stageNumber={5}
                title="Final Conclusion"
                description="Complete all previous stages to generate recommendation"
                status="locked"
            >
                <div className="text-center py-8 text-slate-500">
                    Complete Stages 1-3 to see the final recommendation
                </div>
            </StageCard>
        );
    }

    const handleComplete = () => {
        setIsCompleting(true);
        markComplete(ticker, {
            action: recommendation.action,
            entry_zone: recommendation.entry_zone,
            stop_loss: recommendation.stop_loss,
            targets: recommendation.targets,
            risk_reward: recommendation.risk_reward,
            confidence: recommendation.percentage,
        });
        setTimeout(() => {
            setIsComplete(true);
            setIsCompleting(false);
        }, 500);
    };

    const getActionConfig = (action: string) => {
        switch (action) {
            case 'STRONG_BUY':
                return {
                    color: 'text-emerald-400',
                    bgColor: 'bg-emerald-500/20',
                    borderColor: 'border-emerald-500/50',
                    icon: <Award className="w-8 h-8" />,
                    emoji: '🚀',
                    label: 'STRONG BUY',
                    description: 'High conviction setup with multiple confirmations'
                };
            case 'BUY':
                return {
                    color: 'text-cyan-400',
                    bgColor: 'bg-cyan-500/20',
                    borderColor: 'border-cyan-500/50',
                    icon: <CheckCircle2 className="w-8 h-8" />,
                    emoji: '✅',
                    label: 'BUY',
                    description: 'Favorable setup with good risk/reward'
                };
            case 'HOLD':
                return {
                    color: 'text-amber-400',
                    bgColor: 'bg-amber-500/20',
                    borderColor: 'border-amber-500/50',
                    icon: <AlertTriangle className="w-8 h-8" />,
                    emoji: '⏳',
                    label: 'HOLD',
                    description: 'Wait for better entry or more confirmation'
                };
            case 'AVOID':
                return {
                    color: 'text-red-400',
                    bgColor: 'bg-red-500/20',
                    borderColor: 'border-red-500/50',
                    icon: <X className="w-8 h-8" />,
                    emoji: '❌',
                    label: 'AVOID',
                    description: 'Risk outweighs potential reward'
                };
            default:
                return {
                    color: 'text-slate-400',
                    bgColor: 'bg-slate-500/20',
                    borderColor: 'border-slate-500/50',
                    icon: <Shield className="w-8 h-8" />,
                    emoji: '⚪',
                    label: 'UNKNOWN',
                    description: 'Insufficient data'
                };
        }
    };

    const actionConfig = getActionConfig(recommendation.action);

    return (
        <StageCard
            stageNumber={5}
            title="Final Conclusion"
            description="Comprehensive analysis summary and recommendation"
            status="ready"
        >
            <div className="space-y-4 md:space-y-6">
                {/* Main Recommendation Card */}
                <Card className={cn(
                    "border-2",
                    actionConfig.borderColor,
                    actionConfig.bgColor
                )}>
                    <CardContent className="p-4 md:p-6">
                        <div className="text-center">
                            <div className="text-4xl md:text-5xl mb-2">{actionConfig.emoji}</div>
                            <h2 className={cn("text-2xl md:text-3xl font-bold mb-1", actionConfig.color)}>
                                {actionConfig.label}
                            </h2>
                            <p className="text-xs md:text-sm text-slate-400">
                                {actionConfig.description}
                            </p>

                            {/* Score Bar */}
                            <div className="mt-4 md:mt-6">
                                <div className="flex justify-between text-xs md:text-sm mb-1">
                                    <span className="text-slate-400">Confidence Score</span>
                                    <span className={cn("font-bold", actionConfig.color)}>
                                        {Math.round(recommendation.percentage)}%
                                    </span>
                                </div>
                                <div className="h-2 md:h-3 bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className={cn(
                                            "h-full rounded-full transition-all duration-1000",
                                            recommendation.percentage >= 80 ? "bg-emerald-500" :
                                                recommendation.percentage >= 60 ? "bg-cyan-500" :
                                                    recommendation.percentage >= 40 ? "bg-amber-500" : "bg-red-500"
                                        )}
                                        style={{ width: `${recommendation.percentage}%` }}
                                    />
                                </div>
                                <div className="text-xs text-slate-500 mt-1">
                                    {recommendation.score} / {recommendation.maxScore} points
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Entry Strategy - Mobile Optimized */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-4">
                    <Card className="bg-slate-950/50 border-slate-800">
                        <CardContent className="p-2 md:p-4">
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase mb-1">Entry Zone</div>
                            <div className="text-sm md:text-lg font-bold text-emerald-400">
                                Rp {Math.round(recommendation.entry_zone.low).toLocaleString()}
                            </div>
                            <div className="text-[10px] md:text-xs text-slate-500">
                                - Rp {Math.round(recommendation.entry_zone.high).toLocaleString()}
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-950/50 border-slate-800">
                        <CardContent className="p-2 md:p-4">
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase mb-1">Stop Loss</div>
                            <div className="text-sm md:text-lg font-bold text-red-400">
                                Rp {Math.round(recommendation.stop_loss).toLocaleString()}
                            </div>
                            <div className="text-[10px] md:text-xs text-slate-500">
                                Risk: {((recommendation.entry_zone.high - recommendation.stop_loss) / recommendation.entry_zone.high * 100).toFixed(1)}%
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-950/50 border-slate-800">
                        <CardContent className="p-2 md:p-4">
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase mb-1">Target 1</div>
                            <div className="text-sm md:text-lg font-bold text-cyan-400">
                                Rp {Math.round(recommendation.targets[0]).toLocaleString()}
                            </div>
                            <div className="text-[10px] md:text-xs text-slate-500">
                                2:1 R/R
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-950/50 border-slate-800">
                        <CardContent className="p-2 md:p-4">
                            <div className="text-[10px] md:text-xs text-slate-500 uppercase mb-1">Target 2</div>
                            <div className="text-sm md:text-lg font-bold text-blue-400">
                                Rp {Math.round(recommendation.targets[1]).toLocaleString()}
                            </div>
                            <div className="text-[10px] md:text-xs text-slate-500">
                                3:1 R/R
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Risk/Reward Badge */}
                <div className="flex justify-center">
                    <Badge
                        variant="outline"
                        className={cn(
                            "text-xs md:text-sm px-3 py-1 md:px-4 md:py-2",
                            recommendation.risk_reward >= 2 ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50" :
                                recommendation.risk_reward >= 1.5 ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/50" :
                                    "bg-amber-500/20 text-amber-400 border-amber-500/50"
                        )}
                    >
                        Risk/Reward: 1:{recommendation.risk_reward.toFixed(1)}
                    </Badge>
                </div>

                {/* Expandable Details */}
                <div className="border border-slate-800 rounded-lg overflow-hidden">
                    <button
                        onClick={() => setShowDetails(!showDetails)}
                        className="w-full flex items-center justify-between p-2 md:p-3 bg-slate-900/50 hover:bg-slate-900 transition-colors"
                    >
                        <span className="text-xs md:text-sm text-slate-400 uppercase font-semibold">Analysis Details</span>
                        {showDetails ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </button>
                    {showDetails && (
                        <div className="p-3 md:p-4 bg-slate-950/50 space-y-3">
                            {/* Positive Reasons */}
                            {recommendation.reasons.length > 0 && (
                                <div>
                                    <h4 className="text-[10px] md:text-xs font-semibold text-emerald-400 uppercase mb-2 flex items-center gap-1">
                                        <CheckCircle2 className="w-3 h-3" />
                                        Positive Factors ({recommendation.reasons.length})
                                    </h4>
                                    <ul className="space-y-1">
                                        {recommendation.reasons.map((reason, idx) => (
                                            <li key={idx} className="text-xs md:text-sm text-slate-300 flex items-start gap-2">
                                                <span className="text-emerald-500 mt-0.5">✓</span>
                                                {reason}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Warnings */}
                            {recommendation.warnings.length > 0 && (
                                <div className={recommendation.reasons.length > 0 ? "pt-2 border-t border-slate-800" : ""}>
                                    <h4 className="text-[10px] md:text-xs font-semibold text-amber-400 uppercase mb-2 flex items-center gap-1">
                                        <AlertTriangle className="w-3 h-3" />
                                        Concerns ({recommendation.warnings.length})
                                    </h4>
                                    <ul className="space-y-1">
                                        {recommendation.warnings.map((warning, idx) => (
                                            <li key={idx} className="text-xs md:text-sm text-slate-300 flex items-start gap-2">
                                                <span className="text-amber-500 mt-0.5">!</span>
                                                {warning}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Stage Summary */}
                            <div className="pt-2 border-t border-slate-800">
                                <h4 className="text-[10px] md:text-xs font-semibold text-slate-400 uppercase mb-2">Stage Summary</h4>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Stage 1:</span>
                                        <span className={stage1?.conviction === 'VERY_HIGH' ? 'text-emerald-400' : 'text-slate-300'}>
                                            {stage1?.conviction || 'N/A'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Stage 2:</span>
                                        <span className={stage2?.verdict === 'PASS' ? 'text-emerald-400' : stage2?.verdict === 'WATCH' ? 'text-amber-400' : 'text-red-400'}>
                                            {stage2?.verdict || 'N/A'} ({stage2?.scores?.adjusted_health_score || 0})
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Stage 3:</span>
                                        <span className={(stage3?.checks_passed || 0) >= 3 ? 'text-emerald-400' : (stage3?.checks_passed || 0) >= 2 ? 'text-amber-400' : 'text-red-400'}>
                                            {stage3?.checks_passed || 0}/{stage3?.total_checks || 4} checks
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Stage 4:</span>
                                        <span className={isStage4Skipped ? 'text-slate-500' : stage4?.overall_signal === 'GO' ? 'text-emerald-400' : stage4?.overall_signal === 'CAUTION' ? 'text-amber-400' : 'text-red-400'}>
                                            {isStage4Skipped ? 'Skipped' : stage4?.overall_signal || 'N/A'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Action Buttons */}
                {!isComplete ? (
                    <div className="flex flex-col sm:flex-row gap-2 sm:gap-4 pt-2">
                        <Button
                            onClick={handleComplete}
                            disabled={isCompleting}
                            className={cn(
                                "flex-1 bg-gradient-to-r",
                                recommendation.action === 'STRONG_BUY' || recommendation.action === 'BUY'
                                    ? "from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500"
                                    : recommendation.action === 'HOLD'
                                        ? "from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500"
                                        : "from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500"
                            )}
                        >
                            {isCompleting ? (
                                <>
                                    <div className="w-4 h-4 mr-2 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <FileCheck className="w-4 h-4 mr-2" />
                                    Mark Investigation Complete
                                </>
                            )}
                        </Button>
                    </div>
                ) : (
                    <div className="text-center py-4 bg-emerald-950/20 border border-emerald-500/30 rounded-lg">
                        <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400 mb-2" />
                        <p className="text-emerald-400 font-semibold">Investigation Completed!</p>
                        <p className="text-xs text-slate-500 mt-1">
                            Saved to your watchlist history
                        </p>
                    </div>
                )}
            </div>
        </StageCard>
    );
}
