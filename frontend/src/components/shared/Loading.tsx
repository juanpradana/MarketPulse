/**
 * Loading State Component
 * 
 * Consistent loading spinner/skeleton UI
 */

import { Loader2 } from 'lucide-react';

interface LoadingProps {
    text?: string;
    fullPage?: boolean;
    size?: 'sm' | 'md' | 'lg';
}

const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
};

export function Loading({ text = 'Loading...', fullPage = false, size = 'md' }: LoadingProps) {
    const content = (
        <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className={`${sizeClasses[size]} animate-spin text-blue-500`} />
            <p className="text-sm text-gray-500">{text}</p>
        </div>
    );

    if (fullPage) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                {content}
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center py-12">
            {content}
        </div>
    );
}
