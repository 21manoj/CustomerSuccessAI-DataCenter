/**
 * StorageService - Local storage with AsyncStorage
 * Handles all data persistence on-device
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  CheckIn,
  DailyScores,
  WeeklyIntention,
  UserPreferences,
} from '../types/fulfillment';
import { DetailData } from '../components/AddDetailsScreen';

// Storage keys
const KEYS = {
  CHECK_INS: '@fulfillment/check_ins',
  DAILY_SCORES: '@fulfillment/daily_scores',
  BODY_METRICS: '@fulfillment/body_metrics',
  MIND_METRICS: '@fulfillment/mind_metrics',
  SOUL_METRICS: '@fulfillment/soul_metrics',
  WEEKLY_INTENTIONS: '@fulfillment/weekly_intentions',
  DETAIL_DATA: '@fulfillment/detail_data',
  JOURNALS: '@fulfillment/journals',
  USER_PREFERENCES: '@fulfillment/user_preferences',
  INSIGHTS: '@fulfillment/insights',
};

export class StorageService {
  private static instance: StorageService;

  static getInstance(): StorageService {
    if (!StorageService.instance) {
      StorageService.instance = new StorageService();
    }
    return StorageService.instance;
  }

  // CHECK-INS
  async saveCheckIn(checkIn: CheckIn): Promise<void> {
    const checkIns = await this.getCheckIns();
    checkIns.push(checkIn);
    await AsyncStorage.setItem(KEYS.CHECK_INS, JSON.stringify(checkIns));
  }

  async getCheckIns(): Promise<CheckIn[]> {
    const data = await AsyncStorage.getItem(KEYS.CHECK_INS);
    if (!data) return [];
    
    const parsed = JSON.parse(data);
    // Convert date strings back to Date objects
    return parsed.map((c: any) => ({
      ...c,
      timestamp: new Date(c.timestamp)
    }));
  }

  async getCheckInsForDate(date: Date): Promise<CheckIn[]> {
    const allCheckIns = await this.getCheckIns();
    const dateStr = date.toDateString();
    return allCheckIns.filter(c => c.timestamp.toDateString() === dateStr);
  }

  // DAILY SCORES
  async saveDailyScores(scores: DailyScores): Promise<void> {
    const allScores = await this.getAllScores();
    const existingIndex = allScores.findIndex(
      s => s.date.toDateString() === scores.date.toDateString()
    );

    if (existingIndex >= 0) {
      allScores[existingIndex] = scores;
    } else {
      allScores.push(scores);
    }

    await AsyncStorage.setItem(KEYS.DAILY_SCORES, JSON.stringify(allScores));
  }

  async getAllScores(): Promise<DailyScores[]> {
    const data = await AsyncStorage.getItem(KEYS.DAILY_SCORES);
    if (!data) return [];
    
    const parsed = JSON.parse(data);
    return parsed.map((s: any) => ({
      ...s,
      date: new Date(s.date)
    }));
  }

  async getScoresForDate(date: Date): Promise<DailyScores | null> {
    const allScores = await this.getAllScores();
    return allScores.find(s => s.date.toDateString() === date.toDateString()) || null;
  }

  // DETAIL DATA
  async saveDetailData(date: Date, details: DetailData): Promise<void> {
    const allDetails = await this.getAllDetailData();
    const dateStr = date.toISOString().split('T')[0];
    
    allDetails[dateStr] = details;
    await AsyncStorage.setItem(KEYS.DETAIL_DATA, JSON.stringify(allDetails));
  }

  async getDetailData(date: Date): Promise<DetailData | null> {
    const allDetails = await this.getAllDetailData();
    const dateStr = date.toISOString().split('T')[0];
    return allDetails[dateStr] || null;
  }

  private async getAllDetailData(): Promise<Record<string, DetailData>> {
    const data = await AsyncStorage.getItem(KEYS.DETAIL_DATA);
    return data ? JSON.parse(data) : {};
  }

  // JOURNALS
  async saveJournal(journal: {
    id: string;
    date: Date;
    aiText: string;
    userEditedText?: string;
    userNotes?: string;
    tone: string;
    scores: any;
    isMeaningfulDay: boolean;
  }): Promise<void> {
    const journals = await this.getAllJournals();
    const existingIndex = journals.findIndex(j => j.id === journal.id);

    if (existingIndex >= 0) {
      journals[existingIndex] = journal;
    } else {
      journals.push(journal);
    }

    await AsyncStorage.setItem(KEYS.JOURNALS, JSON.stringify(journals));
  }

  async getAllJournals(): Promise<any[]> {
    const data = await AsyncStorage.getItem(KEYS.JOURNALS);
    if (!data) return [];
    
    const parsed = JSON.parse(data);
    return parsed.map((j: any) => ({
      ...j,
      date: new Date(j.date)
    }));
  }

  async getJournalForDate(date: Date): Promise<any | null> {
    const journals = await this.getAllJournals();
    return journals.find(j => j.date.toDateString() === date.toDateString()) || null;
  }

  // USER PREFERENCES
  async saveUserPreferences(prefs: Partial<UserPreferences>): Promise<void> {
    const current = await this.getUserPreferences();
    const updated = { ...current, ...prefs };
    await AsyncStorage.setItem(KEYS.USER_PREFERENCES, JSON.stringify(updated));
  }

  async getUserPreferences(): Promise<UserPreferences> {
    const data = await AsyncStorage.getItem(KEYS.USER_PREFERENCES);
    if (!data) {
      // Default preferences
      return {
        fulfillmentWeights: {
          body: 0.25,
          mind: 0.25,
          soul: 0.25,
          purpose: 0.25
        },
        bodyThreshold: 70,
        mindThreshold: 65,
        soulThreshold: 75,
        socialMinutesBaseline: 70,
        reminderTimes: {},
        antiGlitterEnabled: false,
        sparkleFilterLevel: 50
      };
    }
    return JSON.parse(data);
  }

  // WEEKLY INTENTIONS
  async saveWeeklyIntention(intention: WeeklyIntention): Promise<void> {
    const intentions = await this.getAllIntentions();
    const existingIndex = intentions.findIndex(i => i.id === intention.id);

    if (existingIndex >= 0) {
      intentions[existingIndex] = intention;
    } else {
      intentions.push(intention);
    }

    await AsyncStorage.setItem(KEYS.WEEKLY_INTENTIONS, JSON.stringify(intentions));
  }

  async getAllIntentions(): Promise<WeeklyIntention[]> {
    const data = await AsyncStorage.getItem(KEYS.WEEKLY_INTENTIONS);
    if (!data) return [];
    
    const parsed = JSON.parse(data);
    return parsed.map((i: any) => ({
      ...i,
      weekStart: new Date(i.weekStart),
      microMoves: i.microMoves.map((m: any) => ({
        ...m,
        completedDate: m.completedDate ? new Date(m.completedDate) : undefined
      }))
    }));
  }

  async getCurrentWeekIntention(): Promise<WeeklyIntention | null> {
    const intentions = await this.getAllIntentions();
    const now = new Date();
    
    return intentions.find(i => {
      const weekStart = new Date(i.weekStart);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 7);
      return now >= weekStart && now < weekEnd;
    }) || null;
  }

  // ONBOARDING STATUS
  async getOnboardingStatus(): Promise<boolean> {
    const status = await AsyncStorage.getItem('onboarding_complete');
    return status === 'true';
  }

  async setOnboardingStatus(complete: boolean): Promise<void> {
    await AsyncStorage.setItem('onboarding_complete', complete.toString());
  }

  // CLEAR ALL DATA (for testing or user delete)
  async clearAllData(): Promise<void> {
    const keys = Object.values(KEYS);
    await AsyncStorage.multiRemove(keys);
    // Also clear onboarding status
    await AsyncStorage.removeItem('onboarding_complete');
  }

  // EXPORT ALL DATA
  async exportAllData(): Promise<string> {
    const allData = {
      checkIns: await this.getCheckIns(),
      scores: await this.getAllScores(),
      journals: await this.getAllJournals(),
      intentions: await this.getAllIntentions(),
      preferences: await this.getUserPreferences(),
      exportDate: new Date().toISOString()
    };

    return JSON.stringify(allData, null, 2);
  }
}

export default StorageService;

