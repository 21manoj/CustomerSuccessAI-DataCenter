/**
 * ProductTour — Lightweight interactive tour overlay
 * ====================================================
 *
 * Custom tour component (no external library). Shows step-by-step highlights
 * with tooltips pointing at DOM elements. Persists completion in localStorage.
 *
 * Usage:
 *   <ProductTour steps={STARTER_TOUR_STEPS} onComplete={() => {}} />
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';

export interface TourStep {
  /** CSS selector for the target element to highlight */
  target: string;
  /** Step title */
  title: string;
  /** Step description */
  content: string;
  /** Tooltip position relative to the target */
  position?: 'top' | 'right' | 'bottom' | 'left';
}

interface ProductTourProps {
  steps: TourStep[];
  /** Called when the tour is completed or skipped */
  onComplete: () => void;
  /** localStorage key to persist completion */
  storageKey?: string;
}

/** Default Starter tier tour steps */
export const STARTER_TOUR_STEPS: TourStep[] = [
  {
    target: '[data-tour="portfolio-overview"]',
    title: 'Portfolio Overview',
    content: 'This is your daily starting point. See all your accounts, their health scores, and what needs attention.',
    position: 'bottom',
  },
  {
    target: '[data-tour="health-scores"]',
    title: 'Health Scores',
    content: 'Each account gets a health score from 0-100. Green means healthy (70+), yellow needs attention (50-69), and red is critical (below 50).',
    position: 'bottom',
  },
  {
    target: '[data-tour="smart-actions"]',
    title: 'Smart Actions',
    content: 'Your AI-powered daily to-do list. Actions are ranked by urgency and impact. Start with #1 each morning.',
    position: 'right',
  },
  {
    target: '[data-tour="account-cards"]',
    title: 'Account Details',
    content: 'Click any account to see its full health breakdown, timeline, and KPI details.',
    position: 'top',
  },
  {
    target: '[data-tour="tab-upload"]',
    title: 'Upload Data',
    content: 'Bring in your CSV files here. We support account lists, KPI measurements, and qualitative signals.',
    position: 'right',
  },
  {
    target: '[data-tour="tab-settings"]',
    title: 'Settings',
    content: 'Fine-tune how scores are calculated. Adjust weights and boundaries to match your priorities.',
    position: 'right',
  },
  {
    target: '',
    title: "You're ready! \ud83c\udf89",
    content: "That's it! You're set to start managing your accounts. If you need this tour again, you can replay it from Settings.",
    position: 'bottom',
  },
];

const ProductTour: React.FC<ProductTourProps> = ({
  steps,
  onComplete,
  storageKey = 'tour_completed',
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
  const tooltipRef = useRef<HTMLDivElement>(null);

  const step = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;
  const isCenterStep = !step.target; // No target = center overlay

  // Position the tooltip near the target element
  const positionTooltip = useCallback(() => {
    if (isCenterStep) {
      // Center in viewport
      setTooltipStyle({
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      });
      return;
    }

    const target = document.querySelector(step.target);
    if (!target) {
      // If target not found, center instead
      setTooltipStyle({
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      });
      return;
    }

    const rect = target.getBoundingClientRect();
    const tooltipWidth = 360;
    const tooltipHeight = 160;
    const gap = 16;

    let top = 0;
    let left = 0;

    switch (step.position) {
      case 'top':
        top = rect.top - tooltipHeight - gap;
        left = rect.left + rect.width / 2 - tooltipWidth / 2;
        break;
      case 'right':
        top = rect.top + rect.height / 2 - tooltipHeight / 2;
        left = rect.right + gap;
        break;
      case 'left':
        top = rect.top + rect.height / 2 - tooltipHeight / 2;
        left = rect.left - tooltipWidth - gap;
        break;
      case 'bottom':
      default:
        top = rect.bottom + gap;
        left = rect.left + rect.width / 2 - tooltipWidth / 2;
        break;
    }

    // Clamp to viewport
    top = Math.max(16, Math.min(window.innerHeight - tooltipHeight - 16, top));
    left = Math.max(16, Math.min(window.innerWidth - tooltipWidth - 16, left));

    setTooltipStyle({
      position: 'fixed',
      top: `${top}px`,
      left: `${left}px`,
    });

    // Scroll target into view
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [currentStep, step, isCenterStep]);

  useEffect(() => {
    positionTooltip();
    const handleResize = () => positionTooltip();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [positionTooltip]);

  const handleNext = () => {
    if (isLastStep) {
      localStorage.setItem(storageKey, 'true');
      onComplete();
    } else {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) setCurrentStep(prev => prev - 1);
  };

  const handleSkip = () => {
    localStorage.setItem(storageKey, 'true');
    onComplete();
  };

  return (
    <div className="fixed inset-0 z-[100]">
      {/* Overlay backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={handleSkip} />

      {/* Tooltip card */}
      <div
        ref={tooltipRef}
        style={tooltipStyle}
        className="z-[101] w-[360px] bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
      >
        {/* Progress bar */}
        <div className="h-1 bg-gray-100">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          />
        </div>

        <div className="p-5">
          {/* Step counter + skip */}
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-gray-400">
              Step {currentStep + 1} of {steps.length}
            </span>
            <button
              onClick={handleSkip}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              Skip tour
            </button>
          </div>

          {/* Content */}
          <h3 className="text-base font-semibold text-gray-900 mb-2 flex items-center">
            {isCenterStep && <Sparkles className="h-5 w-5 text-amber-500 mr-2" />}
            {step.title}
          </h3>
          <p className="text-sm text-gray-600 leading-relaxed mb-4">{step.content}</p>

          {/* Navigation buttons */}
          <div className="flex items-center justify-between">
            <button
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="flex items-center text-sm text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4 mr-1" /> Back
            </button>
            <button
              onClick={handleNext}
              className="flex items-center px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              {isLastStep ? "Let's go!" : 'Next'}
              {!isLastStep && <ChevronRight className="h-4 w-4 ml-1" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductTour;
