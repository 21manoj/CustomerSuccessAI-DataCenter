/**
 * InfoTooltip — Lightweight hover tooltip component
 * ===================================================
 *
 * Pure CSS tooltip using Tailwind. Shows an (i) icon that reveals
 * a plain-English explanation on hover. No external library needed.
 *
 * Usage:
 *   <InfoTooltip text="This score measures overall account health from 0-100." />
 *   <InfoTooltip text="Drag a CSV here." position="bottom" />
 */

import React from 'react';
import { Info } from 'lucide-react';

interface InfoTooltipProps {
  text: string;
  /** Tooltip position relative to the (i) icon */
  position?: 'top' | 'right' | 'bottom' | 'left';
  /** Optional link for "Learn more" */
  learnMoreUrl?: string;
  /** Size of the info icon */
  size?: 'sm' | 'md';
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({
  text,
  position = 'top',
  learnMoreUrl,
  size = 'sm',
}) => {
  const iconSize = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';

  // Position classes for the tooltip bubble
  const positionClasses: Record<string, string> = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  };

  // Arrow position classes
  const arrowClasses: Record<string, string> = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800',
  };

  return (
    <span className="relative inline-flex items-center group ml-1 cursor-help">
      <Info className={`${iconSize} text-gray-400 group-hover:text-blue-500 transition-colors`} />
      {/* Tooltip bubble */}
      <span
        className={`absolute ${positionClasses[position]} z-50 invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none group-hover:pointer-events-auto`}
      >
        <span className="block bg-gray-800 text-white text-xs rounded-lg py-2 px-3 max-w-xs whitespace-normal leading-relaxed shadow-lg">
          {text}
          {learnMoreUrl && (
            <a
              href={learnMoreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block mt-1 text-blue-300 hover:text-blue-200 underline"
            >
              Learn more
            </a>
          )}
        </span>
      </span>
    </span>
  );
};

export default InfoTooltip;
