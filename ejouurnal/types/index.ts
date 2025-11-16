export interface Emotion {
  id: string;
  name: string;
  emoji: string;
  color: string;
  intensity: number; // 1-5 scale
}

export interface JournalEntry {
  id: string;
  timestamp: Date;
  emotion: Emotion;
  who: string;
  when: string;
  where: string;
  how: string;
  additionalNotes?: string;
}

export interface DailySummary {
  date: string;
  entries: JournalEntry[];
  dominantEmotion: Emotion;
  summary: string;
  suggestions: Suggestion[];
}

export interface Suggestion {
  id: string;
  type: 'community' | 'professional';
  title: string;
  description: string;
  action: string;
  priority: 'low' | 'medium' | 'high';
}

export interface AppState {
  entries: JournalEntry[];
  emotions: Emotion[];
  summaries: DailySummary[];
}

