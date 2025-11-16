// Core data types for Fulfillment app

export type DayPart = 'morning' | 'day' | 'evening' | 'night';

export type Mood = 'very-low' | 'low' | 'neutral' | 'good' | 'great';

export type Arousal = 'low' | 'medium' | 'high';

export type ContextTag = 'work' | 'sleep' | 'social';

export type MicroAct = 
  | 'gratitude'
  | 'kindness'
  | 'learning'
  | 'nature'
  | 'meditation'
  | 'breathwork'
  | 'walk'
  | 'journal';

export type SocialQuality = 'energized' | 'neutral' | 'drained';

export type FuelQuality = 'good' | 'ok' | 'poor';

export type PurposeProgress = 'yes' | 'partly' | 'no';

// Check-in data structure
export interface CheckIn {
  id: string;
  timestamp: Date;
  dayPart: DayPart;
  mood: Mood;
  arousal?: Arousal;
  contexts: ContextTag[];
  microAct?: MicroAct;
  voiceNote?: string; // file path or URI
  purposeProgress?: PurposeProgress; // only for night check-in
  sparkleTagged?: boolean;
}

// Body metrics
export interface BodyMetrics {
  date: Date;
  sleepHours?: number;
  sleepQuality?: number; // 0-100 from HealthKit
  steps?: number;
  activeMinutes?: number;
  hrv?: number;
  restingHR?: number;
  fuelQuality?: FuelQuality;
}

// Mind metrics
export interface MindMetrics {
  date: Date;
  focusMinutes: number;
  stressReliefUsed: boolean;
  screenTimeMinutes?: number;
  socialMediaMinutes?: number;
}

// Soul metrics
export interface SoulMetrics {
  date: Date;
  microActs: MicroAct[];
  socialInteractions: SocialQuality[];
}

// Purpose tracking
export interface WeeklyIntention {
  id: string;
  weekStart: Date;
  intention: string;
  microMoves: MicroMove[];
  antiGlitterExperiment?: string;
}

export interface MicroMove {
  id: string;
  description: string;
  completed: boolean;
  completedDate?: Date;
}

// Scores
export interface DailyScores {
  date: Date;
  bodyScore: number; // 0-100
  mindScore: number; // 0-100
  soulScore: number; // 0-100
  purposeScore: number; // 0-100
  fulfillmentScore: number; // weighted average
  isMeaningfulDay: boolean;
}

// Lineage insights
export interface LineageInsight {
  id: string;
  type: 'same-day' | 'lag' | 'breakpoint' | 'purpose-path';
  title: string;
  description: string;
  confidence: 'low' | 'medium' | 'high';
  sourceMetric: string;
  targetMetric: string;
  lagDays?: number;
  impact: number; // e.g., +7 points
}

// Weekly summary
export interface WeeklySummary {
  weekStart: Date;
  weekEnd: Date;
  meaningfulDaysCount: number; // MDW - north star!
  avgBodyScore: number;
  avgMindScore: number;
  avgSoulScore: number;
  avgPurposeScore: number;
  avgFulfillmentScore: number;
  topInsights: LineageInsight[];
  socialMinutesDelta: number; // vs baseline
  purposeAdherence: number; // % of micro-moves completed
}

// User preferences
export interface UserPreferences {
  fulfillmentWeights: {
    body: number;
    mind: number;
    soul: number;
    purpose: number;
  };
  bodyThreshold: number;
  mindThreshold: number;
  soulThreshold: number;
  socialMinutesBaseline: number;
  reminderTimes: {
    morning?: string;
    day?: string;
    evening?: string;
    night?: string;
  };
  antiGlitterEnabled: boolean;
  sparkleFilterLevel: number; // 0-100
}

